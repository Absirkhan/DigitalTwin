'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { authService } from '@/lib/api';
import DigitalTwinLogo from '@/app/components/DigitalTwinLogo';
import ThemeToggle from '@/app/components/ThemeToggle';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  
  // Get redirect URL from query params (e.g., /login?redirect=/dashboard)
  const redirectUrl = searchParams.get('redirect') || '/dashboard';

  // Store redirect URL for after OAuth callback
  useEffect(() => {
    if (redirectUrl) {
      sessionStorage.setItem('loginRedirectUrl', redirectUrl);
    }
  }, [redirectUrl]);

  const handleGoogleLogin = async () => {
    try {
      setIsLoading(true);
      setError('');
      
      // This will redirect the page to Google OAuth
      await authService.loginWithGoogleRedirect();
      
    } catch (err) {
      console.error('Login error:', err);
      setError(err instanceof Error ? err.message : 'Failed to initiate login');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-background" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Theme Toggle - Top Right */}
      <div className="fixed top-4 right-4 z-50">
        <ThemeToggle />
      </div>
      
      {/* Animated background gradient mesh */}
      <div className="absolute inset-0 gradient-mesh opacity-30" />
      <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10" />
      
      <div className="relative z-10 max-w-md w-full mx-4 animate-fade-in">
        {/* Glass card */}
        <div className="glass rounded-2xl p-8 border" style={{ boxShadow: '0 4px 16px rgba(0, 0, 0, 0.08)' }}>
          {/* Header */}
          <div className="text-center mb-8">
            {/* Custom Digital Twin Logo - Robot + Human */}
            <div className="mb-4">
              <DigitalTwinLogo size={80} showShadow={true} />
            </div>
            <h1 className="text-3xl font-bold text-foreground mb-2 tracking-tight">
              Digital Twin
            </h1>
            <p className="text-muted-foreground text-sm">
              AI-Powered Meeting Intelligence
            </p>
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-6 bg-muted/50 border border-border px-4 py-3 rounded-xl animate-scale-in">
              <p className="text-sm font-medium text-foreground">{error}</p>
            </div>
          )}

          {/* Login button */}
          <div className="space-y-4">
            <button
              onClick={handleGoogleLogin}
              disabled={isLoading}
              className="group w-full flex items-center justify-center gap-3 bg-card hover:bg-accent border-2 border-border hover:border-primary/30 rounded-xl px-6 py-3.5 text-foreground font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
              style={{
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                if (!isLoading) {
                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
                  e.currentTarget.style.transform = 'scale(1.02)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = '0 1px 2px 0 rgba(0, 0, 0, 0.05)';
                e.currentTarget.style.transform = 'scale(1)';
              }}
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-primary border-t-transparent"></div>
                  <span className="text-sm">Redirecting to Google...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 transition-transform group-hover:scale-110" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    />
                  </svg>
                  <span className="text-sm font-semibold">Continue with Google</span>
                </>
              )}
            </button>
          </div>

          {/* Privacy notice */}
          <div className="mt-6 text-center text-xs text-muted-foreground">
            <p>
              By continuing, you agree to our{' '}
              <a 
                href="#" 
                className="font-medium transition-all"
                style={{ color: '#D97757', textDecoration: 'none' }}
                onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
              >
                Terms
              </a>
              {' '}and{' '}
              <a 
                href="#" 
                className="font-medium transition-all"
                style={{ color: '#D97757', textDecoration: 'none' }}
                onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
              >
                Privacy Policy
              </a>
            </p>
          </div>
        </div>

        {/* Features */}
        <div className="glass rounded-2xl p-6 shadow-lg border animate-fade-in" style={{ marginTop: '56px', animationDelay: '0.1s' }}>
          <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <svg className="w-4 h-4" style={{ color: '#D97757' }} fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            Why Digital Twin?
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { 
                icon: (
                  <svg width="24" height="24" style={{ color: '#D97757' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                ), 
                text: 'AI Bot Assistant' 
              },
              { 
                icon: (
                  <svg width="24" height="24" style={{ color: '#D97757' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                ), 
                text: 'Auto Transcripts' 
              },
              { 
                icon: (
                  <svg width="24" height="24" style={{ color: '#D97757' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                ), 
                text: 'HD Recordings' 
              },
              { 
                icon: (
                  <svg width="24" height="24" style={{ color: '#D97757' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                ), 
                text: 'Smart Insights' 
              },
            ].map((feature, idx) => (
              <div 
                key={idx}
                className="flex items-center gap-2.5 rounded-lg group"
                style={{
                  padding: '12px',
                  transition: 'all 0.2s ease',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(217, 119, 87, 0.04)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <div className="flex-shrink-0 group-hover:scale-110 transition-transform">
                  {feature.icon}
                </div>
                <span className="text-xs font-medium text-muted-foreground group-hover:text-foreground transition-colors">
                  {feature.text}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
