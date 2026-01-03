"""
API Routes - Flask REST API endpoints for the PDF RAG system.
"""

import logging
import os
import tempfile
import uuid
from datetime import datetime
from functools import wraps

from flask import Blueprint, request, jsonify, Response, stream_with_context, g
from werkzeug.utils import secure_filename

from app import db, cache, limiter
from app.models import User, Document, DocumentChunk, Conversation, Message, QueryLog
from app.services import (
    PDFProcessor, EmbeddingService, FAISSIndexManager, 
    RAGService, S3Service
)

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

# Services (initialized lazily)
pdf_processor = PDFProcessor()
embedding_service = EmbeddingService()
index_manager = FAISSIndexManager()
rag_service = RAGService()
s3_service = S3Service()


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}


def get_user_id():
    """Get user ID from request (simplified - add proper auth in production)."""
    return request.headers.get('X-User-ID', 'default-user')


def require_auth(f):
    """Authentication decorator (simplified)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        g.user_id = user_id
        return f(*args, **kwargs)
    return decorated


# ============== Document Endpoints ==============

@api_bp.route('/documents', methods=['POST'])
@require_auth
@limiter.limit("10 per minute")
def upload_document():
    """
    Upload and process a PDF document.
    
    Expects multipart/form-data with 'file' field.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    try:
        # Secure the filename
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{original_filename}"
        
        # Save temporarily for processing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        # Process PDF
        chunks, metadata = pdf_processor.process_pdf(tmp_path)
        
        # Upload to S3
        with open(tmp_path, 'rb') as f:
            s3_key = s3_service.upload_file(
                f, unique_filename, g.user_id,
                metadata={'page_count': str(metadata.page_count)}
            )
        
        # Create document record
        document = Document(
            user_id=g.user_id,
            filename=unique_filename,
            original_filename=original_filename,
            s3_key=s3_key,
            s3_bucket=s3_service.bucket_name,
            file_size=metadata.file_size,
            page_count=metadata.page_count,
            content_hash=metadata.content_hash,
            processing_status='processing',
            title=metadata.title,
            author=metadata.author,
            subject=metadata.subject
        )
        db.session.add(document)
        db.session.flush()  # Get the document ID
        
        # Generate embeddings
        chunk_texts = [c.content for c in chunks]
        embeddings = embedding_service.generate_embeddings_batch(chunk_texts)
        
        # Create chunk records and add to FAISS
        chunk_ids = []
        chunk_metadata = []
        
        for i, chunk in enumerate(chunks):
            chunk_record = DocumentChunk(
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                token_count=chunk.token_count
            )
            db.session.add(chunk_record)
            db.session.flush()
            
            chunk_ids.append(chunk_record.id)
            chunk_metadata.append({
                'content': chunk.content,
                'page_number': chunk.page_number
            })
        
        # Add to FAISS index
        index_manager.add_embeddings(
            document.id, chunk_ids, embeddings, chunk_metadata
        )
        index_manager.save_index(document.id)
        
        # Update document status
        document.processing_status = 'completed'
        document.processed_at = datetime.utcnow()
        document.faiss_index_id = document.id
        
        db.session.commit()
        
        # Cleanup temp file
        os.unlink(tmp_path)
        
        return jsonify({
            'success': True,
            'document': document.to_dict(),
            'chunks_created': len(chunks),
            'message': 'Document uploaded and processed successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uploading document: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/documents', methods=['GET'])
@require_auth
def list_documents():
    """List all documents for the current user."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    documents = Document.query.filter_by(user_id=g.user_id)\
        .order_by(Document.created_at.desc())\
        .paginate(page=page, per_page=per_page)
    
    return jsonify({
        'documents': [d.to_dict() for d in documents.items],
        'total': documents.total,
        'pages': documents.pages,
        'current_page': documents.page
    })


@api_bp.route('/documents/<document_id>', methods=['GET'])
@require_auth
def get_document(document_id):
    """Get details of a specific document."""
    document = Document.query.filter_by(
        id=document_id, user_id=g.user_id
    ).first_or_404()
    
    # Include index stats
    index_stats = index_manager.get_index_stats(document_id)
    
    doc_dict = document.to_dict()
    doc_dict['index_stats'] = index_stats
    
    return jsonify(doc_dict)


@api_bp.route('/documents/<document_id>', methods=['DELETE'])
@require_auth
def delete_document(document_id):
    """Delete a document and all associated data."""
    document = Document.query.filter_by(
        id=document_id, user_id=g.user_id
    ).first_or_404()
    
    try:
        # Delete from S3
        s3_service.delete_file(document.s3_key)
        
        # Delete FAISS index
        index_manager.delete_index(document_id)
        
        # Delete from database (cascades to chunks)
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Document deleted'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting document: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============== Query Endpoints ==============

@api_bp.route('/documents/<document_id>/query', methods=['POST'])
@require_auth
@limiter.limit("60 per minute")
def query_document(document_id):
    """
    Query a document using RAG.
    
    Request body: { "query": "your question" }
    """
    document = Document.query.filter_by(
        id=document_id, user_id=g.user_id
    ).first_or_404()
    
    if document.processing_status != 'completed':
        return jsonify({'error': 'Document is still being processed'}), 400
    
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    # Load index if not in memory
    if document_id not in index_manager.indices:
        if not index_manager.load_index(document_id):
            return jsonify({'error': 'Document index not found'}), 404
    
    try:
        # Execute RAG query
        response = rag_service.query(document_id, query)
        
        # Log query
        query_log = QueryLog(
            user_id=g.user_id,
            document_id=document_id,
            query_text=query,
            response_text=response.answer,
            response_time_ms=response.response_time_ms,
            tokens_input=response.tokens_used // 2,  # Rough estimate
            tokens_output=response.tokens_used // 2,
            chunks_retrieved=len(response.sources),
            success=True
        )
        db.session.add(query_log)
        db.session.commit()
        
        return jsonify({
            'answer': response.answer,
            'sources': response.sources,
            'confidence': response.confidence_score,
            'response_time_ms': response.response_time_ms,
            'model': response.model
        })
        
    except Exception as e:
        logger.error(f"Error querying document: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/documents/<document_id>/query/stream', methods=['POST'])
@require_auth
@limiter.limit("30 per minute")
def query_document_stream(document_id):
    """
    Query a document with streaming response.
    
    Returns Server-Sent Events (SSE) stream.
    """
    document = Document.query.filter_by(
        id=document_id, user_id=g.user_id
    ).first_or_404()
    
    if document.processing_status != 'completed':
        return jsonify({'error': 'Document is still being processed'}), 400
    
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    # Load index if needed
    if document_id not in index_manager.indices:
        index_manager.load_index(document_id)
    
    def generate():
        """Generator for SSE stream."""
        try:
            for chunk in rag_service.query_stream(document_id, query):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


# ============== Conversation Endpoints ==============

@api_bp.route('/documents/<document_id>/conversations', methods=['POST'])
@require_auth
def create_conversation(document_id):
    """Create a new conversation for a document."""
    document = Document.query.filter_by(
        id=document_id, user_id=g.user_id
    ).first_or_404()
    
    data = request.get_json() or {}
    
    conversation = Conversation(
        user_id=g.user_id,
        document_id=document_id,
        title=data.get('title', f"Conversation about {document.original_filename}")
    )
    
    db.session.add(conversation)
    db.session.commit()
    
    return jsonify(conversation.to_dict()), 201


@api_bp.route('/conversations/<conversation_id>/messages', methods=['POST'])
@require_auth
@limiter.limit("60 per minute")
def send_message(conversation_id):
    """
    Send a message in a conversation and get AI response.
    """
    conversation = Conversation.query.filter_by(
        id=conversation_id, user_id=g.user_id
    ).first_or_404()
    
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Load index if needed
    doc_id = conversation.document_id
    if doc_id not in index_manager.indices:
        index_manager.load_index(doc_id)
    
    try:
        # Save user message
        user_msg = Message(
            conversation_id=conversation_id,
            role='user',
            content=user_message
        )
        db.session.add(user_msg)
        
        # Get conversation history
        history = [
            {'role': m.role, 'content': m.content}
            for m in conversation.messages.order_by(Message.created_at).all()
        ]
        history.append({'role': 'user', 'content': user_message})
        
        # Generate response with history context
        response = rag_service.query_with_history(
            doc_id, user_message, history
        )
        
        # Save assistant message
        assistant_msg = Message(
            conversation_id=conversation_id,
            role='assistant',
            content=response.answer,
            context_chunks=[s['chunk_id'] for s in response.sources],
            confidence_score=response.confidence_score,
            tokens_used=response.tokens_used,
            response_time_ms=response.response_time_ms
        )
        db.session.add(assistant_msg)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'user_message': user_msg.to_dict(),
            'assistant_message': assistant_msg.to_dict(),
            'sources': response.sources
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/conversations/<conversation_id>', methods=['GET'])
@require_auth
def get_conversation(conversation_id):
    """Get a conversation with all messages."""
    conversation = Conversation.query.filter_by(
        id=conversation_id, user_id=g.user_id
    ).first_or_404()
    
    return jsonify(conversation.to_dict(include_messages=True))


@api_bp.route('/conversations', methods=['GET'])
@require_auth
def list_conversations():
    """List all conversations for the current user."""
    page = request.args.get('page', 1, type=int)
    document_id = request.args.get('document_id')
    
    query = Conversation.query.filter_by(user_id=g.user_id)
    
    if document_id:
        query = query.filter_by(document_id=document_id)
    
    conversations = query.order_by(Conversation.updated_at.desc())\
        .paginate(page=page, per_page=20)
    
    return jsonify({
        'conversations': [c.to_dict() for c in conversations.items],
        'total': conversations.total,
        'pages': conversations.pages
    })


# ============== Search Endpoints ==============

@api_bp.route('/search', methods=['POST'])
@require_auth
@limiter.limit("30 per minute")
def search_documents():
    """
    Search across multiple documents.
    """
    data = request.get_json()
    query = data.get('query', '').strip()
    document_ids = data.get('document_ids', [])
    k = data.get('k', 10)
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    # If no document IDs specified, search all user's documents
    if not document_ids:
        documents = Document.query.filter_by(
            user_id=g.user_id,
            processing_status='completed'
        ).all()
        document_ids = [d.id for d in documents]
    
    # Load indices
    for doc_id in document_ids:
        if doc_id not in index_manager.indices:
            index_manager.load_index(doc_id)
    
    # Search
    results = index_manager.search_multiple_documents(document_ids, query, k)
    
    return jsonify({
        'results': [
            {
                'document_id': r.document_id,
                'chunk_id': r.chunk_id,
                'content': r.content,
                'page_number': r.page_number,
                'score': r.score
            }
            for r in results
        ],
        'query': query,
        'documents_searched': len(document_ids)
    })


# ============== Analytics Endpoints ==============

@api_bp.route('/analytics/usage', methods=['GET'])
@require_auth
@cache.cached(timeout=300)
def get_usage_analytics():
    """Get usage analytics for the current user."""
    from sqlalchemy import func
    
    # Document stats
    doc_stats = db.session.query(
        func.count(Document.id).label('total_documents'),
        func.sum(Document.page_count).label('total_pages'),
        func.sum(Document.file_size).label('total_size')
    ).filter_by(user_id=g.user_id).first()
    
    # Query stats (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    query_stats = db.session.query(
        func.count(QueryLog.id).label('total_queries'),
        func.avg(QueryLog.response_time_ms).label('avg_response_time')
    ).filter(
        QueryLog.user_id == g.user_id,
        QueryLog.created_at >= thirty_days_ago
    ).first()
    
    return jsonify({
        'documents': {
            'total': doc_stats.total_documents or 0,
            'total_pages': doc_stats.total_pages or 0,
            'total_size_mb': round((doc_stats.total_size or 0) / (1024 * 1024), 2)
        },
        'queries': {
            'total_last_30_days': query_stats.total_queries or 0,
            'avg_response_time_ms': round(query_stats.avg_response_time or 0, 2)
        }
    })


from datetime import timedelta
