/**
 * Bot Speaking API Client
 *
 * Provides functions for managing bot speaking functionality:
 * - Get response history
 * - Emergency disable
 * - Update settings
 * - View statistics
 */

import apiClient from './client';

export interface BotResponseItem {
  id: number;
  trigger_text: string;
  response_text: string;
  response_style: string;
  timestamp: string;
  success: boolean;
  latency_ms?: number;
  audio_url?: string;
}

export interface BotResponseHistoryResponse {
  meeting_id: number;
  meeting_title: string;
  total_responses: number;
  responses: BotResponseItem[];
  bot_response_enabled: boolean;
  bot_response_count: number;
  bot_max_responses: number;
  bot_response_style: string;
}

export interface MeetingBotSpeakingUpdate {
  bot_response_enabled?: boolean;
  bot_response_style?: 'professional' | 'casual' | 'technical' | 'brief';
  bot_max_responses?: number;
}

export interface BotSpeakingSettings {
  enable_bot_speaking: boolean;
  bot_name: string;
}

export interface BotSpeakingStatsResponse {
  total_responses: number;
  successful_responses: number;
  failed_responses: number;
  success_rate: number;
  average_latency_ms: number;
  responses_by_style: { [key: string]: number };
  total_meetings_with_responses: number;
  period_days: number;
}

/**
 * Get bot response history for a meeting
 */
export async function getMeetingBotResponses(
  meetingId: number,
  limit: number = 50,
  offset: number = 0
): Promise<BotResponseHistoryResponse> {
  const response = await apiClient.get<BotResponseHistoryResponse>(
    `/api/v1/bot-speaking/meeting/${meetingId}/responses?limit=${limit}&offset=${offset}`
  );
  return response;
}

/**
 * Emergency disable bot speaking for a meeting
 */
export async function emergencyDisableBotSpeaking(meetingId: number): Promise<{
  success: boolean;
  message: string;
  meeting_id: number;
  meeting_title: string;
  was_enabled: boolean;
  current_response_count: number;
}> {
  const response = await apiClient.post<{
    success: boolean;
    message: string;
    meeting_id: number;
    meeting_title: string;
    was_enabled: boolean;
    current_response_count: number;
  }>(`/api/v1/bot-speaking/meeting/${meetingId}/disable`);
  return response;
}

/**
 * Update bot speaking settings for a meeting
 */
export async function updateMeetingBotSpeaking(
  meetingId: number,
  settings: MeetingBotSpeakingUpdate
): Promise<{
  success: boolean;
  message: string;
  meeting_id: number;
  bot_response_enabled: boolean;
  bot_response_style: string;
  bot_max_responses: number;
}> {
  const response = await apiClient.patch<{
    success: boolean;
    message: string;
    meeting_id: number;
    bot_response_enabled: boolean;
    bot_response_style: string;
    bot_max_responses: number;
  }>(`/api/v1/bot-speaking/meeting/${meetingId}/settings`, settings);
  return response;
}

/**
 * Get global bot speaking settings
 */
export async function getBotSpeakingSettings(): Promise<BotSpeakingSettings> {
  const response = await apiClient.get<BotSpeakingSettings>('/api/v1/bot-speaking/settings');
  return response;
}

/**
 * Update global bot speaking settings
 */
export async function updateBotSpeakingSettings(
  settings: Partial<BotSpeakingSettings>
): Promise<BotSpeakingSettings> {
  const response = await apiClient.patch<BotSpeakingSettings>('/api/v1/bot-speaking/settings', settings);
  return response;
}

/**
 * Get bot speaking statistics
 */
export async function getBotSpeakingStats(
  days: number = 30
): Promise<BotSpeakingStatsResponse> {
  const response = await apiClient.get<BotSpeakingStatsResponse>(
    `/api/v1/bot-speaking/stats?days=${days}`
  );
  return response;
}
