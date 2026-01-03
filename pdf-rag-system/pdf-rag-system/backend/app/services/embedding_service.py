"""
Embedding Service - Handles vector embeddings with Hugging Face and FAISS.
"""

import logging
import os
import pickle
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import faiss
from sentence_transformers import SentenceTransformer
from flask import current_app
import threading

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a search result from FAISS."""
    chunk_id: str
    content: str
    score: float
    page_number: int
    document_id: str


class EmbeddingService:
    """Service for generating embeddings using Hugging Face models."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for model loading efficiency."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.model_name = os.getenv('HF_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        self.model = None
        self.dimension = 384  # Dimension for all-MiniLM-L6-v2
        self._initialized = True
    
    def _load_model(self):
        """Lazy load the embedding model."""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Embedding dimension: {self.dimension}")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        self._load_model()
        embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.astype('float32')
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generate embeddings for multiple texts efficiently."""
        self._load_model()
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True
        )
        return embeddings.astype('float32')
    
    def get_dimension(self) -> int:
        """Get the dimension of embeddings."""
        self._load_model()
        return self.dimension


class FAISSIndexManager:
    """Manages FAISS indices for vector search."""
    
    def __init__(self, index_path: str = None):
        self.index_path = index_path or os.getenv('FAISS_INDEX_PATH', '/tmp/faiss_indices')
        self.embedding_service = EmbeddingService()
        self.indices: Dict[str, faiss.Index] = {}
        self.metadata: Dict[str, Dict] = {}  # chunk_id -> metadata mapping
        
        # Ensure index directory exists
        os.makedirs(self.index_path, exist_ok=True)
    
    def create_index(self, document_id: str) -> faiss.Index:
        """Create a new FAISS index for a document."""
        dimension = self.embedding_service.get_dimension()
        
        # Use IndexFlatIP for cosine similarity (with normalized vectors)
        # For larger scale, use IndexIVFFlat or IndexHNSW
        index = faiss.IndexFlatIP(dimension)
        
        # Wrap with IDMap to track chunk IDs
        index = faiss.IndexIDMap(index)
        
        self.indices[document_id] = index
        self.metadata[document_id] = {}
        
        logger.info(f"Created FAISS index for document {document_id}")
        return index
    
    def add_embeddings(
        self,
        document_id: str,
        chunk_ids: List[str],
        embeddings: np.ndarray,
        chunk_metadata: List[Dict]
    ):
        """Add embeddings to the index with metadata."""
        if document_id not in self.indices:
            self.create_index(document_id)
        
        index = self.indices[document_id]
        
        # Generate numeric IDs for FAISS
        start_id = len(self.metadata.get(document_id, {}))
        numeric_ids = np.array(range(start_id, start_id + len(chunk_ids)), dtype='int64')
        
        # Add to index
        index.add_with_ids(embeddings, numeric_ids)
        
        # Store metadata mapping
        for i, (chunk_id, meta) in enumerate(zip(chunk_ids, chunk_metadata)):
            self.metadata[document_id][start_id + i] = {
                'chunk_id': chunk_id,
                **meta
            }
        
        logger.info(f"Added {len(chunk_ids)} embeddings to index {document_id}")
    
    def search(
        self,
        document_id: str,
        query: str,
        k: int = 5
    ) -> List[SearchResult]:
        """Search for similar chunks in a document's index."""
        if document_id not in self.indices:
            logger.warning(f"No index found for document {document_id}")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query)
        query_embedding = query_embedding.reshape(1, -1)
        
        # Search
        index = self.indices[document_id]
        scores, indices = index.search(query_embedding, k)
        
        # Build results
        results = []
        doc_metadata = self.metadata.get(document_id, {})
        
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # No result
                continue
            
            meta = doc_metadata.get(int(idx), {})
            if meta:
                results.append(SearchResult(
                    chunk_id=meta.get('chunk_id', ''),
                    content=meta.get('content', ''),
                    score=float(score),
                    page_number=meta.get('page_number', 0),
                    document_id=document_id
                ))
        
        return results
    
    def search_multiple_documents(
        self,
        document_ids: List[str],
        query: str,
        k: int = 5
    ) -> List[SearchResult]:
        """Search across multiple document indices."""
        all_results = []
        
        for doc_id in document_ids:
            results = self.search(doc_id, query, k)
            all_results.extend(results)
        
        # Sort by score and return top k
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:k]
    
    def save_index(self, document_id: str):
        """Save index and metadata to disk."""
        if document_id not in self.indices:
            return
        
        index_file = os.path.join(self.index_path, f"{document_id}.index")
        meta_file = os.path.join(self.index_path, f"{document_id}.meta")
        
        # Save FAISS index
        faiss.write_index(self.indices[document_id], index_file)
        
        # Save metadata
        with open(meta_file, 'wb') as f:
            pickle.dump(self.metadata.get(document_id, {}), f)
        
        logger.info(f"Saved index for document {document_id}")
    
    def load_index(self, document_id: str) -> bool:
        """Load index and metadata from disk."""
        index_file = os.path.join(self.index_path, f"{document_id}.index")
        meta_file = os.path.join(self.index_path, f"{document_id}.meta")
        
        if not os.path.exists(index_file) or not os.path.exists(meta_file):
            return False
        
        # Load FAISS index
        self.indices[document_id] = faiss.read_index(index_file)
        
        # Load metadata
        with open(meta_file, 'rb') as f:
            self.metadata[document_id] = pickle.load(f)
        
        logger.info(f"Loaded index for document {document_id}")
        return True
    
    def delete_index(self, document_id: str):
        """Delete index and metadata."""
        # Remove from memory
        if document_id in self.indices:
            del self.indices[document_id]
        if document_id in self.metadata:
            del self.metadata[document_id]
        
        # Remove files
        index_file = os.path.join(self.index_path, f"{document_id}.index")
        meta_file = os.path.join(self.index_path, f"{document_id}.meta")
        
        for f in [index_file, meta_file]:
            if os.path.exists(f):
                os.remove(f)
        
        logger.info(f"Deleted index for document {document_id}")
    
    def get_index_stats(self, document_id: str) -> Dict:
        """Get statistics about an index."""
        if document_id not in self.indices:
            return {}
        
        index = self.indices[document_id]
        return {
            'total_vectors': index.ntotal,
            'dimension': self.embedding_service.get_dimension(),
            'metadata_entries': len(self.metadata.get(document_id, {}))
        }


