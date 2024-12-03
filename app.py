from flask import Flask, request, make_response, jsonify
from flask_restx import Api, Resource, fields
import requests
from datetime import datetime
import databox
from databox.rest import ApiException
from pprint import pprint
import logging
from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.oauth2.rfc6750 import BearerTokenValidator
from datetime import datetime, timedelta
from authlib.integrations.flask_oauth2 import ResourceProtector
from werkzeug.security import gen_salt

# Initialize Logging with File and Console Handlers
logger = logging.getLogger("databox_logger")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("databox_push.log")
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


app = Flask(__name__)


@app.before_request
def add_bearer_prefix():
    auth_header = request.headers.get('Authorization')
    if auth_header and not auth_header.lower().startswith('bearer '):
        request.environ['HTTP_AUTHORIZATION'] = 'Bearer ' + auth_header


app.secret_key = "solata-je-najboljsa"
require_oauth = ResourceProtector()



class Token:
    def __init__(self, access_token, scope, user, expires_in=3600):
        self.access_token = access_token
        self.scope = scope
        self.user = user
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        self.revoked = False

    def is_expired(self):
        return datetime.utcnow() >= self.expires_at

    def is_revoked(self):
        return self.revoked

    def get_scope(self):
        return self.scope





class MyBearerTokenValidator(BearerTokenValidator):
    def authenticate_token(self, token_string):
        logger.info(f"Authenticating token: {token_string}")
        token = tokens.get(token_string)
        if token and not token.is_expired():
            logger.info(f"Token is valid: {token_string}")
            return token
        else:
            logger.info(f"Token is invalid or expired: {token_string}")
        return None

    def get_token_scopes(self, token):
        logger.info(f"Getting scopes for token: {token.access_token}")
        return token.get_scope().split()


require_oauth.register_token_validator(MyBearerTokenValidator())



authorizations = {
    "BearerAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Enter your access token (without 'Bearer ' prefix)."
    }
}


api = Api(
    app,
    version="1.0",
    title="Metrics API",
    description="API for fetching stock and weather metrics and pushing to Databox",
    authorizations=authorizations,
    security="BearerAuth",
)


ns_token = api.namespace("token", description="get auth token")
ns_stock = api.namespace("stocks", description="Stock Metrics")
ns_weather = api.namespace("weather", description="Weather Metrics")
ns_push = api.namespace("push", description="Push Metrics to Databox")


users = {
    "test_user": {
        "username": "test_user",
        "password": "password123",
        "scope": "read write",
    }
}

clients = {
    "client_id": {
        "client_secret": "client_secret",
        "redirect_uris": [],
        "default_scopes": ["read", "write"],
    }
}

tokens = {} 



def get_user(username, password):
    user = users.get(username)
    if user and user["password"] == password:
        return user
    return None

# API Models for Swagger
stock_model = api.model(
    "StockMetrics",
    {
        "symbol": fields.String(description="Stock Symbol", example="AAPL"),
        "average_closing_price": fields.Float(description="Average Closing Price", example=232.45),
        "maximum_closing_price": fields.Float(description="Maximum Closing Price", example=234.82),
        "minimum_closing_price": fields.Float(description="Minimum Closing Price", example=228.52),
        "total_trading_volume": fields.Float(description="Total Trading Volume", example=123456789),
        "start_date": fields.String(description="Start Date", example="2024-07-11"),
        "end_date": fields.String(description="End Date", example="2024-11-29"),
        "error": fields.String(description="Error message if applicable", example="No data available", required=False),
    },
)

weather_model = api.model(
    "WeatherMetrics",
    {
        "city": fields.String(description="City Name", example="Ljubljana"),
        "temperature": fields.Float(description="Temperature in Celsius", example=2.0),
        "humidity": fields.Float(description="Humidity Percentage", example=85),
        "wind_speed": fields.Float(description="Wind Speed in km/h", example=5),
        "pressure": fields.Float(description="Atmospheric Pressure in hPa", example=1023),
        "error": fields.String(description="Error message if applicable", example="No weather data available", required=False),
    },
)

