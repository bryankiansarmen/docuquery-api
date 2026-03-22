# AI-Powered Document Q&A API

A lightweight FastAPI application that allows users to upload PDF documents and ask questions about their content using Google Gemini AI, with persistent vector storage and caching.

## Features
- **PDF Upload & Processing**: Extracts and chunks text from PDF documents using PyMuPDF.
- **Vector Search**: Stores document embeddings in [ChromaDB](https://www.trychroma.com/) for fast, semantic retrieval.
- **Contextual Q&A**: Leverages Gemini 3 Flash to answer questions based on relevant document context.
- **Result Caching**: Uses [Redis](https://redis.io/) to cache frequent questions and improve response times.
- **API Security**: Protected endpoints using API Key authentication.
- **Docker Ready**: Fully containerized setup with Docker Compose.

## Tech Stack
- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Vector Database**: [ChromaDB](https://www.trychroma.com/)
- **Cache**: [Redis](https://redis.io/)
- **PDF Processing**: [PyMuPDF](https://pymupdf.readthedocs.io/)
- **AI Model**: [Google Gemini API](https://ai.google.dev/) (gemini-3-flash-preview)
- **Containerization**: [Docker](https://www.docker.com/)

## Getting Started

### Prerequisites
- [Docker](https://www.docker.com/get-started/) & [Docker Compose](https://docs.docker.com/compose/install/)
- OR Python 3.10+ (Note: local setup requires running Chroma and Redis separately)

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
| POST   | `/upload` | Upload a PDF document                            | No            |
| POST   | `/ask`    | Ask a question about the uploaded document       | Yes           |

> [!TIP]
> Interactive API documentation (Swagger UI) is available at `http://localhost:8000/docs`.

## Environment Variables

| Variable         | Description                                                                 |
|------------------|-----------------------------------------------------------------------------|
| `GEMINI_API_KEY` | Your Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `APP_API_KEY`    | Secret key required for the `/ask` endpoint (X-API-Key header)              |
| `REDIS_HOST`     | Hostname for the Redis service (use `redis` for Docker)                     |
| `CHROMA_HOST`    | Hostname for the ChromaDB service (use `chromadb` for Docker)               |

## Project Structure
```text
docuquery-api/
├── app/
│   ├── main.py          # FastAPI app instance
│   ├── dependencies.py  # Auth and other dependencies
│   ├── routes/
│   │   ├── upload.py    # /upload endpoint
│   │   └── ask.py       # /ask endpoint
│   ├── services/
│   │   ├── pdf.py       # PDF processing logic
│   │   ├── gemini.py    # Gemini API integration
│   │   ├── vector.py    # ChromaDB integration
│   │   └── cache.py     # Redis caching logic
│   └── models/
│       └── schemas.py   # Pydantic models
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose orchestration
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── README.md           # Project documentation
```

