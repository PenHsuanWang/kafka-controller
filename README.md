# Kafka Controller Backend

## Overview

This repository provides a FastAPI-based backend for managing Kafka clusters. It exposes REST endpoints under `/api/v1` and a WebSocket stream at `/ws/v1/stream` for real-time metrics and events.

## Architecture

The codebase follows a layered design that separates web concerns from business logic and infrastructure access.

### Server entrypoint

`backend-server/server.py` builds the FastAPI application, registers routers and the WebSocket stream, adds problem detail error handling, and schedules a background metrics collector.

### API layer

`backend-server/app/api/` hosts the interface layer.

- `routers/` – REST routers for clusters, brokers, topics, and consumer groups are aggregated into a single `api_router`.
- `web_socket.py` – manages WebSocket connections and broadcasting.
- `dependencies.py` – reusable FastAPI dependencies such as JWT validation.

### Core layer

`backend-server/app/core/` supplies cross-cutting concerns including configuration via Pydantic settings and JWT helpers.

### Domain layer

`backend-server/app/domain/` contains Pydantic models that describe topics, clusters, brokers, consumer groups, and metric payloads. Service classes implement business logic and operate on these models.

### Infrastructure layer

`backend-server/app/infra/` wraps `kafka-python` operations. `KafkaAdminFacade` provides topic and cluster administration methods, while `lag.py` offers consumer lag utilities.

## Running the server

Install dependencies and run the development server:

```bash
pip install -r backend-server/requirements.txt
cd backend-server
uvicorn server:app --reload
```

The server expects a Kafka cluster at `localhost:9092`; override with the `KAFKA_ADMIN_BOOTSTRAP_SERVERS` environment variable.