# Marketstack API Service
class MarketstackService:
    BASE_URL = "http://api.marketstack.com/v1/eod"

    def __init__(self, api_key):
        self.api_key = api_key

    def fetch_metrics(self, symbols, use_demo_data=False):
        if use_demo_data:
            return [
                {
                    "symbol": "AAPL",
                    "average_closing_price": 150.25,
                    "maximum_closing_price": 155.0,
                    "minimum_closing_price": 145.0,
                    "total_trading_volume": 123456789,
                    "start_date": "2024-07-11",
                    "end_date": "2024-11-29",
                },
                {
                    "symbol": "MSFT",
                    "average_closing_price": 280.75,
                    "maximum_closing_price": 285.0,
                    "minimum_closing_price": 275.0,
                    "total_trading_volume": 987654321,
                    "start_date": "2024-07-11",
                    "end_date": "2024-11-29",
                },
            ]

        metrics = []
        for symbol in symbols:
            params = {
                "access_key": self.api_key,
                "symbols": symbol,
                "limit": 100,
            }
            response = requests.get(self.BASE_URL, params=params)
            if response.status_code == 200:
                data = response.json().get("data", [])
                if data:
                    closing_prices = [entry["close"] for entry in data]
                    volumes = [entry["volume"] for entry in data]
                    dates = [entry["date"] for entry in data]

                    avg_close = sum(closing_prices) / len(closing_prices)
                    max_close = max(closing_prices)
                    min_close = min(closing_prices)
                    total_volume = sum(volumes)
                    start_date = dates[-1]
                    end_date = dates[0]

                    metrics.append({
                        "symbol": symbol,
                        "average_closing_price": avg_close,
                        "maximum_closing_price": max_close,
                        "minimum_closing_price": min_close,
                        "total_trading_volume": total_volume,
                        "start_date": start_date,
                        "end_date": end_date,
                    })
                else:
                    metrics.append({
                        "symbol": symbol,
                        "average_closing_price": None,
                        "maximum_closing_price": None,
                        "minimum_closing_price": None,
                        "total_trading_volume": None,
                        "start_date": None,
                        "end_date": None,
                        "error": "No data available."
                    })
            else:
                metrics.append({
                    "symbol": symbol,
                    "average_closing_price": None,
                    "maximum_closing_price": None,
                    "minimum_closing_price": None,
                    "total_trading_volume": None,
                    "start_date": None,
                    "end_date": None,
                    "error": f"API error: {response.status_code}"
                })
        return metrics


# Weatherstack API Service
class WeatherstackService:
    BASE_URL = "http://api.weatherstack.com/current"

    def __init__(self, api_key):
        self.api_key = api_key

    def fetch_metrics(self, cities, use_demo_data=False):
        if use_demo_data:
            return [
                {
                    "city": "Ljubljana",
                    "temperature": 10.5,
                    "humidity": 80,
                    "wind_speed": 5.5,
                    "pressure": 1015,
                    "error": None,
                },
                {
                    "city": "Maribor",
                    "temperature": 12.0,
                    "humidity": 75,
                    "wind_speed": 6.0,
                    "pressure": 1012,
                    "error": None,
                },
                {
                    "city": "Ptuj",
                    "temperature": 9.8,
                    "humidity": 85,
                    "wind_speed": 4.0,
                    "pressure": 1018,
                    "error": None,
                },
            ]

        metrics = []
        for city in cities:
            params = {"access_key": self.api_key, "query": city}
            response = requests.get(self.BASE_URL, params=params)
            if response.status_code == 200:
                data = response.json()
                if "current" in data:
                    current_weather = data["current"]
                    metrics.append({
                        "city": city,
                        "temperature": current_weather["temperature"],
                        "humidity": current_weather["humidity"],
                        "wind_speed": current_weather["wind_speed"],
                        "pressure": current_weather["pressure"],
                        "error": None
                    })
                else:
                    metrics.append({
                        "city": city,
                        "temperature": None,
                        "humidity": None,
                        "wind_speed": None,
                        "pressure": None,
                        "error": "No weather data available."
                    })
            else:
                metrics.append({
                    "city": city,
                    "temperature": None,
                    "humidity": None,
                    "wind_speed": None,
                    "pressure": None,
                    "error": f"API error: {response.status_code}"
                })
        return metrics


# Initialize Services
marketstack_service = MarketstackService(api_key="c32b7528eb6c362af369072db3732d0f")
weatherstack_service = WeatherstackService(api_key="c4502de93e1fda09055d6b0a347b97eb")

# Databox Push Service
class DataboxService:
    def __init__(self, api_token):
        configuration = databox.Configuration(
            host="https://push.databox.com",
            username=api_token,
            password=""
        )
        self.client = databox.ApiClient(configuration, "Accept", "application/vnd.databox.v2+json")

    def push_metrics(self, metrics):
        with self.client as api_client:
            api_instance = databox.DefaultApi(api_client)
            try:
                api_instance.data_post(push_data=metrics)

                logger.info(
                    f"Service: Databox, Metrics Sent: {len(metrics)}, "
                    f"Payload: {metrics}, Status: Success"
                )
                return {"status": "success", "message": "Metrics pushed successfully"}
            except ApiException as e:

                logger.error(
                    f"Service: Databox, Metrics Sent: {len(metrics)}, "
                    f"Payload: {metrics}, Status: Failure, Error: {e}"
                )
                return {"status": "error", "message": f"API Exception: {e}"}
            except Exception as e:
                logger.error(
                    f"Service: Databox, Metrics Sent: {len(metrics)}, "
                    f"Payload: {metrics}, Status: Failure, Error: {e}"
                )
                return {"status": "error", "message": f"Unexpected Error: {e}"}


