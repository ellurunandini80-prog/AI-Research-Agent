import streamlit as st
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
import google.generativeai as genai

from dotenv import load_dotenv
import os
 
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model_gemini = genai.GenerativeModel("gemini-3.5-flash")

# UI
st.title("🔬 AI Research Agent")
st.caption("Analyze research papers,technical documents,and reports using RAG + Gemini + FAISS")

# Sidebar
with st.sidebar:
    st.header("About")
    st.write("""
📄 Upload one or more PDFs

❓ Ask research questions

🔍 Semantic Search (RAG)

🧠 Gemini 3.5 Flash

⚡ FAISS Vector Search
""")

uploaded_files = st.file_uploader(
    "Upload a PDF(s)",
    type="pdf",
    accept_multiple_files=True
)
if uploaded_files:
    text = ""
    documents = []
    if uploaded_files:
       text = ""
       documents = []

    for uploaded_file in uploaded_files:
        pdf_reader = PdfReader(uploaded_file)

        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()

            if page_text:
                documents.append({
                    "text": page_text,
                    "page": page_num + 1,
                    "source": uploaded_file.name
                })

                text += page_text + "\n"
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunk_documents = []

    for doc in documents:
        chunks = text_splitter.split_text(doc["text"])

        for chunk in chunks:
            chunk_documents.append({
                "text": chunk,
                "page": doc["page"],
                "source": doc["source"]
            })
    chunks = [doc["text"] for doc in chunk_documents]
    
    if len(chunks) == 0:
            st.error("No text could be extracted from the uploaded PDFs.")
            st.stop()
    st.write("Text Length:", len(text))
    st.write("Chunks:", len(chunks))

    # Embeddings
    model = SentenceTransformer("all-MiniLM-L6-v2")

    embeddings = model.encode(chunks).astype("float32")

    # FAISS Index
    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)

    index.add(embeddings)

    st.success("Research Documents Indexed Successfully!")

    # Question Input
    question = st.text_input("Ask a Research Question")

    if question:

        query_embedding = model.encode([question]).astype("float32")

        D, I = index.search(query_embedding, k=3)

        selected_docs = [chunk_documents[i] for i in I[0]]

        context = "\n\n".join(
            [doc["text"] for doc in selected_docs]
        )
        prompt = f"""
            You are an AI Research Agent.

            Your job is to analyze research documents and provide accurate, well-structured answers.

            Instructions:
            1. Answer ONLY using the provided context.
            2. If information is missing, say:
            "The uploaded documents do not contain enough information to answer this question."
            3. Explain the answer in simple language.
            4. Use bullet points whenever possible.
            5. If applicable, mention important facts, definitions, advantages, disadvantages, or conclusions from the document.
            6. Do not make up information.

            Context:
            {context}

            Question:
            {question}
            """ 
        with st.spinner("Searching PDF..."):
            try:
                response = model_gemini.generate_content(prompt)

                st.subheader("Answer")
                st.write(response.text)
                st.markdown("### 📚 Sources")

                for doc in selected_docs:
                    st.write(f"📄 File: {doc['source']} | Page: {doc['page']}")
            
            except Exception as e:
                st.error(f"Error: {e}")
            with st.expander("View Source Chunks"):
                st.write(context)
