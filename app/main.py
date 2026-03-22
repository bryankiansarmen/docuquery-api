from fastapi import FastAPI
from app.routes import upload, ask
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

app = FastAPI(title="DocuQuery API")
logger.add("logs/app.log", rotation="1 day", level="INFO")

# Include routers
app.include_router(upload.router)
app.include_router(ask.router)
