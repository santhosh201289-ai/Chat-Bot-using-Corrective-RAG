import streamlit as st
from rag import ingest_pdf, ask

st.set_page_config(page_title="PDF RAG Chatbot", layout="wide")
st.title("📘 PDF RAG Chatbot")

if "chat" not in st.session_state:
    st.session_state.chat = []

# Upload PDFs
uploaded_files = st.file_uploader(
    "Upload PDFs",
    type="pdf",
    accept_multiple_files=True
)

if st.button("Index PDFs"):
    with st.spinner("Indexing PDFs..."):
        for pdf in uploaded_files:
            ingest_pdf(pdf, pdf.name)
    st.success("PDFs indexed successfully")

# Chat UI
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

question = st.chat_input("Ask a question from the PDFs")

if question:
    st.session_state.chat.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.spinner("Thinking..."):
        answer = ask(question, st.session_state.chat)

    st.session_state.chat.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.write(answer)
