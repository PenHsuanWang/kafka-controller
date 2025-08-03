# CodeX Agent Specification – Kafka Cluster Admin Backend

## ✨ Project Goal
Build and maintain a **FastAPI + kafka-python** backend that exposes REST
(`/api/v1/**`) and WebSocket (`/ws/v1/stream`) endpoints so a React UI can
observe & manage Kafka clusters (topics, consumer groups, brokers, KPIs).

---

## 🗂️ Directory Map

| Path                               | Purpose                                           |
| ---------------------------------- | ------------------------------------------------- |
| `server.py`                        | Entry-point (`python server.py` or `uvicorn …`)   |
| `app/api/`                         | **Interface layer** – routers & WebSocket manager |
| `app/core/`                        | Cross-cutting: config, JWT, RFC-7807 exceptions   |
| `app/domain/models/`               | Pydantic DTOs (Topic, ConsumerGroup, …)           |
| `app/domain/services/`             | Business logic (TopicService, …)                  |
| `app/infra/kafka/`                 | Adapters around `kafka-python`                    |

---

## ⚙️ How to Run

```bash
# dev
uvicorn server:app --reload               # hot-reload
# or
python server.py                          # same but via __main__ guard
````

> Requires Python 3.10+, `pip install -r requirements.txt`.

Kafka cluster defaults to `localhost:9092`; override via `.env`
(`KAFKA_ADMIN_BOOTSTRAP_SERVERS`).

---

## 🛠 Key Commands for CodeX

| Trigger phrase           | What the agent should do                                        |
| ------------------------ | --------------------------------------------------------------- |
| “**create router**”      | Scaffold a new file in `app/api/routers/`, add to `api_router`. |
| “**add service method**” | Edit the relevant file in `app/domain/services/`.               |
| “**update infra**”       | Touch `app/infra/kafka/` only; keep API layer unchanged.        |
| “**run tests**”          | Execute `pytest -q`.                                            |
| “**generate schema**”    | Call `app/core/config.get_settings().model_dump_schema()`.      |

---

## 🔒 Constraints

1. **Do not** import FastAPI inside domain or infra layers.
2. All HTTP errors must raise `ProblemDetailException`.
3. Use Pydantic v2 (`pattern=` not `regex=`, `field_validator` decorator).
4. One `KafkaAdminFacade` instance per cluster (cache via `lru_cache`).
5. WebSocket broadcast must stay non-blocking (timeout slow clients).

---

## 🧪 Testing Checklist

* `GET /api/v1/clusters` returns 200 JSON.
* WebSocket `ready` event arrives within 1 s of connect.
* `POST /topics` is idempotent (409 never thrown on duplicate).
* `POST /consumer-groups/{gid}/offsets:reset` with invalid body → 400 + RFC-7807 JSON.
* Unit tests: `pytest` green, coverage ≥ 85 %.

---

## 🚀 Future Tasks (Backlog)

1. **Pagination** for topic & consumer-group listings.
2. Replace in-memory `ConnectionManager` with Redis pub/sub for multi-worker.
3. JMX collection via Jolokia for broker CPU/disk metrics.
4. RBAC scopes (`viewer` / `operator` / `admin`) enforced in `require_jwt`.

---

## 🤖 Agent Persona

> *“I am the CodeX agent for the Kafka-Admin backend.
> I keep routers thin, services pure, and infra isolated.
> I respect PEP 8/257, type hints, and unit coverage.
> I never write frontend code—only Python backend.”*

---

Happy shipping! 🎉

