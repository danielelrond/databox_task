# databox_task

This is a Flask-based application that integrates with external APIs to fetch metrics (e.g., stock and weather data) and push them to the Databox platform. The application uses OAuth2 to secure endpoints and includes comprehensive logging and Swagger documentation.

## **Features**
- OAuth2 authentication for secure access to all API endpoints.
- Integration with:
  - **Marketstack API** for stock metrics.
  - **Weatherstack API** for weather metrics.
- Push metrics to Databox.
- Periodic task scheduling (instructions provided below).
- Swagger documentation available at `/` for testing API endpoints.
- Dockerized for simple deployment.


# API Endpoints

- Authentication
    - POST /token/:
        - Generate an OAuth2 token.
          - Example credentials:
            - Username: test_user
            - Password: password123
  - Stock Metrics
    - GET /stocks/:
      - Fetch stock metrics by providing symbols (e.g., AAPL).
      - Example: GET /stocks/?symbols=AAPL,MSFT.
  - Weather Metrics
    - GET /weather/:
      - Fetch weather metrics by providing city names (e.g., Ljubljana).
      - Example: GET /weather/?cities=Ljubljana,Maribor.
  - Push Metrics
    - POST /push/:
      - Push stock and weather metrics to Databox.
      - Use use_demo_data=true to push demo data instead of live metrics.
     
# Steps to Run

- git clone "repository-url"
- cd "repository-folder"
- docker build -t flask-databox-app .
- docker run -d -p 5022:5022 -v $(pwd)/databox_push.log:/app/databox_push.log flask-databox-app
- Open your browser and navigate to http://0.0.0.0:5022.
- Explore the Swagger UI documentation for API details.
- run unit test with command pytest

# Architecture Overview

- Framework:
  - Flask with Flask-RESTx for a lightweight and extensible API framework.
  - Swagger documentation automatically generated for all endpoints.
- Service Classes:
  - Dedicated service classes for API integrations (e.g., Marketstack, Weatherstack, Databox).
  - Why: Modular, reusable, and easy to extend.
- OAuth2 Security:
  - Token-based authentication for secure access.
  - Why: Industry-standard security for APIs.
- Logging:
  - Console and file-based logging for error tracking and debugging.
  - Why: Transparent operations and audit trail.
- Dockerization:
  - Application is fully containerized for consistent deployment environments.
  - Why: Simplifies setup and deployment.

# Improvements

- To automate pushing metrics at regular intervals, we need to add:
  - Python Scheduler (schedule Library):
      - Lightweight and easy to set up directly within the Flask app.
- used celery, Task Queueing, fastAPI async, and Kubernetes for big data..
- Replace flat-file logging with a database like PostgreSQL or MongoDB.
- Store API keys, secrets, and configuration settings in .env files for easy modification.

# Live data from Push Metrics endpoint
- https://app.databox.com/datawall/09be6ac82daf37195d48a91bd8df01fe14183d0674dae57
- databox user: danielhari949@gmail.com
