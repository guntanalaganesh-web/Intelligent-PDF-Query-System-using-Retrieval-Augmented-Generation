import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CloudArrowUpIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { documentApi } from '../services/api';
import toast from 'react-hot-toast';

function Upload() {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback((acceptedFiles) => {
    const pdfFiles = acceptedFiles.filter(
      (file) => file.type === 'application/pdf'
    );
    
    if (pdfFiles.length !== acceptedFiles.length) {
      toast.error('Only PDF files are allowed');
    }

    const newFiles = pdfFiles.map((file) => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      progress: 0,
      status: 'pending',
      error: null,
    }));

    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
  });

  const uploadFile = async (fileItem) => {
    setFiles((prev) =>
      prev.map((f) =>
        f.id === fileItem.id ? { ...f, status: 'uploading' } : f
      )
    );

    try {
      const result = await documentApi.upload(fileItem.file, (progress) => {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileItem.id ? { ...f, progress } : f
          )
        );
      });

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id
            ? { ...f, status: 'completed', documentId: result.document.id }
            : f
        )
      );

      return result;
    } catch (error) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id
            ? { ...f, status: 'error', error: error.message }
            : f
        )
      );
      throw error;
    }
  };

  const handleUploadAll = async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending');
    
    if (pendingFiles.length === 0) {
      toast.error('No files to upload');
      return;
    }

    setUploading(true);

    for (const fileItem of pendingFiles) {
      try {
        await uploadFile(fileItem);
      } catch (error) {
        console.error('Upload failed:', error);
      }
    }

    setUploading(false);
    
    const completedCount = files.filter((f) => f.status === 'completed').length;
    if (completedCount > 0) {
      toast.success(`${completedCount} file(s) uploaded successfully`);
    }
  };

  const removeFile = (id) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const completedFiles = files.filter((f) => f.status === 'completed');
  const pendingFiles = files.filter((f) => f.status === 'pending');

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Upload Documents</h1>
        <p className="mt-1 text-dark-400">
          Upload PDF files to enable AI-powered document querying
        </p>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`card cursor-pointer transition-all duration-300 ${
          isDragActive
            ? 'border-primary-500 bg-primary-600/10'
            : 'border-dashed border-dark-600 hover:border-dark-500'
        }`}
      >
        <input {...getInputProps()} />
        <div className="text-center py-12">
          <motion.div
            animate={{ y: isDragActive ? -10 : 0 }}
            transition={{ type: 'spring', stiffness: 300 }}
          >
            <CloudArrowUpIcon
              className={`w-16 h-16 mx-auto mb-4 ${
                isDragActive ? 'text-primary-400' : 'text-dark-500'
              }`}
            />
          </motion.div>
          <h3 className="text-xl font-medium text-white mb-2">
            {isDragActive ? 'Drop files here' : 'Drag & drop PDF files'}
          </h3>
          <p className="text-dark-400 mb-4">or click to browse</p>
          <p className="text-sm text-dark-500">Maximum file size: 50MB</p>
        </div>
      </div>

      {/* File List */}
      <AnimatePresence>
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-4"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-white">
                Files ({files.length})
              </h2>
              {pendingFiles.length > 0 && (
                <button
                  onClick={handleUploadAll}
                  disabled={uploading}
                  className="btn-primary flex items-center gap-2"
                >
                  {uploading ? (
                    <>
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <CloudArrowUpIcon className="w-5 h-5" />
                      Upload All ({pendingFiles.length})
                    </>
                  )}
                </button>
              )}
            </div>

            <div className="space-y-3">
              {files.map((fileItem) => (
                <motion.div
                  key={fileItem.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="card flex items-center gap-4"
                >
                  <div className="p-2 bg-red-600/20 rounded-lg">
                    <DocumentTextIcon className="w-6 h-6 text-red-400" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white truncate">
                      {fileItem.file.name}
                    </p>
                    <p className="text-sm text-dark-400">
                      {formatFileSize(fileItem.file.size)}
                    </p>
                    
                    {fileItem.status === 'uploading' && (
                      <div className="mt-2">
                        <div className="h-1.5 bg-dark-700 rounded-full overflow-hidden">
                          <motion.div
                            className="h-full bg-primary-500"
                            initial={{ width: 0 }}
                            animate={{ width: `${fileItem.progress}%` }}
                          />
                        </div>
                        <p className="text-xs text-dark-400 mt-1">
                          {fileItem.progress}% uploaded
                        </p>
                      </div>
                    )}

                    {fileItem.status === 'error' && (
                      <p className="text-sm text-red-400 mt-1">
                        {fileItem.error || 'Upload failed'}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {fileItem.status === 'pending' && (
                      <span className="text-sm text-dark-400">Pending</span>
                    )}
                    {fileItem.status === 'uploading' && (
                      <ArrowPathIcon className="w-5 h-5 text-primary-400 animate-spin" />
                    )}
                    {fileItem.status === 'completed' && (
                      <>
                        <CheckCircleIcon className="w-5 h-5 text-green-400" />
                        <button
                          onClick={() => navigate(`/documents/${fileItem.documentId}/chat`)}
                          className="btn-secondary text-sm"
                        >
                          Chat
                        </button>
                      </>
                    )}
                    {fileItem.status === 'error' && (
                      <XCircleIcon className="w-5 h-5 text-red-400" />
                    )}

                    {fileItem.status !== 'uploading' && (
                      <button
                        onClick={() => removeFile(fileItem.id)}
                        className="p-2 text-dark-400 hover:text-red-400 hover:bg-red-600/20 rounded-lg transition-colors"
                      >
                        <XCircleIcon className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>

            {completedFiles.length > 0 && (
              <div className="flex justify-center pt-4">
                <button
                  onClick={() => navigate('/')}
                  className="btn-secondary"
                >
                  View All Documents
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default Upload;
