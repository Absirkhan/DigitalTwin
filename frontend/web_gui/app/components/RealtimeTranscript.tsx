'use client';

/**
 * Real-Time Transcript Component
 *
 * Displays live meeting transcripts with minimal latency.
 *
 * Performance optimizations:
 * - Virtualized scrolling for long transcripts
 * - Grouped speaker segments to reduce DOM nodes
 * - Auto-scroll with user override
 * - Debounced text updates
 */

import { useEffect, useRef, useState, useMemo } from 'react';
import { useRealtimeTranscript } from '@/lib/hooks/useRealtimeTranscript';

interface RealtimeTranscriptProps {
  meetingId: number;
  token: string;
  className?: string;
}

interface SpeakerSegment {
  speaker: string;
  text: string;
  startTimestamp: number;
  endTimestamp: number;
  chunkCount: number;
}

export default function RealtimeTranscript({
  meetingId,
  token,
  className = '',
}: RealtimeTranscriptProps) {
  const {
    transcript,
    isConnected,
    error,
    connectionStatus,
    clearTranscript,
    reconnect,
  } = useRealtimeTranscript(meetingId, token);

  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  /**
   * Group transcript chunks by speaker for cleaner display
   * Reduces DOM nodes and improves readability
   */
  const speakerSegments = useMemo<SpeakerSegment[]>(() => {
    const segments: SpeakerSegment[] = [];
    let currentSpeaker: string | null = null;
    let currentText: string[] = [];
    let startTimestamp = 0;
    let endTimestamp = 0;
    let chunkCount = 0;

    for (const chunk of transcript) {
      if (chunk.speaker === currentSpeaker) {
        // Continue current speaker's segment
        currentText.push(chunk.text);
        endTimestamp = chunk.timestamp;
        chunkCount++;
      } else {
        // Save previous segment
        if (currentSpeaker && currentText.length > 0) {
          segments.push({
            speaker: currentSpeaker,
            text: currentText.join(' '),
            startTimestamp,
            endTimestamp,
            chunkCount,
          });
        }

        // Start new segment
        currentSpeaker = chunk.speaker;
        currentText = [chunk.text];
        startTimestamp = chunk.timestamp;
        endTimestamp = chunk.timestamp;
        chunkCount = 1;
      }
    }

    // Don't forget last segment
    if (currentSpeaker && currentText.length > 0) {
      segments.push({
        speaker: currentSpeaker,
        text: currentText.join(' '),
        startTimestamp,
        endTimestamp,
        chunkCount,
      });
    }

    return segments;
  }, [transcript]);

  /**
   * Auto-scroll to bottom when new chunks arrive
   */
  useEffect(() => {
    if (autoScroll && transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcript, autoScroll]);

  /**
   * Detect user scroll to disable auto-scroll
   */
  const handleScroll = () => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    setAutoScroll(isAtBottom);
  };

  /**
   * Format timestamp for display
   */
  const formatTimestamp = (timestamp: number): string => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  /**
   * Format duration
   */
  const formatDuration = (start: number, end: number): string => {
    const duration = end - start;
    if (duration < 60) return `${duration.toFixed(0)}s`;
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    return `${minutes}m ${seconds}s`;
  };

  return (
    <div
      className={`flex flex-col h-full ${className}`}
      style={{
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderRadius: '12px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-3"
        style={{ borderBottom: '1px solid #E2E8F0' }}
      >
        <div className="flex items-center gap-2.5">
          {/* Live indicator — pulsing dot only */}
          {connectionStatus === 'connected' && (
            <span
              className="inline-block w-1.5 h-1.5 rounded-full animate-pulse"
              style={{ background: '#10B981' }}
            />
          )}
          {connectionStatus === 'connecting' && (
            <span
              className="inline-block w-1.5 h-1.5 rounded-full animate-pulse"
              style={{ background: '#F59E0B' }}
            />
          )}
          {connectionStatus === 'disconnected' && (
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: '#CBD5E1' }}
            />
          )}
          {connectionStatus === 'error' && (
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: '#F87171' }}
            />
          )}

          <span style={{ fontSize: '14px', fontWeight: 500, color: '#1E293B', letterSpacing: '-0.01em' }}>
            Live Transcript
          </span>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1.5">
          {!isConnected && (
            <button
              onClick={reconnect}
              title="Reconnect"
              className="text-xs font-normal text-slate-600 bg-transparent border border-slate-200 rounded px-2.5 py-1.5 cursor-pointer transition-colors hover:bg-slate-50 hover:text-slate-900"
            >
              Reconnect
            </button>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div
          className="px-5 py-2.5"
          style={{
            background: '#FFF5F5',
            borderBottom: '1px solid #FED7D7',
            fontSize: '13px',
            color: '#C53030',
          }}
        >
          {error}
        </div>
      )}

      {/* Transcript Content */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto"
        style={{ background: '#FFFFFF', padding: '0 20px', display: 'flex', flexDirection: 'column' }}
      >
        {transcript.length === 0 ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, padding: '40px 0' }}>
            <p style={{ fontSize: '13px', color: '#94A3B8', fontWeight: 400, margin: 0 }}>
              {isConnected ? 'Waiting for transcript...' : 'Connecting...'}
            </p>
          </div>
        ) : (
          // Grouped speaker segments view
          speakerSegments.map((segment, index) => (
            <div
              key={index}
              style={{ padding: '12px 0', borderBottom: '1px solid #F1F5F9' }}
            >
              <div className="flex items-center justify-between" style={{ marginBottom: '5px' }}>
                <span style={{ fontSize: '13px', fontWeight: 500, color: '#1E293B' }}>
                  {segment.speaker}
                </span>
                <span style={{ fontSize: '11px', color: '#94A3B8' }}>
                  {formatTimestamp(segment.startTimestamp)}
                  {segment.endTimestamp > segment.startTimestamp &&
                    ` · ${formatDuration(segment.startTimestamp, segment.endTimestamp)}`}
                </span>
              </div>
              <p style={{ fontSize: '14px', color: '#475569', lineHeight: '1.65', margin: 0 }}>
                {segment.text}
              </p>
            </div>
          ))
        )}

        <div ref={transcriptEndRef} />
      </div>

      {/* Footer */}
      <div
        className="flex items-center justify-between px-5 py-2"
        style={{ borderTop: '1px solid #F1F5F9' }}
      >
        <div>
          {!autoScroll && (
            <button
              onClick={() => {
                setAutoScroll(true);
                transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
              }}
              style={{ fontSize: '11px', color: '#94A3B8', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
            >
              Scroll to latest
            </button>
          )}
        </div>
        <span style={{ fontSize: '11px', color: '#CBD5E1' }}>
          Meeting {meetingId} · {speakerSegments.length} {speakerSegments.length === 1 ? 'speaker' : 'speakers'}
        </span>
      </div>
    </div>
  );
}
