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
    <div className="space-y-8">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between" style={{ marginBottom: '32px' }}>
        <div className="flex-1 min-w-0">
          <h1 className="page-title" style={{ color: 'var(--text-primary)', fontSize: '36px', fontWeight: 700 }}>
            Meeting Recordings
          </h1>
          <p className="page-subtitle" style={{ marginBottom: '0', color: 'var(--text-secondary)' }}>
            View and manage your meeting recordings by Bot ID
          </p>
        </div>
        <div className="mt-6 md:mt-0">
          <Link
            href="/dashboard/meetings"
            className="inline-flex items-center px-4 py-2 border rounded-md shadow-sm text-sm font-medium transition-colors"
            style={{ 
              borderColor: 'var(--border-primary)', 
              color: 'var(--text-primary)',
              backgroundColor: 'var(--bg-secondary)'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--bg-secondary)'}
          >
            ← Back to Meetings
          </Link>
        </div>
      </div>

      {/* Fetch Recording Form */}
      <div className="card p-6" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
        <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>Load Recording</h3>
        
        {/* Info Box */}
        <div 
          className="mb-6 rounded-lg" 
          style={{ 
            padding: '20px',
            backgroundColor: 'var(--orange-info-bg)',
            border: '1px solid var(--orange-info-border)'
          }}
        >
          <div className="flex gap-3">
            <div className="flex-shrink-0">
              <svg className="h-6 w-6" style={{ color: '#D97757' }} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>How to get recordings:</h4>
              <ol className="text-sm space-y-1 list-decimal list-inside" style={{ color: 'var(--text-secondary)' }}>
                <li>Join a meeting using the "Join Meeting" feature</li>
                <li>You'll receive a Bot ID when the bot joins</li>
                <li>After the meeting ends, enter the Bot ID here to view the recording</li>
                <li>The recording URL is fetched from the Recall API</li>
              </ol>
            </div>
          </div>
        </div>

        <form onSubmit={handleFetchRecording} className="space-y-4">
          <div>
            <label htmlFor="botId" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
              Bot ID (UUID)
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                id="botId"
                value={botIdInput}
                onChange={(e) => setBotIdInput(e.target.value)}
                placeholder="e.g., 6e2f74d9-1d11-4e82-a4d8-8b9966417330"
                className="input flex-1 font-mono"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || !botIdInput.trim()}
                className="px-6 py-2.5 text-sm rounded-lg font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center"
                style={{ 
                  backgroundColor: 'var(--orange-primary)',
                  opacity: (isLoading || !botIdInput.trim()) ? 0.5 : 1
                }}
                onMouseEnter={(e) => {
                  if (!(isLoading || !botIdInput.trim())) {
                    e.currentTarget.style.opacity = '0.9';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!(isLoading || !botIdInput.trim())) {
                    e.currentTarget.style.opacity = '1';
                  }
                }}
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
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Fetch Recording
                  </>
                )}
              </button>
            </div>
          </div>

          {error && (
            <div className="rounded-lg bg-muted/50 p-4 border border-border">
              <div className="flex gap-3">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-muted-foreground" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{error}</p>
                </div>
              </div>
            </div>
          )}
        </form>
      </div>

      {/* Recordings Grid */}
      {recordings.length > 0 && (
        <div className="space-y-6">
          <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Loaded Recordings ({recordings.length})</h3>
          
          <div className="grid grid-cols-1 gap-6">
            {recordings.map((recording, index) => (
              <div key={recording.bot_id} className="card p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex-1">
                    <h4 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                      Recording #{index + 1}
                    </h4>
                    <p className="mt-1 text-sm text-muted-foreground font-mono break-all">
                      Bot ID: {recording.bot_id}
                    </p>
                    {recording.recording_id && (
                      <p className="mt-1 text-xs text-muted-foreground font-mono break-all">
                        Recording ID: {recording.recording_id}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => handleRemoveRecording(recording.bot_id)}
                    className="ml-4 inline-flex items-center gap-2 px-3 py-1.5 border border-border rounded-md text-sm font-medium text-muted-foreground hover:bg-muted/50 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    Remove
                  </button>
                </div>

                {/* Recording Status */}
                {recording.recording_status && (
                  <div className="mb-4">
                    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                      recording.recording_status.code === 'done' 
                        ? 'bg-primary/10 text-primary border border-primary/20' 
                        : recording.recording_status.code === 'processing'
                        ? 'bg-secondary/10 text-secondary border border-secondary/20'
                        : 'bg-muted text-muted-foreground border border-border'
                    }`}>
                      {recording.recording_status.code === 'done' ? (
                        <>
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Ready
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          {recording.recording_status.code}
                        </>
                      )}
                    </span>
                    {recording.database_updated && (
                      <span className="ml-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                        </svg>
                        Saved to Database
                      </span>
                    )}
                  </div>
                )}

                {/* Recording Info Card */}
                <div className="bg-gradient-primary/5 rounded-lg p-6 border border-primary/20">
                  <div className="flex items-center justify-center mb-4">
                    <div className="p-4 bg-background/50 backdrop-blur-sm rounded-full shadow-md border border-primary/20">
                      <svg className="h-12 w-12 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </div>
                  </div>
                  
                  <h5 className="text-center text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                    Meeting Recording Ready
                  </h5>
                  <p className="text-center text-sm text-muted-foreground mb-6">
                    Your recording is ready to download. Click the button below to view or download the video.
                  </p>

                  {/* Download Button */}
                  <div className="flex flex-col sm:flex-row gap-3">
                    <a
                      href={recording.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-primary flex-1 justify-center px-6 py-3"
                    >
                      <svg className="mr-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                      Open Recording
                    </a>
                    <a
                      href={recording.download_url}
                      download={`meeting-recording-${recording.bot_id}.mp4`}
                      className="btn btn-outline flex-1 justify-center px-6 py-3"
                    >
                      <svg className="mr-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Download Video
                    </a>
                  </div>

                  {/* Recording URL */}
                  <div className="mt-4 pt-4 border-t border-border">
                    <p className="text-xs text-muted-foreground mb-2">Download URL:</p>
                    <div className="bg-muted/50 rounded px-3 py-2 border border-border">
                      <p className="text-xs font-mono text-muted-foreground break-all">
                        {recording.download_url}
                      </p>
                    </div>
                    {recording.expires_at && (
                      <p className="mt-2 text-xs text-muted-foreground flex items-center gap-1.5">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Expires: {new Date(recording.expires_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {recordings.length === 0 && (
        <div className="text-center py-16" style={{ background: 'transparent' }}>
          {/* Improved illustration with orange accents */}
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-primary/10 mx-auto mb-6">
            <svg className="w-12 h-12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Camera body */}
              <rect x="5" y="8" width="8" height="10" rx="1" stroke="#D97757" strokeWidth="2" fill="#FFF8F0"/>
              {/* Lens circles */}
              <circle cx="9" cy="13" r="2" stroke="#D97757" strokeWidth="1.5" fill="none"/>
              <circle cx="9" cy="13" r="1" fill="#D97757" opacity="0.5"/>
              {/* Recording indicator */}
              <circle cx="11" cy="9.5" r="1" fill="#D97757"/>
              {/* Film strip/signal lines */}
              <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14" stroke="#D97757" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          
          {/* Text hierarchy */}
          <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>No recordings loaded</h3>
          <p className="text-sm max-w-sm mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Enter a Bot ID above to load and view a meeting recording.
          </p>
        </div>
      )}
    </div>
  );
}
