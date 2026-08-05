# DocuQuery API

A lightweight FastAPI application that allows users to upload PDF documents and ask questions about their content using Google Gemini AI, with hybrid search, persistent vector storage, and caching.

## Features
- **Asynchronous PDF Processing**: Documents are processed in the background using **Redis Streams** and a dedicated worker, ensuring fast API responses.
- **Hybrid Search (RRF)**: Combines **Splade sparse search** and **vector similarity search** using **Chroma Cloud** (Reciprocal Rank Fusion) for superior retrieval accuracy, de-duplicating related sections from the same document via GroupBy.
- **Semantic Vector Search**: Stores embeddings in **Chroma Cloud** (server-side Qwen dense + Splade sparse embeddings) for fast context retrieval.
- **Hybrid Caching System**:
  - **Exact Cache**: Redis-based caching for identical questions with SHA-256 hashing, 1hr TTL.
  - **Semantic Cache**: Chroma Cloud-based caching for semantically similar questions using a similarity score threshold of 0.3.
- **Persistent Chat History**: Stores user-bot interactions in **MongoDB** using `motor` for asynchronous access, with 10-turn conversation context.
- **Contextual Q&A**: Uses **Google Gemini 3 Flash** to generate answers while maintaining conversation state across sessions.
- **Resilient Sessions**: Recovers active document metadata from Redis if the application restarts.
- **Duplicate Document Detection**: SHA-256 fingerprinting prevents re-processing the same document.

