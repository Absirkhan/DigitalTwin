'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getAuthToken, userService } from '@/lib/api';
import './landing.css';

export default function LandingPage() {
  const router = useRouter();

  // Redirect to dashboard if already logged in
  useEffect(() => {
    const checkAuth = async () => {
      const token = getAuthToken();
      if (token) {
        // Validate the token before redirecting
        try {
          await userService.getMe();
          // Token is valid, redirect to dashboard
          router.push('/dashboard');
        } catch (error) {
          // Token is invalid or expired, clear it silently
          console.log('Invalid token detected on landing page, clearing...');
          localStorage.removeItem('auth_token');
          sessionStorage.removeItem('auth_token');
          // Stay on landing page
        }
      }
    };

    checkAuth();
  }, [router]);

  // Apply saved theme on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
      document.documentElement.classList.add('dark-mode');
    }
  }, []);

  const handleLogin = () => {
    router.push('/login?redirect=/dashboard');
  };

  const toggleTheme = () => {
    const isDark = document.documentElement.classList.toggle('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  };

  return (
    <div className="landing-page">
      {/* Theme Toggle Button */}
      <button 
        className="theme-toggle"
        onClick={toggleTheme}
        aria-label="Toggle theme"
      >
        <svg className="sun-icon" width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M10 3V1M10 19V17M17 10H19M1 10H3M15.657 4.343L17.071 2.929M2.929 17.071L4.343 15.657M15.657 15.657L17.071 17.071M2.929 2.929L4.343 4.343M14 10C14 12.209 12.209 14 10 14C7.791 14 6 12.209 6 10C6 7.791 7.791 6 10 6C12.209 6 14 7.791 14 10Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
        <svg className="moon-icon" width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M17 10.5C17 14.6421 13.6421 18 9.5 18C5.35786 18 2 14.6421 2 10.5C2 6.35786 5.35786 3 9.5 3C9.67679 3 9.85258 3.00647 10.027 3.01921C7.96091 4.12904 6.5 6.31015 6.5 8.83333C6.5 12.3312 9.33546 15.1667 12.8333 15.1667C15.0892 15.1667 17.0725 13.9279 18.2299 12.1068C17.8444 11.5776 17.4345 11.0724 17 10.5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {/* HERO SECTION */}
      <section className="hero">
        <div className="hero-content">
          <div className="logo">
            <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
              <circle cx="40" cy="40" r="38" stroke="var(--orange-primary)" strokeWidth="4"/>
              <circle cx="40" cy="40" r="28" fill="var(--orange-primary)" opacity="0.2"/>
              <path d="M40 20V40L52 52" stroke="var(--orange-primary)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
              <circle cx="40" cy="40" r="4" fill="var(--orange-primary)"/>
            </svg>
          </div>
          <h1>Digital Twin</h1>
          <h2>AI-Powered Meeting Intelligence</h2>
          <p>Transform your meetings into actionable insights with automated transcription, intelligent summaries, and seamless recording management.</p>
          <button onClick={handleLogin} className="btn-primary">
            Get Started
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M7.5 15L12.5 10L7.5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section className="features">
        <h2>Why Digital Twin?</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="icon">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <rect x="8" y="12" width="32" height="24" rx="4" stroke="var(--orange-primary)" strokeWidth="2"/>
                <circle cx="24" cy="24" r="4" fill="var(--orange-primary)"/>
                <path d="M16 24C16 19.5817 19.5817 16 24 16" stroke="var(--orange-primary)" strokeWidth="2" strokeLinecap="round"/>
                <path d="M32 24C32 28.4183 28.4183 32 24 32" stroke="var(--orange-primary)" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <h3>AI Bot Assistant</h3>
            <p>Join meetings automatically and capture every moment</p>
          </div>

          <div className="feature-card">
            <div className="icon">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <path d="M12 8H36C38.2091 8 40 9.79086 40 12V36C40 38.2091 38.2091 40 36 40H12C9.79086 40 8 38.2091 8 36V12C8 9.79086 9.79086 8 12 8Z" stroke="var(--orange-primary)" strokeWidth="2"/>
                <path d="M16 16H32M16 24H32M16 32H24" stroke="var(--orange-primary)" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <h3>Auto Transcripts</h3>
            <p>Get accurate transcriptions of your meetings instantly</p>
          </div>

          <div className="feature-card">
            <div className="icon">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <rect x="10" y="14" width="28" height="20" rx="2" stroke="var(--orange-primary)" strokeWidth="2"/>
                <circle cx="24" cy="24" r="6" stroke="var(--orange-primary)" strokeWidth="2"/>
                <circle cx="24" cy="24" r="2" fill="var(--orange-primary)"/>
                <path d="M38 28L42 32V16L38 20" stroke="var(--orange-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h3>HD Recordings</h3>
            <p>Store and access high-quality meeting recordings</p>
          </div>

          <div className="feature-card">
            <div className="icon">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <path d="M24 8L26.472 18.528L37 21L26.472 23.472L24 34L21.528 23.472L11 21L21.528 18.528L24 8Z" stroke="var(--orange-primary)" strokeWidth="2" strokeLinejoin="round"/>
                <path d="M36 12L37.236 16.764L42 18L37.236 19.236L36 24L34.764 19.236L30 18L34.764 16.764L36 12Z" fill="var(--orange-primary)"/>
                <path d="M14 30L15.236 34.764L20 36L15.236 37.236L14 42L12.764 37.236L8 36L12.764 34.764L14 30Z" fill="var(--orange-primary)"/>
              </svg>
            </div>
            <h3>Smart Insights</h3>
            <p>Generate AI-powered summaries and action items</p>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="how-it-works">
        <h2>How It Works</h2>
        <div className="steps">
          <div className="step">
            <div className="step-number">1</div>
            <h3>Connect Your Platform</h3>
            <p>Link your Google Meet or other meeting platforms</p>
          </div>
          <div className="step">
            <div className="step-number">2</div>
            <h3>AI Bot Joins</h3>
            <p>Our bot automatically joins and records your meetings</p>
          </div>
          <div className="step">
            <div className="step-number">3</div>
            <h3>Get Insights</h3>
            <p>Receive transcripts, summaries, and action items instantly</p>
          </div>
        </div>
      </section>

      {/* CTA SECTION */}
      <section className="cta">
        <h2>Ready to Transform Your Meetings?</h2>
        <p>Start managing your meetings intelligently</p>
        <button onClick={handleLogin} className="btn-primary">
          Login to Dashboard
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M7.5 15L12.5 10L7.5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </section>

      {/* FOOTER */}
      <footer className="footer">
        <p>&copy; 2025 Digital Twin. All rights reserved.</p>
      </footer>
    </div>
  );
}
