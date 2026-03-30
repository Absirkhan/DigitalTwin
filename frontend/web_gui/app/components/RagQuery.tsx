'use client';

import { useState, useEffect } from 'react';
import { queryRag, getCacheStats, getUserStats, clearCache, type RagQueryResponse, type CacheStats, type UserStats } from '@/lib/api/rag';

export default function RagQuery() {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState<RagQueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [queryHistory, setQueryHistory] = useState<Array<{ query: string; response: RagQueryResponse; timestamp: Date }>>([]);

  // Sample queries for quick testing
  const sampleQueries = [
    // Database & Backend
    "What database did we decide to use?",
    "What backend framework are we using?",
    "How are we managing database migrations?",
    "What caching solution did we choose?",

    // Frontend & UI
    "Tell me about our frontend technology stack",
    "What CSS framework are we using?",
    "Should we use Redux or Context API?",
    "What is our approach to state management?",

    // AI/ML & RAG
    "What LLM model are we using for the RAG system?",
    "How are we handling vector search?",
    "What embedding model did we choose?",
    "Why did we pick FAISS for vector search?",

    // Authentication & Security
    "How are we handling authentication?",
    "Are we using JWT tokens?",
    "Should we implement API rate limiting?",

    // Deployment & Infrastructure
    "What's our deployment strategy?",
    "Are we using Docker containers?",
    "Which cloud provider should we use?",
    "Should we use Kubernetes?",

    // Testing & Development
    "Tell me about our testing approach",
    "What testing frameworks are we using?",
    "Do we have CI/CD setup?",

    // General Technical
    "What technologies are we using overall?",
    "What are the main architectural decisions?",
    "How did we optimize for performance?",
  ];

  // Load stats on mount
  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const [cache, user] = await Promise.all([
        getCacheStats(),
        getUserStats(),
      ]);
      setCacheStats(cache);
      setUserStats(user);
    } catch (err: any) {
      console.error('Failed to load stats:', err);
      // Set default values on error to avoid perpetual "Loading..."
      setCacheStats({ hits: 0, misses: 0, hit_rate: 0, total_cached_responses: 0 });
      setUserStats({ user_id: '', total_exchanges: 0, session_messages: 0, profile: {} });

      // Show error if it's not an auth error
      if (!err.message?.includes('401') && !err.message?.includes('credentials')) {
        setError('Failed to load statistics. Please check your connection and try again.');
      }
    }
  };

  const handleQuery = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!message.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const result = await queryRag({
        message: message.trim(),
        use_cache: true,
        auto_store: false, // Don't store test queries
        max_tokens: 200,
      });

      setResponse(result);
      setQueryHistory(prev => [{
        query: message.trim(),
        response: result,
        timestamp: new Date()
      }, ...prev].slice(0, 10)); // Keep last 10 queries

      // Reload stats after query
      await loadStats();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to query RAG system');
    } finally {
      setLoading(false);
    }
  };

  const handleClearCache = async () => {
    if (!confirm('Are you sure you want to clear all cached responses?')) return;

    try {
      await clearCache();
      await loadStats();
      alert('Cache cleared successfully!');
    } catch (err) {
      alert('Failed to clear cache');
    }
  };

  const useSampleQuery = (query: string) => {
    setMessage(query);
  };

  return (
    <div className="space-y-6">
      {/* Header with Stats */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">RAG Query System</h2>
        <p className="text-gray-600 mb-6">
          Ask questions about past meetings and programming discussions. The AI will retrieve relevant context and generate intelligent responses.
        </p>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Cache Stats */}
          <div className="bg-blue-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-blue-900 mb-2">Cache Performance</h3>
            {cacheStats ? (
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-blue-700">Hit Rate:</span>
                  <span className="font-semibold text-blue-900">{(cacheStats.hit_rate * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-blue-700">Hits / Misses:</span>
                  <span className="font-semibold text-blue-900">{cacheStats.hits} / {cacheStats.misses}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-blue-700">Cached:</span>
                  <span className="font-semibold text-blue-900">{cacheStats.total_cached_responses}</span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-blue-700">Loading...</p>
            )}
          </div>

          {/* User Stats */}
          <div className="bg-green-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-green-900 mb-2">Knowledge Base</h3>
            {userStats ? (
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-green-700">Total Exchanges:</span>
                  <span className="font-semibold text-green-900">{userStats.total_exchanges}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-green-700">Session Messages:</span>
                  <span className="font-semibold text-green-900">{userStats.session_messages}</span>
                </div>
                {userStats.total_exchanges === 0 && (
                  <p className="text-xs text-green-600 mt-2 italic">
                    No data yet. Complete meetings to build your knowledge base!
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-green-700">Loading...</p>
            )}
          </div>

          {/* Actions */}
          <div className="bg-purple-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-purple-900 mb-2">Actions</h3>
            <div className="space-y-2">
              <button
                onClick={loadStats}
                className="w-full px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 transition-colors"
              >
                Refresh Stats
              </button>
              <button
                onClick={handleClearCache}
                className="w-full px-3 py-1.5 text-sm bg-purple-100 text-purple-700 rounded hover:bg-purple-200 transition-colors"
              >
                Clear Cache
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Query Input */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Ask a Question</h3>

        {/* Sample Queries */}
        <div className="mb-4">
          <p className="text-sm text-gray-600 mb-2">Try these sample queries:</p>
          <div className="flex flex-wrap gap-2">
            {sampleQueries.map((query, idx) => (
              <button
                key={idx}
                onClick={() => useSampleQuery(query)}
                className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              >
                {query}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleQuery} className="space-y-4">
          <div>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask anything about your past meetings or programming discussions..."
              rows={3}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !message.trim()}
            className="w-full px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Processing...' : 'Send Query'}
          </button>
        </form>

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}
      </div>

      {/* Current Response */}
      {response && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Response</h3>

          {/* Performance Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4 p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-xs text-gray-600">Total Latency</p>
              <p className="text-lg font-bold text-gray-900">{response.total_latency_ms.toFixed(0)}ms</p>
            </div>
            <div>
              <p className="text-xs text-gray-600">Retrieval</p>
              <p className="text-lg font-bold text-blue-600">{response.retrieval_latency_ms.toFixed(0)}ms</p>
            </div>
            <div>
              <p className="text-xs text-gray-600">LLM Generation</p>
              <p className="text-lg font-bold text-green-600">{response.llm_latency_ms.toFixed(0)}ms</p>
            </div>
            <div>
              <p className="text-xs text-gray-600">Tokens</p>
              <p className="text-lg font-bold text-purple-600">{response.tokens_generated}</p>
            </div>
            <div>
              <p className="text-xs text-gray-600">Status</p>
              <p className={`text-lg font-bold ${response.cached ? 'text-green-600' : 'text-orange-600'}`}>
                {response.cached ? '⚡ Cached' : '🔄 Fresh'}
              </p>
            </div>
          </div>

          {/* Context Info */}
          {response.context_items > 0 && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                📚 Retrieved {response.context_items} relevant context item{response.context_items !== 1 ? 's' : ''} from past conversations
              </p>
            </div>
          )}

          {/* AI Response */}
          <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
            <p className="text-gray-900 whitespace-pre-wrap">{response.response}</p>
          </div>

          {/* Performance Breakdown */}
          <div className="mt-4 text-xs text-gray-600 space-y-1">
            <p>⏱️ Performance Breakdown:</p>
            <div className="flex items-center space-x-4 ml-4">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                <span>Retrieval: {((response.retrieval_latency_ms / response.total_latency_ms) * 100).toFixed(1)}%</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                <span>LLM: {((response.llm_latency_ms / response.total_latency_ms) * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Query History */}
      {queryHistory.length > 0 && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Queries</h3>
          <div className="space-y-3">
            {queryHistory.map((item, idx) => (
              <div key={idx} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex justify-between items-start mb-2">
                  <p className="text-sm font-medium text-gray-900">{item.query}</p>
                  <span className="text-xs text-gray-500">{item.timestamp.toLocaleTimeString()}</span>
                </div>
                <div className="flex items-center space-x-4 text-xs text-gray-600">
                  <span>⏱️ {item.response.total_latency_ms.toFixed(0)}ms</span>
                  <span>🎯 {item.response.tokens_generated} tokens</span>
                  <span>{item.response.cached ? '⚡ Cached' : '🔄 Fresh'}</span>
                  <span>📚 {item.response.context_items} context</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
