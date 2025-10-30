'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { meetingService } from '@/lib/api';
import { useAutoSync } from '@/hooks/useAutoSync';
import type { Meeting, MeetingCreate, JoinMeetingRequest } from '@/lib/api/types';

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [lastSyncInfo, setLastSyncInfo] = useState<string>('');
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

  // Auto-sync hook for calendar and meetings
  const { isRunning, lastSync, forceSync } = useAutoSync({
    onMeetingsUpdate: (updatedMeetings) => {
      setMeetings(updatedMeetings);
      // Only turn off loading after initial data fetch
      if (isInitialLoad) {
        setIsInitialLoad(false);
      }
    },
    onSyncSuccess: (eventsSynced) => {
      if (eventsSynced > 0) {
        setLastSyncInfo(`✅ Synced ${eventsSynced} events at ${new Date().toLocaleTimeString()}`);
        // Clear the message after 3 seconds
        setTimeout(() => setLastSyncInfo(''), 3000);
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
    enabled: true,
    syncInterval: 1000 // 1 second
  });

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
            📅 Meetings
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
            onClick={forceSync}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            title="Force immediate sync"
          >
            🔄 Sync Now
          </button>
          <button
            onClick={() => setShowJoinModal(true)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            🤖 Join Meeting
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            ➕ Create Meeting
          </button>
        </div>
      </div>

      {/* Meetings List */}
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {meetings.length === 0 ? (
            <li className="px-4 py-8 text-center text-gray-500">
              No meetings yet. Create your first meeting!
            </li>
          ) : (
            meetings.map((meeting) => (
              <li key={meeting.id}>
                <Link href={`/dashboard/meetings/${meeting.id}`} className="block hover:bg-gray-50">
                  <div className="px-4 py-4 sm:px-6">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-indigo-600 truncate">
                          {meeting.title}
                        </p>
                        {meeting.description && (
                          <p className="mt-1 text-sm text-gray-500">
                            {meeting.description}
                          </p>
                        )}
                      </div>
                      <div className="ml-4 flex-shrink-0 flex items-center space-x-2">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          meeting.status === 'completed' ? 'bg-green-100 text-green-800' :
                          meeting.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                          meeting.status === 'scheduled' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {meeting.status}
                        </span>
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            handleDeleteMeeting(meeting.id);
                          }}
                          className="text-red-600 hover:text-red-800"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                    <div className="mt-2 sm:flex sm:justify-between">
                      <div className="sm:flex">
                        <p className="flex items-center text-sm text-gray-500">
                          {meeting.start_time && (
                            <>📅 {new Date(meeting.start_time).toLocaleString()}</>
                          )}
                        </p>
                      </div>
                      {meeting.meeting_url && (
                        <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                          🔗 {new URL(meeting.meeting_url).hostname}
                        </div>
                      )}
                    </div>
                  </div>
                </Link>
              </li>
            ))
          )}
        </ul>
      </div>

      {/* Create Meeting Modal */}
      {showCreateModal && (
        <div className="fixed z-50 inset-0 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowCreateModal(false)}></div>
            <div className="relative inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6 z-50">
              <form onSubmit={handleCreateMeeting}>
                <div>
                  <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                    Create New Meeting
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                        Title *
                      </label>
                      <input
                        type="text"
                        id="title"
                        required
                        value={newMeeting.title}
                        onChange={(e) => setNewMeeting({ ...newMeeting, title: e.target.value })}
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                        Description
                      </label>
                      <textarea
                        id="description"
                        rows={3}
                        value={newMeeting.description}
                        onChange={(e) => setNewMeeting({ ...newMeeting, description: e.target.value })}
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label htmlFor="meeting_url" className="block text-sm font-medium text-gray-700">
                        Meeting URL *
                      </label>
                      <input
                        type="url"
                        id="meeting_url"
                        required
                        value={newMeeting.meeting_url}
                        onChange={(e) => setNewMeeting({ ...newMeeting, meeting_url: e.target.value })}
                        placeholder="https://meet.google.com/xxx-xxxx-xxx"
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label htmlFor="platform" className="block text-sm font-medium text-gray-700">
                        Platform *
                      </label>
                      <select
                        id="platform"
                        required
                        value={newMeeting.platform}
                        onChange={(e) => setNewMeeting({ ...newMeeting, platform: e.target.value })}
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      >
                        <option value="google_meet">Google Meet</option>
                        <option value="zoom">Zoom</option>
                        <option value="microsoft_teams">Microsoft Teams</option>
                        <option value="webex">Webex</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="scheduled_time" className="block text-sm font-medium text-gray-700">
                        Scheduled Time *
                      </label>
                      <input
                        type="datetime-local"
                        id="scheduled_time"
                        required
                        value={newMeeting.scheduled_time.slice(0, 16)}
                        onChange={(e) => setNewMeeting({ ...newMeeting, scheduled_time: new Date(e.target.value).toISOString() })}
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label htmlFor="duration_minutes" className="block text-sm font-medium text-gray-700">
                        Duration (minutes)
                      </label>
                      <input
                        type="number"
                        id="duration_minutes"
                        min="15"
                        step="15"
                        value={newMeeting.duration_minutes}
                        onChange={(e) => setNewMeeting({ ...newMeeting, duration_minutes: parseInt(e.target.value) })}
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      />
                    </div>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="auto_join"
                        checked={newMeeting.auto_join}
                        onChange={(e) => setNewMeeting({ ...newMeeting, auto_join: e.target.checked })}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                      />
                      <label htmlFor="auto_join" className="ml-2 block text-sm text-gray-700">
                        Auto-join meeting with bot
                      </label>
                    </div>
                  </div>
                </div>
                <div className="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:col-start-2 sm:text-sm disabled:opacity-50"
                  >
                    {isSubmitting ? 'Creating...' : 'Create'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:col-start-1 sm:text-sm"
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
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowJoinModal(false)}></div>
            <div className="relative inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6 z-50">
              <form onSubmit={handleJoinMeeting}>
                <div>
                  <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                    🤖 Join Meeting with Bot
                  </h3>
                  
                  <div className="space-y-4">
                    {/* Meeting URL */}
                    <div>
                      <label htmlFor="join_url" className="block text-sm font-medium text-gray-700">
                        Meeting URL *
                      </label>
                      <input
                        type="url"
                        id="join_url"
                        required
                        value={joinConfig.meeting_url}
                        onChange={(e) => setJoinConfig({ ...joinConfig, meeting_url: e.target.value })}
                        placeholder="https://meet.google.com/xxx-xxxx-xxx"
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      />
                    </div>

                    {/* Bot Name */}
                    <div>
                      <label htmlFor="bot_name" className="block text-sm font-medium text-gray-700">
                        Bot Name (Optional)
                      </label>
                      <input
                        type="text"
                        id="bot_name"
                        value={joinConfig.bot_name}
                        onChange={(e) => setJoinConfig({ ...joinConfig, bot_name: e.target.value })}
                        placeholder="My AI Assistant"
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      />
                      <p className="mt-1 text-xs text-gray-500">Custom name for the bot in the meeting</p>
                    </div>

                    {/* Profile Picture URL */}
                    <div>
                      <label htmlFor="profile_picture" className="block text-sm font-medium text-gray-700">
                        Profile Picture URL (Optional)
                      </label>
                      <input
                        type="url"
                        id="profile_picture"
                        value={joinConfig.profile_picture}
                        onChange={(e) => setJoinConfig({ ...joinConfig, profile_picture: e.target.value })}
                        placeholder="https://example.com/avatar.png"
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      />
                      <p className="mt-1 text-xs text-gray-500">URL for bot's avatar image</p>
                    </div>

                    {/* Checkboxes */}
                    <div className="space-y-3 pt-2">
                      <div className="flex items-start">
                        <div className="flex items-center h-5">
                          <input
                            type="checkbox"
                            id="enable_video_recording"
                            checked={joinConfig.enable_video_recording}
                            onChange={(e) => setJoinConfig({ ...joinConfig, enable_video_recording: e.target.checked })}
                            className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                          />
                        </div>
                        <div className="ml-3">
                          <label htmlFor="enable_video_recording" className="text-sm font-medium text-gray-700">
                            Enable Video Recording
                          </label>
                          <p className="text-xs text-gray-500">Record the meeting video</p>
                        </div>
                      </div>

                      <div className="flex items-start">
                        <div className="flex items-center h-5">
                          <input
                            type="checkbox"
                            id="enable_realtime_processing"
                            checked={joinConfig.enable_realtime_processing}
                            onChange={(e) => setJoinConfig({ ...joinConfig, enable_realtime_processing: e.target.checked })}
                            className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                          />
                        </div>
                        <div className="ml-3">
                          <label htmlFor="enable_realtime_processing" className="text-sm font-medium text-gray-700">
                            Enable Realtime Processing
                          </label>
                          <p className="text-xs text-gray-500">Process transcript in real-time during the meeting</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:col-start-2 sm:text-sm disabled:opacity-50"
                  >
                    {isSubmitting ? '⏳ Joining...' : '🚀 Join Meeting'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowJoinModal(false)}
                    className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:col-start-1 sm:text-sm"
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
