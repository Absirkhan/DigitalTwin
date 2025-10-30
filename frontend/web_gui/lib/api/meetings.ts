/**
 * Meetings API Service
 */

import { get, post, put, del } from './client';
import type {
  Meeting,
  MeetingCreate,
  MeetingUpdate,
  JoinMeetingRequest,
  JoinMeetingResponse,
  GetFormattedTranscriptResponse,
  BotRecordingUrlResponse,
  BotsListResponse,
  BotTranscriptResponse,
  SummarizationResponse,
} from './types';

export const meetingService = {
  /**
   * Get all meetings for the current user
   * GET /api/v1/meetings
   */
  getAll: async (): Promise<Meeting[]> => {
    return get<Meeting[]>('/api/v1/meetings');
  },

  /**
   * Create a new meeting
   * POST /api/v1/meetings
   */
  create: async (data: MeetingCreate): Promise<Meeting> => {
    return post<Meeting>('/api/v1/meetings', data);
  },

  /**
   * Get a specific meeting by ID
   * GET /api/v1/meetings/{meeting_id}
   */
  getById: async (meetingId: number): Promise<Meeting> => {
    return get<Meeting>(`/api/v1/meetings/${meetingId}`);
  },

  /**
   * Update a meeting
   * PUT /api/v1/meetings/{meeting_id}
   */
  update: async (meetingId: number, data: MeetingUpdate): Promise<Meeting> => {
    return put<Meeting>(`/api/v1/meetings/${meetingId}`, data);
  },

  /**
   * Delete a meeting
   * DELETE /api/v1/meetings/{meeting_id}
   */
  delete: async (meetingId: number): Promise<void> => {
    return del<void>(`/api/v1/meetings/${meetingId}`);
  },

  /**
   * Join a meeting with URL (bot joins the meeting)
   * POST /api/v1/meetings/join
   */
  join: async (data: JoinMeetingRequest): Promise<JoinMeetingResponse> => {
    return post<JoinMeetingResponse>('/api/v1/meetings/join', data);
  },

  /**
   * Get formatted transcript for a bot
   * GET /api/v1/meetings/bot/{bot_id}/transcript/formatted
   */
  getFormattedTranscript: async (botId: string): Promise<GetFormattedTranscriptResponse> => {
    return get<GetFormattedTranscriptResponse>(`/api/v1/meetings/bot/${botId}/transcript/formatted`);
  },

  /**
   * Get recording URL for a bot
   * GET /api/v1/meetings/bot/{bot_id}/recording-url
   */
  getBotRecordingUrl: async (botId: string): Promise<BotRecordingUrlResponse> => {
    return get<BotRecordingUrlResponse>(`/api/v1/meetings/bot/${botId}/recording-url`);
  },

  /**
   * Get simple recording URL for a bot (no database update)
   * GET /api/v1/meetings/bot/{bot_id}/recording-url/simple
   */
  getBotRecordingUrlSimple: async (botId: string): Promise<{ success: boolean; bot_id: string; download_url: string }> => {
    return get<{ success: boolean; bot_id: string; download_url: string }>(`/api/v1/meetings/bot/${botId}/recording-url/simple`);
  },

  /**
   * Get all bots for the current user with optional filtering
   * GET /api/v1/meetings/bots
   */
  getBots: async (params?: {
    from_date?: string;
    to_date?: string;
    order_by?: 'asc' | 'desc';
    include_meeting_details?: boolean;
    auto_sync_recall?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<BotsListResponse> => {
    const searchParams = new URLSearchParams();
    
    if (params?.from_date) searchParams.append('from_date', params.from_date);
    if (params?.to_date) searchParams.append('to_date', params.to_date);
    if (params?.order_by) searchParams.append('order_by', params.order_by);
    if (params?.include_meeting_details !== undefined) {
      searchParams.append('include_meeting_details', params.include_meeting_details.toString());
    }
    if (params?.auto_sync_recall !== undefined) {
      searchParams.append('auto_sync_recall', params.auto_sync_recall.toString());
    }
    if (params?.limit) searchParams.append('limit', params.limit.toString());
    if (params?.offset) searchParams.append('offset', params.offset.toString());

    const queryString = searchParams.toString();
    const url = `/api/v1/meetings/bots${queryString ? `?${queryString}` : ''}`;
    
    return get<BotsListResponse>(url);
  },

  /**
   * Get formatted transcript for a bot
   * GET /api/v1/meetings/bot/{bot_id}/transcript/formatted
   */
  getBotTranscript: async (botId: string): Promise<BotTranscriptResponse> => {
    return get<BotTranscriptResponse>(`/api/v1/meetings/bot/${botId}/transcript/formatted`);
  },

  /**
   * Get summary for text/transcript
   * POST /api/v1/meetings/summarize
   */
  getSummary: async (data: {
    text: string;
    is_meeting_transcript?: boolean;
    max_length?: number;
    min_length?: number;
  }): Promise<SummarizationResponse> => {
    return post<SummarizationResponse>('/api/v1/meetings/summarize', data);
  },

  /**
   * Toggle auto-join setting for a meeting
   * POST /api/v1/meetings/{meeting_id}/toggle-auto-join?auto_join={boolean}
   */
  toggleAutoJoin: async (meetingId: number, autoJoin: boolean): Promise<{ success: boolean; message: string; auto_join: boolean }> => {
    return post<{ success: boolean; message: string; auto_join: boolean }>(`/api/v1/meetings/${meetingId}/toggle-auto-join?auto_join=${autoJoin}`, {});
  },
};
