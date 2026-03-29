'use client';

/**
 * Voice Setup Component
 *
 * Allows users to create, manage, and delete their voice profile for TTS.
 * Supports both microphone recording and file upload.
 *
 * Features:
 * - 15-second microphone recording with countdown
 * - File upload (.wav, .mp3)
 * - Reference text confirmation
 * - Voice profile status display
 * - Delete with confirmation
 */

import { useEffect, useState, useRef } from 'react';
import { getVoiceStatus, getVoiceInfo, uploadVoice, deleteVoice, synthesizeSpeechAsync, getTTSJobStatus, getOriginalRecording } from '@/lib/api/tts';

interface VoiceSetupProps {
  userFullName?: string;
  className?: string;
}

type SetupState = 'no_profile' | 'has_profile' | 'recording' | 'uploading';

export default function VoiceSetup({
  userFullName = 'User',
  className = '',
}: VoiceSetupProps) {
  const [state, setState] = useState<SetupState>('no_profile');
  const [hasProfile, setHasProfile] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioSource, setAudioSource] = useState<'record' | 'upload' | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Reference text state
  const [refText, setRefText] = useState('');
  const [showRefTextInput, setShowRefTextInput] = useState(false);
  const [uploadingProgress, setUploadingProgress] = useState(false);

  // Delete confirmation state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Voice preview state
  const [previewText, setPreviewText] = useState('');
  const [isGeneratingPreview, setIsGeneratingPreview] = useState(false);
  const [previewAudioUrl, setPreviewAudioUrl] = useState<string | null>(null);
  const [estimatedTime, setEstimatedTime] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Original recording state
  const [originalRecordingUrl, setOriginalRecordingUrl] = useState<string | null>(null);
  const [originalRefText, setOriginalRefText] = useState<string | null>(null);
  const [loadingOriginal, setLoadingOriginal] = useState(false);
  const originalAudioRef = useRef<HTMLAudioElement | null>(null);

  // Default script for recording
  const defaultScript = `My name is ${userFullName}. I use DigitalTwin to automate my meetings.`;

  // Load voice status on mount
  useEffect(() => {
    loadVoiceStatus();
  }, []);

  // Cleanup audio URLs on unmount
  useEffect(() => {
    return () => {
      if (previewAudioUrl) {
        URL.revokeObjectURL(previewAudioUrl);
      }
      if (originalRecordingUrl) {
        URL.revokeObjectURL(originalRecordingUrl);
      }
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    };
  }, [previewAudioUrl, originalRecordingUrl]);

  const loadVoiceStatus = async () => {
    try {
      setLoading(true);
      const status = await getVoiceStatus();
      setHasProfile(status.has_voice_profile);
      setState(status.has_voice_profile ? 'has_profile' : 'no_profile');

      // If has profile, load additional info
      if (status.has_voice_profile) {
        try {
          const info = await getVoiceInfo();
          setOriginalRefText(info.reference_text);

          // Load original recording if available
          if (info.has_original_recording) {
            loadOriginalRecording();
          }
        } catch (err) {
          console.error('Failed to load voice info:', err);
        }
      }
    } catch (err) {
      setError('Failed to load voice status');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadOriginalRecording = async () => {
    try {
      setLoadingOriginal(true);

      // Clean up previous URL
      if (originalRecordingUrl) {
        URL.revokeObjectURL(originalRecordingUrl);
      }

      const audioBlob = await getOriginalRecording();
      const audioUrl = URL.createObjectURL(audioBlob);
      setOriginalRecordingUrl(audioUrl);
    } catch (err) {
      console.error('Failed to load original recording:', err);
    } finally {
      setLoadingOriginal(false);
    }
  };

  const startRecording = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.addEventListener('dataavailable', (event) => {
        audioChunksRef.current.push(event.data);
      });

      mediaRecorder.addEventListener('stop', () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioBlob(audioBlob);
        setAudioSource('record');
        setShowRefTextInput(true);
        setRefText(defaultScript); // Pre-fill with default script
        stream.getTracks().forEach((track) => track.stop());
      });

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);

      // Countdown timer (15 seconds)
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => {
          if (prev >= 15) {
            stopRecording();
            return 15;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err: any) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setError('Microphone permission denied. Please allow microphone access in your browser settings.');
      } else {
        setError('Failed to access microphone. Please check your device settings.');
      }
      console.error(err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['audio/wav', 'audio/mpeg', 'audio/mp3'];
    if (!allowedTypes.includes(file.type) && !file.name.match(/\.(wav|mp3)$/i)) {
      setError('Invalid file format. Please upload .wav or .mp3 file.');
      return;
    }

    // Validate file size (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('File too large. Maximum size is 10MB.');
      return;
    }

    setError(null);
    setAudioBlob(file);
    setAudioSource('upload');
    setShowRefTextInput(true);
    setRefText(defaultScript); // Pre-fill with default script
  };

  const handleUploadVoice = async () => {
    if (!audioBlob || !refText.trim()) {
      setError('Please provide both audio and reference text.');
      return;
    }

    try {
      setError(null);
      setSuccess(null);
      setUploadingProgress(true);

      const response = await uploadVoice(audioBlob, refText.trim());

      setSuccess(response.message);
      setHasProfile(true);
      setState('has_profile');
      setAudioBlob(null);
      setRefText('');
      setShowRefTextInput(false);
      setAudioSource(null);

      // Reload status
      setTimeout(() => loadVoiceStatus(), 500);
    } catch (err: any) {
      setError(err.message || 'Voice upload failed');
      console.error(err);
    } finally {
      setUploadingProgress(false);
    }
  };

  const handleDeleteVoice = async () => {
    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      const response = await deleteVoice();

      setSuccess(response.message);
      setHasProfile(false);
      setState('no_profile');
      setShowDeleteConfirm(false);

      // Reload status
      setTimeout(() => loadVoiceStatus(), 500);
    } catch (err: any) {
      setError(err.message || 'Voice deletion failed');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setAudioBlob(null);
    setRefText('');
    setShowRefTextInput(false);
    setAudioSource(null);
    setError(null);
    setRecordingTime(0);
  };

  const handleGeneratePreview = async () => {
    if (!previewText.trim()) {
      setError('Please enter some text to preview');
      return;
    }

    // Validate word count (max 50 words for optimal latency)
    const wordCount = previewText.trim().split(/\s+/).length;
    if (wordCount > 50) {
      setError(`Text too long (${wordCount} words). Please keep it under 50 words for faster generation.`);
      return;
    }

    try {
      setError(null);
      setIsGeneratingPreview(true);

      // Calculate estimated time based on word count
      const wordCount = previewText.trim().split(/\s+/).filter(w => w).length;
      // Formula: ~100ms per word (after model is pre-warmed + caching)
      const estimated = Math.max(2, Math.ceil(wordCount * 0.1));
      setEstimatedTime(estimated);
      setElapsedTime(0);

      // Start timer
      const startTime = Date.now();
      timerIntervalRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        setElapsedTime(elapsed);
      }, 100);

      // Clean up previous audio URL
      if (previewAudioUrl) {
        URL.revokeObjectURL(previewAudioUrl);
        setPreviewAudioUrl(null);
      }

      // Start async TTS job (non-blocking)
      const { job_id } = await synthesizeSpeechAsync(previewText.trim());

      // Poll for completion
      const pollJob = async () => {
        while (true) {
          const status = await getTTSJobStatus(job_id);

          if (status.status === 'success') {
            // Decode base64 audio data
            const audioData = status.result.audio_data;
            const binaryString = atob(audioData);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            const audioBlob = new Blob([bytes], { type: 'audio/wav' });

            // Stop timer
            if (timerIntervalRef.current) {
              clearInterval(timerIntervalRef.current);
              timerIntervalRef.current = null;
            }

            // Create object URL for playback
            const audioUrl = URL.createObjectURL(audioBlob);
            setPreviewAudioUrl(audioUrl);

            // Auto-play the preview
            if (audioPlayerRef.current) {
              audioPlayerRef.current.src = audioUrl;
              audioPlayerRef.current.play().catch((err) => {
                console.error('Failed to auto-play:', err);
              });
            }

            // Show cache hit indicator if applicable
            if (status.result.cache_hit) {
              setSuccess('Retrieved from cache (instant response!)');
              setTimeout(() => setSuccess(null), 3000);
            }

            break;
          } else if (status.status === 'error') {
            throw new Error(status.error || 'TTS job failed');
          }

          // Wait 500ms before next poll
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      };

      await pollJob();

    } catch (err: any) {
      setError(err.message || 'Failed to generate voice preview');
      console.error(err);

      // Stop timer on error
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
    } finally {
      setIsGeneratingPreview(false);
    }
  };

  const handleDownloadPreview = () => {
    if (previewAudioUrl) {
      const a = document.createElement('a');
      a.href = previewAudioUrl;
      a.download = 'voice_preview.wav';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  if (loading) {
    return (
      <div className={`p-6 ${className}`} style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px' }}>
        <p style={{ fontSize: '14px', color: '#64748B' }}>Loading voice status...</p>
      </div>
    );
  }

  return (
    <div className={`p-6 ${className}`} style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px' }}>
      {/* Header */}
      <div style={{ marginBottom: '16px' }}>
        <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#1E293B', marginBottom: '8px' }}>
          Voice Profile
        </h3>
        <p style={{ fontSize: '14px', color: '#64748B', lineHeight: '1.6' }}>
          Enable the bot to speak in your voice during meetings by recording a 15-second sample.
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div style={{ padding: '12px', background: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: '8px', marginBottom: '16px' }}>
          <p style={{ fontSize: '14px', color: '#DC2626', margin: 0 }}>{error}</p>
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div style={{ padding: '12px', background: '#F0FDF4', border: '1px solid #86EFAC', borderRadius: '8px', marginBottom: '16px' }}>
          <p style={{ fontSize: '14px', color: '#16A34A', margin: 0 }}>{success}</p>
        </div>
      )}

      {/* State: No Profile */}
      {state === 'no_profile' && !showRefTextInput && (
        <div>
          {/* Recording Script */}
          <div style={{ padding: '16px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', marginBottom: '20px' }}>
            <p style={{ fontSize: '13px', fontWeight: 500, color: '#475569', marginBottom: '8px' }}>
              Read this script aloud when recording:
            </p>
            <p style={{ fontSize: '14px', color: '#1E293B', lineHeight: '1.7', fontStyle: 'italic', margin: 0 }}>
              "{defaultScript}"
            </p>
          </div>

          {/* Record Button */}
          {!isRecording && (
            <button
              onClick={startRecording}
              style={{
                width: '100%',
                padding: '14px',
                background: '#3B82F6',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: 500,
                cursor: 'pointer',
                marginBottom: '12px',
              }}
              className="hover:opacity-90 transition-opacity"
            >
              Record Now (15 seconds)
            </button>
          )}

          {/* Recording in Progress */}
          {isRecording && (
            <div style={{ padding: '20px', background: '#FEF3C7', border: '1px solid #FDE68A', borderRadius: '8px', textAlign: 'center', marginBottom: '12px' }}>
              <div style={{ fontSize: '32px', fontWeight: 600, color: '#DC2626', marginBottom: '8px' }}>
                {15 - recordingTime}s
              </div>
              <p style={{ fontSize: '14px', color: '#92400E', margin: 0 }}>Recording... Speak clearly!</p>
              <button
                onClick={stopRecording}
                style={{
                  marginTop: '12px',
                  padding: '8px 16px',
                  background: '#DC2626',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  cursor: 'pointer',
                }}
                className="hover:opacity-90"
              >
                Stop Recording
              </button>
            </div>
          )}

          {/* OR Divider */}
          <div style={{ display: 'flex', alignItems: 'center', margin: '16px 0' }}>
            <div style={{ flex: 1, height: '1px', background: '#E2E8F0' }}></div>
            <span style={{ padding: '0 12px', fontSize: '13px', color: '#94A3B8' }}>OR</span>
            <div style={{ flex: 1, height: '1px', background: '#E2E8F0' }}></div>
          </div>

          {/* Upload File Button */}
          <label
            style={{
              display: 'block',
              width: '100%',
              padding: '14px',
              background: '#FFFFFF',
              color: '#3B82F6',
              border: '2px solid #3B82F6',
              borderRadius: '8px',
              fontSize: '15px',
              fontWeight: 500,
              textAlign: 'center',
              cursor: 'pointer',
            }}
            className="hover:bg-blue-50 transition-colors"
          >
            Upload Audio File (.wav, .mp3)
            <input
              type="file"
              accept=".wav,.mp3,audio/wav,audio/mpeg"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
          </label>
        </div>
      )}

      {/* State: Reference Text Input */}
      {showRefTextInput && audioBlob && (
        <div>
          <div style={{ marginBottom: '16px' }}>
            <p style={{ fontSize: '14px', fontWeight: 500, color: '#475569', marginBottom: '4px' }}>
              Audio {audioSource === 'record' ? 'recorded' : 'uploaded'} successfully
            </p>
            <p style={{ fontSize: '13px', color: '#64748B' }}>
              Confirm what you said in the audio:
            </p>
          </div>

          <textarea
            value={refText}
            onChange={(e) => setRefText(e.target.value)}
            rows={4}
            placeholder="Enter the exact transcript of your audio..."
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #CBD5E1',
              borderRadius: '8px',
              fontSize: '14px',
              color: '#1E293B',
              resize: 'vertical',
              marginBottom: '16px',
              fontFamily: 'inherit',
            }}
          />

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={handleUploadVoice}
              disabled={uploadingProgress || !refText.trim()}
              style={{
                flex: 1,
                padding: '12px',
                background: uploadingProgress || !refText.trim() ? '#CBD5E1' : '#10B981',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: 500,
                cursor: uploadingProgress || !refText.trim() ? 'not-allowed' : 'pointer',
              }}
              className="hover:opacity-90 transition-opacity"
            >
              {uploadingProgress ? 'Uploading...' : 'Submit Voice Profile'}
            </button>
            <button
              onClick={handleCancel}
              disabled={uploadingProgress}
              style={{
                padding: '12px 20px',
                background: '#FFFFFF',
                color: '#64748B',
                border: '1px solid #CBD5E1',
                borderRadius: '8px',
                fontSize: '15px',
                fontWeight: 500,
                cursor: uploadingProgress ? 'not-allowed' : 'pointer',
              }}
              className="hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* State: Has Profile */}
      {state === 'has_profile' && !showDeleteConfirm && (
        <div>
          <div style={{ padding: '16px', background: '#F0FDF4', border: '1px solid #86EFAC', borderRadius: '8px', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '18px' }}>✓</span>
              <span style={{ fontSize: '15px', fontWeight: 500, color: '#16A34A' }}>
                Voice profile active
              </span>
            </div>
            <p style={{ fontSize: '13px', color: '#15803D', margin: '8px 0 0 0' }}>
              Your bot will speak in your voice during meetings.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={() => {
                setHasProfile(false);
                setState('no_profile');
                setAudioBlob(null);
                setRefText('');
                setShowRefTextInput(false);
              }}
              style={{
                flex: 1,
                padding: '12px',
                background: '#3B82F6',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 500,
                cursor: 'pointer',
              }}
              className="hover:opacity-90 transition-opacity"
            >
              Re-record Voice
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              style={{
                padding: '12px 20px',
                background: '#FFFFFF',
                color: '#DC2626',
                border: '1px solid #FCA5A5',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 500,
                cursor: 'pointer',
              }}
              className="hover:bg-red-50 transition-colors"
            >
              Delete Voice Profile
            </button>
          </div>

          {/* Original Recording Section */}
          {originalRecordingUrl && (
            <div style={{ marginTop: '24px', padding: '20px', background: '#FEF9F5', border: '1px solid #FDBA74', borderRadius: '12px' }}>
              <div style={{ marginBottom: '12px' }}>
                <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#1E293B', marginBottom: '4px' }}>
                  Your Original Voice Recording
                </h4>
                <p style={{ fontSize: '13px', color: '#64748B' }}>
                  This is the voice sample you provided for training
                </p>
              </div>

              {originalRefText && (
                <div style={{ padding: '12px', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px', marginBottom: '12px' }}>
                  <p style={{ fontSize: '12px', fontWeight: 500, color: '#64748B', marginBottom: '4px' }}>
                    Transcript:
                  </p>
                  <p style={{ fontSize: '14px', color: '#1E293B', fontStyle: 'italic', margin: 0, lineHeight: '1.6' }}>
                    "{originalRefText}"
                  </p>
                </div>
              )}

              <audio
                ref={originalAudioRef}
                controls
                style={{ width: '100%', height: '40px' }}
              >
                <source src={originalRecordingUrl} type="audio/wav" />
                Your browser does not support the audio element.
              </audio>
            </div>
          )}

          {/* Voice Preview Section */}
          <div style={{ marginTop: '24px', padding: '20px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '12px' }}>
            <div style={{ marginBottom: '12px' }}>
              <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#1E293B', marginBottom: '4px' }}>
                Voice Preview
              </h4>
              <p style={{ fontSize: '13px', color: '#64748B' }}>
                Enter any text to hear how your bot will sound in meetings
              </p>
            </div>

            <div style={{ position: 'relative', marginBottom: '12px' }}>
              <textarea
                value={previewText}
                onChange={(e) => setPreviewText(e.target.value)}
                placeholder="Type something for your bot to say... (e.g., 'Hello everyone, I'll be joining this meeting today.')"
                rows={3}
                style={{
                  width: '100%',
                  padding: '12px',
                  paddingBottom: '32px',
                  border: '1px solid #CBD5E1',
                  borderRadius: '8px',
                  fontSize: '14px',
                  color: '#1E293B',
                  resize: 'vertical',
                  fontFamily: 'inherit',
                }}
              />
              <div style={{
                position: 'absolute',
                bottom: '8px',
                right: '12px',
                fontSize: '12px',
                color: previewText.trim().split(/\s+/).filter(w => w).length > 50 ? '#DC2626' : '#64748B',
                fontWeight: 500
              }}>
                {previewText.trim() ? previewText.trim().split(/\s+/).filter(w => w).length : 0} / 50 words
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button
                onClick={handleGeneratePreview}
                disabled={isGeneratingPreview || !previewText.trim()}
                style={{
                  flex: 1,
                  minWidth: '150px',
                  padding: '12px 16px',
                  background: isGeneratingPreview || !previewText.trim() ? '#CBD5E1' : '#8B5CF6',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: isGeneratingPreview || !previewText.trim() ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                }}
                className="hover:opacity-90 transition-opacity"
              >
                {isGeneratingPreview ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                    <span>Generating... {elapsedTime}s / ~{estimatedTime}s</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Generate Preview
                  </>
                )}
              </button>

              {previewAudioUrl && (
                <button
                  onClick={handleDownloadPreview}
                  style={{
                    padding: '12px 16px',
                    background: '#FFFFFF',
                    color: '#3B82F6',
                    border: '1px solid #3B82F6',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                  className="hover:bg-blue-50 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download
                </button>
              )}
            </div>

            {/* Audio Player */}
            {previewAudioUrl && (
              <div style={{ marginTop: '16px', padding: '16px', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <svg className="w-5 h-5" style={{ color: '#8B5CF6' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                  <span style={{ fontSize: '14px', fontWeight: 500, color: '#475569' }}>Your Voice Preview</span>
                </div>
                <audio
                  ref={audioPlayerRef}
                  controls
                  style={{ width: '100%', height: '40px' }}
                >
                  <source src={previewAudioUrl} type="audio/wav" />
                  Your browser does not support the audio element.
                </audio>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div style={{ padding: '16px', background: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: '8px' }}>
          <p style={{ fontSize: '15px', fontWeight: 500, color: '#DC2626', marginBottom: '12px' }}>
            Are you sure you want to delete your voice profile?
          </p>
          <p style={{ fontSize: '13px', color: '#991B1B', marginBottom: '16px' }}>
            This action cannot be undone. You'll need to record a new sample to use voice cloning again.
          </p>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={handleDeleteVoice}
              disabled={loading}
              style={{
                flex: 1,
                padding: '12px',
                background: loading ? '#FCA5A5' : '#DC2626',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 500,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
              className="hover:opacity-90 transition-opacity"
            >
              {loading ? 'Deleting...' : 'Yes, Delete'}
            </button>
            <button
              onClick={() => setShowDeleteConfirm(false)}
              disabled={loading}
              style={{
                padding: '12px 20px',
                background: '#FFFFFF',
                color: '#64748B',
                border: '1px solid #CBD5E1',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 500,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
              className="hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
