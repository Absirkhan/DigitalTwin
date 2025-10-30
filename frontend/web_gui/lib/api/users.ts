/**
 * User API Service
 */

import { get, put } from './client';
import type { User, UserUpdate } from './types';

export const userService = {
  /**
   * Get current user profile
   * GET /api/v1/users/me
   */
  getMe: async (): Promise<User> => {
    return get<User>('/api/v1/users/me');
  },

  /**
   * Update current user profile
   * PUT /api/v1/users/me
   */
  updateMe: async (data: UserUpdate): Promise<User> => {
    return put<User>('/api/v1/users/me', data);
  },
};
