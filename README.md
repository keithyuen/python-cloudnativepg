# CloudNativePG FastAPI Demo

This demo application showcases how to work with CloudNativePG using FastAPI and SQLAlchemy. It demonstrates various features including connection to multiple database nodes, read/write operations, load balancing, and failover handling.

## Features

- FastAPI-based REST API
- Connection to multiple database nodes (primary/replica)
- Read/write operation examples
- Load balancing demonstration
- Failover handling
- Prometheus metrics integration
- Health check endpoint

## Prerequisites

- Python 3.8+
- CloudNativePG cluster
- Poetry or pip for dependency management

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your CloudNativePG cluster credentials
   ```
4. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Environment Variables

- `PRIMARY_DB_URL`: URL for the primary database node
- `REPLICA_DB_URL`: URL for the replica database node(s)
- `APP_NAME`: Application name (default: "cloudnativepg-demo")
- `APP_PORT`: Application port (default: 8000)

## API Endpoints

- `GET /health`: Health check endpoint
- `GET /metrics`: Prometheus metrics
- `POST /items`: Create a new item (writes to primary)
- `GET /items`: List all items (reads from replica)
- `GET /items/{id}`: Get specific item (reads from replica)
- `PUT /items/{id}`: Update an item (writes to primary)
- `DELETE /items/{id}`: Delete an item (writes to primary)

## Load Balancing

The application demonstrates load balancing by:
- Routing all write operations to the primary node
- Distributing read operations across replica nodes
- Handling failover scenarios automatically

## Monitoring

The application exposes Prometheus metrics at `/metrics` including:
- Request latency
- Database operation counters
- Connection pool statistics 