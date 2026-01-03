import React from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  DocumentTextIcon,
  ChatBubbleLeftRightIcon,
  TrashIcon,
  ArrowLeftIcon,
  ClockIcon,
  DocumentDuplicateIcon,
  ServerStackIcon,
} from '@heroicons/react/24/outline';
import { documentApi } from '../services/api';
import toast from 'react-hot-toast';

function DocumentView() {
  const { documentId } = useParams();
  const navigate = useNavigate();

  const { data: document, isLoading } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => documentApi.get(documentId),
  });

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
      try {
        await documentApi.delete(documentId);
        toast.success('Document deleted successfully');
        navigate('/');
      } catch (error) {
        toast.error('Failed to delete document');
      }
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-dark-800 rounded w-1/3"></div>
        <div className="card">
          <div className="h-40 bg-dark-800 rounded"></div>
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="text-center py-12">
        <DocumentTextIcon className="w-16 h-16 text-dark-600 mx-auto mb-4" />
        <h2 className="text-xl font-medium text-white mb-2">Document not found</h2>
        <Link to="/" className="btn-primary">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/"
          className="p-2 text-dark-400 hover:text-white hover:bg-dark-800 rounded-lg transition-colors"
        >
          <ArrowLeftIcon className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white truncate">
            {document.filename}
          </h1>
          <p className="text-dark-400">
            Uploaded {formatDate(document.created_at)}
          </p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3">
        <Link
          to={`/documents/${documentId}/chat`}
          className="btn-primary flex items-center gap-2"
        >
          <ChatBubbleLeftRightIcon className="w-5 h-5" />
          Start Chat
        </Link>
        <button
          onClick={handleDelete}
          className="btn-secondary flex items-center gap-2 text-red-400 hover:text-red-300 hover:border-red-600/50"
        >
          <TrashIcon className="w-5 h-5" />
          Delete
        </button>
      </div>

      {/* Document Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card"
        >
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <DocumentTextIcon className="w-5 h-5 text-primary-400" />
            Document Details
          </h2>
          
          <dl className="space-y-4">
            <div className="flex justify-between">
              <dt className="text-dark-400">Filename</dt>
              <dd className="text-white font-medium truncate max-w-xs">
                {document.filename}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-dark-400">Pages</dt>
              <dd className="text-white font-medium">{document.page_count || 'Unknown'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-dark-400">File Size</dt>
              <dd className="text-white font-medium">{formatFileSize(document.file_size)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-dark-400">Status</dt>
              <dd>
                <span
                  className={`px-2 py-1 rounded-full text-sm ${
                    document.processing_status === 'completed'
                      ? 'bg-green-600/20 text-green-400'
                      : document.processing_status === 'processing'
                      ? 'bg-yellow-600/20 text-yellow-400'
                      : 'bg-red-600/20 text-red-400'
                  }`}
                >
                  {document.processing_status}
                </span>
              </dd>
            </div>
            {document.title && (
              <div className="flex justify-between">
                <dt className="text-dark-400">Title</dt>
                <dd className="text-white font-medium truncate max-w-xs">
                  {document.title}
                </dd>
              </div>
            )}
            {document.author && (
              <div className="flex justify-between">
                <dt className="text-dark-400">Author</dt>
                <dd className="text-white font-medium">{document.author}</dd>
              </div>
            )}
          </dl>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card"
        >
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <ServerStackIcon className="w-5 h-5 text-cyan-400" />
            Index Statistics
          </h2>
          
          {document.index_stats ? (
            <dl className="space-y-4">
              <div className="flex justify-between">
                <dt className="text-dark-400">Total Vectors</dt>
                <dd className="text-white font-medium">
                  {document.index_stats.total_vectors?.toLocaleString() || 0}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-dark-400">Embedding Dimension</dt>
                <dd className="text-white font-medium">
                  {document.index_stats.dimension || 384}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-dark-400">Index Type</dt>
                <dd className="text-white font-medium">FAISS FlatIP</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-dark-400">Embedding Model</dt>
                <dd className="text-white font-medium text-sm">
                  all-MiniLM-L6-v2
                </dd>
              </div>
            </dl>
          ) : (
            <p className="text-dark-400">No index statistics available</p>
          )}
        </motion.div>
      </div>

      {/* Processing Timeline */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card"
      >
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <ClockIcon className="w-5 h-5 text-yellow-400" />
          Processing Timeline
        </h2>
        
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-dark-700"></div>
          
          <div className="space-y-6 relative">
            <div className="flex gap-4 items-start">
              <div className="w-8 h-8 rounded-full bg-green-600/20 flex items-center justify-center z-10">
                <div className="w-3 h-3 rounded-full bg-green-400"></div>
              </div>
              <div>
                <p className="font-medium text-white">Document Uploaded</p>
                <p className="text-sm text-dark-400">{formatDate(document.created_at)}</p>
              </div>
            </div>

            {document.processed_at && (
              <div className="flex gap-4 items-start">
                <div className="w-8 h-8 rounded-full bg-primary-600/20 flex items-center justify-center z-10">
                  <div className="w-3 h-3 rounded-full bg-primary-400"></div>
                </div>
                <div>
                  <p className="font-medium text-white">Processing Completed</p>
                  <p className="text-sm text-dark-400">{formatDate(document.processed_at)}</p>
                </div>
              </div>
            )}

            <div className="flex gap-4 items-start">
              <div className="w-8 h-8 rounded-full bg-cyan-600/20 flex items-center justify-center z-10">
                <div className="w-3 h-3 rounded-full bg-cyan-400"></div>
              </div>
              <div>
                <p className="font-medium text-white">Ready for Queries</p>
                <p className="text-sm text-dark-400">FAISS index created and optimized</p>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default DocumentView;
