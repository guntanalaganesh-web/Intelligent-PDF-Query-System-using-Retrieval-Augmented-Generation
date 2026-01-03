"""
Database models for the PDF RAG system.
"""

from datetime import datetime
from app import db
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class User(db.Model):
    """User model for authentication and tracking."""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    documents = db.relationship('Document', backref='owner', lazy='dynamic')
    conversations = db.relationship('Conversation', backref='user', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }


class Document(db.Model):
    """Model for storing PDF document metadata."""
    __tablename__ = 'documents'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    s3_key = db.Column(db.String(512), nullable=False)
    s3_bucket = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger)
    page_count = db.Column(db.Integer)
    content_hash = db.Column(db.String(64), index=True)  # SHA-256 hash
    processing_status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Metadata
    title = db.Column(db.String(512))
    author = db.Column(db.String(255))
    subject = db.Column(db.Text)
    
    # FAISS index reference
    faiss_index_id = db.Column(db.String(36), index=True)
    
    # Relationships
    chunks = db.relationship('DocumentChunk', backref='document', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.original_filename,
            'file_size': self.file_size,
            'page_count': self.page_count,
            'processing_status': self.processing_status,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'title': self.title,
            'author': self.author
        }


class DocumentChunk(db.Model):
    """Model for storing document chunks and their embeddings metadata."""
    __tablename__ = 'document_chunks'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False, index=True)
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer)
    start_char = db.Column(db.Integer)
    end_char = db.Column(db.Integer)
    token_count = db.Column(db.Integer)
    embedding_id = db.Column(db.String(36))  # Reference to FAISS vector
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Index for fast lookup
    __table_args__ = (
        db.Index('idx_document_chunk', 'document_id', 'chunk_index'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'chunk_index': self.chunk_index,
            'content': self.content,
            'page_number': self.page_number,
            'token_count': self.token_count
        }


class Conversation(db.Model):
    """Model for storing conversation history."""
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), index=True)
    title = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy='dynamic', cascade='all, delete-orphan')
    document = db.relationship('Document', backref='conversations')
    
    def to_dict(self, include_messages=False):
        data = {
            'id': self.id,
            'document_id': self.document_id,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'message_count': self.messages.count()
        }
        if include_messages:
            data['messages'] = [m.to_dict() for m in self.messages.order_by(Message.created_at)]
        return data


class Message(db.Model):
    """Model for storing individual messages in conversations."""
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # RAG metadata
    context_chunks = db.Column(db.JSON)  # Store chunk IDs used for context
    confidence_score = db.Column(db.Float)
    tokens_used = db.Column(db.Integer)
    response_time_ms = db.Column(db.Integer)
    
    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'confidence_score': self.confidence_score,
            'response_time_ms': self.response_time_ms
        }


class QueryLog(db.Model):
    """Model for logging queries for analytics and monitoring."""
    __tablename__ = 'query_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), index=True)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), index=True)
    query_text = db.Column(db.Text, nullable=False)
    response_text = db.Column(db.Text)
    response_time_ms = db.Column(db.Integer)
    tokens_input = db.Column(db.Integer)
    tokens_output = db.Column(db.Integer)
    chunks_retrieved = db.Column(db.Integer)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Index for analytics queries
    __table_args__ = (
        db.Index('idx_query_log_date', 'created_at', 'success'),
    )
