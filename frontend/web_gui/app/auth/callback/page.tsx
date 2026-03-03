'use client';

import { useEffect, useState, Suspense, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { authService } from '@/lib/api';

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(true);
  const hasProcessed = useRef(false);

  useEffect(() => {
    const handleCallback = async () => {
      // Prevent duplicate execution (React Strict Mode runs effects twice)
      if (hasProcessed.current) {
        console.log('OAuth callback already processed, skipping');
        return;
      }
      hasProcessed.current = true;
      try {
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');
        
        console.log('OAuth callback received:', {
          hasCode: !!code,
          codeLength: code?.length,
          hasState: !!state,
          state,
          error,
          allParams: Object.fromEntries(searchParams.entries())
        });
        
        if (error) {
          setError(`OAuth error: ${error}`);
          setIsProcessing(false);
          return;
        }
        
        if (!code) {
          setError('No authorization code received');
          setIsProcessing(false);
          return;
        }

        // Exchange code for token using the POST endpoint
        console.log('Exchanging code for token...');
        const response = await authService.exchangeCodeForToken(code, state || undefined);
        
        console.log('Token exchange response:', { 
          hasAccessToken: !!response.access_token, 
          tokenLength: response.access_token?.length,
          tokenType: response.token_type,
          tokenPreview: response.access_token ? `${response.access_token.substring(0, 20)}...` : 'none'
        });
        
        if (response.access_token) {
          console.log('Token received, storing...');
          // Store token and redirect to dashboard
          localStorage.setItem('auth_token', response.access_token);
          
          // Verify token is stored before redirecting
          const storedToken = localStorage.getItem('auth_token');
          console.log('Token stored:', storedToken ? 'Yes' : 'No');
          console.log('Stored token matches:', storedToken === response.access_token);
          
          if (storedToken) {
            // Get redirect URL from session storage (set during login)
            const redirectUrl = sessionStorage.getItem('loginRedirectUrl') || '/dashboard';
            sessionStorage.removeItem('loginRedirectUrl'); // Clean up
            
            // Use router.replace instead of router.push to avoid back button issues
            // And add a longer delay to ensure token is fully available
            setTimeout(() => {
              console.log('Redirecting to:', redirectUrl);
              router.replace(redirectUrl);
            }, 300);
          } else {
            setError('Failed to store authentication token');
            setIsProcessing(false);
          }
        } else {
          setError('Failed to receive access token');
          setIsProcessing(false);
        }
      } catch (err) {
        console.error('Callback error:', err);
        setError(err instanceof Error ? err.message : 'Authentication failed');
        setIsProcessing(false);
      }
    };

    handleCallback();
  }, [searchParams, router]);

  if (isProcessing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center animate-fade-in">
          <div className="relative mb-6">
            <div className="animate-spin rounded-full h-12 w-12 border-2 border-primary border-t-transparent mx-auto"></div>
            <div className="absolute inset-0 rounded-full bg-primary/20 blur-xl animate-pulse"></div>
          </div>
          <h2 className="text-xl font-semibold text-foreground">Completing sign in...</h2>
          <p className="text-muted-foreground mt-2">Please wait while we authenticate you</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="max-w-md w-full card shadow-warm-lg p-8 animate-scale-in">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#C56846]/10 mb-4">
              <svg className="w-8 h-8 text-[#C56846]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-foreground mb-2">Authentication Failed</h2>
            <p className="text-muted-foreground mb-8">{error}</p>
            <button
              onClick={() => router.push('/login')}
              className="w-full btn btn-primary py-3 text-sm"
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center animate-fade-in">
          <div className="relative mb-6">
            <div className="animate-spin rounded-full h-12 w-12 border-2 border-primary border-t-transparent mx-auto"></div>
            <div className="absolute inset-0 rounded-full bg-primary/20 blur-xl animate-pulse"></div>
          </div>
          <h2 className="text-xl font-semibold text-foreground">Loading...</h2>
        </div>
      </div>
    }>
      <AuthCallbackContent />
    </Suspense>
  );
}