## Tech Stack
- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous)
- **Background Worker**: Python-based worker using Redis Streams for job orchestration.
- **Hybrid Search Engine**: [Chroma Cloud](https://www.trychroma.com/) (dense + sparse with RRF)
- **Vector Search Engine**: [Chroma Cloud](https://www.trychroma.com/)
- **Document Store & Chat History**: [MongoDB](https://www.mongodb.com/) (Motor + PyMongo drivers)
- **Caching & Job Status**: [Redis](https://redis.io/)
- **PDF Processing**: [PyMuPDF](https://pymupdf.readthedocs.io/)
- **AI Model**: [Google Gemini API](https://ai.google.dev/) (Gemini 3 Flash)
- **Embedding Model**: Server-side Qwen 3 Embedding (dense) + Splade (sparse) via Chroma Cloud
- **Logger**: [Loguru](https://github.com/Delgan/loguru)
- **API Gateway**: Spring Boot gateway with routing + rate limiting (separate repo)
- **Containerization**: [Docker](https://www.docker.com/)
- **Orchestration**: [Helm](https://helm.sh/) (Kubernetes deployment)
- **CI/CD**: [Jenkins](https://www.jenkins.io/) declarative pipeline
- **Load Testing**: [Locust](https://locust.io/)

## Getting Started

### Prerequisites
- [Docker](https://www.docker.com/get-started/) & [Docker Compose](https://docs.docker.com/compose/install/)
- OR Python 3.10+ (local setup requires running Redis, MongoDB, and a Chroma Cloud account separately)

### Run with Docker Compose (Recommended)
1. **Clone the repository**
   ```bash
   git clone https://github.com/yourname/docuquery-api.git
   cd docuquery-api
   ```

2. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Open .env and add your GEMINI_API_KEY and APP_API_KEY
   ```

3. **Start the application**
   ```bash
   docker compose up --build
   ```
   The API will be available at `http://localhost:8000`.

### Admin Interfaces
When running via Docker Compose, you can access the following management UIs:

| Service | URL |
|---------|-----|
| **FastAPI Swagger Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **Redis Commander** | [http://localhost:8081](http://localhost:8081) |

## API Endpoints

| Method | Endpoint                        | Description                                           | Auth Required |
|--------|---------------------------------|-------------------------------------------------------|---------------|
| POST   | `/upload`                       | Upload a PDF document (Async - returns 202 + job_id)  | Yes           |
| GET    | `/upload/status/{job_id}`       | Check the processing status of a document             | Yes           |
| POST   | `/ask`                          | Ask a question about the uploaded document            | Yes           |
| GET    | `/documents`                    | List all uploaded documents metadata                  | Yes           |
| GET    | `/documents/{document_id}`      | Get specific document metadata                        | Yes           |

All endpoints require the `X-API-Key` header with the value of your `APP_API_KEY`.

> [!TIP]
> Interactive API documentation (Swagger UI) is available at `http://localhost:8000/docs`.

## Environment Variables

| Variable              | Required | Description                                                                 |
|-----------------------|----------|-----------------------------------------------------------------------------|
| `GEMINI_API_KEY`      | **Yes**  | Your Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `APP_API_KEY`         | **Yes**  | Secret key required for all endpoints (`X-API-Key` header)                  |
| `REDIS_HOST`          | No       | Hostname for Redis service (default: `redis` for Docker)                    |
| `REDIS_PORT`          | No       | Port for Redis service (default: `6379`)                                    |
| `CHROMA_HOST`         | No       | Chroma Cloud hostname (default: `api.trychroma.com`)                        |
| `CHROMA_PORT`         | No       | Chroma Cloud port (default: `443`)                                          |
| `CHROMA_API_KEY`      | **Yes**  | API key for your Chroma Cloud tenant                                        |
| `CHROMA_TENANT`       | **Yes**  | Chroma Cloud tenant ID (e.g. from the console SDK snippet)                  |
| `CHROMA_DATABASE`     | No       | Chroma Cloud database name (default: `docuquery`)                           |
| `MONGO_URL`           | No       | Explicit MongoDB connection string override (overrides composed URI)        |
| `MONGO_HOST`          | No       | MongoDB host (default: `mongodb`; Atlas uses e.g. `cluster0.xxx.mongodb.net`) |
| `MONGO_PORT`          | No       | MongoDB port (default: `27017`)                                             |
| `MONGO_SRV`           | No       | Use `mongodb+srv` scheme when `true` (Atlas DNS-based clusters)             |
| `MONGO_USERNAME`      | No       | MongoDB username; combined with `MONGO_PASSWORD` to build the connection URI |
| `MONGO_PASSWORD`      | No       | MongoDB password                                                            |

## Testing

### Unit & Integration Tests

The project uses `pytest` with heavy mocking so tests run in isolation without needing active container instances.

```bash
pytest -v tests/
```

Coverage threshold is enforced at 80% minimum via `pytest.ini`.

### Load Testing (Locust)

Performance tests are located in `tests/locust/`. Two user classes simulate realistic traffic:

- **`DocuQueryUser`**: Uploads a document, then asks questions, tests cache hits, and tests duplicate uploads.
- **`GatewayUser`**: Tests traffic through the Spring Boot gateway at port 8080.

**Run locally (web UI):**
```bash
locust -f tests/locust/locustfile.py --host http://localhost:8000
# Open http://localhost:8089
```

**Run headless (CLI):**
```bash
locust -f tests/locust/locustfile.py \
  --host http://localhost:8000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 3m \
  --headless \
  --html locust-report.html
```

Configuration is in `tests/locust/config.py`. Override the test PDF path with `TEST_PDF_PATH` env var and the target host with `LOCUST_HOST`.

## CI/CD Pipeline

The Jenkinsfile defines a 6-stage declarative pipeline:

1. **Checkout** - pull source
2. **Run tests** - pytest with venv
3. **Performance Test** - Locust headless (50 users, 3-minute run, HTML + CSV reports archived)
4. **Build Docker image** - tagged with build number + `latest`
5. **Helm lint** - validate chart against dev values
6. **Deploy to dev** - `helm upgrade --install` with secrets from Jenkins credentials store, rollout verification

On failure the pipeline triggers `helm rollback` automatically.

## Project Structure
```text
docuquery-api/
├── app/
│   ├── clients/         # External API clients
│   │   └── gemini.py    # Gemini API client
│   ├── db/              # Database connection logic
│   │   ├── chroma.py    # Chroma Cloud client & schema
│   │   ├── mongo.py     # MongoDB client (motor + pymongo)
│   │   └── redis.py     # Redis client
│   ├── models/
│   │   └── schemas.py   # Pydantic models & JobStatus
│   ├── routes/
│   │   ├── ask.py       # /ask endpoint
│   │   ├── documents.py # /documents endpoints
│   │   └── upload.py    # /upload & /upload/status endpoints
│   ├── services/
│   │   ├── cache.py     # Redis exact-match caching
│   │   ├── chat.py      # MongoDB chat history
│   │   ├── document.py  # Document metadata service (MongoDB)
│   │   ├── gemini.py    # Gemini API integration
│   │   ├── pdf.py       # PDF text extraction & chunking
│   │   ├── store.py     # In-memory document store
│   │   ├── stream.py    # Redis Stream job orchestration
│   │   └── vector.py    # Chroma Cloud hybrid search & semantic cache
│   ├── dependencies.py  # Shared FastAPI dependencies (API key auth)
│   ├── main.py          # FastAPI entry point with lifespan
│   └── worker.py        # Background PDF processing worker
├── docuquery-api/       # Helm Chart for Kubernetes deployment
│   ├── templates/       # Chart templates (deployment, service, worker)
│   ├── values.yaml      # Default chart values
│   ├── values-dev.yaml  # Dev environment overrides
│   └── values-prod.yaml # Prod environment overrides
├── tests/               # Unit & Integration test suite
│   ├── db/              # Database interaction tests
│   ├── routes/          # API endpoint tests
│   ├── services/        # Service logic tests
│   ├── locust/          # Load testing (Locust)
│   │   ├── config.py    # Test configuration
│   │   ├── locustfile.py # User scenarios
│   │   └── sample.pdf   # Test document
│   ├── conftest.py      # Shared mocks & fixtures
│   ├── test_dependencies.py
│   └── test_worker_integration.py # E2E background worker test
├── logs/                # Application log files (Loguru, 1-day rotation)
├── Dockerfile           # Docker configuration (python:3.14)
├── Jenkinsfile          # CI/CD Pipeline configuration
├── docker-compose.yml   # Orchestration (API, Worker, Redis, Mongo, Gateway + admin UIs)
├── requirements.txt     # Python dependencies
├── pytest.ini           # Pytest configuration
├── .env.example         # Environment variable template
└── README.md            # You are here
```
