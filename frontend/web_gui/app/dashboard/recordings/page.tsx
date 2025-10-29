'use client';

import { useState } from 'react';
import { meetingService } from '@/lib/api';
import Link from 'next/link';

interface RecordingData {
  bot_id: string;
  download_url: string;
  success: boolean;
  recording_id?: string;
  recording_status?: {
    code: string;
    sub_code?: string | null;
    updated_at: string;
  };
  database_updated?: boolean;
  expires_at?: string | null;
}

export default function RecordingsPage() {
  const [botIdInput, setBotIdInput] = useState<string>('');
  const [recordings, setRecordings] = useState<RecordingData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFetchRecording = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!botIdInput.trim()) {
      setError('Please enter a Bot ID');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await meetingService.getBotRecordingUrl(botIdInput);
      console.log('Recording URL response:', data); // Debug log
      
      if (data.success && data.download_url) {
        // Add to recordings list (avoiding duplicates)
        setRecordings(prev => {
          const exists = prev.find(r => r.bot_id === botIdInput);
          if (exists) {
            return prev.map(r => 
              r.bot_id === botIdInput 
                ? { 
                    bot_id: botIdInput, 
                    download_url: data.download_url!, 
                    success: true,
                    recording_id: data.recording_id,
                    recording_status: data.recording_status,
                    database_updated: data.database_updated,
                    expires_at: data.expires_at,
                  }
                : r
            );
          }
          return [...prev, { 
            bot_id: botIdInput, 
            download_url: data.download_url!, 
            success: true,
            recording_id: data.recording_id,
            recording_status: data.recording_status,
            database_updated: data.database_updated,
            expires_at: data.expires_at,
          }];
        });
        setBotIdInput(''); // Clear input after successful fetch
      } else {
        setError(data.message || 'Failed to fetch recording');
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch recording');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveRecording = (botId: string) => {
    setRecordings(prev => prev.filter(r => r.bot_id !== botId));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between">
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate">
            📹 Meeting Recordings
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            View and manage your meeting recordings by Bot ID
          </p>
        </div>
        <div className="mt-4 md:mt-0">
          <Link
            href="/dashboard/meetings"
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            ← Back to Meetings
          </Link>
        </div>
      </div>

      {/* Fetch Recording Form */}
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Load Recording</h3>
          
          {/* Info Box */}
          <div className="mb-4 bg-blue-50 border-l-4 border-blue-400 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-blue-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-blue-700">
                  <strong>How to get recordings:</strong>
                  <br />1. Join a meeting using the "Join Meeting" feature
                  <br />2. You'll receive a Bot ID when the bot joins
                  <br />3. After the meeting ends, enter the Bot ID here to view the recording
                  <br />4. The recording URL is fetched from the Recall API
                </p>
              </div>
            </div>
          </div>

          <form onSubmit={handleFetchRecording} className="space-y-4">
            <div>
              <label htmlFor="botId" className="block text-sm font-medium text-gray-700 mb-2">
                Bot ID (UUID)
              </label>
              <div className="flex space-x-3">
                <input
                  type="text"
                  id="botId"
                  value={botIdInput}
                  onChange={(e) => setBotIdInput(e.target.value)}
                  placeholder="e.g., 6e2f74d9-1d11-4e82-a4d8-8b9966417330"
                  className="flex-1 border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={isLoading || !botIdInput.trim()}
                  className="inline-flex items-center px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  {isLoading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Loading...
                    </>
                  ) : (
                    <>📹 Fetch Recording</>
                  )}
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-md bg-red-50 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
              </div>
            )}
          </form>
        </div>
      </div>

      {/* Recordings Grid */}
      {recordings.length > 0 && (
        <div className="space-y-6">
          <h3 className="text-lg font-medium text-gray-900">Loaded Recordings ({recordings.length})</h3>
          
          <div className="grid grid-cols-1 gap-6">
            {recordings.map((recording, index) => (
              <div key={recording.bot_id} className="bg-white shadow rounded-lg overflow-hidden">
                <div className="px-4 py-5 sm:p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex-1">
                      <h4 className="text-base font-medium text-gray-900">
                        Recording #{index + 1}
                      </h4>
                      <p className="mt-1 text-sm text-gray-500 font-mono break-all">
                        Bot ID: {recording.bot_id}
                      </p>
                      {recording.recording_id && (
                        <p className="mt-1 text-xs text-gray-400 font-mono break-all">
                          Recording ID: {recording.recording_id}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => handleRemoveRecording(recording.bot_id)}
                      className="ml-4 inline-flex items-center px-3 py-1 border border-red-300 rounded-md shadow-sm text-sm font-medium text-red-700 bg-white hover:bg-red-50"
                    >
                      🗑️ Remove
                    </button>
                  </div>

                  {/* Recording Status */}
                  {recording.recording_status && (
                    <div className="mb-4">
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                        recording.recording_status.code === 'done' 
                          ? 'bg-green-100 text-green-800' 
                          : recording.recording_status.code === 'processing'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {recording.recording_status.code === 'done' ? '✅ Ready' : `⏳ ${recording.recording_status.code}`}
                      </span>
                      {recording.database_updated && (
                        <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          💾 Saved to Database
                        </span>
                      )}
                    </div>
                  )}

                  {/* Recording Info Card */}
                  <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-lg p-6 border border-indigo-200">
                    <div className="flex items-center justify-center mb-4">
                      <div className="p-4 bg-white rounded-full shadow-md">
                        <svg className="h-12 w-12 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      </div>
                    </div>
                    
                    <h5 className="text-center text-lg font-semibold text-gray-900 mb-2">
                      Meeting Recording Ready
                    </h5>
                    <p className="text-center text-sm text-gray-600 mb-6">
                      Your recording is ready to download. Click the button below to view or download the video.
                    </p>

                    {/* Download Button */}
                    <div className="flex flex-col sm:flex-row gap-3">
                      <a
                        href={recording.download_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 inline-flex items-center justify-center px-6 py-3 border border-transparent rounded-lg shadow-sm text-base font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                      >
                        <svg className="mr-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                        Open Recording
                      </a>
                      <a
                        href={recording.download_url}
                        download={`meeting-recording-${recording.bot_id}.mp4`}
                        className="flex-1 inline-flex items-center justify-center px-6 py-3 border border-indigo-300 rounded-lg shadow-sm text-base font-medium text-indigo-700 bg-white hover:bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                      >
                        <svg className="mr-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download Video
                      </a>
                    </div>

                    {/* Recording URL */}
                    <div className="mt-4 pt-4 border-t border-indigo-200">
                      <p className="text-xs text-gray-500 mb-2">Download URL:</p>
                      <div className="bg-white rounded px-3 py-2 border border-gray-200">
                        <p className="text-xs font-mono text-gray-600 break-all">
                          {recording.download_url}
                        </p>
                      </div>
                      {recording.expires_at && (
                        <p className="mt-2 text-xs text-gray-500">
                          ⏰ Expires: {new Date(recording.expires_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {recordings.length === 0 && (
        <div className="text-center py-12 bg-white shadow sm:rounded-lg">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No recordings loaded</h3>
          <p className="mt-1 text-sm text-gray-500">
            Enter a Bot ID above to load and view a meeting recording.
          </p>
        </div>
      )}
    </div>
  );
}
