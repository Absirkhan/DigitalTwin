'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { meetingService, summarizationService } from '@/lib/api';
import type { Meeting, FormattedTranscript, SummarizationResponse, MeetingUpdate } from '@/lib/api/types';

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const meetingId = parseInt(params.id as string);

  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [transcript, setTranscript] = useState<FormattedTranscript | null>(null);
  const [summary, setSummary] = useState<SummarizationResponse | null>(null);
  const [recordingUrl, setRecordingUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingTranscript, setIsLoadingTranscript] = useState(false);
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<MeetingUpdate>({});
  const [botIdInput, setBotIdInput] = useState<string>('');
  const [autoJoinEnabled, setAutoJoinEnabled] = useState<boolean>(false);
  const [isUpdatingAutoJoin, setIsUpdatingAutoJoin] = useState(false);

  useEffect(() => {
    loadMeeting();
  }, [meetingId]);

  const loadMeeting = async () => {
    setIsLoading(true);
    try {
      const data = await meetingService.getById(meetingId);
      setMeeting(data);
      setEditForm({
        title: data.title,
        description: data.description,
        meeting_url: data.meeting_url,
        status: data.status,
        auto_join: data.auto_join,
      });
      // Set auto-join state
      setAutoJoinEnabled(data.auto_join ?? false);
      // Set bot_id if available from meeting
      if (data.bot_id) {
        setBotIdInput(data.bot_id);
      }
    } catch (error) {
      console.error('Failed to load meeting:', error);
      alert('Failed to load meeting');
    } finally {
      setIsLoading(false);
    }
  };

  const loadTranscript = async (botId: string) => {
    setIsLoadingTranscript(true);
    try {
      const data = await meetingService.getFormattedTranscript(botId);
      console.log('Transcript response:', data); // Debug log
      
      if (data.success && data.formatted_transcript) {
        // Accept either speaker_segments format or clean_continuous_text
        const transcript = data.formatted_transcript;
        if ((transcript.speaker_segments && Array.isArray(transcript.speaker_segments)) || 
            transcript.clean_continuous_text) {
          setTranscript(transcript);
        } else {
          console.error('Invalid transcript structure:', transcript);
          alert('Transcript received but format is invalid. Check console for details.');
        }
      } else {
        alert('Failed to load transcript: No data received');
      }
    } catch (error) {
      console.error('Transcript error:', error);
      alert('Failed to load transcript: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsLoadingTranscript(false);
    }
  };

  const loadRecordingUrl = async (botId: string) => {
    try {
      const data = await meetingService.getBotRecordingUrl(botId);
      if (data.success && data.video_url) {
        setRecordingUrl(data.video_url);
      }
    } catch (error) {
      console.error('Failed to load recording URL:', error);
    }
  };

  const generateSummary = async () => {
    if (!botIdInput) {
      alert('Please enter a Bot ID first');
      return;
    }
    setIsGeneratingSummary(true);
    try {
      const data = await summarizationService.generateForBot(botIdInput);
      setSummary(data);
    } catch (error) {
      alert('Failed to generate summary: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsGeneratingSummary(false);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await meetingService.update(meetingId, editForm);
      setIsEditing(false);
      await loadMeeting();
    } catch (error) {
      alert('Failed to update meeting: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this meeting?')) return;
    try {
      await meetingService.delete(meetingId);
      router.push('/dashboard/meetings');
    } catch (error) {
      alert('Failed to delete meeting: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  const handleToggleAutoJoin = async () => {
    setIsUpdatingAutoJoin(true);
    try {
      const newAutoJoinValue = !autoJoinEnabled;
      const result = await meetingService.toggleAutoJoin(meetingId, newAutoJoinValue);
      
      if (result.success) {
        setAutoJoinEnabled(result.auto_join);
        alert(`Auto-join ${result.auto_join ? 'enabled' : 'disabled'} successfully!`);
        // Reload meeting data to ensure consistency
        await loadMeeting();
      } else {
        alert('Failed to toggle auto-join setting');
      }
    } catch (error) {
      alert('Failed to toggle auto-join: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsUpdatingAutoJoin(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!meeting) {
    return <div className="text-center py-8 text-gray-500">Meeting not found</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between">
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate">
            {meeting.title}
          </h2>
        </div>
        <div className="mt-4 flex md:mt-0 md:ml-4 space-x-3">
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            {isEditing ? '❌ Cancel' : '✏️ Edit'}
          </button>
          <button
            onClick={handleDelete}
            className="inline-flex items-center px-4 py-2 border border-red-300 rounded-md shadow-sm text-sm font-medium text-red-700 bg-white hover:bg-red-50"
          >
            🗑️ Delete
          </button>
        </div>
      </div>

      {/* Edit Form */}
      {isEditing && (
        <div className="bg-white shadow sm:rounded-lg p-6">
          <form onSubmit={handleUpdate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Title</label>
              <input
                type="text"
                value={editForm.title || ''}
                onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Description</label>
              <textarea
                rows={3}
                value={editForm.description || ''}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Status</label>
              <select
                value={editForm.status || 'scheduled'}
                onChange={(e) => setEditForm({ ...editForm, status: e.target.value as any })}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="scheduled">Scheduled</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                id="autoJoinEdit"
                checked={editForm.auto_join ?? false}
                onChange={(e) => setEditForm({ ...editForm, auto_join: e.target.checked })}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <label htmlFor="autoJoinEdit" className="ml-2 block text-sm text-gray-700">
                Enable auto-join for this meeting
              </label>
            </div>
            <button
              type="submit"
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
            >
              💾 Save Changes
            </button>
          </form>
        </div>
      )}

      {/* Meeting Details */}
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-gray-500">Status</dt>
              <dd className="mt-1">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  meeting.status === 'completed' ? 'bg-green-100 text-green-800' :
                  meeting.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                  meeting.status === 'scheduled' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {meeting.status}
                </span>
              </dd>
            </div>
            {meeting.description && (
              <div className="sm:col-span-2">
                <dt className="text-sm font-medium text-gray-500">Description</dt>
                <dd className="mt-1 text-sm text-gray-900">{meeting.description}</dd>
              </div>
            )}
            {meeting.meeting_url && (
              <div className="sm:col-span-2">
                <dt className="text-sm font-medium text-gray-500">Meeting URL</dt>
                <dd className="mt-1 text-sm text-indigo-600">
                  <a href={meeting.meeting_url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                    {meeting.meeting_url}
                  </a>
                </dd>
              </div>
            )}
            {meeting.start_time && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Start Time</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(meeting.start_time).toLocaleString()}
                </dd>
              </div>
            )}
            {meeting.end_time && (
              <div>
                <dt className="text-sm font-medium text-gray-500">End Time</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(meeting.end_time).toLocaleString()}
                </dd>
              </div>
            )}
            <div>
              <dt className="text-sm font-medium text-gray-500">Auto-Join</dt>
              <dd className="mt-1">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  meeting.auto_join ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {meeting.auto_join ? '✅ Enabled' : '❌ Disabled'}
                </span>
              </dd>
            </div>
            {meeting.bot_id && (
              <div className="sm:col-span-2">
                <dt className="text-sm font-medium text-gray-500">Bot ID</dt>
                <dd className="mt-1 text-sm text-gray-900 font-mono bg-gray-50 px-2 py-1 rounded">
                  {meeting.bot_id}
                </dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      {/* Auto-Join Settings */}
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">⚙️ Auto-Join Settings</h3>
          
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex-1">
              <h4 className="text-sm font-medium text-gray-900">Auto-Join Meeting</h4>
              <p className="text-sm text-gray-500 mt-1">
                Automatically join this meeting when it starts. The bot will join and start recording/transcribing.
              </p>
            </div>
            
            <div className="flex items-center space-x-3">
              <label className="inline-flex items-center">
                <input
                  type="checkbox"
                  checked={autoJoinEnabled}
                  onChange={(e) => setAutoJoinEnabled(e.target.checked)}
                  className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                  disabled={isUpdatingAutoJoin}
                />
                <span className="ml-2 text-sm text-gray-700">
                  {autoJoinEnabled ? 'Enabled' : 'Disabled'}
                </span>
              </label>
              
              <button
                onClick={handleToggleAutoJoin}
                disabled={isUpdatingAutoJoin}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isUpdatingAutoJoin ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Saving...
                  </>
                ) : (
                  '💾 Save Settings'
                )}
              </button>
            </div>
          </div>
          
          {/* Status Indicator */}
          <div className="mt-4 flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${autoJoinEnabled ? 'bg-green-500' : 'bg-gray-400'}`}></div>
            <span className="text-sm text-gray-600">
              Auto-join is currently <strong>{autoJoinEnabled ? 'enabled' : 'disabled'}</strong> for this meeting
            </span>
          </div>
        </div>
      </div>

      {/* Bot ID Input Section */}
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">🤖 Bot Controls</h3>
          
          {/* Info Box */}
          {!meeting.bot_id && (
            <div className="mb-4 bg-blue-50 border-l-4 border-blue-400 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-blue-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-blue-700">
                    <strong>How to get a Bot ID:</strong>
                    <br />1. Go to the main meetings page
                    <br />2. Click "Join Meeting" and enter the meeting URL
                    <br />3. The bot will join and you'll receive a Bot ID
                    <br />4. Come back here and enter the Bot ID to access transcript and summary
                  </p>
                </div>
              </div>
            </div>
          )}
          
          <div className="space-y-4">
            <div>
              <label htmlFor="botIdInput" className="block text-sm font-medium text-gray-700 mb-2">
                Bot ID {meeting.bot_id && <span className="text-green-600">(Auto-filled from meeting)</span>}
              </label>
              <div className="flex space-x-3">
                <input
                  type="text"
                  id="botIdInput"
                  value={botIdInput}
                  onChange={(e) => setBotIdInput(e.target.value)}
                  placeholder="Enter Bot ID (UUID)"
                  className="flex-1 border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono"
                />
                <button
                  onClick={() => {
                    if (botIdInput) {
                      loadTranscript(botIdInput);
                      loadRecordingUrl(botIdInput);
                    }
                  }}
                  disabled={!botIdInput || isLoadingTranscript}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoadingTranscript ? '⏳ Loading...' : '📝 Load Transcript'}
                </button>
                <button
                  onClick={generateSummary}
                  disabled={!botIdInput || isGeneratingSummary}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isGeneratingSummary ? '⏳ Generating...' : '✨ Generate Summary'}
                </button>
              </div>
              <p className="mt-2 text-sm text-gray-500">
                Enter the Bot ID to load transcript and generate AI summary. 
                {!meeting.bot_id && ' You can get this ID after joining a meeting.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Section */}
      {summary && summary.success && (
        <div className="bg-white shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">AI Summary</h3>
            <div className="bg-gray-50 rounded-md p-4">
              <p className="text-gray-700 whitespace-pre-wrap">{summary.summary}</p>
              {summary.metrics && (
                <div className="mt-4 flex items-center space-x-4 text-sm text-gray-500">
                  <span>Original: {summary.metrics.original_words || 0} words</span>
                  <span>•</span>
                  <span>Summary: {summary.metrics.summary_words || 0} words</span>
                  <span>•</span>
                  <span>Compression: {((summary.metrics.compression_ratio || 0) * 100).toFixed(1)}%</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Transcript Section */}
      {transcript && (
        <div className="bg-white shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Transcript</h3>
            <div className="space-y-4">
              <div className="bg-gray-50 rounded-md p-4 max-h-96 overflow-y-auto">
                {transcript.speaker_segments && transcript.speaker_segments.length > 0 ? (
                  // Display speaker segments if available
                  transcript.speaker_segments.map((segment, index) => (
                    <div key={index} className="mb-3">
                      <p className="text-sm font-medium text-gray-900">{segment.speaker}</p>
                      <p className="text-sm text-gray-700">{segment.text}</p>
                    </div>
                  ))
                ) : (
                  // Fallback to clean continuous text
                  <div className="whitespace-pre-wrap text-sm text-gray-700">
                    {transcript.clean_continuous_text}
                  </div>
                )}
              </div>
              {transcript.total_words && (
                <p className="text-sm text-gray-500">Total words: {transcript.total_words}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Recording Section */}
      {recordingUrl && (
        <div className="bg-white shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Recording</h3>
            <video
              controls
              className="w-full rounded-lg"
              src={recordingUrl || undefined}
            >
              Your browser does not support the video tag.
            </video>
          </div>
        </div>
      )}
    </div>
  );
}
