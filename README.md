# AI-Powered Document Q&A API

A lightweight FastAPI application that allows users to upload PDF documents and ask questions about their content using Google Gemini AI, with persistent vector storage and caching.

## Features
- **PDF Upload & Storage**: Extracts and chunks text using PyMuPDF and stores metadata in Redis and memory.
- **Semantic Vector Search**: Stores embeddings in [ChromaDB](https://www.trychroma.com/) for fast context retrieval.
- **Hybrid Caching System**: 
  - **Exact Cache**: Redis-based caching for identical questions and file associations.
  - **Semantic Cache**: ChromaDB-based caching for semantically similar questions using vector distance.
- **Persistent Chat History**: Stores user-bot interactions in [MongoDB](https://www.mongodb.com/) using `motor` for asynchronous access.
- **Contextual Q&A**: Uses Gemini 3 Flash to generate answers while maintaining conversation state across sessions.
- **Resilient Sessions**: Recovers active document metadata from Redis if the application restarts.

## Tech Stack
- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous for high performance)
- **Vector Search**: [ChromaDB](https://www.trychroma.com/)
- **Document Store & Chat History**: [MongoDB](https://www.mongodb.com/) (Motor driver)
- **Caching & Session State**: [Redis](https://redis.io/)
- **PDF Processing**: [PyMuPDF](https://pymupdf.readthedocs.io/)
- **AI Model**: [Google Gemini API](https://ai.google.dev/) (gemini-3-flash-preview)
- **Embedding Model**: `gemini-embedding-001`
- **Logger**: [Loguru](https://github.com/Delgan/loguru)
- **Containerization**: [Docker](https://www.docker.com/)

## Getting Started

### Prerequisites
- [Docker](https://www.docker.com/get-started/) & [Docker Compose](https://docs.docker.com/compose/install/)
- OR Python 3.10+ (Note: local setup requires running Chroma, Redis, and MongoDB separately)

### Run with Docker (Recommended)
1. **Clone the repository**
   ```bash
   git clone https://github.com/yourname/docuquery-api.git
   cd docuquery-api
   ```

2. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Open .env and add your GEMINI_API_KEY and other configuration
   ```

3. **Start the application**
   ```bash
   docker compose up --build
   ```
   The API will be available at `http://localhost:8000`.

### Admin Interfaces
When running via Docker Compose, you can access the following management UIs:
- **ChromaDB Admin**: [http://localhost:8082](http://localhost:8082)
- **Redis Commander**: [http://localhost:8081](http://localhost:8081)

## API Endpoints

| Method | Endpoint  | Description                                      | Auth Required |
|--------|-----------|--------------------------------------------------|---------------|
| POST   | `/upload` | Upload a PDF document                            | Yes           |
| POST   | `/ask`    | Ask a question about the uploaded document       | Yes           |

> [!TIP]
> Interactive API documentation (Swagger UI) is available at `http://localhost:8000/docs`.

## Environment Variables

| Variable         | Required | Description                                                                 |
|------------------|----------|-----------------------------------------------------------------------------|
| `GEMINI_API_KEY` | **Yes**  | Your Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `APP_API_KEY`    | **Yes**  | Secret key required for the `/ask` endpoint (X-API-Key header)              |
| `REDIS_HOST`     | No       | Hostname for Redis service (default: `redis` for Docker)                    |
| `REDIS_PORT`     | No       | Port for Redis service (default: `6379`)                                    |
| `CHROMA_HOST`    | No       | Hostname for ChromaDB service (default: `chromadb` for Docker)              |
| `CHROMA_PORT`    | No       | Port for ChromaDB service (default: `8000`)                                 |
| `MONGO_URL`      | **Yes**  | MongoDB connection string (default: `mongodb://mongodb:27017`)              |

## Project Structure
```text
docuquery-api/
├── app/
│   ├── db/              # Database connection logic
│   │   ├── chroma.py    # ChromaDB client
│   │   ├── mongo.py     # MongoDB client (motor)
│   │   └── redis.py     # Redis client
│   ├── routes/
│   │   ├── upload.py    # /upload endpoint
│   │   └── ask.py       # /ask endpoint
│   ├── services/
│   │   ├── pdf.py       # PDF processing logic
│   │   ├── gemini.py    # Gemini API integration
│   │   ├── vector.py    # ChromaDB indexing logic
│   │   ├── cache.py     # Semantic cache logic
│   │   ├── store.py     # Direct storage service
│   │   └── chat.py      # LLM chat interaction
│   ├── models/
│   │   └── schemas.py   # Pydantic models
│   ├── dependencies.py  # Shared FastAPI dependencies
│   └── main.py          # FastAPI entry point
├── logs/                # Application log files
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose orchestration
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── README.md            # You are here