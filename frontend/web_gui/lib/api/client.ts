/**
 * API Client Configuration
 * Handles all HTTP requests to the FastAPI backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RequestOptions extends RequestInit {
  requiresAuth?: boolean;
}

/**
 * Get the authentication token from localStorage
 */
export const getAuthToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
};

/**
 * Set the authentication token in localStorage
 */
export const setAuthToken = (token: string): void => {
  localStorage.setItem('auth_token', token);
};

/**
 * Remove the authentication token from localStorage
 */
export const removeAuthToken = (): void => {
  localStorage.removeItem('auth_token');
};

/**
 * Generic API request handler
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { requiresAuth = true, headers = {}, ...fetchOptions } = options;

  const url = `${API_BASE_URL}${endpoint}`;

  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(headers as Record<string, string>),
  };

  // Add authorization header if required
  if (requiresAuth) {
    const token = getAuthToken();
    if (token) {
      requestHeaders['Authorization'] = `Bearer ${token}`;
      console.log('API Request: Token present, length:', token.length);
    } else {
      console.warn('API Request: No auth token found but auth required!');
    }
  }

  try {
    console.log('API Request:', { url, method: fetchOptions.method, hasAuth: !!requestHeaders['Authorization'] });
    
    const response = await fetch(url, {
      ...fetchOptions,
      headers: requestHeaders,
    });

    // Handle non-OK responses
    if (!response.ok) {
      // Try to get response text first to see what the server actually returned
      const responseText = await response.text();
      let errorData: any = {};
      
      try {
        errorData = JSON.parse(responseText);
      } catch {
        // Only log non-JSON responses if it's not a 401 (expected for unauthenticated users)
        if (response.status !== 401) {
          console.error('Response is not JSON:', responseText);
        }
      }
      
      const errorMessage = errorData.detail || `HTTP ${response.status}: ${response.statusText}`;
      
      // For 401 errors or credential validation failures, throw a special error that won't be logged
      if (response.status === 401 || errorMessage.includes('Could not validate credentials')) {
        const authError = new Error(errorMessage);
        (authError as any).isAuthError = true; // Mark as expected auth error
        throw authError;
      }
      
      // Only log detailed errors for unexpected failures
      console.error('API Error Details:', {
        url,
        method: fetchOptions.method,
        status: response.status,
        statusText: response.statusText,
        errorData,
        responseText: responseText.substring(0, 200), // First 200 chars
        requestHeaders: { ...requestHeaders, Authorization: requestHeaders['Authorization'] ? 'Bearer ***' : 'none' },
        headers: Object.fromEntries(response.headers.entries())
      });
      throw new Error(errorMessage);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error) {
    console.error('API Request Error:', error);
    throw error;
  }
}

/**
 * GET request
 */
export const get = <T>(endpoint: string, options?: RequestOptions): Promise<T> => {
  return apiRequest<T>(endpoint, { ...options, method: 'GET' });
};

/**
 * POST request
 */
export const post = <T>(
  endpoint: string,
  data?: unknown,
  options?: RequestOptions
): Promise<T> => {
  return apiRequest<T>(endpoint, {
    ...options,
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
};

/**
 * PUT request
 */
export const put = <T>(
  endpoint: string,
  data?: unknown,
  options?: RequestOptions
): Promise<T> => {
  return apiRequest<T>(endpoint, {
    ...options,
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });
};

/**
 * DELETE request
 */
export const del = <T>(endpoint: string, options?: RequestOptions): Promise<T> => {
  return apiRequest<T>(endpoint, { ...options, method: 'DELETE' });
};

export default {
  get,
  post,
  put,
  delete: del,
  getAuthToken,
  setAuthToken,
  removeAuthToken,
};
