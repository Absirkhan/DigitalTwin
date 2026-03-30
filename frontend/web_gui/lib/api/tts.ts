/**
 * TTS (Text-to-Speech) API Helper
 *
 * Handles voice cloning operations:
 * - Upload voice samples
 * - Check voice profile status
 * - Delete voice profiles
 * - Synthesize speech (testing)
 */

import { getAuthToken } from './client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface VoiceStatusResponse {
  has_voice_profile: boolean;
}

interface VoiceInfoResponse {
  has_voice_profile: boolean;
  has_original_recording: boolean;
  reference_text: string | null;
}

interface ApiResponse {
  success: boolean;
  message: string;
}

/**
 * Get the current user's voice profile status
 */
export async function getVoiceStatus(): Promise<VoiceStatusResponse> {
  const token = getAuthToken();

  const response = await fetch(`${API_BASE_URL}/api/v1/tts/voice-status`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to get voice status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Upload a voice sample to create/update voice profile
 *
 * @param audioBlob - Audio file blob (.wav or .mp3)
 * @param refText - Transcript of what was said in the audio
 */
export async function uploadVoice(
  audioBlob: Blob,
  refText: string
): Promise<ApiResponse> {
  const token = getAuthToken();

  // Create FormData to send multipart/form-data
  const formData = new FormData();
  formData.append('audio_file', audioBlob, 'voice_sample.wav');
  formData.append('ref_text', refText);

  const response = await fetch(`${API_BASE_URL}/api/v1/tts/upload-voice`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      // Don't set Content-Type - browser will set it with boundary for multipart/form-data
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Voice upload failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete the current user's voice profile
 */
export async function deleteVoice(): Promise<ApiResponse> {
  const token = getAuthToken();

  const response = await fetch(`${API_BASE_URL}/api/v1/tts/voice`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Voice deletion failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Synthesize speech from text (testing endpoint)
 * Returns an audio blob
 *
 * @param text - Text to synthesize
 */
export async function synthesizeSpeech(text: string): Promise<Blob> {
  const token = getAuthToken();

  const formData = new FormData();
  formData.append('text', text);

  const response = await fetch(`${API_BASE_URL}/api/v1/tts/synthesize`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Speech synthesis failed: ${response.statusText}`);
  }

  return response.blob();
}

/**
 * Get detailed voice profile information
 */
export async function getVoiceInfo(): Promise<VoiceInfoResponse> {
  const token = getAuthToken();

  const response = await fetch(`${API_BASE_URL}/api/v1/tts/voice-info`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to get voice info: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get the original voice recording
 * Returns an audio blob
 */
export async function getOriginalRecording(): Promise<Blob> {
  const token = getAuthToken();

  const response = await fetch(`${API_BASE_URL}/api/v1/tts/original-recording`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to get original recording: ${response.statusText}`);
  }

  return response.blob();
}

/**
 * Start async TTS synthesis job (non-blocking)
 *
 * @param text - Text to synthesize
 * @returns Job ID for polling
 */
export async function synthesizeSpeechAsync(text: string): Promise<{ job_id: string; status: string }> {
  const token = getAuthToken();

  const formData = new FormData();
  formData.append('text', text);

  const response = await fetch(`${API_BASE_URL}/api/v1/tts/synthesize-async`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to start TTS job: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Poll for TTS job status
 *
 * @param jobId - Job ID returned from synthesizeSpeechAsync
 * @returns Job status and result
 */
export async function getTTSJobStatus(jobId: string): Promise<any> {
  const token = getAuthToken();

  const response = await fetch(`${API_BASE_URL}/api/v1/tts/job/${jobId}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to get job status: ${response.statusText}`);
  }

  return response.json();
}

export default {
  getVoiceStatus,
  getVoiceInfo,
  uploadVoice,
  deleteVoice,
  synthesizeSpeech,
  synthesizeSpeechAsync,
  getTTSJobStatus,
  getOriginalRecording,
};
