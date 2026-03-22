from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    # This will be handled by the application startup or environment check
    pass

client = genai.Client(api_key=api_key)

def generate_answer(question: str, chunks: list[str], client):
    context = "\n\n".join(chunks)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=f"""Answer the question directly and concisely using the context provided.
        Do not say "based on the document", "according to the context", or any similar phrase.
        Just answer as if you already know the information.
        <context>
        {context}
        </context>
        Question: {question}""",
    )
    return response.text
