'use client';

/**
 * Authentication Hook
 * Manages user authentication state
 */

import { useState, useEffect, useCallback } from 'react';
import type { User } from '@/lib/api/types';
import { authService, userService, getAuthToken } from '@/lib/api';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check if user is authenticated on mount
  useEffect(() => {
    const token = getAuthToken();
    console.log('useAuth: Checking authentication, token present:', !!token);
    if (token) {
      fetchUser();
    } else {
      // Give it a moment in case token is being set (during OAuth callback)
      const recheckTimeout = setTimeout(() => {
        const recheckToken = getAuthToken();
        if (recheckToken) {
          console.log('useAuth: Token found on recheck');
          fetchUser();
        } else {
          console.log('useAuth: No token found');
          setIsLoading(false);
        }
      }, 200);
      
      return () => clearTimeout(recheckTimeout);
    }
  }, []);

  const fetchUser = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      console.log('useAuth: Fetching user data...');
      const userData = await userService.getMe();
      console.log('useAuth: User data received:', userData?.email);
      setUser(userData);
      setIsAuthenticated(true);
    } catch (err: any) {
      // Check if this is an expected authentication error
      const isAuthError = err?.isAuthError || (err instanceof Error && err.message.includes('Could not validate credentials'));
      
      if (isAuthError) {
        // Clear invalid token from storage
        console.log('useAuth: Invalid token detected, clearing from storage');
        localStorage.removeItem('auth_token');
        sessionStorage.removeItem('auth_token');
      } else {
        console.error('useAuth: Failed to fetch user:', err);
      }
      
      setError(null); // Don't set error for expected auth failures
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loginWithGoogle = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Redirect to Google OAuth (will leave the page)
      await authService.loginWithGoogleRedirect();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      setIsAuthenticated(false);
      setUser(null);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    setUser(null);
    setIsAuthenticated(false);
    setError(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    loginWithGoogle,
    logout,
    fetchUser,
    clearError,
  };
}

