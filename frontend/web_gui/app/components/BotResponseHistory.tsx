"use client";

import React, { useEffect, useState } from 'react';
import { getMeetingBotResponses, emergencyDisableBotSpeaking, type BotResponseHistoryResponse, type BotResponseItem } from '@/lib/api/botSpeaking';

interface BotResponseHistoryProps {
  meetingId: number;
  onEmergencyDisable?: () => void;
}

export default function BotResponseHistory({ meetingId, onEmergencyDisable }: BotResponseHistoryProps) {
  const [data, setData] = useState<BotResponseHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDisabling, setIsDisabling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const itemsPerPage = 20;

  useEffect(() => {
    loadResponses();
  }, [meetingId, currentPage]);

  const loadResponses = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getMeetingBotResponses(
        meetingId,
        itemsPerPage,
        currentPage * itemsPerPage
      );
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load response history');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmergencyDisable = async () => {
    if (!confirm('Are you sure you want to emergency disable bot speaking for this meeting? The bot will stop responding immediately.')) {
      return;
    }

    setIsDisabling(true);
    try {
      const result = await emergencyDisableBotSpeaking(meetingId);
      alert(result.message);
      loadResponses(); // Reload to show updated status
      if (onEmergencyDisable) {
        onEmergencyDisable();
      }
    } catch (err) {
      alert('Failed to disable bot speaking: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setIsDisabling(false);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
  };

  const getStyleBadgeColor = (style: string) => {
    switch (style) {
      case 'professional':
        return 'bg-blue-100 text-blue-800';
      case 'casual':
        return 'bg-green-100 text-green-800';
      case 'technical':
        return 'bg-purple-100 text-purple-800';
      case 'brief':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (isLoading) {
    return (
      <div className="card">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="px-4 py-5 sm:p-6">
          <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded">
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={loadResponses}
              className="mt-2 text-sm text-red-700 underline hover:no-underline"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const totalPages = Math.ceil(data.total_responses / itemsPerPage);

  return (
    <div className="card">
      <div className="px-4 py-5 sm:p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-medium text-foreground flex items-center gap-2">
              <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              Bot Response History
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {data.total_responses} total response{data.total_responses !== 1 ? 's' : ''} • {data.bot_response_count} / {data.bot_max_responses} used
            </p>
          </div>

          {/* Status and Emergency Disable */}
          <div className="flex items-center gap-3">
            {data.bot_response_enabled ? (
              <>
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  Bot Speaking Active
                </span>
                <button
                  onClick={handleEmergencyDisable}
                  disabled={isDisabling}
                  className="btn btn-outline text-red-600 border-red-600 hover:bg-red-50 px-3 py-1 text-sm disabled:opacity-50"
                >
                  {isDisabling ? 'Disabling...' : 'Emergency Disable'}
                </button>
              </>
            ) : (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                Bot Speaking Disabled
              </span>
            )}
          </div>
        </div>

        {/* Settings Summary */}
        <div className="mb-4 bg-accent rounded-lg p-3">
          <div className="flex items-center justify-between text-sm">
            <div>
              <span className="text-muted-foreground">Response Style:</span>
              <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${getStyleBadgeColor(data.bot_response_style)}`}>
                {data.bot_response_style}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Progress:</span>
              <span className="ml-2 font-medium text-foreground">
                {data.bot_response_count} / {data.bot_max_responses}
              </span>
            </div>
          </div>
          {/* Progress Bar */}
          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all"
              style={{ width: `${Math.min((data.bot_response_count / data.bot_max_responses) * 100, 100)}%` }}
            ></div>
          </div>
        </div>

        {/* Response List */}
        {data.responses.length === 0 ? (
          <div className="text-center py-12 bg-accent rounded-lg">
            <svg className="mx-auto h-12 w-12 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="mt-4 text-sm text-muted-foreground">
              No bot responses yet. The bot will respond when directly addressed by name.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {data.responses.map((response: BotResponseItem) => (
              <div
                key={response.id}
                className={`border rounded-lg p-4 ${response.success ? 'border-border bg-background' : 'border-red-200 bg-red-50'}`}
              >
                {/* Response Header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStyleBadgeColor(response.response_style)}`}>
                      {response.response_style}
                    </span>
                    {response.success ? (
                      <span className="text-green-600 text-xs flex items-center gap-1">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        Success
                      </span>
                    ) : (
                      <span className="text-red-600 text-xs flex items-center gap-1">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        Failed
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {formatTimestamp(response.timestamp)}
                    {response.latency_ms && (
                      <span className="ml-2">• {response.latency_ms}ms</span>
                    )}
                  </div>
                </div>

                {/* Trigger Text */}
                <div className="mb-2">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Triggered by:</p>
                  <p className="text-sm text-foreground bg-accent px-3 py-2 rounded italic">
                    "{response.trigger_text}"
                  </p>
                </div>

                {/* Response Text */}
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Bot response:</p>
                  <p className="text-sm text-foreground bg-primary/5 px-3 py-2 rounded border border-primary/20">
                    {response.response_text}
                  </p>
                </div>

                {/* Audio URL (if available) */}
                {response.audio_url && (
                  <div className="mt-2">
                    <audio controls className="w-full h-8">
                      <source src={response.audio_url} type="audio/mp3" />
                      Your browser does not support the audio element.
                    </audio>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-6 flex items-center justify-between border-t pt-4" style={{ borderColor: 'var(--border-primary)' }}>
            <button
              onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
              disabled={currentPage === 0}
              className="btn btn-outline px-3 py-1 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-muted-foreground">
              Page {currentPage + 1} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages - 1, prev + 1))}
              disabled={currentPage === totalPages - 1}
              className="btn btn-outline px-3 py-1 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
