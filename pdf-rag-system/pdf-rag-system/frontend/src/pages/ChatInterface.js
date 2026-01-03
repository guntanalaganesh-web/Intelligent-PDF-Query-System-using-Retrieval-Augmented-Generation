import React, { useState, useRef, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
  PaperAirplaneIcon,
  DocumentTextIcon,
  SparklesIcon,
  ArrowLeftIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import { documentApi } from '../services/api';
import toast from 'react-hot-toast';

function ChatInterface() {
  const { documentId } = useParams();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const { data: document } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => documentApi.get(documentId),
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const query = input.trim();
    if (!query || isLoading) return;

    // Add user message
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: query,
      timestamp: new Date(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setStreamingContent('');

    try {
      // Use streaming API
      let fullResponse = '';
      
      for await (const chunk of documentApi.queryStream(documentId, query)) {
        fullResponse += chunk;
        setStreamingContent(fullResponse);
      }

      // Add assistant message
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: fullResponse,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setStreamingContent('');

    } catch (error) {
      toast.error('Failed to get response');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const suggestedQuestions = [
    'What is the main topic of this document?',
    'Summarize the key points',
    'What are the conclusions?',
    'List all mentioned dates or deadlines',
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center gap-4 pb-4 border-b border-dark-800">
        <Link
          to={`/documents/${documentId}`}
          className="p-2 text-dark-400 hover:text-white hover:bg-dark-800 rounded-lg transition-colors"
        >
          <ArrowLeftIcon className="w-5 h-5" />
        </Link>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-red-600/20 rounded-lg">
            <DocumentTextIcon className="w-5 h-5 text-red-400" />
          </div>
          <div>
            <h1 className="font-medium text-white truncate max-w-md">
              {document?.filename || 'Document'}
            </h1>
            <p className="text-sm text-dark-400">
              {document?.page_count} pages • Ask anything about this document
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-6 space-y-6">
        {messages.length === 0 && !isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-12"
          >
            <SparklesIcon className="w-16 h-16 text-primary-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-white mb-2">
              Ask anything about your document
            </h2>
            <p className="text-dark-400 mb-8 max-w-md mx-auto">
              I'll search through the document and provide accurate answers with references to specific pages.
            </p>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl mx-auto">
              {suggestedQuestions.map((question) => (
                <button
                  key={question}
                  onClick={() => {
                    setInput(question);
                    inputRef.current?.focus();
                  }}
                  className="p-4 text-left bg-dark-800 hover:bg-dark-700 border border-dark-700 hover:border-dark-600 rounded-xl transition-colors"
                >
                  <span className="text-dark-200">{question}</span>
                </button>
              ))}
            </div>
          </motion.div>
        )}

        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-4 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-cyan-500 flex items-center justify-center">
                  <SparklesIcon className="w-4 h-4 text-white" />
                </div>
              )}
              
              <div
                className={`max-w-2xl rounded-2xl px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-primary-600 text-white'
                    : 'bg-dark-800 text-dark-100'
                }`}
              >
                {message.role === 'assistant' ? (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p>{message.content}</p>
                )}
              </div>

              {message.role === 'user' && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-dark-700 flex items-center justify-center">
                  <span className="text-sm font-medium text-dark-300">U</span>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Streaming response */}
        {streamingContent && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-4"
          >
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-cyan-500 flex items-center justify-center">
              <SparklesIcon className="w-4 h-4 text-white" />
            </div>
            <div className="max-w-2xl rounded-2xl px-4 py-3 bg-dark-800 text-dark-100">
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{streamingContent}</ReactMarkdown>
              </div>
              <span className="inline-block w-2 h-4 bg-primary-400 animate-pulse ml-1" />
            </div>
          </motion.div>
        )}

        {/* Loading indicator */}
        {isLoading && !streamingContent && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex gap-4"
          >
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-cyan-500 flex items-center justify-center">
              <SparklesIcon className="w-4 h-4 text-white" />
            </div>
            <div className="px-4 py-3 bg-dark-800 rounded-2xl">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="pt-4 border-t border-dark-800">
        <form onSubmit={handleSubmit} className="relative">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about the document..."
            rows={1}
            className="input pr-14 resize-none"
            style={{ minHeight: '56px', maxHeight: '200px' }}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="absolute right-2 bottom-2 p-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <PaperAirplaneIcon className="w-5 h-5" />
          </button>
        </form>
        <p className="text-xs text-dark-500 mt-2 flex items-center gap-1">
          <InformationCircleIcon className="w-4 h-4" />
          AI responses are generated based on document content. Always verify important information.
        </p>
      </div>
    </div>
  );
}

export default ChatInterface;
