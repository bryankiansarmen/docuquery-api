# DocuQuery API

A lightweight FastAPI application that allows users to upload PDF documents and ask questions about their content using OpenRouter-hosted LLMs, with hybrid search, persistent vector storage, and caching.

## Features
- **Asynchronous PDF Processing**: Documents are processed in the background using **Redis Streams** and a dedicated worker, ensuring fast API responses.
- **Hybrid Search (RRF)**: Combines **Splade sparse search** and **vector similarity search** using **Chroma Cloud** (Reciprocal Rank Fusion) for superior retrieval accuracy, de-duplicating related sections from the same document via GroupBy.
- **Semantic Vector Search**: Stores embeddings in **Chroma Cloud** (client-side OpenRouter `bge-m3` dense + server-side Splade sparse embeddings) for fast context retrieval.
- **Hybrid Caching System**:
  - **Exact Cache**: Redis-based caching for identical questions with SHA-256 hashing, 1hr TTL.
  - **Semantic Cache**: Chroma Cloud-based caching for semantically similar questions using a similarity score threshold of 0.3.
- **Persistent Chat History**: Stores user-bot interactions in **MongoDB** using `motor` for asynchronous access, with 10-turn conversation context.
- **Contextual Q&A**: Uses an OpenRouter chat model (configurable via `OPENROUTER_CHAT_MODEL`, default `deepseek/deepseek-chat`) to generate answers while maintaining conversation state across sessions.
- **Resilient Sessions**: Recovers active document metadata from Redis if the application restarts.
- **Duplicate Document Detection**: SHA-256 fingerprinting prevents re-processing the same document.
- **Per-Key Rate Limiting**: Redis-backed fixed-window rate limiting per `X-API-Key` (falls back to client IP) enforced directly in the API.

## Tech Stack
- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous)
- **Background Worker**: Python-based worker using Redis Streams for job orchestration.
- **Hybrid Search Engine**: [Chroma Cloud](https://www.trychroma.com/) (dense + sparse with RRF)
- **Vector Search Engine**: [Chroma Cloud](https://www.trychroma.com/)
- **Document Store & Chat History**: [MongoDB](https://www.mongodb.com/) (Motor + PyMongo drivers)
- **Caching & Job Status**: [Redis](https://redis.io/)
- **PDF Processing**: [PyMuPDF](https://pymupdf.readthedocs.io/)
- **AI Model**: [OpenRouter](https://openrouter.ai/) chat completions (default: `deepseek/deepseek-chat`)
- **Embedding Model**: [OpenRouter `BAAI/bge-m3`](https://openrouter.ai/baai/bge-m3) (dense) + Splade (sparse) via Chroma Cloud
- **Logger**: [Loguru](https://github.com/Delgan/loguru)
- **Containerization**: [Docker](https://www.docker.com/)
- **Deployment**: [Render](https://render.com/) (Web Service + Background Worker)

## Getting Started

### Prerequisites
- Python 3.10+
- Redis, MongoDB, and a Chroma Cloud account (see Environment Variables below)

### Run Locally
1. **Clone the repository**
   ```bash
   git clone https://github.com/yourname/docuquery-api.git
   cd docuquery-api
   ```

2. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Open .env and add your OPENROUTER_API_KEY and APP_API_KEY
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the application**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   The API will be available at `http://localhost:8000`.

### Admin Interface
- **FastAPI Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## API Endpoints

| Method | Endpoint                        | Description                                           | Auth Required |
|--------|---------------------------------|-------------------------------------------------------|---------------|
| POST   | `/upload`                       | Upload a PDF document (Async - returns 202 + job_id)  | Yes           |
| GET    | `/upload/status/{job_id}`       | Check the processing status of a document             | Yes           |
| POST   | `/ask`                          | Ask a question about the uploaded document            | Yes           |
| GET    | `/documents`                    | List all uploaded documents metadata                  | Yes           |
| GET    | `/documents/{document_id}`      | Get specific document metadata                        | Yes           |

All endpoints require the `X-API-Key` header with the value of your `APP_API_KEY`.

Rate limits are enforced per `X-API-Key` (falling back to client IP) with a fixed window: **10 req/min** for `/upload`, **30 req/min** for `/ask`, and **60 req/min** for `/upload/status/*` and `/documents`. Set `RATE_LIMIT_ENABLED=false` to disable.

> [!TIP]
> Interactive API documentation (Swagger UI) is available at `http://localhost:8000/docs`.

## Environment Variables

| Variable              | Required | Description                                                                 |
|-----------------------|----------|-----------------------------------------------------------------------------|
| `OPENROUTER_API_KEY`  | **Yes**  | Your [OpenRouter API key](https://openrouter.ai/keys)                       |
| `OPENROUTER_CHAT_MODEL`| No      | Chat model for answer generation (default: `deepseek/deepseek-chat`)        |
| `OPENROUTER_EMBEDDING_MODEL`| No | Embedding model (default: `baai/bge-m3`)                      |
| `APP_API_KEY`         | **Yes**  | Secret key required for all endpoints (`X-API-Key` header)                  |
| `REDIS_HOST`          | No       | Hostname for Redis service (default: `redis` for Docker)                    |
| `REDIS_PORT`          | No       | Port for Redis service (default: `6379`)                                    |
| `RATE_LIMIT_ENABLED`   | No       | Per-key rate limiting (default: `true`)                                     |
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

## Deployment

Deployed to [Render](https://render.com/) using a Dockerfile-based **Web Service** for the FastAPI app and a **Background Worker** service running `python -m app.worker`.

The `Dockerfile` exposes the app on port `8000`; set `PORT` and the environment variables in the Render dashboard.

## Project Structure
```text
docuquery-api/
├── app/
│   ├── clients/         # External API clients
│   │   └── openrouter.py # OpenRouter API client (chat + bge-m3 embeddings)
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
│   │   ├── llm.py       # Prompt building & OpenRouter answer generation
│   │   ├── pdf.py       # PDF text extraction & chunking
│   │   ├── store.py     # In-memory document store
│   │   ├── stream.py    # Redis Stream job orchestration
│   │   └── vector.py    # Chroma Cloud hybrid search & semantic cache
│   ├── dependencies.py  # Shared FastAPI dependencies (API key auth)
│   ├── main.py          # FastAPI entry point with lifespan
│   ├── rate_limit.py    # Redis-backed per-key rate limiting
│   └── worker.py        # Background PDF processing worker
├── tests/               # Unit & Integration test suite
│   ├── db/              # Database interaction tests
│   ├── routes/          # API endpoint tests
│   ├── services/        # Service logic tests
│   ├── conftest.py      # Shared mocks & fixtures
│   ├── test_dependencies.py
│   ├── test_rate_limit.py
│   └── test_worker_integration.py # E2E background worker test
├── logs/                # Application log files (Loguru, 1-day rotation)
├── Dockerfile           # Docker configuration (python:3.14)
├── requirements.txt     # Python dependencies
├── pytest.ini           # Pytest configuration
├── .env.example         # Environment variable template
└── README.md            # You are here
```
