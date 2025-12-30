import os
import uuid
from dotenv import load_dotenv
from pypdf import PdfReader
import chromadb
from chromadb.config import Settings
from openai import OpenAI

load_dotenv()

# ---------------- CONFIG ----------------
EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4.1-mini"
TEMPERATURE = 0.2
CHROMA_DIR = "./chroma_db"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------- VECTOR DB ----------------
chroma = chromadb.Client(
    Settings(persist_directory=CHROMA_DIR, anonymized_telemetry=False)
)

collection = chroma.get_or_create_collection(name="pdf_rag")

# ---------------- PDF INGEST ----------------
def ingest_pdf(file, filename):
    reader = PdfReader(file)
    chunks = []
    metas = []

    full_text = ""

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if len(text.strip()) < 50:
            continue

        full_text += "\n" + text

        # chunk per page (bigger chunks)
        for i in range(0, len(text), 800):
            chunk = text[i:i+800]
            chunks.append(chunk)
            metas.append({
                "source": filename,
                "page": page_num
            })

    # 🔥 document-level overview chunk
    if len(full_text) > 500:
        chunks.append(full_text[:3000])
        metas.append({
            "source": filename,
            "page": "overview"
        })

    if not chunks:
        return False

    embeddings = embed_texts(chunks)

    collection.add(
        ids=[str(uuid.uuid4()) for _ in chunks],
        documents=chunks,
        metadatas=metas,
        embeddings=embeddings
    )

    return True

# ---------------- EMBEDDINGS ----------------
def embed_texts(texts):
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts
    )
    return [e.embedding for e in response.data]

# ---------------- RETRIEVAL ----------------
def retrieve(query, k=5):
    q_embed = embed_texts([query])[0]

    results = collection.query(
        query_embeddings=[q_embed],
        n_results=k
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    return docs, metas

# ---------------- CORRECTIVE RAG ----------------
def ask(question, chat_history):
    docs, metas = retrieve(question)

    # ❌ True fallback (only if NOTHING retrieved)
    if not docs:
        return "I could not find this information in the uploaded documents."

    context = "\n\n".join(docs)

    system_prompt = (
        "You are a strict PDF-based assistant.\n"
        "Answer ONLY using the provided context.\n"
        "If the answer is not explicitly present, say you cannot find it.\n"
    )

    messages = [{"role": "system", "content": system_prompt}]

    # memory
    for turn in chat_history[-6:]:
        messages.append(turn)

    messages.append({
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {question}"
    })

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=TEMPERATURE,
        messages=messages
    )

    return response.choices[0].message.content
