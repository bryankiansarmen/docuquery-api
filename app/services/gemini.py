from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    # This will be handled by the application startup or environment check
    pass

client = genai.Client(api_key=api_key)

def generate_answer(content: str, question: str):
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=f"""You are a helpful assistant. Answer the user's question based strictly on the document content below.
        <document>
        {content}
        </document>
        Question: {question}""",
    )
    return response.text
