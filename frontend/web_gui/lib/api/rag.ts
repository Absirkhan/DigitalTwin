/**
 * RAG (Retrieval-Augmented Generation) API Client
 *
 * Provides functions to interact with the RAG system:
 * - Query with AI response generation
 * - Cache statistics
 * - User statistics
 * - Session management
 */

import { get, post, del } from './client';

export interface RagQueryRequest {
  message: string;
  use_cache?: boolean;
  auto_store?: boolean;
  max_tokens?: number;
}

export interface RagQueryResponse {
  response: string;
  retrieval_latency_ms: number;
  llm_latency_ms: number;
  total_latency_ms: number;
  tokens_generated: number;
  cached: boolean;
  context_items: number;
}

export interface UserStats {
  user_id: string;
  total_exchanges: number;
  session_messages: number;
  profile: {
    speaking_style?: any;
    common_topics?: string[];
  };
}

export interface CacheStats {
  hits: number;
  misses: number;
  hit_rate: number;
  total_cached_responses: number;
}

/**
 * Query the RAG system with a message and get AI-generated response
 */
export async function queryRag(
  request: RagQueryRequest
): Promise<RagQueryResponse> {
  return await post<RagQueryResponse>('/api/v1/rag/query', request);
}

/**
 * Get user statistics from RAG system
 */
export async function getUserStats(): Promise<UserStats> {
  return await get<UserStats>('/api/v1/rag/stats');
}

/**
 * Get cache statistics
 */
export async function getCacheStats(): Promise<CacheStats> {
  return await get<CacheStats>('/api/v1/rag/cache/stats');
}

/**
 * Clear cached responses
 */
export async function clearCache(): Promise<{ success: boolean; message: string; entries_cleared: number }> {
  return await del<{ success: boolean; message: string; entries_cleared: number }>('/api/v1/rag/cache/clear');
}

/**
 * End current RAG session (clears session memory)
 */
export async function endSession(): Promise<{
  success: boolean;
  session_cleared: boolean;
  messages_in_session: number;
  total_exchanges_stored: number;
}> {
  return await post<{
    success: boolean;
    session_cleared: boolean;
    messages_in_session: number;
    total_exchanges_stored: number;
  }>('/api/v1/rag/session/end');
}

export interface ResponseCheckRequest {
  trigger_text: string;
  bot_name?: string;
  response_style?: string;
  simulate_filler?: boolean;
  use_cache?: boolean;
}

export interface ResponseCheckChunk {
  chunk_number: number;
  text: string;
  tts_latency_ms: number;
  audio_size_bytes: number;
  audio_duration_seconds: number;
}

export interface ResponseCheckResponse {
  detected: boolean;
  detection_reason?: string;
  extracted_query?: string;
  filler_category?: string;
  filler_text?: string;
  filler_latency_ms?: number;
  rag_context_items?: number;
  rag_retrieval_ms?: number;
  llm_response?: string;
  llm_tokens?: number;
  llm_latency_ms?: number;
  response_chunks?: ResponseCheckChunk[];
  total_pipeline_ms?: number;
  perceived_latency_ms?: number;
  cached: boolean;
}

/**
 * Check bot response simulation (test without joining meeting)
 */
export async function checkBotResponse(
  request: ResponseCheckRequest
): Promise<ResponseCheckResponse> {
  return await post<ResponseCheckResponse>('/api/v1/rag/response-check', request);
}

/**
 * Manually store a meeting transcript in RAG
 */
export async function storeTranscript(meetingId: number): Promise<{
  success: boolean;
  total_exchanges_stored: number;
  speakers: string[];
  error?: string;
}> {
  return await post<{
    success: boolean;
    total_exchanges_stored: number;
    speakers: string[];
    error?: string;
  }>(`/api/v1/rag/store-transcript/${meetingId}`);
}
