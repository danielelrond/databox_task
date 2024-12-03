import pytest
import json
from app import app, marketstack_service, weatherstack_service, databox_service, tokens, Token
from werkzeug.security import gen_salt
from datetime import datetime, timedelta

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


@pytest.fixture
def access_token(client):
    response = client.post('/token/', json={
        'username': 'test_user',
        'password': 'password123'
    })
    assert response.status_code == 200
    data = response.get_json()
    return data['access_token']


def test_token_endpoint(client):
    response = client.post('/token/', json={
        'username': 'test_user',
        'password': 'password123'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data
    assert data['token_type'] == 'Bearer'
    assert data['expires_in'] == 3600
    assert data['scope'] == 'read write'

# Test for the /token endpoint with invalid credentials
def test_token_endpoint_invalid_credentials(client):
    response = client.post('/token/', json={
        'username': 'test_user',
        'password': 'wrong_password'
    })
    assert response.status_code == 401
    data = response.get_json()
    assert 'message' in data
    assert data['message'] == 'Invalid credentials'

# Test for stock metrics endpoint with valid token
def test_stock_metrics(client, mocker, access_token):
    mocker.patch.object(marketstack_service, 'fetch_metrics', return_value=[
        {
            "symbol": "AAPL",
            "average_closing_price": 150.25,
            "maximum_closing_price": 155.0,
            "minimum_closing_price": 145.0,
            "total_trading_volume": 123456789,
            "start_date": "2024-07-11",
            "end_date": "2024-11-29",
            "error": None
        }
    ])


    headers = {'Authorization': access_token}
    response = client.get('/stocks/?symbols=AAPL', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['symbol'] == 'AAPL'
    assert data[0]['average_closing_price'] == 150.25

# Test for weather metrics endpoint with valid token
def test_weather_metrics(client, mocker, access_token):
    mocker.patch.object(weatherstack_service, 'fetch_metrics', return_value=[
        {
            "city": "Ljubljana",
            "temperature": 2.0,
            "humidity": 85,
            "wind_speed": 5.0,
            "pressure": 1023,
            "error": None
        }
    ])


    headers = {'Authorization': access_token}
    response = client.get('/weather/?cities=Ljubljana', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['city'] == 'Ljubljana'
    assert data[0]['temperature'] == 2.0

# Test for invalid stock symbols
def test_invalid_stock_symbols(client, mocker, access_token):
    mocker.patch.object(marketstack_service, 'fetch_metrics', return_value=[
        {"symbol": "INVALID", "error": "No data available."}
    ])

    headers = {'Authorization': access_token}
    response = client.get('/stocks/?symbols=INVALID', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['symbol'] == "INVALID"
    assert "error" in data[0]
    assert data[0]['error'] == "No data available."

# Test for invalid weather cities
def test_invalid_weather_city(client, mocker, access_token):
    mocker.patch.object(weatherstack_service, 'fetch_metrics', return_value=[
        {"city": "InvalidCity", "error": "No weather data available."}
    ])

    headers = {'Authorization': access_token}
    response = client.get('/weather/?cities=InvalidCity', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['city'] == "InvalidCity"
    assert "error" in data[0]
    assert data[0]['error'] == "No weather data available."

# Test for unauthorized access to stock metrics
def test_stock_metrics_unauthorized(client, mocker):
    mocker.patch.object(marketstack_service, 'fetch_metrics', return_value=[])

    response = client.get('/stocks/?symbols=AAPL')

    assert response.status_code == 401

# Test for unauthorized access to weather metrics
def test_weather_metrics_unauthorized(client, mocker):
    mocker.patch.object(weatherstack_service, 'fetch_metrics', return_value=[])

    response = client.get('/weather/?cities=Ljubljana')

    assert response.status_code == 401

# Test for push metrics endpoint with valid token
def test_push_metrics(client, mocker, access_token):
    mocker.patch.object(marketstack_service, 'fetch_metrics', return_value=[
        {
            "symbol": "AAPL",
            "average_closing_price": 150.25,
            "maximum_closing_price": 155.0,
            "minimum_closing_price": 145.0,
            "total_trading_volume": 123456789,
            "start_date": "2024-07-11",
            "end_date": "2024-11-29",
            "error": None
        }
    ])
    mocker.patch.object(weatherstack_service, 'fetch_metrics', return_value=[
        {
            "city": "Ljubljana",
            "temperature": 2.0,
            "humidity": 85,
            "wind_speed": 5.0,
            "pressure": 1023,
            "error": None
        }
    ])
    mocker.patch.object(databox_service, 'push_metrics', return_value={
        "status": "success",
        "message": "Metrics pushed successfully"
    })

    headers = {'Authorization': access_token}
    response = client.post('/push/', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == 'Metrics pushed successfully'

# Test for unauthorized access to push metrics
def test_push_metrics_unauthorized(client):
    response = client.post('/push/')

    assert response.status_code == 401

# Test for expired token
def test_expired_token(client, mocker):
    token_string = gen_salt(32)
    expires_in = -3600 
    user = {'username': 'test_user', 'scope': 'read write'}
    token = Token(access_token=token_string, scope='read write', user=user, expires_in=expires_in)
    tokens[token_string] = token

    headers = {'Authorization': token_string}
    response = client.get('/stocks/', headers=headers)


    assert response.status_code == 401

# Test for default parameters (no symbols provided)
def test_stock_metrics_default_parameters(client, mocker, access_token):
    mocker.patch.object(marketstack_service, 'fetch_metrics', return_value=[
        {
            "symbol": "AAPL",
            "average_closing_price": 150.25,
            "maximum_closing_price": 155.0,
            "minimum_closing_price": 145.0,
            "total_trading_volume": 123456789,
            "start_date": "2024-07-11",
            "end_date": "2024-11-29",
            "error": None
        },
        {
            "symbol": "MSFT",
            "average_closing_price": 250.50,
            "maximum_closing_price": 260.0,
            "minimum_closing_price": 240.0,
            "total_trading_volume": 987654321,
            "start_date": "2024-07-11",
            "end_date": "2024-11-29",
            "error": None
        }
    ])


    headers = {'Authorization': access_token}
    response = client.get('/stocks/', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    symbols = [item['symbol'] for item in data]
    assert 'AAPL' in symbols
    assert 'MSFT' in symbols

# Test for default parameters (no cities provided)
def test_weather_metrics_default_parameters(client, mocker, access_token):
    mocker.patch.object(weatherstack_service, 'fetch_metrics', return_value=[
        {
            "city": "Ljubljana",
            "temperature": 2.0,
            "humidity": 85,
            "wind_speed": 5.0,
            "pressure": 1023,
            "error": None
        },
        {
            "city": "Maribor",
            "temperature": 3.0,
            "humidity": 80,
            "wind_speed": 6.0,
            "pressure": 1025,
            "error": None
        },
        {
            "city": "Ptuj",
            "temperature": 1.0,
            "humidity": 90,
            "wind_speed": 4.0,
            "pressure": 1022,
            "error": None
        }
    ])

    headers = {'Authorization': access_token}
    response = client.get('/weather/', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 3
    cities = [item['city'] for item in data]
    assert 'Ljubljana' in cities
    assert 'Maribor' in cities
    assert 'Ptuj' in cities

# Test for the presence of error key when there is an error
def test_stock_metrics_with_error(client, mocker, access_token):
    mocker.patch.object(marketstack_service, 'fetch_metrics', return_value=[
        {
            "symbol": "AAPL",
            "error": "API error: 500"
        }
    ])

    headers = {'Authorization': access_token}
    response = client.get('/stocks/?symbols=AAPL', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data[0]['symbol'] == 'AAPL'
    assert 'error' in data[0]
    assert data[0]['error'] == 'API error: 500'

# Test for the push endpoint with use_demo_data parameter
def test_push_metrics_with_demo_data(client, mocker, access_token):
    mocker.patch.object(marketstack_service, 'fetch_metrics')
    mocker.patch.object(weatherstack_service, 'fetch_metrics')

    mocker.patch.object(databox_service, 'push_metrics', return_value={
        "status": "success",
        "message": "Metrics pushed successfully"
    })

    headers = {'Authorization': access_token}
    response = client.post('/push/?use_demo_data=true', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == 'Metrics pushed successfully'
