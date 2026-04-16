'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { meetingService } from '@/lib/api';
import { useAutoSync } from '@/hooks/useAutoSync';
import type { Meeting, MeetingCreate, JoinMeetingRequest } from '@/lib/api/types';
import BotSpeakingWarning from '@/app/components/BotSpeakingWarning';

// Meeting Card Component
function MeetingCard({ meeting, onDelete }: { meeting: Meeting; onDelete: (id: number) => void }) {
  const formatMeetingTime = (dateString: string) => {
    // Backend sends UTC time, add 5 hours for Pakistan timezone (UTC+5)
    const date = new Date(dateString);
    const pakistanTime = new Date(date.getTime() + (5 * 60 * 60 * 1000));

    return pakistanTime.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  const getStatusBadge = (status: string) => {
    if (status === 'in_progress') {
      return (
        <span
          className="inline-flex items-center px-3 py-1 rounded-md text-xs font-medium"
          style={{ backgroundColor: 'var(--status-active-bg)', color: 'var(--status-active-text)' }}
        >
          Active
        </span>
      );
    } else if (status === 'scheduled') {
      return (
        <span
          className="inline-flex items-center px-3 py-1 rounded-md text-xs font-medium"
          style={{ backgroundColor: 'var(--status-scheduled-bg)', color: 'var(--status-scheduled-text)' }}
        >
          Scheduled
        </span>
      );
    } else if (status === 'completed') {
      return (
        <span
          className="inline-flex items-center px-3 py-1 rounded-md text-xs font-medium"
          style={{ backgroundColor: 'var(--status-completed-bg)', color: 'var(--status-completed-text)' }}
        >
          Completed
        </span>
      );
    }
    return null;
  };

  const getPlatformIcon = (url: string) => {
    if (url.includes('meet.google.com')) {
      return (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 3c1.93 0 3.5 1.57 3.5 3.5S13.93 13 12 13s-3.5-1.57-3.5-3.5S10.07 6 12 6zm7 13H5v-.23c0-.62.28-1.2.76-1.58C7.47 15.82 9.64 15 12 15s4.53.82 6.24 2.19c.48.38.76.97.76 1.58V19z"/>
        </svg>
      );
    }
    return (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    );
  };

  return (
    <Link href={`/dashboard/meetings/${meeting.id}`} className="group block">
      <div
        className="border rounded-lg transition-all"
        style={{ 
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-primary)', 
          borderWidth: '1px',
          borderRadius: '8px',
          padding: '20px',
          boxShadow: 'var(--shadow-sm)'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.boxShadow = 'var(--shadow-md)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
        }}
      >
        {/* Top row: Title and Status Badge */}
        <div className="flex items-start justify-between gap-4 mb-2">
          <h4 className="font-bold transition-colors flex-1" style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
            {meeting.title}
          </h4>
          <div className="flex items-center gap-2">
            {getStatusBadge(meeting.status)}

            {/* Bot Response Badge */}
            {meeting.bot_response_enabled && (
              <span
                className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium"
                style={{
                  backgroundColor: meeting.bot_response_count && meeting.bot_response_count > 0
                    ? 'var(--status-active-bg)'
                    : 'var(--status-scheduled-bg)',
                  color: meeting.bot_response_count && meeting.bot_response_count > 0
                    ? 'var(--status-active-text)'
                    : 'var(--status-scheduled-text)'
                }}
                title={`Bot speaking: ${meeting.bot_response_count || 0} / ${meeting.bot_max_responses || 10} responses`}
              >
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
                </svg>
                {meeting.bot_response_count || 0}/{meeting.bot_max_responses || 10}
              </span>
            )}

            {/* Delete button on hover */}
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (confirm('Are you sure you want to delete this meeting?')) {
                  onDelete(meeting.id);
                }
              }}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded hover:bg-red-50"
              style={{ color: '#9CA3AF' }}
              onMouseEnter={(e) => e.currentTarget.style.color = '#EF4444'}
              onMouseLeave={(e) => e.currentTarget.style.color = '#9CA3AF'}
              title="Delete meeting"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>

        {/* Second row: Date/time */}
        {meeting.start_time && (
          <div className="mb-2" style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            {formatMeetingTime(meeting.start_time)}
          </div>
        )}

        {/* Third row: Join meeting link with icon */}
        {meeting.meeting_url && (
          <div
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              window.open(meeting.meeting_url, '_blank', 'noopener,noreferrer');
            }}
            className="flex items-center gap-1.5 transition-colors cursor-pointer"
            style={{ color: 'var(--orange-primary)', fontSize: '14px' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.opacity = '0.8';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = '1';
            }}
          >
            {getPlatformIcon(meeting.meeting_url)}
            <span className="font-medium">Join meeting</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </div>
        )}
      </div>
    </Link>
  );
}

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [newMeeting, setNewMeeting] = useState<MeetingCreate>({
    title: '',
    description: '',
    meeting_url: '',
    platform: 'google_meet',
    scheduled_time: new Date().toISOString(),
    duration_minutes: 60,
    auto_join: false,
    bot_response_enabled: false,
    bot_response_style: 'professional',
    bot_max_responses: 10,
  });
  const [joinUrl, setJoinUrl] = useState('');
  const [joinConfig, setJoinConfig] = useState<JoinMeetingRequest>({
    meeting_url: '',
    bot_name: '',
    profile_picture: '',
    enable_realtime_processing: false,
    enable_video_recording: true,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Auto-sync hook for meetings (disabled - webhook handles all updates)
  const { isRunning, lastSync, forceSync } = useAutoSync({
    onMeetingsUpdate: (updatedMeetings) => {
      setMeetings(updatedMeetings);
      // Only turn off loading after initial data fetch
      if (isInitialLoad) {
        setIsInitialLoad(false);
      }
    },
    onError: (error) => {
      console.error('Auto-sync error:', error);
      // Don't show error alerts for background sync, just log
      // Still disable loading on error
      if (isInitialLoad) {
        setIsInitialLoad(false);
      }
    },
    enabled: false, // Disabled - only manual refresh via button
    syncInterval: 1000 // 1 second
  });

  // Load initial meetings on mount
  useEffect(() => {
    const loadMeetings = async () => {
      try {
        const data = await meetingService.getAll();
        setMeetings(data);
      } catch (error) {
        console.error('Failed to load meetings:', error);
      } finally {
        setIsInitialLoad(false);
      }
    };
    loadMeetings();
  }, []);

  const handleCreateMeeting = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await meetingService.create(newMeeting);
      setShowCreateModal(false);
      setNewMeeting({
        title: '',
        description: '',
        meeting_url: '',
        platform: 'google_meet',
        scheduled_time: new Date().toISOString(),
        duration_minutes: 60,
        auto_join: false,
        bot_response_enabled: false,
        bot_response_style: 'professional',
        bot_max_responses: 10,
      });
      // Auto-sync will pick up the new meeting automatically
      forceSync();
    } catch (error) {
      alert('Failed to create meeting: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleJoinMeeting = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const result = await meetingService.join(joinConfig);
      alert(`Bot joined successfully! Bot ID: ${result.bot_id}`);
      setShowJoinModal(false);
      setJoinConfig({
        meeting_url: '',
        bot_name: '',
        profile_picture: '',
        enable_realtime_processing: false,
        enable_video_recording: true,
      });
      // Auto-sync will pick up the changes automatically
      forceSync();
    } catch (error) {
      alert('Failed to join meeting: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteMeeting = async (id: number) => {
    if (!confirm('Are you sure you want to delete this meeting?')) return;
    try {
      await meetingService.delete(id);
      // Auto-sync will pick up the changes automatically
      forceSync();
    } catch (error) {
      alert('Failed to delete meeting: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  if (isInitialLoad) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-2 border-primary border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between" style={{ marginBottom: '32px' }}>
        <div className="flex-1 min-w-0">
          <h2 className="page-title" style={{ color: 'var(--text-primary)', fontSize: '36px', fontWeight: 700 }}>
            Meetings
          </h2>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
            Updates via webhook. Use Refresh button to manually update.
          </p>
        </div>
        <div className="mt-4 flex md:mt-0 md:ml-4 gap-3">
          <button
            onClick={forceSync}
            className="btn btn-outline inline-flex items-center px-3 py-2 text-sm"
            title="Manually refresh meetings"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <button
            onClick={() => setShowJoinModal(true)}
            className="btn btn-outline inline-flex items-center px-4 py-2"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Join Meeting
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary inline-flex items-center px-4 py-2"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create Meeting
          </button>
        </div>
      </div>

      {/* Meetings List */}
      <div className="grid gap-3">
        {meetings.length === 0 ? (
          <div className="card flex items-center justify-center" style={{ minHeight: '400px' }}>
            <div className="text-center max-w-md mx-auto px-6">
              {/* Orange-themed illustration */}
              <div className="mb-6 inline-flex items-center justify-center w-24 h-24 rounded-full bg-primary/10">
                <svg className="w-12 h-12 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 12v4m0 0l-2-2m2 2l2-2" />
                </svg>
              </div>
              
              {/* Text hierarchy */}
              <h3 className="font-semibold mb-2" style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' }}>
                No meetings found
              </h3>
              <p className="text-muted-foreground" style={{ fontSize: '14px', marginBottom: '24px' }}>
                You don't have any meeting bots yet.
              </p>
              
              {/* CTA Button */}
              <button
                onClick={() => setShowCreateModal(true)}
                className="btn btn-primary inline-flex items-center px-6 py-3"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Create Your First Meeting
              </button>
            </div>
          </div>
        ) : (
          (() => {
            // Group meetings by date
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const tomorrow = new Date(today);
            tomorrow.setDate(tomorrow.getDate() + 1);
            const nextWeek = new Date(today);
            nextWeek.setDate(nextWeek.getDate() + 7);

            const groupedMeetings = {
              today: [] as Meeting[],
              tomorrow: [] as Meeting[],
              thisWeek: [] as Meeting[],
              later: [] as Meeting[]
            };

            meetings.forEach((meeting) => {
              if (!meeting.start_time) {
                groupedMeetings.later.push(meeting);
                return;
              }
              
              const meetingDate = new Date(meeting.start_time);
              meetingDate.setHours(0, 0, 0, 0);
              
              if (meetingDate.getTime() === today.getTime()) {
                groupedMeetings.today.push(meeting);
              } else if (meetingDate.getTime() === tomorrow.getTime()) {
                groupedMeetings.tomorrow.push(meeting);
              } else if (meetingDate < nextWeek) {
                groupedMeetings.thisWeek.push(meeting);
              } else {
                groupedMeetings.later.push(meeting);
              }
            });

            return (
              <>
                {groupedMeetings.today.length > 0 && (
                  <div>
                    <h3 className="font-semibold mb-4" style={{ fontSize: '18px', fontWeight: 600, marginTop: '32px', color: 'var(--text-primary)' }}>
                      Today
                    </h3>
                    <div className="space-y-4">
                      {groupedMeetings.today.map((meeting) => (
                        <MeetingCard key={meeting.id} meeting={meeting} onDelete={handleDeleteMeeting} />
                      ))}
                    </div>
                  </div>
                )}

                {groupedMeetings.tomorrow.length > 0 && (
                  <div>
                    <h3 className="font-semibold mb-4" style={{ fontSize: '18px', fontWeight: 600, marginTop: '32px', color: 'var(--text-primary)' }}>
                      Tomorrow
                    </h3>
                    <div className="space-y-4">
                      {groupedMeetings.tomorrow.map((meeting) => (
                        <MeetingCard key={meeting.id} meeting={meeting} onDelete={handleDeleteMeeting} />
                      ))}
                    </div>
                  </div>
                )}

                {groupedMeetings.thisWeek.length > 0 && (
                  <div>
                    <h3 className="font-semibold mb-4" style={{ fontSize: '18px', fontWeight: 600, marginTop: '32px', color: 'var(--text-primary)' }}>
                      This Week
                    </h3>
                    <div className="space-y-4">
                      {groupedMeetings.thisWeek.map((meeting) => (
                        <MeetingCard key={meeting.id} meeting={meeting} onDelete={handleDeleteMeeting} />
                      ))}
                    </div>
                  </div>
                )}

                {groupedMeetings.later.length > 0 && (
                  <div>
                    <h3 className="font-semibold mb-4" style={{ fontSize: '18px', fontWeight: 600, marginTop: '32px', color: 'var(--text-primary)' }}>
                      Later
                    </h3>
                    <div className="space-y-4">
                      {groupedMeetings.later.map((meeting) => (
                        <MeetingCard key={meeting.id} meeting={meeting} onDelete={handleDeleteMeeting} />
                      ))}
                    </div>
                  </div>
                )}
              </>
            );
          })()
        )}
      </div>

      {/* Create Meeting Modal */}
      {showCreateModal && (
        <div className="fixed z-50 inset-0 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity" onClick={() => setShowCreateModal(false)}></div>
            <div className="relative inline-block align-bottom card rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6 z-50">
              <form onSubmit={handleCreateMeeting}>
                <div>
                  <h3 className="text-lg leading-6 font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
                    Create New Meeting
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <label htmlFor="title" className="block text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                        Title *
                      </label>
                      <input
                        type="text"
                        id="title"
                        required
                        value={newMeeting.title}
                        onChange={(e) => setNewMeeting({ ...newMeeting, title: e.target.value })}
                        className="input mt-1 block w-full"
                      />
                    </div>
                    <div>
                      <label htmlFor="description" className="block text-sm font-medium text-foreground">
                        Description
                      </label>
                      <textarea
                        id="description"
                        rows={3}
                        value={newMeeting.description}
                        onChange={(e) => setNewMeeting({ ...newMeeting, description: e.target.value })}
                        className="input mt-1 block w-full"
                      />
                    </div>
                    <div>
                      <label htmlFor="meeting_url" className="block text-sm font-medium text-foreground">
                        Meeting URL *
                      </label>
                      <input
                        type="url"
                        id="meeting_url"
                        required
                        value={newMeeting.meeting_url}
                        onChange={(e) => setNewMeeting({ ...newMeeting, meeting_url: e.target.value })}
                        placeholder="https://meet.google.com/xxx-xxxx-xxx"
                        className="input mt-1 block w-full"
                      />
                    </div>
                    <div>
                      <label htmlFor="platform" className="block text-sm font-medium text-foreground">
                        Platform *
                      </label>
                      <select
                        id="platform"
                        required
                        value={newMeeting.platform}
                        onChange={(e) => setNewMeeting({ ...newMeeting, platform: e.target.value })}
                        className="input mt-1 block w-full"
                      >
                        <option value="google_meet">Google Meet</option>
                        <option value="zoom">Zoom</option>
                        <option value="microsoft_teams">Microsoft Teams</option>
                        <option value="webex">Webex</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="scheduled_time" className="block text-sm font-medium text-foreground">
                        Scheduled Time *
                      </label>
                      <input
                        type="datetime-local"
                        id="scheduled_time"
                        required
                        value={newMeeting.scheduled_time.slice(0, 16)}
                        onChange={(e) => setNewMeeting({ ...newMeeting, scheduled_time: new Date(e.target.value).toISOString() })}
                        className="input mt-1 block w-full"
                      />
                    </div>
                    <div>
                      <label htmlFor="duration_minutes" className="block text-sm font-medium text-foreground">
                        Duration (minutes)
                      </label>
                      <input
                        type="number"
                        id="duration_minutes"
                        min="15"
                        step="15"
                        value={newMeeting.duration_minutes}
                        onChange={(e) => setNewMeeting({ ...newMeeting, duration_minutes: parseInt(e.target.value) })}
                        className="input mt-1 block w-full"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="auto_join"
                        checked={newMeeting.auto_join}
                        onChange={(e) => setNewMeeting({ ...newMeeting, auto_join: e.target.checked })}
                        className="h-4 w-4 text-primary focus:ring-primary border-border rounded"
                      />
                      <label htmlFor="auto_join" className="block text-sm text-foreground">
                        Auto-join meeting with bot
                      </label>
                    </div>

                    {/* Bot Speaking Section */}
                    <div className="border-t pt-4 mt-4" style={{ borderColor: 'var(--border-primary)' }}>
                      <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
                        Bot Speaking Settings (Experimental)
                      </h4>

                      {/* Enable Bot Speaking Toggle */}
                      <div className="flex items-center gap-2 mb-4">
                        <input
                          type="checkbox"
                          id="bot_response_enabled"
                          checked={newMeeting.bot_response_enabled}
                          onChange={(e) => setNewMeeting({ ...newMeeting, bot_response_enabled: e.target.checked })}
                          className="h-4 w-4 text-primary focus:ring-primary border-border rounded"
                        />
                        <label htmlFor="bot_response_enabled" className="block text-sm font-medium text-foreground">
                          Enable bot to respond when directly addressed
                        </label>
                      </div>

                      {/* Bot Speaking Configuration (shown when enabled) */}
                      {newMeeting.bot_response_enabled && (
                        <div className="space-y-4 ml-6 pl-4 border-l-2" style={{ borderColor: 'var(--orange-primary)' }}>
                          {/* Response Style */}
                          <div>
                            <label htmlFor="bot_response_style" className="block text-sm font-medium text-foreground mb-1">
                              Response Style
                            </label>
                            <select
                              id="bot_response_style"
                              value={newMeeting.bot_response_style}
                              onChange={(e) => setNewMeeting({ ...newMeeting, bot_response_style: e.target.value })}
                              className="input w-full"
                            >
                              <option value="professional">Professional (40 words max)</option>
                              <option value="casual">Casual (35 words max)</option>
                              <option value="technical">Technical (60 words max)</option>
                              <option value="brief">Brief (15 words max)</option>
                            </select>
                            <p className="mt-1 text-xs text-muted-foreground">
                              How the bot should communicate in meetings
                            </p>
                          </div>

                          {/* Max Responses */}
                          <div>
                            <label htmlFor="bot_max_responses" className="block text-sm font-medium text-foreground mb-1">
                              Maximum Responses: {newMeeting.bot_max_responses}
                            </label>
                            <input
                              type="range"
                              id="bot_max_responses"
                              min="1"
                              max="50"
                              value={newMeeting.bot_max_responses}
                              onChange={(e) => setNewMeeting({ ...newMeeting, bot_max_responses: parseInt(e.target.value) })}
                              className="w-full"
                            />
                            <div className="flex justify-between text-xs text-muted-foreground mt-1">
                              <span>1</span>
                              <span>50</span>
                            </div>
                            <p className="mt-1 text-xs text-muted-foreground">
                              Limit bot responses per meeting (30-second cooldown between responses)
                            </p>
                          </div>

                          {/* Warning Component */}
                          <div className="mt-4">
                            <BotSpeakingWarning variant="compact" />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                <div className="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="btn btn-primary w-full justify-center sm:col-start-2"
                  >
                    {isSubmitting ? 'Creating...' : 'Create'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="btn btn-outline mt-3 w-full justify-center sm:mt-0 sm:col-start-1"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Join Meeting Modal */}
      {showJoinModal && (
        <div className="fixed z-50 inset-0 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity" onClick={() => setShowJoinModal(false)}></div>
            <div className="relative inline-block align-bottom card rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6 z-50">
              <form onSubmit={handleJoinMeeting}>
                <div>
                  <h3 className="text-lg leading-6 font-semibold text-foreground mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    Join Meeting with Bot
                  </h3>
                  
                  <div className="space-y-4">
                    {/* Meeting URL */}
                    <div>
                      <label htmlFor="join_url" className="block text-sm font-medium text-foreground">
                        Meeting URL *
                      </label>
                      <input
                        type="url"
                        id="join_url"
                        required
                        value={joinConfig.meeting_url}
                        onChange={(e) => setJoinConfig({ ...joinConfig, meeting_url: e.target.value })}
                        placeholder="https://meet.google.com/xxx-xxxx-xxx"
                        className="input mt-1 block w-full"
                      />
                    </div>

                    {/* Bot Name */}
                    <div>
                      <label htmlFor="bot_name" className="block text-sm font-medium text-foreground">
                        Bot Name (Optional)
                      </label>
                      <input
                        type="text"
                        id="bot_name"
                        value={joinConfig.bot_name}
                        onChange={(e) => setJoinConfig({ ...joinConfig, bot_name: e.target.value })}
                        placeholder="My AI Assistant"
                        className="input mt-1 block w-full"
                      />
                      <p className="mt-1 text-xs text-muted-foreground">Custom name for the bot in the meeting</p>
                    </div>

                    {/* Profile Picture URL */}
                    <div>
                      <label htmlFor="profile_picture" className="block text-sm font-medium text-foreground">
                        Profile Picture URL (Optional)
                      </label>
                      <input
                        type="url"
                        id="profile_picture"
                        value={joinConfig.profile_picture}
                        onChange={(e) => setJoinConfig({ ...joinConfig, profile_picture: e.target.value })}
                        placeholder="https://example.com/avatar.png"
                        className="input mt-1 block w-full"
                      />
                      <p className="mt-1 text-xs text-muted-foreground">URL for bot's avatar image</p>
                    </div>

                    {/* Checkboxes */}
                    <div className="space-y-3 pt-2">
                      <div className="flex items-start gap-3">
                        <div className="flex items-center h-5">
                          <input
                            type="checkbox"
                            id="enable_video_recording"
                            checked={joinConfig.enable_video_recording}
                            onChange={(e) => setJoinConfig({ ...joinConfig, enable_video_recording: e.target.checked })}
                            className="h-4 w-4 text-primary focus:ring-primary border-border rounded"
                          />
                        </div>
                        <div className="flex-1">
                          <label htmlFor="enable_video_recording" className="text-sm font-medium text-foreground">
                            Enable Video Recording
                          </label>
                          <p className="text-xs text-muted-foreground">Record the meeting video</p>
                        </div>
                      </div>

                      <div className="flex items-start gap-3">
                        <div className="flex items-center h-5">
                          <input
                            type="checkbox"
                            id="enable_realtime_processing"
                            checked={joinConfig.enable_realtime_processing}
                            onChange={(e) => setJoinConfig({ ...joinConfig, enable_realtime_processing: e.target.checked })}
                            className="h-4 w-4 text-primary focus:ring-primary border-border rounded"
                          />
                        </div>
                        <div className="flex-1">
                          <label htmlFor="enable_realtime_processing" className="text-sm font-medium text-foreground">
                            Enable Realtime Processing
                          </label>
                          <p className="text-xs text-muted-foreground">Process transcript in real-time during the meeting</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="btn btn-primary w-full justify-center sm:col-start-2"
                  >
                    {isSubmitting ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Joining...
                      </>
                    ) : (
                      'Join Meeting'
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowJoinModal(false)}
                    className="btn btn-outline mt-3 w-full justify-center sm:mt-0 sm:col-start-1"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
