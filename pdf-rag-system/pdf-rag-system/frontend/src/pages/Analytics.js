import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  ChartBarIcon,
  DocumentTextIcon,
  ClockIcon,
  BoltIcon,
  ServerStackIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline';
import { analyticsApi } from '../services/api';

function Analytics() {
  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => analyticsApi.getUsage(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const stats = [
    {
      name: 'Total Documents',
      value: analytics?.documents?.total || 0,
      icon: DocumentTextIcon,
      color: 'primary',
    },
    {
      name: 'Total Pages',
      value: analytics?.documents?.total_pages || 0,
      icon: DocumentTextIcon,
      color: 'cyan',
    },
    {
      name: 'Storage Used',
      value: `${analytics?.documents?.total_size_mb || 0} MB`,
      icon: ServerStackIcon,
      color: 'green',
    },
    {
      name: 'Queries (30 days)',
      value: analytics?.queries?.total_last_30_days || 0,
      icon: ChartBarIcon,
      color: 'yellow',
    },
    {
      name: 'Avg Response Time',
      value: `${analytics?.queries?.avg_response_time_ms || 0}ms`,
      icon: ClockIcon,
      color: 'purple',
    },
    {
      name: 'Uptime',
      value: '99.9%',
      icon: BoltIcon,
      color: 'emerald',
    },
  ];

  const colorClasses = {
    primary: 'bg-primary-600/20 text-primary-400',
    cyan: 'bg-cyan-600/20 text-cyan-400',
    green: 'bg-green-600/20 text-green-400',
    yellow: 'bg-yellow-600/20 text-yellow-400',
    purple: 'bg-purple-600/20 text-purple-400',
    emerald: 'bg-emerald-600/20 text-emerald-400',
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Analytics</h1>
        <p className="mt-1 text-dark-400">
          Monitor your document processing and query performance
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="card"
          >
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-xl ${colorClasses[stat.color]}`}>
                <stat.icon className="w-6 h-6" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {isLoading ? (
                    <span className="inline-block w-16 h-7 bg-dark-700 rounded animate-pulse" />
                  ) : (
                    stat.value
                  )}
                </p>
                <p className="text-sm text-dark-400">{stat.name}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* System Performance */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="card"
      >
        <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
          <CpuChipIcon className="w-5 h-5 text-primary-400" />
          System Architecture
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 bg-dark-800 rounded-xl">
            <h3 className="font-medium text-white mb-2">Backend</h3>
            <ul className="text-sm text-dark-400 space-y-1">
              <li>• Python Flask</li>
              <li>• OpenAI GPT-3.5</li>
              <li>• FAISS Vector Store</li>
              <li>• PostgreSQL</li>
            </ul>
          </div>
          
          <div className="p-4 bg-dark-800 rounded-xl">
            <h3 className="font-medium text-white mb-2">Frontend</h3>
            <ul className="text-sm text-dark-400 space-y-1">
              <li>• React 18</li>
              <li>• TailwindCSS</li>
              <li>• Framer Motion</li>
              <li>• React Query</li>
            </ul>
          </div>
          
          <div className="p-4 bg-dark-800 rounded-xl">
            <h3 className="font-medium text-white mb-2">Infrastructure</h3>
            <ul className="text-sm text-dark-400 space-y-1">
              <li>• AWS ECS</li>
              <li>• AWS S3</li>
              <li>• Redis Cache</li>
              <li>• CloudWatch</li>
            </ul>
          </div>
          
          <div className="p-4 bg-dark-800 rounded-xl">
            <h3 className="font-medium text-white mb-2">ML Pipeline</h3>
            <ul className="text-sm text-dark-400 space-y-1">
              <li>• HuggingFace Embeddings</li>
              <li>• Sentence Transformers</li>
              <li>• RAG Architecture</li>
              <li>• Semantic Search</li>
            </ul>
          </div>
        </div>
      </motion.div>

      {/* Performance Metrics */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
        className="card"
      >
        <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
          <BoltIcon className="w-5 h-5 text-yellow-400" />
          Performance Targets
        </h2>
        
        <div className="space-y-4">
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-dark-300">Response Time</span>
              <span className="text-primary-400">&lt;200ms target</span>
            </div>
            <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
              <div className="h-full w-[95%] bg-gradient-to-r from-primary-500 to-cyan-500 rounded-full" />
            </div>
          </div>
          
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-dark-300">Uptime</span>
              <span className="text-green-400">99.9% target</span>
            </div>
            <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
              <div className="h-full w-[99%] bg-gradient-to-r from-green-500 to-emerald-500 rounded-full" />
            </div>
          </div>
          
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-dark-300">Concurrent Users</span>
              <span className="text-cyan-400">10,000+ capacity</span>
            </div>
            <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
              <div className="h-full w-[85%] bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full" />
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default Analytics;
