import os
import streamlit as st
from dotenv import load_dotenv

from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQAWithSourcesChain
from langchain_community.document_loaders import UnstructuredURLLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Streamlit UI
st.set_page_config(page_title="📘 ScholarBot – Research Assistant ")
st.title("🎓 ScholarBot – Ask Questions from Research Articles")
st.markdown("Choose input type: Paste article URLs or Upload a PDF")

# Choose input method
input_mode = st.radio("Select Input Method:", ["🔗 Use URLs", "📄 Upload PDF"])
VECTOR_DIR = "faiss_index_openai"

# Initialize OpenAI LLM
llm = ChatOpenAI(
    temperature=0.3,
    openai_api_key=OPENAI_API_KEY,
    model_name="gpt-3.5-turbo"
)

# Embeddings Model
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Process URLs
if input_mode == "🔗 Use URLs":
    urls = []
    for i in range(3):
        url = st.text_input(f"Article URL {i+1}")
        if url:
            urls.append(url)

    if st.button("📚 Process URLs") and urls:
        st.info("🔄 Loading articles from URLs...")
        loader = UnstructuredURLLoader(urls=urls)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=100)
        split_docs = splitter.split_documents(docs)

        vector_index = FAISS.from_documents(split_docs, embeddings)
        vector_index.save_local(VECTOR_DIR)
        st.success("✅ Vector index built from URLs!")

# Process PDF
elif input_mode == "📄 Upload PDF":
    uploaded_file = st.file_uploader("Upload a PDF (Max 5MB)", type=["pdf"])

    if uploaded_file:
        if uploaded_file.size > 5 * 1024 * 1024:
            st.error("❌ File too large. Please upload a PDF smaller than 5MB.")
        else:
            with open("uploaded.pdf", "wb") as f:
                f.write(uploaded_file.read())

            loader = PyPDFLoader("uploaded.pdf")
            docs = loader.load()

            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            split_docs = splitter.split_documents(docs)

            vector_index = FAISS.from_documents(split_docs, embeddings)
            vector_index.save_local(VECTOR_DIR)
            st.success("✅ Vector index built from PDF!")

# Ask questions
query = st.text_input("💬 Ask your academic question:")
if query:
    if os.path.exists(os.path.join(VECTOR_DIR, "index.faiss")):
        vectorstore = FAISS.load_local(VECTOR_DIR, embeddings, allow_dangerous_deserialization=True)

        chain = RetrievalQAWithSourcesChain.from_llm(llm=llm, retriever=vectorstore.as_retriever())
        result = chain.invoke({"question": query})

        st.subheader("📘 Answer")
        st.write(result["answer"])

        st.subheader("🔗 Sources")
        sources = result.get("sources", "")
        for source in sources.split("\n"):
            st.write("•", source.strip())

        if sources:
            st.subheader("📝 Suggested APA Citation(s)")
            for src in sources.split("\n"):
                st.write(f"{src.strip()} (n.d.). *Accessed from document or article link.*")
