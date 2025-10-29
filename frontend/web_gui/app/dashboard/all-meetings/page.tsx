'use client';

import { useState, useEffect } from 'react';
import { meetingService, summarizationService } from '@/lib/api';
import { useAutoSync } from '@/hooks/useAutoSync';
import type { Bot, BotsListResponse, BotTranscriptResponse, SummarizationResponse } from '@/lib/api/types';

interface AllMeetingsPageProps {}

// Modal component for displaying results
interface ResultModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  content: any;
  type: 'transcript' | 'summary' | 'recording';
}

function ResultModal({ isOpen, onClose, title, content, type }: ResultModalProps) {
  if (!isOpen) return null;

  const renderContent = () => {
    switch (type) {
      case 'transcript':
        return (
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Raw Transcript:</h4>
              <div className="bg-gray-50 p-4 rounded-md max-h-96 overflow-y-auto">
                <pre className="whitespace-pre-wrap text-sm text-gray-700">
                  {content.clean_continuous_text || content.formatted_transcript?.clean_continuous_text || 'No transcript available'}
                </pre>
              </div>
            </div>
            {content.statistics && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Statistics:</h4>
                <div className="bg-blue-50 p-3 rounded-md">
                  <pre className="text-sm text-blue-800">
                    {JSON.stringify(content.statistics, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        );
      
      case 'summary':
        return (
          <div className="space-y-4">
            {content.success === false && content.error && (
              <div className="bg-red-50 p-4 rounded-md">
                <p className="text-red-800 font-medium">Error:</p>
                <p className="text-red-700">{content.error}</p>
              </div>
            )}
            
            {content.success && content.summary && (
              <div>
                <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-lg p-6 border border-purple-200">
                  <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">{content.summary}</p>
                  {content.metrics && (
                    <div className="mt-6 pt-4 border-t border-purple-200 flex flex-wrap items-center gap-4 text-sm text-gray-600">
                      <div className="flex items-center">
                        <span className="font-medium">Original:</span>
                        <span className="ml-1">{content.metrics.original_words || 0} words</span>
                      </div>
                      <div className="flex items-center">
                        <span className="font-medium">Summary:</span>
                        <span className="ml-1">{content.metrics.summary_words || 0} words</span>
                      </div>
                      <div className="flex items-center">
                        <span className="font-medium">Compression:</span>
                        <span className="ml-1">{((content.metrics.compression_ratio || 0) * 100).toFixed(1)}%</span>
                      </div>
                      {content.metrics.model_used && (
                        <div className="flex items-center">
                          <span className="font-medium">Model:</span>
                          <span className="ml-1">{content.metrics.model_used}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {content.action_items && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Action Items:</h4>
                <div className="bg-yellow-50 p-4 rounded-md">
                  <p className="text-gray-700 whitespace-pre-wrap">{content.action_items}</p>
                </div>
              </div>
            )}
            
            {content.key_decisions && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Key Decisions:</h4>
                <div className="bg-purple-50 p-4 rounded-md">
                  <p className="text-gray-700 whitespace-pre-wrap">{content.key_decisions}</p>
                </div>
              </div>
            )}
            
            {!content.summary && !content.action_items && !content.key_decisions && !content.error && (
              <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-gray-600">No summary content available.</p>
              </div>
            )}
          </div>
        );
      
      case 'recording':
        return (
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Recording Download:</h4>
              <div className="bg-purple-50 p-4 rounded-md">
                <a 
                  href={content.download_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
                >
                  📹 Download Recording
                </a>
                <p className="text-sm text-gray-600 mt-2">
                  Bot ID: {content.bot_id}
                </p>
              </div>
            </div>
          </div>
        );
      
      default:
        return <pre className="text-sm">{JSON.stringify(content, null, 2)}</pre>;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div className="flex justify-between items-center p-6 border-b">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[70vh]">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}

export default function AllMeetingsPage({}: AllMeetingsPageProps) {
  const [bots, setBots] = useState<Bot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});
  const [lastSyncInfo, setLastSyncInfo] = useState<string>('');

  // Auto-sync hook for calendar (will trigger bot data refresh)
  const { isRunning, forceSync } = useAutoSync({
    onMeetingsUpdate: () => {
      // When meetings are updated, refresh bots data
      loadBots();
    },
    onSyncSuccess: (eventsSynced) => {
      if (eventsSynced > 0) {
        setLastSyncInfo(`✅ Synced ${eventsSynced} events at ${new Date().toLocaleTimeString()}`);
        setTimeout(() => setLastSyncInfo(''), 3000);
      }
    },
    onError: (error) => {
      console.error('All-meetings auto-sync error:', error);
    },
    enabled: true,
    syncInterval: 1000 // 1 second
  });
  
  // Modal state
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    title: string;
    content: any;
    type: 'transcript' | 'summary' | 'recording';
  }>({
    isOpen: false,
    title: '',
    content: null,
    type: 'transcript',
  });

  const closeModal = () => {
    setModalState(prev => ({ ...prev, isOpen: false }));
  };

  const showModal = (title: string, content: any, type: 'transcript' | 'summary' | 'recording') => {
    setModalState({
      isOpen: true,
      title,
      content,
      type,
    });
  };

  // Load bots data
  const loadBots = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await meetingService.getBots({
        order_by: sortOrder,
        include_meeting_details: true,
        auto_sync_recall: true,
      });

      setBots(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load meetings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBots();
  }, [sortOrder]);

  // Action handlers
  const handleGetTranscript = async (botId: string) => {
    try {
      setActionLoading(prev => ({ ...prev, [`transcript-${botId}`]: true }));
      
      const response = await meetingService.getBotTranscript(botId);
      
      // Show transcript in modal
      showModal(
        `Transcript for Bot ${botId.substring(0, 8)}...`,
        response,
        'transcript'
      );
    } catch (err) {
      alert(`Failed to get transcript: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setActionLoading(prev => ({ ...prev, [`transcript-${botId}`]: false }));
    }
  };

  const handleGetSummary = async (botId: string) => {
    try {
      setActionLoading(prev => ({ ...prev, [`summary-${botId}`]: true }));
      
      console.log('Generating summary for bot:', botId); // Debug log
      
      // Use the same working endpoint as transcripts page
      const summaryResponse = await summarizationService.generateForBot(botId);
      
      console.log('Summary response:', summaryResponse); // Debug log

      // Show summary in modal
      showModal(
        `Summary for Bot ${botId.substring(0, 8)}...`,
        summaryResponse,
        'summary'
      );
    } catch (err) {
      console.error('Summary error:', err); // Debug log
      alert(`Failed to get summary: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setActionLoading(prev => ({ ...prev, [`summary-${botId}`]: false }));
    }
  };

  const handleGetRecording = async (botId: string) => {
    try {
      setActionLoading(prev => ({ ...prev, [`recording-${botId}`]: true }));
      
      const response = await meetingService.getBotRecordingUrlSimple(botId);
      
      if (response.download_url) {
        // Show recording info in modal
        showModal(
          `Recording for Bot ${botId.substring(0, 8)}...`,
          response,
          'recording'
        );
      } else {
        throw new Error('No recording URL available');
      }
    } catch (err) {
      alert(`Failed to get recording: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setActionLoading(prev => ({ ...prev, [`recording-${botId}`]: false }));
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-600 text-center">
          <h2 className="text-xl font-semibold mb-2">Error</h2>
          <p>{error}</p>
          <button
            onClick={loadBots}
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">All Meetings</h1>
          <p className="text-gray-600">View and manage all your meeting bots and recordings</p>
          
          {/* Auto-sync status indicator */}
          <div className="mt-2 flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}></div>
              <span className="text-sm text-gray-600">
                {isRunning ? 'Auto-sync active' : 'Auto-sync inactive'}
              </span>
            </div>
            
            {lastSyncInfo && (
              <div className="text-sm text-green-600 font-medium">
                {lastSyncInfo}
              </div>
            )}
          </div>
        </div>
        
        {/* Sort Controls */}
        <div className="flex items-center space-x-4">
          <button
            onClick={forceSync}
            className="px-3 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm"
            title="Force immediate sync"
          >
            🔄 Sync Now
          </button>
          <label className="text-sm font-medium text-gray-700">Sort by:</label>
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="desc">Newest First</option>
            <option value="asc">Oldest First</option>
          </select>
          <button
            onClick={loadBots}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Meetings Table */}
      {bots.length === 0 ? (
        <div className="text-center py-12">
          <h3 className="text-lg font-medium text-gray-900 mb-2">No meetings found</h3>
          <p className="text-gray-600">You don't have any meeting bots yet.</p>
        </div>
      ) : (
        <div className="bg-white shadow-sm rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Bot ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Meeting Title
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Meeting URL
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Meeting Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Platform
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {bots.map((bot) => (
                  <tr key={bot.bot_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                      {bot.bot_id.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {bot.meeting_title || 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {bot.meeting_url ? (
                        <a
                          href={bot.meeting_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-600 hover:text-indigo-900 hover:underline truncate block max-w-xs"
                        >
                          {bot.meeting_url}
                        </a>
                      ) : (
                        'N/A'
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {bot.meeting_scheduled_time ? formatDate(bot.meeting_scheduled_time) : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-md">
                        {bot.platform || 'Unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                      <button
                        onClick={() => handleGetTranscript(bot.bot_id)}
                        disabled={actionLoading[`transcript-${bot.bot_id}`]}
                        className="inline-flex items-center px-3 py-1 text-xs font-medium text-blue-600 bg-blue-100 rounded-md hover:bg-blue-200 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {actionLoading[`transcript-${bot.bot_id}`] ? (
                          <>
                            <div className="animate-spin rounded-full h-3 w-3 border-b border-blue-600 mr-1"></div>
                            Loading...
                          </>
                        ) : (
                          '📝 Transcript'
                        )}
                      </button>
                      
                      <button
                        onClick={() => handleGetSummary(bot.bot_id)}
                        disabled={actionLoading[`summary-${bot.bot_id}`]}
                        className="inline-flex items-center px-3 py-1 text-xs font-medium text-green-600 bg-green-100 rounded-md hover:bg-green-200 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {actionLoading[`summary-${bot.bot_id}`] ? (
                          <>
                            <div className="animate-spin rounded-full h-3 w-3 border-b border-green-600 mr-1"></div>
                            Loading...
                          </>
                        ) : (
                          '📋 Summary'
                        )}
                      </button>
                      
                      <button
                        onClick={() => handleGetRecording(bot.bot_id)}
                        disabled={actionLoading[`recording-${bot.bot_id}`]}
                        className="inline-flex items-center px-3 py-1 text-xs font-medium text-purple-600 bg-purple-100 rounded-md hover:bg-purple-200 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {actionLoading[`recording-${bot.bot_id}`] ? (
                          <>
                            <div className="animate-spin rounded-full h-3 w-3 border-b border-purple-600 mr-1"></div>
                            Loading...
                          </>
                        ) : (
                          '📹 Recording'
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Result Modal */}
      <ResultModal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        title={modalState.title}
        content={modalState.content}
        type={modalState.type}
      />
    </div>
  );
}