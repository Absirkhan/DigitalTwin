'use client';

import { useState } from 'react';
import { meetingService, summarizationService } from '@/lib/api';
import type { FormattedTranscript, SummarizationResponse } from '@/lib/api/types';
import Link from 'next/link';
import { FormattedSummaryDisplay } from '@/app/components/FormattedSummaryDisplay';

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
      <div className="md:flex md:items-center md:justify-between" style={{ marginBottom: '32px' }}>
        <div className="flex-1 min-w-0">
          <h2 className="page-title" style={{ color: 'var(--text-primary)', fontSize: '36px', fontWeight: 700 }}>
            Transcripts & AI Summaries
          </h2>
        </div>
        <div className="mt-4 md:mt-0 flex gap-3">
          <Link
            href="/dashboard/meetings"
            className="btn btn-outline inline-flex items-center gap-2 px-4 py-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            View Meetings
          </Link>
          <Link
            href="/dashboard/recordings"
            className="btn btn-outline inline-flex items-center gap-2 px-4 py-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            View Recordings
          </Link>
        </div>
      </div>

      {/* Bot ID Input Section */}
      <div className="card p-6" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-primary)' }}>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
          <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          Enter Bot ID
        </h3>
        
        {/* Info Box */}
        <div className="mb-6 rounded-lg" style={{ padding: '20px', backgroundColor: 'var(--orange-info-bg)', border: '1px solid var(--orange-info-border)' }}>
          <div className="flex gap-3">
            <div className="flex-shrink-0">
              <svg className="h-6 w-6 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>How to get a Bot ID:</h4>
              <ol className="text-sm space-y-1 list-decimal list-inside" style={{ color: 'var(--text-secondary)' }}>
                <li>Go to the <Link href="/dashboard/meetings" className="text-primary font-medium hover:underline transition-all">Meetings page</Link></li>
                <li>Click "Join Meeting" and enter your meeting URL</li>
                <li>The bot will join the meeting and you'll receive a Bot ID</li>
                <li>Copy the Bot ID and paste it here to access transcripts and summaries</li>
              </ol>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label htmlFor="botIdInput" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
              Bot ID (UUID Format)
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                id="botIdInput"
                value={botIdInput}
                onChange={(e) => setBotIdInput(e.target.value)}
                placeholder="e.g., 7b34cc53-a92b-445f-942e-daf3ed697d0b"
                className="input flex-1 py-3 px-4 font-mono"
              />
              <button
                onClick={handleClear}
                disabled={!botIdInput && !transcript && !summary}
                className="btn btn-outline inline-flex items-center gap-2 px-4 py-3"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Clear
              </button>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={loadTranscript}
              disabled={!botIdInput.trim() || isLoadingTranscript}
              className="flex-1 justify-center px-6 py-3 rounded-lg font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center"
              style={{ 
                backgroundColor: 'var(--orange-primary)',
                opacity: (!botIdInput.trim() || isLoadingTranscript) ? 0.5 : 1
              }}
              onMouseEnter={(e) => {
                if (!(!botIdInput.trim() || isLoadingTranscript)) {
                  e.currentTarget.style.opacity = '0.9';
                }
              }}
              onMouseLeave={(e) => {
                if (!(!botIdInput.trim() || isLoadingTranscript)) {
                  e.currentTarget.style.opacity = '1';
                }
              }}
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
                <>
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Load Transcript
                </>
              )}
            </button>
            
            <button
              onClick={generateSummary}
              disabled={!botIdInput.trim() || isGeneratingSummary}
              className="flex-1 justify-center px-6 py-3 rounded-lg font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center"
              style={{ 
                backgroundColor: 'var(--orange-primary)',
                opacity: (!botIdInput.trim() || isGeneratingSummary) ? 0.5 : 1
              }}
              onMouseEnter={(e) => {
                if (!(!botIdInput.trim() || isGeneratingSummary)) {
                  e.currentTarget.style.opacity = '0.9';
                }
              }}
              onMouseLeave={(e) => {
                if (!(!botIdInput.trim() || isGeneratingSummary)) {
                  e.currentTarget.style.opacity = '1';
                }
              }}
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
                <>
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Generate AI Summary
                </>
              )}
            </button>
          </div>

          {/* Error Display */}
          {error && (
            <div className="rounded-xl bg-[#C56846]/10 p-4 border border-[#C56846]/30 animate-scale-in">
              <div className="flex gap-3">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-[#C56846]" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-[#C56846]">{error}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Summary Section */}
      {summary && summary.success && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <svg className="w-5 h-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              AI Summary
            </h3>
            <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium bg-gradient-secondary/10 text-secondary border border-secondary/20">
              Powered by FLAN-T5-Large
            </span>
          </div>
          <div className="bg-gradient-secondary/5 rounded-lg p-6 border border-secondary/20">
            {summary.summary && (
              <FormattedSummaryDisplay summaryText={summary.summary} />
            )}
            {summary.metrics && (
              <div className="mt-6 pt-4 border-t border-secondary/20 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <span className="font-medium" style={{ color: 'var(--text-primary)' }}>Original:</span>
                  <span>{summary.metrics.original_words || 0} words</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="font-medium" style={{ color: 'var(--text-primary)' }}>Summary:</span>
                  <span>{summary.metrics.summary_words || 0} words</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="font-medium" style={{ color: 'var(--text-primary)' }}>Compression:</span>
                  <span>{((summary.metrics.compression_ratio || 0) * 100).toFixed(1)}%</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Transcript Section */}
      {transcript && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Meeting Transcript
            </h3>
            {transcript.total_words && (
              <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium bg-gradient-primary/10 text-primary border border-primary/20">
                {transcript.total_words} words
              </span>
            )}
          </div>
          <div className="bg-muted/30 rounded-lg border border-border">
            <div className="p-4 max-h-96 overflow-y-auto">
              {transcript.speaker_segments && transcript.speaker_segments.length > 0 ? (
                // Display speaker segments if available
                <div className="space-y-4">
                  {transcript.speaker_segments.map((segment, index) => (
                    <div key={index} className="bg-background/50 backdrop-blur-sm rounded-md p-3 border border-border">
                      <p className="text-sm font-semibold text-primary mb-2">{segment.speaker}</p>
                      <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>{segment.text}</p>
                    </div>
                  ))}
                </div>
              ) : (
                // Fallback to clean continuous text
                <div className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                  {transcript.clean_continuous_text}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!transcript && !summary && !error && (
        <div className="text-center py-16" style={{ background: 'transparent' }}>
          {/* Custom Orange-Themed Document Illustration - 80px */}
          <svg 
            width="80" 
            height="80" 
            viewBox="0 0 80 80" 
            fill="none" 
            xmlns="http://www.w3.org/2000/svg"
            style={{ margin: '0 auto 24px' }}
          >
            {/* Main document with gradient background */}
            <rect x="15" y="10" width="50" height="60" rx="4" fill="#FFF8F0"/>
            <rect x="15" y="10" width="50" height="60" rx="4" stroke="#D97757" strokeWidth="2"/>
            
            {/* Folded corner with depth effect */}
            <path d="M55 10 L55 20 L65 20 Z" fill="#FAF9F6" stroke="#D97757" strokeWidth="2" strokeLinejoin="round"/>
            <path d="M55 10 L55 20 L65 20" stroke="#D97757" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            
            {/* Header section with orange background */}
            <rect x="20" y="18" width="30" height="4" rx="2" fill="#D97757" opacity="0.3"/>
            
            {/* Text lines - varying opacity for depth */}
            <rect x="20" y="28" width="35" height="2" rx="1" fill="#D97757" opacity="0.6"/>
            <rect x="20" y="33" width="35" height="2" rx="1" fill="#D97757" opacity="0.6"/>
            <rect x="20" y="38" width="28" height="2" rx="1" fill="#D97757" opacity="0.4"/>
            
            {/* Highlighted text block */}
            <rect x="20" y="44" width="35" height="2" rx="1" fill="#D97757" opacity="0.8"/>
            <rect x="20" y="49" width="35" height="2" rx="1" fill="#D97757" opacity="0.8"/>
            <rect x="20" y="54" width="30" height="2" rx="1" fill="#D97757" opacity="0.6"/>
            
            {/* Bottom accent line */}
            <rect x="20" y="60" width="20" height="2" rx="1" fill="#D97757" opacity="0.4"/>
            
            {/* AI Sparkle icon overlay - bottom right */}
            <circle cx="58" cy="60" r="10" fill="#D97757" opacity="0.9"/>
            <path d="M58 54 L58 66 M52 60 L64 60" stroke="white" strokeWidth="2" strokeLinecap="round"/>
            <path d="M54 56 L62 64 M62 56 L54 64" stroke="white" strokeWidth="1.5" strokeLinecap="round" opacity="0.6"/>
          </svg>
          
          {/* Text hierarchy */}
          <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>No content loaded</h3>
          <p className="text-sm max-w-sm mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Enter a Bot ID above to load transcripts and generate AI summaries.
          </p>
        </div>
      )}
    </div>
  );
}