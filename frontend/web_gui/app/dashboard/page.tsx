'use client';

import { useEffect, useState } from 'react';
import { meetingService, summarizationService, calendarService } from '@/lib/api';
import { useAutoSync } from '@/hooks/useAutoSync';
import type { Meeting, SummarizationResponse } from '@/lib/api/types';
import Link from 'next/link';

export default function DashboardPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [recentSummary, setRecentSummary] = useState<SummarizationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncInfo, setLastSyncInfo] = useState<string>('');

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
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      const meetingsData = await meetingService.getAll();
      setMeetings(meetingsData.slice(0, 5)); // Show only 5 most recent
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
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
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between">
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate">
            Dashboard
          </h2>
          
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
        <div className="mt-4 flex md:mt-0 md:ml-4 space-x-3">
          <button
            onClick={handleSyncCalendar}
            disabled={isSyncing}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {isSyncing ? 'Syncing...' : '🔄 Sync Now'}
          </button>
          <button
            onClick={handleGenerateSummary}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            ✨ Generate Summary
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <span className="text-3xl">📅</span>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Meetings
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {meetings.length}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <span className="text-3xl">✅</span>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Completed
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {meetings.filter(m => m.status === 'completed').length}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <span className="text-3xl">📊</span>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    In Progress
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {meetings.filter(m => m.status === 'in_progress').length}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <Link href="/dashboard/transcripts" className="bg-gradient-to-br from-purple-500 to-indigo-600 overflow-hidden shadow rounded-lg hover:shadow-lg transition-shadow">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <span className="text-3xl">📝</span>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-white truncate">
                    Transcripts
                  </dt>
                  <dd className="text-lg font-medium text-white">
                    View All →
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </Link>

        <Link href="/dashboard/recordings" className="bg-gradient-to-br from-indigo-500 to-purple-600 overflow-hidden shadow rounded-lg hover:shadow-lg transition-shadow">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <span className="text-3xl">📹</span>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-white truncate">
                    Recordings
                  </dt>
                  <dd className="text-lg font-medium text-white">
                    View All →
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </Link>
      </div>

      {/* Recent Summary */}
      {recentSummary && recentSummary.success && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Latest Summary</h3>
          <div className="bg-gray-50 rounded-md p-4">
            <p className="text-gray-700 whitespace-pre-wrap">{recentSummary.summary}</p>
            {recentSummary.metrics && (
              <div className="mt-4 flex items-center space-x-4 text-sm text-gray-500">
                <span>Original: {recentSummary.metrics.original_words || 0} words</span>
                <span>•</span>
                <span>Summary: {recentSummary.metrics.summary_words || 0} words</span>
                <span>•</span>
                <span>Compression: {((recentSummary.metrics.compression_ratio || 0) * 100).toFixed(1)}%</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recent Meetings */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Recent Meetings
          </h3>
        </div>
        <ul className="divide-y divide-gray-200">
          {meetings.length === 0 ? (
            <li className="px-4 py-4 text-center text-gray-500">
              No meetings yet. Create your first meeting!
            </li>
          ) : (
            meetings.map((meeting) => (
              <li key={meeting.id} className="px-4 py-4 sm:px-6 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-indigo-600 truncate">
                      {meeting.title}
                    </p>
                    {meeting.description && (
                      <p className="mt-1 text-sm text-gray-500 truncate">
                        {meeting.description}
                      </p>
                    )}
                    <div className="mt-2 flex items-center text-sm text-gray-500">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        meeting.status === 'completed' ? 'bg-green-100 text-green-800' :
                        meeting.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                        meeting.status === 'scheduled' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {meeting.status}
                      </span>
                      {meeting.start_time && (
                        <span className="ml-4">
                          {new Date(meeting.start_time).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
