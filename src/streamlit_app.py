"""RAG File MCP Server - Streamlit Interface.

Provides a user-friendly web interface for:
- File uploads and document management
- Search testing
- Configuration viewing
- Log viewing and filtering
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from rag_core import RAGConfig, Retriever
from rag_core.chunking import FixedSizeChunker
from rag_core.embeddings import OllamaEmbedding
from rag_core.vectorstores.chroma import ChromaVectorStore

from src.file_parser import get_parser_for_file
from src.logging import setup_logging, LogManager, LogLevel, LogQuery

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="RAG File MCP Server",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern dark theme
st.markdown("""
<style>
    /* Dark glassmorphism theme */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    .main .block-container {
        padding-top: 2rem;
    }
    
    /* Cards with glassmorphism */
    .css-1r6slb0, .css-12oz5g7 {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Status indicators */
    .status-success {
        color: #00ff88;
        font-weight: bold;
    }
    .status-error {
        color: #ff4444;
        font-weight: bold;
    }
    .status-warning {
        color: #ffaa00;
        font-weight: bold;
    }
    
    /* Log level colors */
    .log-debug { color: #888; }
    .log-info { color: #4dabf7; }
    .log-warning { color: #ffd43b; }
    .log-error { color: #ff6b6b; }
    .log-critical { color: #ff0000; font-weight: bold; }
    
    /* Metric cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.08);
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# Initialize session state without retriever caching
if "config" not in st.session_state:
    st.session_state.config = None
if "log_manager" not in st.session_state:
    log_db_path = os.getenv("LOG_DB_PATH", "./data/logs.db")
    st.session_state.log_manager = LogManager(log_db_path)


def get_upload_dir() -> Path:
    """Get the upload directory path."""
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


async def get_retriever() -> Retriever:
    """Get a fresh retriever instance.
    
    We do not cache this in session_state because Streamlit's execution model
    combined with run_async creates new event loops, which causes issues with
    cached async clients (like httpx used by Ollama) bound to closed loops.
    """
    config = RAGConfig()
    # Update cached config
    st.session_state.config = config
    
    embedding = OllamaEmbedding(config)
    store = ChromaVectorStore(persist_dir=config.chroma_persist_dir)
    chunker = FixedSizeChunker(config)
    
    return Retriever(embedding, store, chunker)


def run_async(coro):
    """Run async coroutine in Streamlit."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Sidebar navigation
st.sidebar.title("📚 RAG File Server")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["📤 File Upload", "📁 Documents", "🔍 Search", "⚙️ Configuration", "📋 Logs"],
    label_visibility="collapsed",
)


# Page: File Upload
if page == "📤 File Upload":
    st.title("📤 File Upload")
    st.markdown("Upload PDF, TXT, MD, or RST files for RAG indexing.")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=["pdf", "txt", "md", "rst"],
        accept_multiple_files=True,
    )
    
    # Upload settings
    col1, col2 = st.columns(2)
    with col1:
        auto_ingest = st.checkbox("Auto-ingest after upload", value=True)
    with col2:
        max_size_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
        st.info(f"Max file size: {max_size_mb} MB")
    
    if uploaded_files:
        upload_dir = get_upload_dir()
        
        for uploaded_file in uploaded_files:
            # Check file size
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size_mb > max_size_mb:
                st.error(f"❌ {uploaded_file.name}: File too large ({file_size_mb:.1f} MB)")
                continue
            
            # Save file
            file_path = upload_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            st.success(f"✅ Uploaded: {uploaded_file.name}")
            
            # Auto-ingest
            if auto_ingest:
                with st.spinner(f"Ingesting {uploaded_file.name}..."):
                    try:
                        parser = get_parser_for_file(uploaded_file.name)
                        if parser:
                            parsed = parser.parse(file_path)
                            retriever = run_async(get_retriever())
                            
                            metadata = {
                                "source": str(file_path),
                                "filename": uploaded_file.name,
                                **parsed.metadata,
                            }
                            
                            ids = run_async(retriever.add_document(
                                text=parsed.text,
                                metadata=metadata,
                            ))
                            
                            st.info(f"📥 Ingested: {len(ids)} chunks from {uploaded_file.name}")
                        else:
                            st.warning(f"⚠️ No parser for {uploaded_file.name}")
                    except Exception as e:
                        st.error(f"❌ Failed to ingest {uploaded_file.name}: {e}")


# Page: Documents
elif page == "📁 Documents":
    st.title("📁 Document Management")
    
    upload_dir = get_upload_dir()
    files = list(upload_dir.iterdir()) if upload_dir.exists() else []
    files = [f for f in files if f.is_file()]
    
    # Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Uploaded Files", len(files))
    with col2:
        total_size = sum(f.stat().st_size for f in files) / (1024 * 1024)
        st.metric("Total Size", f"{total_size:.2f} MB")
    with col3:
        try:
            retriever = run_async(get_retriever())
            chunk_count = run_async(retriever.count())
            st.metric("Indexed Chunks", chunk_count)
        except Exception:
            st.metric("Indexed Chunks", "N/A")
    
    st.markdown("---")
    
    if files:
        for file_path in sorted(files):
            with st.expander(f"📄 {file_path.name}"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.text(f"Size: {file_path.stat().st_size / 1024:.1f} KB")
                    st.text(f"Type: {file_path.suffix}")
                
                with col2:
                    if st.button("👀 View Content", key=f"view_{file_path.name}"):
                        st.session_state[f"view_content_{file_path.name}"] = \
                            not st.session_state.get(f"view_content_{file_path.name}", False)
                    
                    if st.button("🔄 Re-index", key=f"reindex_{file_path.name}"):
                        with st.spinner("Re-indexing..."):
                            try:
                                parser = get_parser_for_file(file_path.name)
                                if parser:
                                    parsed = parser.parse(file_path)
                                    retriever = run_async(get_retriever())
                                    ids = run_async(retriever.add_document(
                                        text=parsed.text,
                                        metadata={"filename": file_path.name},
                                    ))
                                    st.success(f"Indexed {len(ids)} chunks")
                            except Exception as e:
                                st.error(f"Failed: {e}")
                
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{file_path.name}"):
                        file_path.unlink()
                        st.rerun()

            # Display content if toggled
            if st.session_state.get(f"view_content_{file_path.name}", False):
                with st.spinner("Loading content..."):
                    try:
                        parser = get_parser_for_file(file_path.name)
                        if parser:
                            parsed = parser.parse(file_path)
                            st.markdown("### Document Content")
                            st.text_area(
                                label="Content",
                                value=parsed.text,
                                height=400,
                                label_visibility="collapsed",
                                disabled=True,
                                key=f"content_{file_path.name}"
                            )
                        else:
                            st.warning("No parser available for this file type.")
                    except Exception as e:
                        st.error(f"Failed to read content: {e}")
    else:
        st.info("No files uploaded yet. Go to File Upload to add documents.")


# Page: Search
elif page == "🔍 Search":
    st.title("🔍 Search Documents")
    
    query = st.text_input("Enter search query", placeholder="Search for...")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        k = st.number_input("Results", min_value=1, max_value=20, value=5)
    with col2:
        search_button = st.button("🔍 Search", type="primary")
    
    if search_button and query:
        with st.spinner("Searching..."):
            try:
                retriever = run_async(get_retriever())
                results = run_async(retriever.search(query, k=k))
                
                st.markdown(f"### Found {len(results)} results")
                
                for i, result in enumerate(results, 1):
                    with st.expander(
                        f"Result {i} (Score: {result.score:.3f})",
                        expanded=i == 1
                    ):
                        st.markdown(result.text)
                        if result.metadata:
                            st.json(result.metadata)
                            
            except Exception as e:
                st.error(f"Search failed: {e}")
    
    elif search_button:
        st.warning("Please enter a search query")


# Page: Configuration
elif page == "⚙️ Configuration":
    st.title("⚙️ Configuration")
    
    config = RAGConfig()
    
    st.markdown("### Embedding Provider")
    col1, col2 = st.columns(2)
    with col1:
        st.text(f"Provider: {config.embedding_provider}")
    with col2:
        if config.embedding_provider == "ollama":
            st.text(f"Model: {config.ollama_model}")
            st.text(f"URL: {config.ollama_base_url}")
        else:
            st.text(f"Model: {config.openai_model}")
    
    st.markdown("### Vector Store")
    col1, col2 = st.columns(2)
    with col1:
        st.text(f"Type: {config.vector_store_type}")
    with col2:
        if config.vector_store_type == "chroma":
            st.text(f"Dir: {config.chroma_persist_dir}")
            st.text(f"Collection: {config.chroma_collection_name}")
    
    st.markdown("### Chunking")
    col1, col2 = st.columns(2)
    with col1:
        st.text(f"Chunk Size: {config.chunk_size}")
    with col2:
        st.text(f"Overlap: {config.chunk_overlap}")
    
    st.markdown("### File Upload")
    st.text(f"Upload Dir: {os.getenv('UPLOAD_DIR', './data/uploads')}")
    st.text(f"Max Size: {os.getenv('MAX_UPLOAD_SIZE_MB', '50')} MB")
    st.text(f"Extensions: {os.getenv('ALLOWED_EXTENSIONS', 'pdf,txt,md,rst')}")

    st.markdown("### Index Management")
    st.warning("⚠️ re-building the index completes clears and re-ingests all documents.")
    if st.button("🔴 Rebuild Index", type="secondary"):
        with st.spinner("Rebuilding index... This may take a while."):
            try:
                # Clear existing index in a dedicated async context
                async def clear_index():
                    r = await get_retriever()
                    await r.store.clear()
                
                run_async(clear_index())
                
                upload_dir = get_upload_dir()
                files = list(upload_dir.iterdir()) if upload_dir.exists() else []
                files = [f for f in files if f.is_file()]
                
                if not files:
                    st.warning("No files to ingest.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    success_count = 0
                    for i, file_path in enumerate(files):
                        status_text.text(f"Processing {file_path.name}...")
                        try:
                            # Define async task for single file ingestion
                            # ensuring retriever is created and used in the same loop
                            async def ingest_file():
                                parser = get_parser_for_file(file_path.name)
                                if parser:
                                    parsed = parser.parse(file_path)
                                    
                                    metadata = {
                                        "source": str(file_path),
                                        "filename": file_path.name,
                                        **parsed.metadata,
                                    }
                                    
                                    # Get fresh retriever in THIS loop
                                    r = await get_retriever()
                                    await r.add_document(
                                        text=parsed.text, 
                                        metadata=metadata
                                    )
                                    return True
                                return False
                                
                            if run_async(ingest_file()):
                                success_count += 1
                                
                        except Exception as e:
                            st.error(f"Failed {file_path.name}: {e}")
                        
                        progress_bar.progress((i + 1) / len(files))
                    
                    st.success(f"✅ Rebuild complete! Processed {success_count}/{len(files)} files.")
                    status_text.empty()
                    progress_bar.empty()
                    
            except Exception as e:
                st.error(f"Rebuild failed: {e}")


# Page: Logs
elif page == "📋 Logs":
    st.title("📋 Application Logs")
    
    log_manager: LogManager = st.session_state.log_manager
    
    # Filters in sidebar
    st.sidebar.markdown("### Log Filters")
    
    # Level filter
    selected_levels = st.sidebar.multiselect(
        "Log Levels",
        options=[l.value for l in LogLevel],
        default=["INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    
    # Logger filter
    try:
        logger_names = log_manager.get_logger_names()
        selected_loggers = st.sidebar.multiselect(
            "Loggers",
            options=logger_names,
            default=[],
        )
    except Exception:
        selected_loggers = []
    
    # Time filter
    time_range = st.sidebar.selectbox(
        "Time Range",
        ["Last Hour", "Last 24 Hours", "Last 7 Days", "All Time", "Custom"],
    )
    
    start_time = None
    end_time = None
    
    if time_range == "Last Hour":
        start_time = datetime.now() - timedelta(hours=1)
    elif time_range == "Last 24 Hours":
        start_time = datetime.now() - timedelta(days=1)
    elif time_range == "Last 7 Days":
        start_time = datetime.now() - timedelta(days=7)
    elif time_range == "Custom":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("Start Date")
            start_time = datetime.combine(start_date, datetime.min.time())
        with col2:
            end_date = st.date_input("End Date")
            end_time = datetime.combine(end_date, datetime.max.time())
    
    # Search
    search_text = st.text_input("🔍 Search in logs", placeholder="Search...")
    
    # Build query
    query = LogQuery(
        levels=[LogLevel(l) for l in selected_levels] if selected_levels else None,
        logger_names=selected_loggers if selected_loggers else None,
        start_time=start_time,
        end_time=end_time,
        search_text=search_text if search_text else None,
        limit=100,
    )
    
    # Control buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        refresh = st.button("🔄 Refresh")
    with col2:
        auto_refresh = st.checkbox("Auto-refresh (10s)")
    with col3:
        export_format = st.selectbox("Export", ["CSV", "JSON"], label_visibility="collapsed")
    with col4:
        if st.button("📥 Export"):
            try:
                if export_format == "CSV":
                    data = log_manager.export_csv(query)
                    st.download_button(
                        "Download CSV",
                        data,
                        "logs.csv",
                        "text/csv",
                    )
                else:
                    data = log_manager.export_json(query)
                    st.download_button(
                        "Download JSON",
                        data,
                        "logs.json",
                        "application/json",
                    )
            except Exception as e:
                st.error(f"Export failed: {e}")
    
    # Auto-refresh
    if auto_refresh:
        st.empty()
        import time
        time.sleep(10)
        st.rerun()
    
    # Stats
    try:
        stats = log_manager.get_stats()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Logs", stats.total_count)
        with col2:
            st.metric("Errors", stats.counts_by_level.get(LogLevel.ERROR, 0))
        with col3:
            st.metric("Warnings", stats.counts_by_level.get(LogLevel.WARNING, 0))
        with col4:
            st.metric("Info", stats.counts_by_level.get(LogLevel.INFO, 0))
    except Exception:
        pass
    
    st.markdown("---")
    
    # Display logs
    try:
        logs = log_manager.get_logs(query)
        
        if not logs:
            st.info("No logs found matching the filters.")
        else:
            for log in logs:
                level_class = f"log-{log.level.value.lower()}"
                
                # Format timestamp
                ts = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                # Create expander with level color
                with st.expander(
                    f"[{log.level.value}] {ts} - {log.logger_name}: {log.message[:80]}...",
                    expanded=log.level in [LogLevel.ERROR, LogLevel.CRITICAL],
                ):
                    st.markdown(f"**Level:** <span class='{level_class}'>{log.level.value}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Timestamp:** {ts}")
                    st.markdown(f"**Logger:** {log.logger_name}")
                    st.markdown(f"**Module:** {log.module}")
                    st.markdown(f"**Function:** {log.function}")
                    st.markdown("---")
                    st.markdown("**Message:**")
                    st.code(log.message)
                    
                    if log.exception:
                        st.markdown("**Exception:**")
                        st.code(log.exception)
                    
                    if log.extra_data:
                        st.markdown("**Extra Data:**")
                        st.json(log.extra_data)
                        
    except Exception as e:
        st.error(f"Failed to load logs: {e}")
    
    # Maintenance
    st.markdown("---")
    st.markdown("### Maintenance")
    
    col1, col2 = st.columns(2)
    with col1:
        retention_days = st.number_input(
            "Clear logs older than (days)",
            min_value=1,
            max_value=365,
            value=int(os.getenv("LOG_RETENTION_DAYS", "30")),
        )
        if st.button("🧹 Clear Old Logs"):
            try:
                deleted = log_manager.clear_old_logs(days=retention_days)
                st.success(f"Deleted {deleted} old log entries")
            except Exception as e:
                st.error(f"Failed to clear logs: {e}")
    
    with col2:
        st.warning("⚠️ Danger Zone")
        if st.button("🗑️ Clear All Logs", type="secondary"):
            try:
                deleted = log_manager.clear_all_logs()
                st.success(f"Deleted all {deleted} log entries")
            except Exception as e:
                st.error(f"Failed to clear logs: {e}")


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='text-align: center; color: #888; font-size: 0.8em;'>
        RAG File MCP Server v0.1.0<br/>
        Built with Streamlit & rag-core
    </div>
    """,
    unsafe_allow_html=True,
)
