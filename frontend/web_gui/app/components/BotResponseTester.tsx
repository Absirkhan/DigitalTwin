'use client';

import { useState } from 'react';
import { checkBotResponse, type ResponseCheckRequest, type ResponseCheckResponse } from '@/lib/api/rag';

export default function BotResponseTester() {
  const [triggerText, setTriggerText] = useState('');
  const [botName, setBotName] = useState('');
  const [simulateFiller, setSimulateFiller] = useState(true);
  const [useCache, setUseCache] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResponseCheckResponse | null>(null);
  const [logs, setLogs] = useState<Array<{ timestamp: Date; type: 'info' | 'success' | 'error'; message: string }>>([]);

  // Sample trigger texts
  const sampleTriggers = [
    "Hey Alice, what database are we using?",
    "Bob, can you summarize the last meeting?",
    "Hello Assistant!",
    "Digital Twin, what's the project status?",
    "Alice, how should we handle authentication?",
    "Hey Bob, goodbye for now!",
  ];

  const addLog = (type: 'info' | 'success' | 'error', message: string) => {
    setLogs(prev => [...prev, { timestamp: new Date(), type, message }]);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const handleTest = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!triggerText.trim()) return;

    setLoading(true);
    setError(null);
    clearLogs();

    const startTime = performance.now();

    try {
      const request: ResponseCheckRequest = {
        trigger_text: triggerText.trim(),
        bot_name: botName.trim() || undefined,
        simulate_filler: simulateFiller,
        use_cache: useCache,
      };

      addLog('info', '🚀 Sending request to /api/v1/rag/response-check...');
      addLog('info', `📝 Request: ${JSON.stringify(request, null, 2)}`);

      const response = await checkBotResponse(request);

      const endTime = performance.now();
      const clientLatency = endTime - startTime;

      addLog('success', `✅ Response received in ${clientLatency.toFixed(0)}ms`);
      addLog('info', `📊 Response: ${JSON.stringify(response, null, 2)}`);

      // Log detection result
      if (response.detected) {
        addLog('success', `✅ Bot detected: "${response.detection_reason}"`);
        addLog('info', `🔍 Extracted query: "${response.extracted_query}"`);
      } else {
        addLog('error', `❌ Bot not detected: "${response.detection_reason}"`);
      }

      // Log filler
      if (response.filler_text) {
        addLog('info', `💬 Filler: "${response.filler_text}" (${response.filler_category}, ${response.filler_latency_ms?.toFixed(0)}ms)`);
      }

      // Log RAG
      if (response.rag_context_items !== undefined) {
        addLog('info', `📚 RAG: Retrieved ${response.rag_context_items} items in ${response.rag_retrieval_ms?.toFixed(0)}ms`);
      }

      // Log LLM
      if (response.llm_response) {
        addLog('success', `🤖 LLM: Generated ${response.llm_tokens} tokens in ${response.llm_latency_ms?.toFixed(0)}ms ${response.cached ? '(cached)' : ''}`);
        addLog('info', `💭 Response: "${response.llm_response}"`);
      }

      // Log performance
      if (response.total_pipeline_ms) {
        addLog('info', `⏱️ Total pipeline: ${response.total_pipeline_ms.toFixed(0)}ms`);
        addLog('success', `🎤 Perceived latency: ${response.perceived_latency_ms?.toFixed(0)}ms`);
      }

      setResult(response);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to test bot response';
      addLog('error', `❌ Error: ${errorMsg}`);
      if (err.response) {
        addLog('error', `📊 Status: ${err.response.status}`);
        addLog('error', `📝 Full error: ${JSON.stringify(err.response.data, null, 2)}`);
      }
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const useSampleTrigger = (trigger: string) => {
    setTriggerText(trigger);
  };

  return (
    <div className="space-y-6">
      {/* Test Input */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Test Bot Trigger</h3>

        {/* Sample Triggers */}
        <div className="mb-4">
          <p className="text-sm text-gray-600 mb-2">Try these sample triggers:</p>
          <div className="flex flex-wrap gap-2">
            {sampleTriggers.map((trigger, idx) => (
              <button
                key={idx}
                onClick={() => useSampleTrigger(trigger)}
                className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
              >
                {trigger}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleTest} className="space-y-4">
          {/* Trigger Text */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Trigger Text
            </label>
            <input
              type="text"
              value={triggerText}
              onChange={(e) => setTriggerText(e.target.value)}
              placeholder="E.g., 'Hey Alice, what database are we using?'"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
          </div>

          {/* Bot Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Bot Name (optional - uses your profile's bot_name if empty)
            </label>
            <input
              type="text"
              value={botName}
              onChange={(e) => setBotName(e.target.value)}
              placeholder="E.g., 'Alice', 'Bob', 'Assistant'"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
          </div>

          {/* Options */}
          <div className="flex items-center space-x-6">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={simulateFiller}
                onChange={(e) => setSimulateFiller(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={loading}
              />
              <span className="ml-2 text-sm text-gray-700">Simulate Filler Injection</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={useCache}
                onChange={(e) => setUseCache(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={loading}
              />
              <span className="ml-2 text-sm text-gray-700">Use Cache</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={loading || !triggerText.trim()}
            className="w-full px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Testing...' : 'Test Bot Response'}
          </button>
        </form>

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}
      </div>

      {/* Backend Logs */}
      {logs.length > 0 && (
        <div className="bg-gray-900 shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">🖥️ Backend Logs</h3>
            <button
              onClick={clearLogs}
              className="px-3 py-1 text-xs bg-gray-700 text-white rounded hover:bg-gray-600 transition-colors"
            >
              Clear Logs
            </button>
          </div>
          <div className="bg-black rounded-lg p-4 font-mono text-xs space-y-1 max-h-96 overflow-y-auto">
            {logs.map((log, idx) => (
              <div
                key={idx}
                className={`flex items-start space-x-2 ${
                  log.type === 'error' ? 'text-red-400' :
                  log.type === 'success' ? 'text-green-400' :
                  'text-gray-300'
                }`}
              >
                <span className="text-gray-500 shrink-0">
                  [{log.timestamp.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 })}]
                </span>
                <span className="whitespace-pre-wrap break-all">{log.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Detection Status */}
          <div className={`bg-white shadow rounded-lg p-6 border-l-4 ${
            result.detected ? 'border-green-500' : 'border-red-500'
          }`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {result.detected ? '✅ Bot Detected' : '❌ Bot Not Detected'}
              </h3>
              {result.filler_category && (
                <span className="px-3 py-1 text-xs font-medium bg-purple-100 text-purple-800 rounded-full">
                  {result.filler_category}
                </span>
              )}
            </div>

            {result.detection_reason && (
              <p className="text-sm text-gray-600 mb-2">
                <strong>Reason:</strong> {result.detection_reason}
              </p>
            )}

            {result.extracted_query && (
              <p className="text-sm text-gray-600">
                <strong>Extracted Query:</strong> "{result.extracted_query}"
              </p>
            )}
          </div>

          {/* Filler Info */}
          {result.detected && result.filler_text && (
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Filler Injection</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-600">Filler Text</p>
                  <p className="text-lg font-bold text-purple-600">"{result.filler_text}"</p>
                </div>
                <div>
                  <p className="text-xs text-gray-600">Filler Latency</p>
                  <p className="text-lg font-bold text-purple-600">
                    {result.filler_latency_ms?.toFixed(0)}ms
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Pipeline Metrics */}
          {result.detected && result.llm_response && (
            <>
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Metrics</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-xs text-gray-600">Perceived Latency</p>
                    <p className="text-2xl font-bold text-green-600">
                      {result.perceived_latency_ms?.toFixed(0)}ms
                    </p>
                    <p className="text-xs text-gray-500">User hears response</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-600">RAG Retrieval</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {result.rag_retrieval_ms?.toFixed(0)}ms
                    </p>
                    <p className="text-xs text-gray-500">{result.rag_context_items || 0} items</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-600">LLM Generation</p>
                    <p className="text-2xl font-bold text-orange-600">
                      {result.llm_latency_ms?.toFixed(0)}ms
                    </p>
                    <p className="text-xs text-gray-500">{result.llm_tokens || 0} tokens</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-600">Total Pipeline</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {result.total_pipeline_ms?.toFixed(0)}ms
                    </p>
                    <p className={`text-xs ${result.cached ? 'text-green-600' : 'text-orange-500'}`}>
                      {result.cached ? '⚡ Cached' : '🔄 Fresh'}
                    </p>
                  </div>
                </div>

                {/* Performance Bar */}
                <div className="mt-6">
                  <p className="text-xs text-gray-600 mb-2">Pipeline Breakdown</p>
                  <div className="flex h-8 rounded-lg overflow-hidden">
                    <div
                      className="bg-blue-500 flex items-center justify-center text-white text-xs"
                      style={{
                        width: `${((result.rag_retrieval_ms || 0) / (result.total_pipeline_ms || 1)) * 100}%`
                      }}
                    >
                      RAG
                    </div>
                    <div
                      className="bg-orange-500 flex items-center justify-center text-white text-xs"
                      style={{
                        width: `${((result.llm_latency_ms || 0) / (result.total_pipeline_ms || 1)) * 100}%`
                      }}
                    >
                      LLM
                    </div>
                  </div>
                </div>
              </div>

              {/* LLM Response */}
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Generated Response</h3>
                <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200 mb-4">
                  <p className="text-gray-900 whitespace-pre-wrap">{result.llm_response}</p>
                </div>

                {/* TTS Chunks */}
                {result.response_chunks && result.response_chunks.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">
                      TTS Chunks ({result.response_chunks.length})
                    </h4>
                    <div className="space-y-2">
                      {result.response_chunks.map((chunk) => (
                        <div key={chunk.chunk_number} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                          <div className="flex justify-between items-start mb-2">
                            <span className="text-xs font-medium text-gray-500">Chunk {chunk.chunk_number}</span>
                            <div className="text-xs text-gray-600 space-x-3">
                              <span>⏱️ {chunk.tts_latency_ms.toFixed(0)}ms</span>
                              <span>📦 {(chunk.audio_size_bytes / 1024).toFixed(1)}KB</span>
                              <span>🔊 {chunk.audio_duration_seconds.toFixed(1)}s</span>
                            </div>
                          </div>
                          <p className="text-sm text-gray-900">"{chunk.text}"</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Latency Analysis */}
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Latency Analysis</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-green-900">User Experience</p>
                      <p className="text-xs text-green-700">First audio perceived by user</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-green-600">
                        {result.perceived_latency_ms?.toFixed(0)}ms
                      </p>
                      <p className="text-xs text-green-700">
                        {(result.perceived_latency_ms || 0) < 100 ? '⚡ Instant' :
                         (result.perceived_latency_ms || 0) < 1000 ? '✅ Fast' :
                         (result.perceived_latency_ms || 0) < 2000 ? '⚠️ Acceptable' : '❌ Slow'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-blue-900">Context Retrieval</p>
                      <p className="text-xs text-blue-700">FAISS vector search + metadata</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-blue-600">
                        {result.rag_retrieval_ms?.toFixed(0)}ms
                      </p>
                      <p className="text-xs text-blue-700">
                        {result.rag_context_items || 0} items retrieved
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-orange-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-orange-900">LLM Generation</p>
                      <p className="text-xs text-orange-700">Qwen2.5-0.5B streaming inference</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-orange-600">
                        {result.llm_latency_ms?.toFixed(0)}ms
                      </p>
                      <p className="text-xs text-orange-700">
                        {((result.llm_latency_ms || 0) / (result.llm_tokens || 1)).toFixed(0)}ms/token
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
