import os

BASE_URL = os.getenv("LOCUST_HOST", "http://localhost:8000")
API_KEY = os.environ["APP_API_KEY"]

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

SAMPLE_QUESTIONS = [
    "What is the main topic of this document?",
    "Can you summarize the key points?",
    "What are the conclusions?",
    "Who are the main authors mentioned?",
    "What methodology was used?",
]