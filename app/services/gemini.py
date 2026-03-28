def build_prompt(question: str, chunks: list[str], history: list[dict]) -> str:
    context = "\n\n".join(chunks)
    history_text = ""
    for turn in history:
        history_text += f"User: {turn['question']}\nAssistant: {turn['answer']}\n\n"

    return f"""Answer the question directly using the context below.
    Do not say "based on the document" or similar phrases.

    <context>
    {context}
    </context>

    {f'<history>{history_text}</history>' if history_text else ''}

    Question: {question}"""

def generate_answer(question: str, chunks: list[str], history: list[dict], client):
    prompt = build_prompt(question, chunks, history)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return response.text
