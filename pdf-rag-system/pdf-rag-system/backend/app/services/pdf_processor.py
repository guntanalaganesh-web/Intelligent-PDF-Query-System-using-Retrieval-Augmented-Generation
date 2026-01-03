"""
PDF Processing Service - Handles PDF extraction, chunking, and preprocessing.
"""

import hashlib
import logging
import os
import tempfile
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class PDFChunk:
    """Represents a chunk of text from a PDF."""
    content: str
    page_number: int
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int


@dataclass
class PDFMetadata:
    """Metadata extracted from PDF."""
    title: Optional[str]
    author: Optional[str]
    subject: Optional[str]
    page_count: int
    file_size: int
    content_hash: str


class PDFProcessor:
    """Handles PDF text extraction and chunking."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, PDFMetadata]:
        """Extract text and metadata from a PDF file."""
        try:
            doc = fitz.open(pdf_path)
            
            # Extract metadata
            metadata = PDFMetadata(
                title=doc.metadata.get('title'),
                author=doc.metadata.get('author'),
                subject=doc.metadata.get('subject'),
                page_count=len(doc),
                file_size=os.path.getsize(pdf_path),
                content_hash=self._compute_file_hash(pdf_path)
            )
            
            # Extract text from all pages
            full_text = ""
            page_texts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                page_texts.append({
                    'page_number': page_num + 1,
                    'text': text,
                    'start_char': len(full_text)
                })
                full_text += text + "\n"
            
            doc.close()
            
            return full_text, metadata, page_texts
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
    
    def chunk_text(
        self,
        text: str,
        page_texts: List[Dict]
    ) -> List[PDFChunk]:
        """Split text into overlapping chunks with page tracking."""
        chunks = []
        
        # Clean and normalize text
        text = self._clean_text(text)
        
        if len(text) < self.min_chunk_size:
            # Document too small to chunk
            return [PDFChunk(
                content=text,
                page_number=1,
                chunk_index=0,
                start_char=0,
                end_char=len(text),
                token_count=self._estimate_tokens(text)
            )]
        
        # Create chunks with overlap
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size
            
            # Adjust to avoid cutting words
            if end < len(text):
                # Find nearest sentence or paragraph break
                break_point = self._find_break_point(text, end)
                if break_point > start:
                    end = break_point
            else:
                end = len(text)
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                # Determine page number for this chunk
                page_number = self._get_page_for_position(start, page_texts)
                
                chunks.append(PDFChunk(
                    content=chunk_text,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end,
                    token_count=self._estimate_tokens(chunk_text)
                ))
                chunk_index += 1
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start <= chunks[-1].start_char if chunks else 0:
                start = end  # Prevent infinite loop
        
        logger.info(f"Created {len(chunks)} chunks from document")
        return chunks
    
    def process_pdf(self, pdf_path: str) -> Tuple[List[PDFChunk], PDFMetadata]:
        """Complete PDF processing pipeline."""
        # Extract text and metadata
        full_text, metadata, page_texts = self.extract_text_from_pdf(pdf_path)
        
        # Create chunks
        chunks = self.chunk_text(full_text, page_texts)
        
        return chunks, metadata
    
    def process_pdf_from_bytes(self, pdf_bytes: bytes) -> Tuple[List[PDFChunk], PDFMetadata]:
        """Process PDF from bytes (for S3 downloads)."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = tmp_file.name
        
        try:
            return self.process_pdf(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might cause issues
        text = text.replace('\x00', '')
        
        # Normalize unicode
        import unicodedata
        text = unicodedata.normalize('NFKC', text)
        
        return text.strip()
    
    def _find_break_point(self, text: str, position: int) -> int:
        """Find a natural break point near the given position."""
        # Look for paragraph break first (within 200 chars)
        search_range = min(200, len(text) - position)
        
        # Check for paragraph breaks
        for i in range(search_range):
            if position + i < len(text) and text[position + i:position + i + 2] == '\n\n':
                return position + i + 2
        
        # Check for sentence breaks
        for i in range(search_range):
            if position + i < len(text):
                char = text[position + i]
                if char in '.!?' and (position + i + 1 >= len(text) or text[position + i + 1] == ' '):
                    return position + i + 1
        
        # Fall back to word break
        for i in range(search_range):
            if position + i < len(text) and text[position + i] == ' ':
                return position + i + 1
        
        return position
    
    def _get_page_for_position(self, char_position: int, page_texts: List[Dict]) -> int:
        """Determine which page a character position belongs to."""
        for i, page in enumerate(page_texts):
            if i + 1 < len(page_texts):
                if page_texts[i + 1]['start_char'] > char_position:
                    return page['page_number']
            else:
                return page['page_number']
        return 1
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Average English word is ~4-5 characters, 1 token ≈ 4 characters
        return len(text) // 4
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


class BatchPDFProcessor:
    """Process multiple PDFs in parallel."""
    
    def __init__(self, max_workers: int = 4):
        self.processor = PDFProcessor()
        self.max_workers = max_workers
    
    def process_batch(self, pdf_paths: List[str]) -> Dict[str, Tuple[List[PDFChunk], PDFMetadata]]:
        """Process multiple PDFs in parallel."""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self.processor.process_pdf, path): path
                for path in pdf_paths
            }
            
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    chunks, metadata = future.result()
                    results[path] = (chunks, metadata)
                except Exception as e:
                    logger.error(f"Error processing {path}: {str(e)}")
                    results[path] = None
        
        return results
