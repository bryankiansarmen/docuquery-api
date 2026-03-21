# AI-Powered Document Q&A API

A lightweight FastAPI application that allows users to upload PDF documents and ask questions about their content using Google Gemini AI.

## Features
- **PDF Upload**: Extracts text from PDF documents using PyMuPDF.
- **Contextual Q&A**: leverages Gemini 3 Flash to answer questions based strictly on the uploaded document.
- **Fast & Efficient**: Built with FastAPI for high performance.
- **Docker Ready**: Easy deployment using Docker and Docker Compose.

## Tech Stack
- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **PDF Processing**: [PyMuPDF](https://pymupdf.readthedocs.io/)
- **AI Model**: [Google Gemini API](https://ai.google.dev/) (gemini-3-flash-preview)
- **Containerization**: [Docker](https://www.docker.com/)

## Getting Started

### Prerequisites
- [Docker](https://www.docker.com/get-started/) & [Docker Compose](https://docs.docker.com/compose/install/)
- OR Python 3.14+

### Run with Docker (Recommended)
1. **Clone the repository**
   ```bash
   git clone https://github.com/yourname/docuquery-api.git
   cd docuquery-api
   ```

2. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Open .env and add your GEMINI_API_KEY
   ```

3. **Start the application**
   ```bash
   docker compose up --build
   ```
   The API will be available at `http://localhost:8000`.

### Run Locally
1. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\Activate.ps1
   # Mac/Linux:
   source .venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server**
   ```bash
   fastapi dev app/main.py
   ```

## API Endpoints

| Method | Endpoint  | Description                                      |
|--------|-----------|--------------------------------------------------|
| POST   | `/upload` | Upload a PDF document                            |
| POST   | `/ask`    | Ask a question about the most recently uploaded PDF |

> [!TIP]
> Interactive API documentation is automatically generated at `http://localhost:8000/docs`.

## Environment Variables

| Variable         | Description                                      |
|------------------|--------------------------------------------------|
| `GEMINI_API_KEY` | Your Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey) |

## Project Structure
```text
docuquery-api/
├── app/
│   ├── main.py          # FastAPI app instance
│   ├── routes/
│   │   ├── upload.py    # /upload endpoint
│   │   └── ask.py       # /ask endpoint
│   ├── services/
│   │   ├── pdf.py       # PyMuPDF extraction logic
│   │   └── gemini.py    # Gemini API logic
│   └── models/
│       └── schemas.py   # Pydantic models
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose orchestration
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── README.md           # Project documentation
```
