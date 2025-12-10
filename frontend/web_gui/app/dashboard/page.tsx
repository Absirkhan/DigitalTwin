'use client';

import { useEffect, useState } from 'react';
import { meetingService, summarizationService, calendarService, getAuthToken } from '@/lib/api';
import { useAutoSync } from '@/hooks/useAutoSync';
import type { Meeting, SummarizationResponse } from '@/lib/api/types';
import Link from 'next/link';
import { FormattedSummaryDisplay } from '@/app/components/FormattedSummaryDisplay';

export default function DashboardPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [recentSummary, setRecentSummary] = useState<SummarizationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncInfo, setLastSyncInfo] = useState<string>('');
  const [isTokenReady, setIsTokenReady] = useState(false);

  // Wait for token to be available before loading data
  useEffect(() => {
    const checkToken = () => {
      const token = getAuthToken();
      if (token) {
        console.log('Dashboard: Token is ready');
        setIsTokenReady(true);
      } else {
        console.log('Dashboard: Waiting for token...');
        // Check again after a short delay
        setTimeout(checkToken, 100);
      }
    };
    checkToken();
  }, []);

  // Auto-sync hook for calendar and meetings
  const { isRunning, forceSync } = useAutoSync({
    onMeetingsUpdate: (updatedMeetings) => {
      setMeetings(updatedMeetings.slice(0, 5)); // Show only 5 most recent
      setIsLoading(false);
    },
    onSyncSuccess: (eventsSynced) => {
      if (eventsSynced > 0) {
        setLastSyncInfo(`✅ Synced ${eventsSynced} events`);
        setTimeout(() => setLastSyncInfo(''), 3000);
      }
    },
    onError: (error) => {
      console.error('Dashboard auto-sync error:', error);
    },
    enabled: true,
    syncInterval: 1000 // 1 second
  });

  useEffect(() => {
    // Only load data when token is ready
    if (isTokenReady) {
      loadDashboardData();
    }
  }, [isTokenReady]);

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      console.log('Loading dashboard data...');
      const meetingsData = await meetingService.getAll();
      console.log('Meetings loaded successfully:', meetingsData);
      setMeetings(meetingsData.slice(0, 5)); // Show only 5 most recent
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      console.error('Error details:', {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSyncCalendar = async () => {
    setIsSyncing(true);
    try {
      // Use the force sync from the hook instead
      forceSync();
      setLastSyncInfo('🔄 Manual sync triggered...');
    } catch (error) {
      alert('Failed to sync calendar: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsSyncing(false);
    }
  };

  const handleGenerateSummary = async () => {
    try {
      const summary = await summarizationService.generate();
      setRecentSummary(summary);
    } catch (error) {
      alert('Failed to generate summary: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="relative">
          <div
            className="animate-spin rounded-full h-12 w-12 border-2"
            style={{ borderColor: 'var(--color-primary)', borderTopColor: 'transparent' }}
          ></div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '48px' }}>
      {/* Header */}
      <div className="md:flex md:items-start md:justify-between">
        <div className="flex-1 min-w-0">
          <h1 className="page-title" style={{ color: 'var(--text-primary)', fontSize: '36px', fontWeight: 700 }}>
            Dashboard
          </h1>          
          {/* Auto-sync status indicator */}
          <div className="mt-4 flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent border border-border">
              <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-primary animate-pulse' : 'bg-muted-foreground'}`}></div>
              <span className="text-xs font-medium text-foreground">
                {isRunning ? 'Auto-sync active' : 'Auto-sync inactive'}
              </span>
            </div>

            {lastSyncInfo && (
              <div className="text-xs font-medium text-muted-foreground px-3 py-1.5 rounded-full bg-accent border border-border animate-scale-in flex items-center gap-1.5">
                <svg className="w-3 h-3 text-primary" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                {lastSyncInfo.replace('✅ ', '')}
              </div>
            )}
          </div>
        </div>
        
        <div className="mt-6 flex gap-3 md:mt-0 md:ml-4">
          <button
            onClick={handleSyncCalendar}
            disabled={isSyncing}
            className="btn btn-outline px-4 py-2.5 text-sm"
          >
            <svg className={`w-4 h-4 mr-2 ${isSyncing ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {isSyncing ? 'Syncing...' : 'Sync Now'}
          </button>
          <button
            onClick={handleGenerateSummary}
            className="btn btn-primary px-4 py-2.5 text-sm"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
            </svg>
            Generate Summary
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {/* Total Meetings */}
        <div className="card card-hover p-5 group" style={{ backgroundColor: 'var(--bg-secondary)' }}>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform" style={{ backgroundColor: 'var(--orange-light-bg)' }}>
                <svg className="w-6 h-6" style={{ color: 'var(--orange-primary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                Total Meetings
              </p>
              <p className="text-5xl font-bold mt-1" style={{ color: 'var(--text-primary)' }}>
                {meetings.length}
              </p>
            </div>
          </div>
        </div>

        {/* Completed */}
        <div className="card card-hover p-5 group" style={{ backgroundColor: 'var(--bg-secondary)' }}>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform" style={{ backgroundColor: 'var(--orange-light-bg)' }}>
                <svg className="w-6 h-6" style={{ color: 'var(--orange-primary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                Completed
              </p>
              <p className="text-5xl font-bold mt-1" style={{ color: 'var(--text-primary)' }}>
                {meetings.filter(m => m.status === 'completed').length}
              </p>
            </div>
          </div>
        </div>

        {/* In Progress */}
        <div className="card card-hover p-5 group" style={{ backgroundColor: 'var(--bg-secondary)' }}>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform" style={{ backgroundColor: 'var(--orange-light-bg)' }}>
                <svg className="w-6 h-6" style={{ color: 'var(--orange-primary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                In Progress
              </p>
              <p className="text-5xl font-bold mt-1" style={{ color: 'var(--text-primary)' }}>
                {meetings.filter(m => m.status === 'in_progress').length}
              </p>
            </div>
          </div>
        </div>

        {/* Transcripts Link */}
        <Link href="/dashboard/transcripts" className="card card-hover p-5 group transition-all" style={{ backgroundColor: 'var(--bg-secondary)' }}>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform" style={{ backgroundColor: 'var(--orange-light-bg)' }}>
                <svg className="w-6 h-6" style={{ color: 'var(--orange-primary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                Transcripts
              </p>
              <p className="text-base font-semibold flex items-center gap-1 group-hover:opacity-80 transition-colors mt-1" style={{ color: 'var(--orange-primary)' }}>
                View All
                <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </p>
            </div>
          </div>
        </Link>

        {/* Recordings Link */}
        <Link href="/dashboard/recordings" className="card card-hover p-5 group transition-all" style={{ backgroundColor: 'var(--bg-secondary)' }}>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform" style={{ backgroundColor: 'var(--orange-light-bg)' }}>
                <svg className="w-6 h-6" style={{ color: 'var(--orange-primary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                Recordings
              </p>
              <p className="text-base font-semibold flex items-center gap-1 group-hover:opacity-80 transition-colors mt-1" style={{ color: 'var(--orange-primary)' }}>
                View All
                <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </p>
            </div>
          </div>
        </Link>
      </div>

      {/* Recent Summary */}
      {recentSummary && recentSummary.success && (
        <div className="card p-6 animate-scale-in">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg gradient-primary flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-foreground">Latest Summary</h3>
          </div>
          <div className="bg-muted rounded-xl p-4 border border-border">
            {recentSummary.summary && (
              <FormattedSummaryDisplay summaryText={recentSummary.summary} className="text-sm" />
            )}
            {recentSummary.metrics && (
              <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                    <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                  </svg>
                  Original: {recentSummary.metrics.original_words || 0} words
                </span>
                <span>•</span>
                <span>Summary: {recentSummary.metrics.summary_words || 0} words</span>
                <span>•</span>
                <span className="font-medium text-foreground">
                  {((recentSummary.metrics.compression_ratio || 0) * 100).toFixed(1)}% compression
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recent Meetings */}
      <div>
        <div className="mb-4">
          <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)', fontSize: '24px', fontWeight: 600 }}>
            Recent Meetings
          </h3>
          <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
            Your latest meeting activity
          </p>
        </div>
        
        {meetings.length === 0 ? (
          <div className="card p-12 text-center">
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center">
                <svg className="w-8 h-8 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-sm text-muted-foreground">No meetings yet. Create your first meeting!</p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {meetings.map((meeting) => {
              const formatMeetingTime = (dateString: string) => {
                const date = new Date(dateString);
                const today = new Date();
                const tomorrow = new Date(today);
                tomorrow.setDate(tomorrow.getDate() + 1);
                
                const isToday = date.toDateString() === today.toDateString();
                const isTomorrow = date.toDateString() === tomorrow.toDateString();
                
                const time = date.toLocaleTimeString('en-US', { 
                  hour: 'numeric', 
                  minute: '2-digit',
                  hour12: true 
                });
                
                if (isToday) return `Today, ${time}`;
                if (isTomorrow) return `Tomorrow, ${time}`;
                
                return date.toLocaleDateString('en-US', { 
                  month: 'short', 
                  day: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit',
                  hour12: true
                });
              };

              return (
                <Link 
                  key={meeting.id} 
                  href={`/dashboard/meetings/${meeting.id}`}
                  className="block rounded-lg border transition-all group"
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    borderColor: 'var(--border-primary)',
                    borderWidth: '1px',
                    padding: '16px 20px',
                    boxShadow: 'var(--shadow-sm)',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                  }}
                >
                  {/* Top row: Title and Status */}
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <h4 className="font-semibold transition-colors" style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {meeting.title}
                    </h4>
                    <span 
                      className="inline-flex items-center rounded-md text-xs font-medium flex-shrink-0"
                      style={{ 
                        backgroundColor: 'var(--orange-badge-bg)',
                        color: 'var(--orange-badge-text)',
                        padding: '4px 12px'
                      }}
                    >
                      {meeting.status === 'in_progress' ? 'In Progress'
                        : meeting.status === 'completed' ? 'Completed'
                        : meeting.status.charAt(0).toUpperCase() + meeting.status.slice(1)}
                    </span>
                  </div>

                  {/* Bottom row: Date/time and Google Meet link */}
                  <div className="flex items-center gap-4">
                    {meeting.start_time && (
                      <span className="text-sm" style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                        {formatMeetingTime(meeting.start_time)}
                      </span>
                    )}
                    
                    {meeting.meeting_url && meeting.meeting_url.includes('meet.google.com') && (
                      <div 
                        className="flex items-center gap-1.5 text-sm hover:text-primary transition-colors"
                        style={{ color: 'var(--text-secondary)' }}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          window.open(meeting.meeting_url, '_blank', 'noopener,noreferrer');
                        }}
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 3c1.93 0 3.5 1.57 3.5 3.5S13.93 13 12 13s-3.5-1.57-3.5-3.5S10.07 6 12 6zm7 13H5v-.23c0-.62.28-1.2.76-1.58C7.47 15.82 9.64 15 12 15s4.53.82 6.24 2.19c.48.38.76.97.76 1.58V19z"/>
                        </svg>
                        <span className="text-xs">Google Meet</span>
                      </div>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
