'use client';

import { useState } from 'react';
import { meetingService, summarizationService } from '@/lib/api';
import type { FormattedTranscript, SummarizationResponse } from '@/lib/api/types';
import Link from 'next/link';

export default function TranscriptsPage() {
  const [botIdInput, setBotIdInput] = useState<string>('');
  const [transcript, setTranscript] = useState<FormattedTranscript | null>(null);
  const [summary, setSummary] = useState<SummarizationResponse | null>(null);
  const [isLoadingTranscript, setIsLoadingTranscript] = useState(false);
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTranscript = async () => {
    if (!botIdInput.trim()) {
      setError('Please enter a Bot ID');
      return;
    }

    setIsLoadingTranscript(true);
    setError(null);

    try {
      const data = await meetingService.getFormattedTranscript(botIdInput);
      console.log('Transcript response:', data); // Debug log
      
      if (data.success && data.formatted_transcript) {
        // Accept either speaker_segments format or clean_continuous_text
        const transcript = data.formatted_transcript;
        if ((transcript.speaker_segments && Array.isArray(transcript.speaker_segments)) || 
            transcript.clean_continuous_text) {
          setTranscript(transcript);
        } else {
          console.error('Invalid transcript structure:', transcript);
          setError('Transcript received but format is invalid. Check console for details.');
        }
      } else {
        setError('Failed to load transcript: No data received');
      }
    } catch (error) {
      console.error('Transcript error:', error);
      setError('Failed to load transcript: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsLoadingTranscript(false);
    }
  };

  const generateSummary = async () => {
    if (!botIdInput.trim()) {
      setError('Please enter a Bot ID');
      return;
    }

    setIsGeneratingSummary(true);
    setError(null);

    try {
      const data = await summarizationService.generateForBot(botIdInput);
      setSummary(data);
    } catch (error) {
      console.error('Summary error:', error);
      setError('Failed to generate summary: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsGeneratingSummary(false);
    }
  };

  const handleClear = () => {
    setBotIdInput('');
    setTranscript(null);
    setSummary(null);
    setError(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between">
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate">
            📝 Transcripts & AI Summaries
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Access meeting transcripts and generate AI-powered summaries using Bot IDs
          </p>
        </div>
        <div className="mt-4 md:mt-0 flex space-x-3">
          <Link
            href="/dashboard/meetings"
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            📅 View Meetings
          </Link>
          <Link
            href="/dashboard/recordings"
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            📹 View Recordings
          </Link>
        </div>
      </div>

      {/* Bot ID Input Section */}
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">🤖 Enter Bot ID</h3>
          
          {/* Info Box */}
          <div className="mb-6 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-3">
                <h4 className="text-sm font-semibold text-blue-900 mb-2">How to get a Bot ID:</h4>
                <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                  <li>Go to the <Link href="/dashboard/meetings" className="underline hover:text-blue-600">Meetings page</Link></li>
                  <li>Click "Join Meeting" and enter your meeting URL</li>
                  <li>The bot will join the meeting and you'll receive a Bot ID</li>
                  <li>Copy the Bot ID and paste it here to access transcripts and summaries</li>
                </ol>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label htmlFor="botIdInput" className="block text-sm font-medium text-gray-700 mb-2">
                Bot ID (UUID Format)
              </label>
              <div className="flex space-x-3">
                <input
                  type="text"
                  id="botIdInput"
                  value={botIdInput}
                  onChange={(e) => setBotIdInput(e.target.value)}
                  placeholder="e.g., 7b34cc53-a92b-445f-942e-daf3ed697d0b"
                  className="flex-1 border border-gray-300 rounded-md shadow-sm py-3 px-4 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono"
                />
                <button
                  onClick={handleClear}
                  disabled={!botIdInput && !transcript && !summary}
                  className="inline-flex items-center px-4 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  🔄 Clear
                </button>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={loadTranscript}
                disabled={!botIdInput.trim() || isLoadingTranscript}
                className="flex-1 inline-flex items-center justify-center px-6 py-3 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                {isLoadingTranscript ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Loading...
                  </>
                ) : (
                  <>📝 Load Transcript</>
                )}
              </button>
              
              <button
                onClick={generateSummary}
                disabled={!botIdInput.trim() || isGeneratingSummary}
                className="flex-1 inline-flex items-center justify-center px-6 py-3 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
              >
                {isGeneratingSummary ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Generating...
                  </>
                ) : (
                  <>✨ Generate AI Summary</>
                )}
              </button>
            </div>

            {/* Instructions */}
            <p className="text-sm text-gray-500">
              Enter a Bot ID to load the meeting transcript and generate an AI-powered summary. 
              You can get Bot IDs by joining meetings through the Meetings page.
            </p>

            {/* Error Display */}
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
          </div>
        </div>
      </div>

      {/* AI Summary Section */}
      {summary && summary.success && (
        <div className="bg-white shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">✨ AI Summary</h3>
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                Powered by FLAN-T5-Large
              </span>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-lg p-6 border border-purple-200">
              <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">{summary.summary}</p>
              {summary.metrics && (
                <div className="mt-6 pt-4 border-t border-purple-200 flex flex-wrap items-center gap-4 text-sm text-gray-600">
                  <div className="flex items-center">
                    <span className="font-medium">Original:</span>
                    <span className="ml-1">{summary.metrics.original_words || 0} words</span>
                  </div>
                  <div className="flex items-center">
                    <span className="font-medium">Summary:</span>
                    <span className="ml-1">{summary.metrics.summary_words || 0} words</span>
                  </div>
                  <div className="flex items-center">
                    <span className="font-medium">Compression:</span>
                    <span className="ml-1">{((summary.metrics.compression_ratio || 0) * 100).toFixed(1)}%</span>
                  </div>
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
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">📝 Meeting Transcript</h3>
              {transcript.total_words && (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 text-indigo-800">
                  {transcript.total_words} words
                </span>
              )}
            </div>
            <div className="bg-gray-50 rounded-lg border border-gray-200">
              <div className="p-4 max-h-96 overflow-y-auto">
                {transcript.speaker_segments && transcript.speaker_segments.length > 0 ? (
                  // Display speaker segments if available
                  <div className="space-y-4">
                    {transcript.speaker_segments.map((segment, index) => (
                      <div key={index} className="bg-white rounded-md p-3 border border-gray-200">
                        <p className="text-sm font-semibold text-indigo-900 mb-2">{segment.speaker}</p>
                        <p className="text-sm text-gray-700 leading-relaxed">{segment.text}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  // Fallback to clean continuous text
                  <div className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">
                    {transcript.clean_continuous_text}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!transcript && !summary && !error && (
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
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No content loaded</h3>
          <p className="mt-1 text-sm text-gray-500">
            Enter a Bot ID above to load transcripts and generate AI summaries.
          </p>
        </div>
      )}
    </div>
  );
}