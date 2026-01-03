import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  DocumentTextIcon,
  CloudArrowUpIcon,
  ChatBubbleLeftRightIcon,
  ClockIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { documentApi } from '../services/api';
import toast from 'react-hot-toast';

function Dashboard() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentApi.list(),
  });

  const handleDelete = async (e, documentId) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (window.confirm('Are you sure you want to delete this document?')) {
      try {
        await documentApi.delete(documentId);
        toast.success('Document deleted successfully');
        refetch();
      } catch (error) {
        toast.error('Failed to delete document');
      }
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Your Documents</h1>
          <p className="mt-1 text-dark-400">
            Upload PDFs and ask questions using AI-powered search
          </p>
        </div>
        <Link to="/upload" className="btn-primary flex items-center gap-2">
          <CloudArrowUpIcon className="w-5 h-5" />
          Upload PDF
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-primary-600/20 rounded-xl">
              <DocumentTextIcon className="w-6 h-6 text-primary-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{data?.total || 0}</p>
              <p className="text-sm text-dark-400">Total Documents</p>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-600/20 rounded-xl">
              <ChatBubbleLeftRightIcon className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">
                {data?.documents?.reduce((sum, d) => sum + (d.page_count || 0), 0) || 0}
              </p>
              <p className="text-sm text-dark-400">Total Pages</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-cyan-600/20 rounded-xl">
              <ClockIcon className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">&lt;200ms</p>
              <p className="text-sm text-dark-400">Avg Response Time</p>
            </div>
          </div>
        </div>
      </div>

      {/* Documents Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-4 bg-dark-700 rounded w-3/4 mb-3"></div>
              <div className="h-3 bg-dark-700 rounded w-1/2 mb-4"></div>
              <div className="h-8 bg-dark-700 rounded"></div>
            </div>
          ))}
        </div>
      ) : data?.documents?.length > 0 ? (
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          initial="hidden"
          animate="visible"
          variants={{
            visible: { transition: { staggerChildren: 0.05 } },
          }}
        >
          {data.documents.map((doc) => (
            <motion.div
              key={doc.id}
              variants={{
                hidden: { opacity: 0, y: 20 },
                visible: { opacity: 1, y: 0 },
              }}
            >
              <Link to={`/documents/${doc.id}`} className="block">
                <div className="card-hover group">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-red-600/20 rounded-lg group-hover:bg-red-600/30 transition-colors">
                        <DocumentTextIcon className="w-5 h-5 text-red-400" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-medium text-white truncate">
                          {doc.filename}
                        </h3>
                        <p className="text-sm text-dark-400">
                          {doc.page_count} pages • {formatFileSize(doc.file_size)}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleDelete(e, doc.id)}
                      className="p-2 text-dark-500 hover:text-red-400 hover:bg-red-600/20 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div className="mt-4 pt-4 border-t border-dark-800 flex items-center justify-between">
                    <span className="text-xs text-dark-500">
                      {formatDate(doc.created_at)}
                    </span>
                    <span
                      className={`text-xs px-2 py-1 rounded-full ${
                        doc.processing_status === 'completed'
                          ? 'bg-green-600/20 text-green-400'
                          : doc.processing_status === 'processing'
                          ? 'bg-yellow-600/20 text-yellow-400'
                          : 'bg-red-600/20 text-red-400'
                      }`}
                    >
                      {doc.processing_status}
                    </span>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <div className="card text-center py-12">
          <DocumentTextIcon className="w-16 h-16 text-dark-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">No documents yet</h3>
          <p className="text-dark-400 mb-6">
            Upload your first PDF to start asking questions
          </p>
          <Link to="/upload" className="btn-primary inline-flex items-center gap-2">
            <CloudArrowUpIcon className="w-5 h-5" />
            Upload PDF
          </Link>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
