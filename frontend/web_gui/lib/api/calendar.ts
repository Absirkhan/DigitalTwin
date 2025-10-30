/**
 * Calendar API Service
 */

import { post } from './client';
import type { CalendarSyncResponse } from './types';

export const calendarService = {
  /**
   * Sync calendar events with Google Calendar
   * POST /api/v1/calendar/sync
   */
  sync: async (): Promise<CalendarSyncResponse> => {
    return post<CalendarSyncResponse>('/api/v1/calendar/sync', {});
  },
};
