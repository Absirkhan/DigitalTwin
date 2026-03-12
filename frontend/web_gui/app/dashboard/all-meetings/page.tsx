'use client';

import { useState, useEffect } from 'react';
import { meetingService, summarizationService } from '@/lib/api';
import { useAutoSync } from '@/hooks/useAutoSync';
import type { Bot, BotsListResponse, BotTranscriptResponse, SummarizationResponse } from '@/lib/api/types';
import { FormattedSummaryDisplay } from '@/app/components/FormattedSummaryDisplay';

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
              <h4 className="font-semibold mb-4" style={{ 
                fontSize: '16px',
                color: 'var(--text-primary)' 
              }}>Transcript:</h4>
              <div className="rounded-lg border" style={{
                background: 'var(--bg-tertiary)',
                borderColor: 'var(--border-primary)',
                padding: '20px',
                maxHeight: '500px',
                overflowY: 'auto'
              }}>
                <div style={{ lineHeight: '1.6' }}>
                  {(content.clean_continuous_text || content.formatted_transcript?.clean_continuous_text || 'No transcript available')
                    .split('\n')
                    .map((line: string, index: number) => {
                      // Match speaker names (name followed by colon)
                      const speakerMatch = line.match(/^([^:]+):\s*(.*)$/);
                      if (speakerMatch) {
                        return (
                          <div key={index} style={{ marginBottom: '16px' }}>
                            <span style={{ 
                              fontWeight: 600, 
                              color: '#E07856',
                              marginRight: '8px'
                            }}>
                              {speakerMatch[1]}:
                            </span>
                            <span style={{ color: 'var(--text-primary)' }}>
                              {speakerMatch[2]}
                            </span>
                          </div>
                        );
                      }
                      return line ? <div key={index} style={{ marginBottom: '12px', color: 'var(--text-primary)' }}>{line}</div> : null;
                    })}
                </div>
              </div>
            </div>
            {content.statistics && (
              <div>
                <h4 className="font-semibold text-foreground mb-2">Statistics:</h4>
                <div className="bg-gradient-primary/5 p-3 rounded-lg border border-primary/20">
                  <pre className="text-sm text-muted-foreground">
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
              <div className="bg-muted/50 border border-border p-4 rounded-xl">
                <p className="text-foreground font-medium">Error:</p>
                <p className="text-muted-foreground">{content.error}</p>
              </div>
            )}
            
            {content.success && content.summary && (
              <div>
                <div className="rounded-lg p-6 border" style={{
                  background: 'var(--bg-tertiary)',
                  borderColor: 'var(--border-primary)'
                }}>
                  <FormattedSummaryDisplay summaryText={content.summary} />
                  {content.metrics && (
                    <div className="mt-6 pt-4 flex flex-wrap items-center gap-4 text-sm" style={{
                      borderTop: '1px solid var(--border-primary)'
                    }}>
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium" style={{ color: 'var(--text-primary)' }}>Original:</span>
                        <span style={{ color: 'var(--text-secondary)' }}>{content.metrics.original_words || 0} words</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium" style={{ color: 'var(--text-primary)' }}>Summary:</span>
                        <span style={{ color: 'var(--text-secondary)' }}>{content.metrics.summary_words || 0} words</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium" style={{ color: 'var(--text-primary)' }}>Compression:</span>
                        <span style={{ color: 'var(--text-secondary)' }}>{((content.metrics.compression_ratio || 0) * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {content.action_items && (
              <div>
                <h4 className="font-semibold text-foreground mb-2">Action Items:</h4>
                <div className="bg-secondary/5 p-4 rounded-lg border border-secondary/20">
                  <p className="text-foreground whitespace-pre-wrap">{content.action_items}</p>
                </div>
              </div>
            )}
            
            {content.key_decisions && (
              <div>
                <h4 className="font-semibold text-foreground mb-2">Key Decisions:</h4>
                <div className="bg-gradient-secondary/5 p-4 rounded-lg border border-secondary/20">
                  <p className="text-foreground whitespace-pre-wrap">{content.key_decisions}</p>
                </div>
              </div>
            )}
            
            {!content.summary && !content.action_items && !content.key_decisions && !content.error && (
              <div className="bg-muted/30 p-4 rounded-lg border border-border">
                <p className="text-muted-foreground">No summary content available.</p>
              </div>
            )}
          </div>
        );
      
      case 'recording':
        return (
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold text-foreground mb-2">Recording Download:</h4>
              <div className="bg-gradient-secondary/5 p-4 rounded-lg border border-secondary/20">
                <a 
                  href={content.download_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="btn btn-primary inline-flex items-center gap-2 px-4 py-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Download Recording
                </a>
                <p className="text-sm text-muted-foreground mt-3">
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
    <div className="fixed inset-0 flex items-center justify-center z-50 p-4" style={{
      background: 'rgba(0, 0, 0, 0.5)',
      backdropFilter: 'blur(4px)'
    }}>
      <div className="w-full flex flex-col" style={{
        maxWidth: '900px',
        maxHeight: '90vh',
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-primary)',
        borderRadius: '12px',
        overflow: 'hidden'
      }}>
        <div className="flex justify-between items-center" style={{
          padding: '24px 32px',
          borderBottom: '1px solid var(--border-primary)'
        }}>
          <h3 style={{ 
            fontSize: '24px', 
            fontWeight: 500, 
            color: 'var(--text-primary)',
            margin: 0
          }}>{title}</h3>
          <button
            onClick={onClose}
            className="transition-all"
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              border: '1px solid var(--border-primary)',
              background: 'transparent',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--bg-tertiary)';
              e.currentTarget.style.borderColor = 'var(--orange-primary)';
              e.currentTarget.style.color = 'var(--orange-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.borderColor = 'var(--border-primary)';
              e.currentTarget.style.color = 'var(--text-secondary)';
            }}
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div style={{ 
          padding: '32px', 
          overflowY: 'auto',
          flex: 1
        }}>
          {renderContent()}
        </div>
      </div>
    </div>
  );
}

export default function AllMeetingsPage({}: AllMeetingsPageProps) {
  const [bots, setBots] = useState<Bot[]>([]);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});

  // Auto-sync hook disabled - webhook handles all updates
  const { isRunning, forceSync } = useAutoSync({
    onMeetingsUpdate: () => {
      // When meetings are updated, refresh bots data without showing loading spinner
      loadBots(false);
    },
    onError: (error) => {
      console.error('All-meetings auto-sync error:', error);
    },
    enabled: false, // Disabled - only manual refresh via button
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
  const loadBots = async (showLoading: boolean = true) => {
    try {
      // Only show loading spinner on initial load or manual refresh
      if (showLoading) {
        setIsInitialLoad(true);
      }
      setError(null);

      const response = await meetingService.getBots({
        order_by: sortOrder,
        include_meeting_details: true,
        auto_sync_recall: true,
      });

      console.log('🤖 Loaded bots:', response.data.length, 'bots');
      response.data.forEach((bot, index) => {
        console.log(`  Bot ${index + 1}:`, {
          bot_id: bot.bot_id,
          meeting_title: bot.meeting_title,
          meeting_url: bot.meeting_url,
          meeting_id: bot.meeting_id
        });
      });

      setBots(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load meetings');
    } finally {
      if (isInitialLoad) {
        setIsInitialLoad(false);
      }
    }
  };

  useEffect(() => {
    loadBots(true);
  }, [sortOrder]);

  // Action handlers
  const handleGetTranscript = async (botId: string) => {
    try {
      console.log('🎯 handleGetTranscript called with botId:', botId);
      setActionLoading(prev => ({ ...prev, [`transcript-${botId}`]: true }));
      
      const response = await meetingService.getBotTranscript(botId);
      console.log('📄 Transcript response received for botId:', botId, response);
      
      // Show transcript in modal
      showModal(
        'Transcript',
        response,
        'transcript'
      );
    } catch (err) {
      console.error('❌ Transcript error for botId:', botId, err);
      alert(`Failed to get transcript: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setActionLoading(prev => ({ ...prev, [`transcript-${botId}`]: false }));
    }
  };

  const handleGetSummary = async (botId: string) => {
    try {
      console.log('🎯 handleGetSummary called with botId:', botId);
      setActionLoading(prev => ({ ...prev, [`summary-${botId}`]: true }));
      
      console.log('Generating summary for bot:', botId);
      
      // Use the same working endpoint as transcripts page
      const summaryResponse = await summarizationService.generateForBot(botId);
      
      console.log('📊 Summary response received for botId:', botId, summaryResponse);

      // Show summary in modal
      showModal(
        'Summary',
        summaryResponse,
        'summary'
      );
    } catch (err) {
      console.error('❌ Summary error for botId:', botId, err);
      alert(`Failed to get summary: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setActionLoading(prev => ({ ...prev, [`summary-${botId}`]: false }));
    }
  };

  const handleGetRecording = async (botId: string) => {
    try {
      console.log('🎯 handleGetRecording called with botId:', botId);
      setActionLoading(prev => ({ ...prev, [`recording-${botId}`]: true }));
      
      const response = await meetingService.getBotRecordingUrlSimple(botId);
      console.log('🎥 Recording response received for botId:', botId, response);
      
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
      console.error('❌ Recording error for botId:', botId, err);
      alert(`Failed to get recording: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setActionLoading(prev => ({ ...prev, [`recording-${botId}`]: false }));
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (isInitialLoad) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div
          className="animate-spin rounded-full h-12 w-12 border-2"
          style={{ borderColor: 'var(--color-primary)', borderTopColor: 'transparent' }}
        ></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-foreground text-center">
          <h2 className="text-xl font-semibold mb-2">Error</h2>
          <p className="text-muted-foreground">{error}</p>
          <button
            onClick={() => { loadBots(true); }}
            className="mt-4 btn btn-primary px-4 py-2"
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
      <div className="flex justify-between items-center" style={{ marginBottom: '32px' }}>
        <div>
          <h1 className="page-title" style={{ marginBottom: '8px', color: 'var(--text-primary)', fontSize: '36px', fontWeight: 700 }}>All Meetings</h1>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
            Updates via webhook. Use Refresh button to manually update.
          </p>
        </div>
        
        {/* Sort Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={forceSync}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all"
            style={{
              background: 'transparent',
              borderColor: 'var(--border-primary)',
              color: 'var(--text-primary)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--bg-tertiary)';
              e.currentTarget.style.borderColor = 'var(--orange-primary)';
              e.currentTarget.style.color = 'var(--orange-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.borderColor = 'var(--border-primary)';
              e.currentTarget.style.color = 'var(--text-primary)';
            }}
            title="Manually refresh meetings"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium whitespace-nowrap" style={{ color: 'var(--text-primary)' }}>Sort by:</label>
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
              className="px-4 py-2 rounded-lg border text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary min-w-[150px]"
              style={{
                background: 'var(--bg-secondary)',
                borderColor: 'var(--border-primary)',
                color: 'var(--text-primary)'
              }}
            >
              <option value="desc">Newest First</option>
              <option value="asc">Oldest First</option>
            </select>
          </div>
          <button
            onClick={() => { loadBots(true); }}
            className="btn btn-primary"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Meetings Table */}
      {bots.length === 0 ? (
        <div className="text-center flex flex-col items-center justify-center" style={{ padding: '80px 40px', background: 'transparent' }}>
          {/* Custom Orange Meeting/Calendar Illustration */}
          <svg 
            width="120" 
            height="120" 
            viewBox="0 0 120 120" 
            fill="none" 
            xmlns="http://www.w3.org/2000/svg"
            style={{ marginBottom: '32px' }}
          >
            {/* Calendar background */}
            <rect x="20" y="25" width="80" height="70" rx="8" fill="#FFF8F0" stroke="#D97757" strokeWidth="2"/>
            
            {/* Calendar header bar */}
            <rect x="20" y="25" width="80" height="15" rx="8" fill="#D97757"/>
            <rect x="20" y="32" width="80" height="8" fill="#D97757"/>
            
            {/* Binding rings */}
            <circle cx="35" cy="32" r="3" fill="#FAF9F6" stroke="#D97757" strokeWidth="1.5"/>
            <circle cx="60" cy="32" r="3" fill="#FAF9F6" stroke="#D97757" strokeWidth="1.5"/>
            <circle cx="85" cy="32" r="3" fill="#FAF9F6" stroke="#D97757" strokeWidth="1.5"/>
            
            {/* Calendar grid - Week 1 */}
            <rect x="28" y="48" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="40" y="48" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="52" y="48" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="64" y="48" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="76" y="48" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="88" y="48" width="8" height="8" rx="2" fill="#E8E8E8"/>
            
            {/* Calendar grid - Week 2 */}
            <rect x="28" y="60" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="40" y="60" width="8" height="8" rx="2" fill="#D97757"/>
            <rect x="52" y="60" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="64" y="60" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="76" y="60" width="8" height="8" rx="2" fill="#D97757"/>
            <rect x="88" y="60" width="8" height="8" rx="2" fill="#E8E8E8"/>
            
            {/* Calendar grid - Week 3 */}
            <rect x="28" y="72" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="40" y="72" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="52" y="72" width="8" height="8" rx="2" fill="#D97757"/>
            <rect x="64" y="72" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="76" y="72" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="88" y="72" width="8" height="8" rx="2" fill="#E8E8E8"/>
            
            {/* Calendar grid - Week 4 */}
            <rect x="28" y="84" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="40" y="84" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="52" y="84" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="64" y="84" width="8" height="8" rx="2" fill="#D97757"/>
            <rect x="76" y="84" width="8" height="8" rx="2" fill="#E8E8E8"/>
            <rect x="88" y="84" width="8" height="8" rx="2" fill="#E8E8E8"/>
            
            {/* Video camera icon overlay */}
            <circle cx="85" cy="75" r="18" fill="#D97757" opacity="0.9"/>
            <rect x="77" y="70" width="10" height="8" rx="1.5" fill="white"/>
            <path d="M87 71 L92 68 L92 77 L87 74 Z" fill="white"/>
            <circle cx="80" cy="72" r="1" fill="#D97757"/>
          </svg>
          
          {/* Text Content */}
          <h3 style={{ 
            fontSize: '20px', 
            fontWeight: 600, 
            marginBottom: '8px',
            color: 'var(--text-primary)'
          }}>
            No meetings found
          </h3>
          <p style={{ 
            fontSize: '14px', 
            color: 'var(--text-secondary)',
            marginBottom: '24px'
          }}>
            You don't have any meeting bots yet.
          </p>
          
          {/* CTA Button */}
          <button
            onClick={forceSync}
            style={{
              backgroundColor: 'var(--orange-primary)',
              color: 'white',
              padding: '12px 24px',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: 500,
              border: 'none',
              cursor: 'pointer',
              transition: 'opacity 0.2s ease'
            }}
            onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
            onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
          >
            Create Your First Meeting
          </button>
        </div>
      ) : (
        <div className="overflow-hidden" style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-primary)',
          borderRadius: '12px',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <div className="overflow-x-auto">
            <table className="min-w-full" style={{ borderCollapse: 'collapse' }}>
              <thead style={{
                background: 'var(--bg-tertiary)',
                borderBottom: '2px solid var(--border-primary)'
              }}>
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider" style={{
                    color: 'var(--text-secondary)',
                    letterSpacing: '0.05em'
                  }}>
                    Meeting Title
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider" style={{
                    color: 'var(--text-secondary)',
                    letterSpacing: '0.05em'
                  }}>
                    Meeting URL
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider" style={{
                    color: 'var(--text-secondary)',
                    letterSpacing: '0.05em'
                  }}>
                    Meeting Date
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider" style={{
                    color: 'var(--text-secondary)',
                    letterSpacing: '0.05em'
                  }}>
                    Platform
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider" style={{
                    color: 'var(--text-secondary)',
                    letterSpacing: '0.05em'
                  }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody style={{ background: 'transparent' }}>
                {bots.map((bot) => (
                  <tr key={bot.bot_id} className="transition-colors" style={{
                    borderBottom: '1px solid var(--border-primary)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                    <td className="px-6 py-5 whitespace-nowrap text-sm" style={{ color: 'var(--text-primary)' }}>
                      {bot.meeting_title || 'N/A'}
                    </td>
                    <td className="px-6 py-5 text-sm">
                      {bot.meeting_url ? (
                        <a
                          href={bot.meeting_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:underline truncate block max-w-xs transition-colors"
                          style={{ color: 'var(--orange-primary)' }}
                          onMouseEnter={(e) => e.currentTarget.style.color = 'var(--orange-hover)'}
                          onMouseLeave={(e) => e.currentTarget.style.color = 'var(--orange-primary)'}
                        >
                          {bot.meeting_url}
                        </a>
                      ) : (
                        'N/A'
                      )}
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap text-sm" style={{ color: 'var(--text-primary)' }}>
                      {bot.meeting_scheduled_time ? formatDate(bot.meeting_scheduled_time) : 'N/A'}
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap text-sm">
                      <span className="px-3 py-1.5 text-xs font-medium rounded-xl" style={{
                        background: 'var(--bg-tertiary)',
                        border: '1px solid var(--border-primary)',
                        color: 'var(--text-secondary)'
                      }}>
                        {bot.platform || 'Unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <div className="flex flex-col gap-2">
                        {/* Transcript Button */}
                        <button
                          onClick={() => handleGetTranscript(bot.bot_id)}
                          disabled={actionLoading[`transcript-${bot.bot_id}`]}
                          className="group relative inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed w-full justify-start"
                          style={{
                            background: actionLoading[`transcript-${bot.bot_id}`] ? 'rgba(224, 120, 86, 0.1)' : 'transparent',
                            border: '1px solid rgba(224, 120, 86, 0.3)',
                            color: '#E07856'
                          }}
                          onMouseEnter={(e) => {
                            if (!actionLoading[`transcript-${bot.bot_id}`]) {
                              e.currentTarget.style.background = '#E07856';
                              e.currentTarget.style.color = 'white';
                              e.currentTarget.style.borderColor = '#E07856';
                              e.currentTarget.style.transform = 'translateY(-1px)';
                              e.currentTarget.style.boxShadow = '0 4px 12px rgba(224, 120, 86, 0.3)';
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!actionLoading[`transcript-${bot.bot_id}`]) {
                              e.currentTarget.style.background = 'transparent';
                              e.currentTarget.style.color = '#E07856';
                              e.currentTarget.style.borderColor = 'rgba(224, 120, 86, 0.3)';
                              e.currentTarget.style.transform = 'translateY(0)';
                              e.currentTarget.style.boxShadow = 'none';
                            }
                          }}
                        >
                          {actionLoading[`transcript-${bot.bot_id}`] ? (
                            <>
                              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                              <span>Loading...</span>
                            </>
                          ) : (
                            <>
                              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                              <span>Transcript</span>
                            </>
                          )}
                        </button>
                        
                        {/* Summary Button */}
                        <button
                          onClick={() => handleGetSummary(bot.bot_id)}
                          disabled={actionLoading[`summary-${bot.bot_id}`]}
                          className="group relative inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed w-full justify-start"
                          style={{
                            background: actionLoading[`summary-${bot.bot_id}`] ? 'rgba(91, 155, 213, 0.1)' : 'transparent',
                            border: '1px solid rgba(91, 155, 213, 0.3)',
                            color: '#7BAED9'
                          }}
                          onMouseEnter={(e) => {
                            if (!actionLoading[`summary-${bot.bot_id}`]) {
                              e.currentTarget.style.background = '#5B9BD5';
                              e.currentTarget.style.color = 'white';
                              e.currentTarget.style.borderColor = '#5B9BD5';
                              e.currentTarget.style.transform = 'translateY(-1px)';
                              e.currentTarget.style.boxShadow = '0 4px 12px rgba(91, 155, 213, 0.3)';
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!actionLoading[`summary-${bot.bot_id}`]) {
                              e.currentTarget.style.background = 'transparent';
                              e.currentTarget.style.color = '#7BAED9';
                              e.currentTarget.style.borderColor = 'rgba(91, 155, 213, 0.3)';
                              e.currentTarget.style.transform = 'translateY(0)';
                              e.currentTarget.style.boxShadow = 'none';
                            }
                          }}
                        >
                          {actionLoading[`summary-${bot.bot_id}`] ? (
                            <>
                              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                              <span>Loading...</span>
                            </>
                          ) : (
                            <>
                              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                              </svg>
                              <span>Summary</span>
                            </>
                          )}
                        </button>
                        
                        {/* Recording Button */}
                        <button
                          onClick={() => handleGetRecording(bot.bot_id)}
                          disabled={actionLoading[`recording-${bot.bot_id}`]}
                          className="group relative inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed w-full justify-start"
                          style={{
                            background: actionLoading[`recording-${bot.bot_id}`] ? 'rgba(240, 133, 102, 0.1)' : 'transparent',
                            border: '1px solid rgba(240, 133, 102, 0.3)',
                            color: '#F08566'
                          }}
                          onMouseEnter={(e) => {
                            if (!actionLoading[`recording-${bot.bot_id}`]) {
                              e.currentTarget.style.background = '#F08566';
                              e.currentTarget.style.color = 'white';
                              e.currentTarget.style.borderColor = '#F08566';
                              e.currentTarget.style.transform = 'translateY(-1px)';
                              e.currentTarget.style.boxShadow = '0 4px 12px rgba(240, 133, 102, 0.3)';
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!actionLoading[`recording-${bot.bot_id}`]) {
                              e.currentTarget.style.background = 'transparent';
                              e.currentTarget.style.color = '#F08566';
                              e.currentTarget.style.borderColor = 'rgba(240, 133, 102, 0.3)';
                              e.currentTarget.style.transform = 'translateY(0)';
                              e.currentTarget.style.boxShadow = 'none';
                            }
                          }}
                        >
                          {actionLoading[`recording-${bot.bot_id}`] ? (
                            <>
                              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                              <span>Loading...</span>
                            </>
                          ) : (
                            <>
                              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                              <span>Recording</span>
                            </>
                          )}
                        </button>
                      </div>
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