class GlobalIndexManager(FAISSIndexManager):
    """
    Manages a global FAISS index for cross-document search.
    Uses IndexIVF for efficient large-scale search.
    """
    
    def __init__(self, index_path: str = None, nlist: int = 100):
        super().__init__(index_path)
        self.nlist = nlist  # Number of clusters for IVF
        self.global_index = None
        self.global_metadata = {}
        self.is_trained = False
    
    def create_global_index(self, training_vectors: np.ndarray = None):
        """Create a global IVF index for large-scale search."""
        dimension = self.embedding_service.get_dimension()
        
        # Quantizer
        quantizer = faiss.IndexFlatIP(dimension)
        
        # IVF index
        self.global_index = faiss.IndexIVFFlat(quantizer, dimension, self.nlist, faiss.METRIC_INNER_PRODUCT)
        
        if training_vectors is not None and len(training_vectors) >= self.nlist:
            self.global_index.train(training_vectors)
            self.is_trained = True
            logger.info("Global index trained")
    
    def add_to_global_index(
        self,
        document_id: str,
        chunk_ids: List[str],
        embeddings: np.ndarray,
        chunk_metadata: List[Dict]
    ):
        """Add embeddings to the global index."""
        if self.global_index is None:
            self.create_global_index(embeddings)
        
        if not self.is_trained and len(embeddings) >= self.nlist:
            self.global_index.train(embeddings)
            self.is_trained = True
        
        if not self.is_trained:
            logger.warning("Global index not trained yet. Need more vectors.")
            return
        
        # Add to global index
        start_id = len(self.global_metadata)
        numeric_ids = np.array(range(start_id, start_id + len(chunk_ids)), dtype='int64')
        
        self.global_index.add_with_ids(embeddings, numeric_ids)
        
        # Store metadata
        for i, (chunk_id, meta) in enumerate(zip(chunk_ids, chunk_metadata)):
            self.global_metadata[start_id + i] = {
                'chunk_id': chunk_id,
                'document_id': document_id,
                **meta
            }
    
    def global_search(self, query: str, k: int = 10) -> List[SearchResult]:
        """Search across all documents in the global index."""
        if self.global_index is None or not self.is_trained:
            return []
        
        query_embedding = self.embedding_service.generate_embedding(query)
        query_embedding = query_embedding.reshape(1, -1)
        
        # Set number of probes for search quality
        self.global_index.nprobe = min(10, self.nlist)
        
        scores, indices = self.global_index.search(query_embedding, k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            
            meta = self.global_metadata.get(int(idx), {})
            if meta:
                results.append(SearchResult(
                    chunk_id=meta.get('chunk_id', ''),
                    content=meta.get('content', ''),
                    score=float(score),
                    page_number=meta.get('page_number', 0),
                    document_id=meta.get('document_id', '')
                ))
        
        return results
