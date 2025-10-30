/**
 * Summarization API Service
 */

import { post } from './client';
import type { SummarizationResponse } from './types';

export const summarizationService = {
  /**
   * Generate summary for the latest bot's transcript
   * POST /api/v1/summarization/generate
   */
  generate: async (): Promise<SummarizationResponse> => {
    return post<SummarizationResponse>('/api/v1/summarization/generate', {});
  },

  /**
   * Generate summary for a specific bot
   * POST /api/v1/summarization/generate/{bot_id}
   */
  generateForBot: async (botId: string): Promise<SummarizationResponse> => {
    return post<SummarizationResponse>(`/api/v1/summarization/generate/${botId}`, {});
  },
};
