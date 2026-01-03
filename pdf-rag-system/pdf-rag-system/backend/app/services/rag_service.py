"""
RAG Service - Retrieval-Augmented Generation with OpenAI GPT-3.5 Turbo.
"""

import logging
import os
import time
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass
import openai
from flask import current_app

from app.services.embedding_service import FAISSIndexManager, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Response from RAG query."""
    answer: str
    sources: List[Dict]
    confidence_score: float
    tokens_used: int
    response_time_ms: int
    model: str


class RAGService:
    """
    Retrieval-Augmented Generation service using OpenAI GPT-3.5 Turbo.
    Combines semantic search with LLM generation for intelligent document queries.
    """
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        self.index_manager = FAISSIndexManager()
        
        # Configure OpenAI client
        openai.api_key = self.api_key
        
        # RAG configuration
        self.max_context_chunks = 5
        self.max_context_tokens = 3000
        self.temperature = 0.7
        self.max_response_tokens = 1000
    
    def build_context(self, search_results: List[SearchResult]) -> str:
        """Build context string from search results."""
        context_parts = []
        total_tokens = 0
        
        for i, result in enumerate(search_results[:self.max_context_chunks]):
            # Estimate tokens (rough approximation)
            chunk_tokens = len(result.content) // 4
            
            if total_tokens + chunk_tokens > self.max_context_tokens:
                break
            
            context_parts.append(
                f"[Source {i+1}, Page {result.page_number}]:\n{result.content}"
            )
            total_tokens += chunk_tokens
        
        return "\n\n".join(context_parts)
    
    def create_prompt(self, query: str, context: str) -> List[Dict]:
        """Create the prompt for OpenAI API."""
        system_prompt = """You are an intelligent document assistant that answers questions based on the provided context from PDF documents.

Guidelines:
1. Answer questions accurately based ONLY on the provided context
2. If the context doesn't contain relevant information, say so clearly
3. Cite specific sources using [Source N] notation when referencing information
4. Be concise but comprehensive
5. If asked about something not in the context, acknowledge the limitation
6. Maintain a professional, helpful tone"""

        user_prompt = f"""Context from document:
{context}

Question: {query}

Please provide a detailed answer based on the context above. If the context doesn't contain sufficient information to answer the question, please indicate that."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def query(
        self,
        document_id: str,
        query: str,
        k: int = 5
    ) -> RAGResponse:
        """
        Process a query using RAG pipeline.
        
        1. Retrieve relevant chunks using semantic search
        2. Build context from retrieved chunks
        3. Generate response using OpenAI
        """
        start_time = time.time()
        
        # Step 1: Retrieve relevant chunks
        search_results = self.index_manager.search(document_id, query, k)
        
        if not search_results:
            return RAGResponse(
                answer="I couldn't find any relevant information in the document to answer your question. Please try rephrasing your question or ensure the document has been processed correctly.",
                sources=[],
                confidence_score=0.0,
                tokens_used=0,
                response_time_ms=int((time.time() - start_time) * 1000),
                model=self.model
            )
        
        # Step 2: Build context
        context = self.build_context(search_results)
        
        # Step 3: Generate response
        messages = self.create_prompt(query, context)
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_response_tokens,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # Calculate confidence based on search scores
            avg_score = sum(r.score for r in search_results) / len(search_results)
            confidence = min(avg_score, 1.0)
            
            # Build sources list
            sources = [
                {
                    'chunk_id': r.chunk_id,
                    'page_number': r.page_number,
                    'score': r.score,
                    'preview': r.content[:200] + '...' if len(r.content) > 200 else r.content
                }
                for r in search_results
            ]
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return RAGResponse(
                answer=answer,
                sources=sources,
                confidence_score=confidence,
                tokens_used=tokens_used,
                response_time_ms=response_time_ms,
                model=self.model
            )
            
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def query_stream(
        self,
        document_id: str,
        query: str,
        k: int = 5
    ) -> Generator[str, None, None]:
        """
        Stream query response for real-time UI updates.
        Yields chunks of the response as they're generated.
        """
        # Retrieve relevant chunks
        search_results = self.index_manager.search(document_id, query, k)
        
        if not search_results:
            yield "I couldn't find any relevant information in the document."
            return
        
        # Build context and prompt
        context = self.build_context(search_results)
        messages = self.create_prompt(query, context)
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_response_tokens,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.get('content'):
                    yield chunk.choices[0].delta.content
                    
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI streaming error: {str(e)}")
            yield f"Error generating response: {str(e)}"
    
    def query_with_history(
        self,
        document_id: str,
        query: str,
        conversation_history: List[Dict],
        k: int = 5
    ) -> RAGResponse:
        """
        Process query with conversation history for context-aware responses.
        """
        start_time = time.time()
        
        # Retrieve relevant chunks
        search_results = self.index_manager.search(document_id, query, k)
        
        if not search_results:
            return RAGResponse(
                answer="I couldn't find relevant information for this follow-up question.",
                sources=[],
                confidence_score=0.0,
                tokens_used=0,
                response_time_ms=int((time.time() - start_time) * 1000),
                model=self.model
            )
        
        # Build context
        context = self.build_context(search_results)
        
        # Build messages with history
        system_prompt = """You are an intelligent document assistant. Answer questions based on the provided document context and conversation history.

Guidelines:
1. Use the document context to answer questions accurately
2. Reference conversation history for context when relevant
3. Cite sources using [Source N] notation
4. Be concise and professional"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (limit to last 10 exchanges)
        for msg in conversation_history[-20:]:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        # Add current query with context
        messages.append({
            "role": "user",
            "content": f"Document Context:\n{context}\n\nQuestion: {query}"
        })
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_response_tokens
            )
            
            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            avg_score = sum(r.score for r in search_results) / len(search_results)
            
            sources = [
                {
                    'chunk_id': r.chunk_id,
                    'page_number': r.page_number,
                    'score': r.score,
                    'preview': r.content[:200] + '...'
                }
                for r in search_results
            ]
            
            return RAGResponse(
                answer=answer,
                sources=sources,
                confidence_score=min(avg_score, 1.0),
                tokens_used=tokens_used,
                response_time_ms=int((time.time() - start_time) * 1000),
                model=self.model
            )
            
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise


class ConversationManager:
    """Manages conversation state and history."""
    
    def __init__(self, max_history: int = 50):
        self.max_history = max_history
    
    def format_history_for_storage(self, messages: List[Dict]) -> List[Dict]:
        """Format messages for database storage."""
        return [
            {
                'role': msg['role'],
                'content': msg['content'],
                'timestamp': msg.get('timestamp')
            }
            for msg in messages[-self.max_history:]
        ]
    
    def truncate_history(self, messages: List[Dict], max_tokens: int = 2000) -> List[Dict]:
        """Truncate history to fit within token limits."""
        total_tokens = 0
        truncated = []
        
        # Keep most recent messages
        for msg in reversed(messages):
            msg_tokens = len(msg['content']) // 4
            if total_tokens + msg_tokens > max_tokens:
                break
            truncated.insert(0, msg)
            total_tokens += msg_tokens
        
        return truncated
