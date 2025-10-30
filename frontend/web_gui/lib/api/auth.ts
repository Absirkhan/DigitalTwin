/**
 * Authentication API Service
 */

import { get, post, setAuthToken } from './client';
import type { GoogleLoginResponse, AuthCallbackResponse } from './types';

export const authService = {
  /**
   * Get Google OAuth login URL
   * GET /api/v1/auth/google/login
   */
  getGoogleLoginUrl: async (): Promise<GoogleLoginResponse> => {
    const response = await get<{ auth_url: string }>('/api/v1/auth/google/login', {
      requiresAuth: false,
    });
    return { authorization_url: response.auth_url };
  },

  /**
   * Exchange authorization code for JWT token
   * POST /api/v1/auth/google/token
   */
  exchangeCodeForToken: async (code: string, state?: string): Promise<{ access_token: string; token_type: string }> => {
    const response = await post<{ access_token: string; token_type: string }>(
      '/api/v1/auth/google/token',
      { code, state },
      { requiresAuth: false }
    );
    
    // Store the token
    if (response.access_token) {
      setAuthToken(response.access_token);
    }
    
    return response;
  },

  /**
   * Initiate Google login flow using redirect (simpler approach)
   * This redirects the entire page to Google, then back to our callback
   */
  loginWithGoogleRedirect: async (): Promise<void> => {
    const { authorization_url } = await authService.getGoogleLoginUrl();
    // Full page redirect to Google
    window.location.href = authorization_url;
  },

  /**
   * Logout user
   * POST /api/v1/auth/logout
   */
  logout: async (): Promise<void> => {
    try {
      await post('/api/v1/auth/logout', {});
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setAuthToken('');
      localStorage.removeItem('auth_token');
    }
  },
};
