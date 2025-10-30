/**
 * Type definitions for API requests and responses
 */

// ============================================================================
// User Types
// ============================================================================

export interface User {
  id: number;
  email: string;
  full_name: string;
  bot_name?: string;
  google_id?: string;
  profile_picture?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface UserUpdate {
  full_name?: string;
  email?: string;
  bot_name?: string;
}

// ============================================================================
// Auth Types
// ============================================================================

export interface GoogleLoginResponse {
  authorization_url: string;
}

export interface AuthCallbackResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ============================================================================
// Meeting Types
// ============================================================================

export interface Meeting {
  id: number;
  user_id: number;
  title: string;
  description?: string;
  meeting_url?: string;
  start_time?: string;
  end_time?: string;
  status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
  calendar_event_id?: string;
  created_at: string;
  updated_at?: string;
  bot_id?: string;  // Recall bot ID if meeting has been joined
  auto_join?: boolean;  // Auto-join setting for the meeting
}

export interface MeetingCreate {
  title: string;
  description?: string;
  meeting_url: string;
  platform: string;
  scheduled_time: string;  // ISO date string
  duration_minutes?: number;
  auto_join?: boolean;
}

export interface MeetingUpdate {
  title?: string;
  description?: string;
  meeting_url?: string;
  start_time?: string;
  end_time?: string;
  status?: 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
  auto_join?: boolean;
}

export interface JoinMeetingRequest {
  meeting_url: string;
  recording_config?: Record<string, any>;
  bot_name?: string;
  profile_picture?: string;
  enable_realtime_processing?: boolean;
  enable_video_recording?: boolean;
}

export interface JoinMeetingResponse {
  success: boolean;
  bot_id: string;
  message: string;
  meeting_id?: number;
}

export interface FormattedTranscript {
  continuous_text?: string;
  clean_continuous_text: string;
  speaker_segments?: Array<{
    speaker: string;
    text: string;
    timestamp?: string;
  }>;
  total_words?: number;
  chunks?: any[];  // Raw chunks from backend
  participants?: any;
  total_chunks?: number;
}

export interface GetFormattedTranscriptResponse {
  success: boolean;
  bot_id: string;
  formatted_transcript: FormattedTranscript;
}

export interface BotRecordingUrlResponse {
  success: boolean;
  bot_id: string;
  download_url?: string;
  video_url?: string;
  recording_id?: string;
  recording_status?: {
    code: string;
    sub_code?: string | null;
    updated_at: string;
  };
  database_updated?: boolean;
  expires_at?: string | null;
  message?: string;
}

// ============================================================================
// Bot Types
// ============================================================================

export interface Bot {
  id: number;
  bot_id: string;
  user_id: number;
  platform?: string;
  bot_name?: string;
  video_download_url?: string;
  transcript_url?: string;
  meeting_id?: number;
  recording_status: 'pending' | 'recording' | 'completed' | 'failed';
  recording_data?: Record<string, any>;
  video_recording_url?: string;
  recording_expires_at?: string;
  created_at: string;
  updated_at?: string;
}

// ============================================================================
// Bot Types
// ============================================================================

export interface Bot {
  id: number;
  bot_id: string;
  user_id: number;
  platform?: string;
  bot_name?: string;
  video_download_url?: string;
  transcript_url?: string;
  meeting_id?: number;
  recording_status: 'pending' | 'recording' | 'completed' | 'failed';
  recording_data?: Record<string, any>;
  video_recording_url?: string;
  recording_expires_at?: string;
  created_at: string;
  updated_at?: string;
  // Meeting details (when include_meeting_details=true)
  meeting_title?: string;
  meeting_url?: string;
  meeting_platform?: string;
  meeting_scheduled_time?: string;
  meeting_status?: string;
}

export interface BotsListResponse {
  success: boolean;
  message: string;
  data: Bot[];
  total_count: number;
  filtered_count?: number;
  filters_applied?: {
    order_by: string;
    include_meeting_details?: boolean;
    auto_sync_recall?: boolean;
    sync_stats?: {
      attempted: number;
      successful: number;
      failed: number;
    };
    from_date?: string;
    to_date?: string;
  };
}

export interface BotTranscriptResponse {
  success: boolean;
  bot_id: string;
  transcript_id?: string;
  download_url?: string;
  formatted_transcript?: FormattedTranscript;
  clean_continuous_text?: string;
  statistics?: Record<string, any>;
  metadata?: Record<string, any>;
}

// ============================================================================
// Summarization Types
// ============================================================================

export interface SummarizationResponse {
  success: boolean;
  summary?: string;
  action_items?: string;
  key_decisions?: string;
  error?: string;
  metrics?: {
    original_words?: number;
    summary_words?: number;
    compression_ratio?: number;
    model_used?: string;
  };
}

// ============================================================================
// Calendar Types
// ============================================================================

export interface CalendarEvent {
  id: string;
  summary: string;
  description?: string;
  start: {
    dateTime: string;
    timeZone?: string;
  };
  end: {
    dateTime: string;
    timeZone?: string;
  };
  attendees?: Array<{
    email: string;
    displayName?: string;
  }>;
  meetLink?: string;
}

export interface CalendarSyncResponse {
  success: boolean;
  events_synced: number;
  message: string;
  events?: CalendarEvent[];
}

// ============================================================================
// API Response Wrappers
// ============================================================================

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
