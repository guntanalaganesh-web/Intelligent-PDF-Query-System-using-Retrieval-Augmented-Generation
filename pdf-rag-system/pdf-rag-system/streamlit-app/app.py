"""
Intelligent PDF Query System - Streamlit Interface
Alternative UI for document querying using Streamlit
"""

import streamlit as st
import requests
import os
from datetime import datetime
import time

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api/v1")
USER_ID = "streamlit-user"

# Page configuration
st.set_page_config(
    page_title="PDF Intelligence | RAG Query System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #3b82f6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem;
    }
    .stTextInput > div > div > input {
        background-color: #1e293b;
        border-color: #334155;
        color: white;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    .user-message {
        background: #3b82f6;
        color: white;
        margin-left: 2rem;
    }
    .assistant-message {
        background: #1e293b;
        border: 1px solid #334155;
        color: #e2e8f0;
        margin-right: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def api_request(method, endpoint, **kwargs):
    """Make API request with error handling."""
    headers = kwargs.pop('headers', {})
    headers['X-User-ID'] = USER_ID
    
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{endpoint}",
            headers=headers,
            **kwargs
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None


def upload_document(file):
    """Upload a document to the API."""
    files = {'file': (file.name, file.getvalue(), 'application/pdf')}
    return api_request('POST', '/documents', files=files)


def get_documents():
    """Get list of documents."""
    return api_request('GET', '/documents')


def query_document(document_id, query):
    """Query a document."""
    return api_request('POST', f'/documents/{document_id}/query', json={'query': query})


def delete_document(document_id):
    """Delete a document."""
    return api_request('DELETE', f'/documents/{document_id}')


# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'selected_document' not in st.session_state:
    st.session_state.selected_document = None


# Sidebar
with st.sidebar:
    st.markdown("### 📄 PDF Intelligence")
    st.markdown("*RAG-powered document querying*")
    st.markdown("---")
    
    # Document Upload
    st.markdown("#### Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload a PDF document to start querying"
    )
    
    if uploaded_file:
        if st.button("🚀 Process Document", use_container_width=True):
            with st.spinner("Processing document..."):
                result = upload_document(uploaded_file)
                if result and result.get('success'):
                    st.success(f"✅ Uploaded successfully! Created {result['chunks_created']} chunks.")
                    st.session_state.selected_document = result['document']['id']
                    st.rerun()
    
    st.markdown("---")
    
    # Document List
    st.markdown("#### Your Documents")
    docs_data = get_documents()
    
    if docs_data and docs_data.get('documents'):
        for doc in docs_data['documents']:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(
                    f"📄 {doc['filename'][:30]}...",
                    key=f"doc_{doc['id']}",
                    use_container_width=True
                ):
                    st.session_state.selected_document = doc['id']
                    st.session_state.messages = []
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{doc['id']}"):
                    delete_document(doc['id'])
                    st.rerun()
    else:
        st.info("No documents uploaded yet")
    
    st.markdown("---")
    
    # Stats
    st.markdown("#### Statistics")
    if docs_data:
        total_docs = docs_data.get('total', 0)
        total_pages = sum(d.get('page_count', 0) for d in docs_data.get('documents', []))
        st.metric("Documents", total_docs)
        st.metric("Total Pages", total_pages)


# Main Content
st.markdown('<h1 class="main-header">🔍 Intelligent PDF Query System</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Ask questions about your documents using AI-powered semantic search</p>', unsafe_allow_html=True)

if st.session_state.selected_document:
    # Get document info
    doc_info = api_request('GET', f'/documents/{st.session_state.selected_document}')
    
    if doc_info:
        # Document Info Bar
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**📄 Current Document:** {doc_info.get('filename', 'Unknown')}")
        with col2:
            st.markdown(f"**📖 Pages:** {doc_info.get('page_count', 'N/A')}")
        with col3:
            status = doc_info.get('processing_status', 'unknown')
            status_emoji = "✅" if status == "completed" else "⏳" if status == "processing" else "❌"
            st.markdown(f"**Status:** {status_emoji} {status}")
        
        st.markdown("---")
        
        # Chat Interface
        chat_container = st.container()
        
        with chat_container:
            # Display messages
            for message in st.session_state.messages:
                if message['role'] == 'user':
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <strong>You:</strong><br>{message['content']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message assistant-message">
                        <strong>🤖 Assistant:</strong><br>{message['content']}
                        {f"<br><br><em>Confidence: {message.get('confidence', 'N/A')}</em>" if 'confidence' in message else ""}
                    </div>
                    """, unsafe_allow_html=True)
        
        # Query Input
        st.markdown("---")
        
        query = st.text_input(
            "Ask a question about the document",
            placeholder="e.g., What are the main conclusions of this document?",
            key="query_input"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            submit = st.button("🔍 Search", type="primary", use_container_width=True)
        with col2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        if submit and query:
            # Add user message
            st.session_state.messages.append({
                'role': 'user',
                'content': query
            })
            
            # Get response
            with st.spinner("Searching document..."):
                start_time = time.time()
                result = query_document(st.session_state.selected_document, query)
                response_time = (time.time() - start_time) * 1000
            
            if result:
                # Add assistant message
                st.session_state.messages.append({
                    'role': 'assistant',
                    'content': result.get('answer', 'No response'),
                    'confidence': f"{result.get('confidence', 0) * 100:.1f}%",
                    'response_time': f"{response_time:.0f}ms"
                })
                
                # Show sources
                if result.get('sources'):
                    with st.expander("📚 View Sources"):
                        for i, source in enumerate(result['sources'], 1):
                            st.markdown(f"""
                            **Source {i}** (Page {source.get('page_number', 'N/A')}, Score: {source.get('score', 0):.2f})
                            
                            > {source.get('preview', 'No preview available')}
                            """)
            
            st.rerun()
        
        # Suggested Questions
        if len(st.session_state.messages) == 0:
            st.markdown("#### 💡 Suggested Questions")
            col1, col2 = st.columns(2)
            
            suggestions = [
                "What is the main topic of this document?",
                "Summarize the key points",
                "What are the conclusions?",
                "List any important dates mentioned"
            ]
            
            for i, suggestion in enumerate(suggestions):
                with col1 if i % 2 == 0 else col2:
                    if st.button(suggestion, key=f"suggest_{i}", use_container_width=True):
                        st.session_state.messages.append({
                            'role': 'user',
                            'content': suggestion
                        })
                        with st.spinner("Searching..."):
                            result = query_document(st.session_state.selected_document, suggestion)
                        if result:
                            st.session_state.messages.append({
                                'role': 'assistant',
                                'content': result.get('answer', 'No response'),
                                'confidence': f"{result.get('confidence', 0) * 100:.1f}%"
                            })
                        st.rerun()

else:
    # Welcome Screen
    st.markdown("""
    ### 👋 Welcome to PDF Intelligence!
    
    Get started by uploading a PDF document in the sidebar. Once uploaded, you can:
    
    - 🔍 **Ask questions** about your document in natural language
    - 📖 **Get accurate answers** with page references
    - ⚡ **Experience fast responses** with sub-200ms query times
    - 🤖 **Powered by GPT-3.5** and semantic search
    
    ---
    
    #### 🏗️ Architecture
    
    This system uses **RAG (Retrieval-Augmented Generation)**:
    
    1. **Document Processing**: PDF → Text chunks → Vector embeddings
    2. **Semantic Search**: FAISS index for fast similarity search
    3. **AI Generation**: OpenAI GPT-3.5 Turbo for answer synthesis
    
    ---
    
    #### 🚀 Tech Stack
    
    | Component | Technology |
    |-----------|------------|
    | Backend | Python Flask |
    | Embeddings | Hugging Face Sentence Transformers |
    | Vector Store | FAISS |
    | LLM | OpenAI GPT-3.5 Turbo |
    | Storage | AWS S3 |
    | Database | PostgreSQL |
    | Cache | Redis |
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #64748b;'>"
    "Built with ❤️ using Flask, React, FAISS, and OpenAI"
    "</div>",
    unsafe_allow_html=True
)
