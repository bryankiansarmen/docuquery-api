from google import genai
import os
from loguru import logger

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = None

try:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("Successfully initialized Gemini API client")
except Exception as e:
    logger.error(f"Failed to initialize Gemini client: {e}")
