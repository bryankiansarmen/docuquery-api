from fastapi import FastAPI
from app.routes import upload, ask
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="DocuQuery API")

# Include routers
app.include_router(upload.router)
app.include_router(ask.router)

@app.get("/")
async def root():
    return {"message": "Welcome to DocuQuery API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