databox_service = DataboxService(api_token="80c3cb33843d458d8df2690dea44be13")


# Push Data to Databox Endpoint
@ns_push.route("/")
class PushMetrics(Resource):
    @api.doc(params={
        "use_demo_data": "Set to 'true' to push predefined demo data to Databox"
    })
    @require_oauth('write')
    def post(self):
        """
        Push metrics (stock and weather) to Databox.
        """
        use_demo_data = request.args.get("use_demo_data", "false").lower() == "true"

        stock_metrics = marketstack_service.fetch_metrics(["AAPL", "MSFT"], use_demo_data=use_demo_data)

        weather_metrics = weatherstack_service.fetch_metrics(["Ljubljana", "Maribor", "Ptuj"], use_demo_data=use_demo_data)

        databox_data = []

        for metric in stock_metrics:
            if not metric.get("error"):
                databox_data.extend([
                    {"key": f"stock_{metric['symbol']}_avg_price", "value": metric["average_closing_price"]},
                    {"key": f"stock_{metric['symbol']}_max_price", "value": metric["maximum_closing_price"]},
                    {"key": f"stock_{metric['symbol']}_min_price", "value": metric["minimum_closing_price"]},
                    {"key": f"stock_{metric['symbol']}_total_volume", "value": metric["total_trading_volume"]},
                ])

        for metric in weather_metrics:
            if not metric.get("error"):
                databox_data.extend([
                    {"key": f"weather_{metric['city']}_temperature", "value": metric["temperature"]},
                    {"key": f"weather_{metric['city']}_humidity", "value": metric["humidity"]},
                    {"key": f"weather_{metric['city']}_wind_speed", "value": metric["wind_speed"]},
                    {"key": f"weather_{metric['city']}_pressure", "value": metric["pressure"]},
                ])


        logger.info(f"Preparing to push {len(databox_data)} metrics: {databox_data}")

        result = databox_service.push_metrics(databox_data)
        return result



@ns_stock.route("/")
class StockMetrics(Resource):
    @api.doc(params={
        "symbols": "Comma-separated list of stock symbols (e.g., AAPL,MSFT)",
        "use_demo_data": "Set to 'true' to fetch demo data instead of live data",
    })
    @require_oauth('read')
    @api.marshal_list_with(stock_model)
    def get(self):
        logger.debug(f"Request Headers: {dict(request.headers)}")
        symbols = request.args.get("symbols", "AAPL,MSFT").split(",")
        use_demo_data = request.args.get("use_demo_data", "false").lower() == "true"
        return marketstack_service.fetch_metrics(symbols, use_demo_data=use_demo_data)


@ns_weather.route("/")
class WeatherMetrics(Resource):
    @api.doc(params={
        "cities": "Comma-separated list of cities (e.g., Ljubljana,Maribor,Ptuj)",
        "use_demo_data": "Set to 'true' to fetch demo data instead of live data",
    })
    @require_oauth('read')
    @api.marshal_list_with(weather_model)
    def get(self):
        """
        Fetch weather metrics for the given cities.
        
        ### Instructions:
        - Use `cities` to specify the cities you want to fetch metrics for.
        - Add `use_demo_data=true` to fetch predefined demo data instead of live data.
        - Demo data simulates weather data for demonstration and testing purposes.
        """
        cities = request.args.get("cities", "Ljubljana,Maribor,Ptuj").split(",")
        use_demo_data = request.args.get("use_demo_data", "false").lower() == "true"
        return weatherstack_service.fetch_metrics(cities, use_demo_data=use_demo_data)



@ns_token.route("/")
@api.doc(description="""
Generate an access token.

### Instructions:
- Use this endpoint to obtain an access token.
- For testing purposes, you can use the following credentials:
  - **Username**: `test_user`
  - **Password**: `password123`

### Example Request:
```json
{
  "username": "test_user",
  "password": "password123"
}""")
class TokenEndpoint(Resource):
    @api.expect(api.model('TokenRequest', {
        'username': fields.String(required=True, description="Username for authentication"),
        'password': fields.String(required=True, description="Password for authentication"),
    }))
    def post(self):
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        user = get_user(username, password)
        if not user:
            return make_response(jsonify({"message": "Invalid credentials"}), 401)


        token_string = gen_salt(32)
        expires_in = 3600  
        token = Token(access_token=token_string, scope=user['scope'], user=user, expires_in=expires_in)
        tokens[token_string] = token


        logger.info(f"Generated Token: {token_string}, Tokens Stored: {list(tokens.keys())}")

        return jsonify({
            "access_token": token_string,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "scope": user['scope']
        })



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5022)
