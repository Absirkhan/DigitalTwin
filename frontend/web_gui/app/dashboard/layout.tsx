'use client';

import { useAuth } from '@/lib/hooks/useAuth';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import DigitalTwinLogo from '@/app/components/DigitalTwinLogo';
import ThemeToggle from '@/app/components/ThemeToggle';

const navigation = [
  { 
    name: 'Dashboard', 
    href: '/dashboard', 
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    )
  },
  { 
    name: 'Meetings', 
    href: '/dashboard/meetings', 
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    )
  },
  { 
    name: 'All Meetings', 
    href: '/dashboard/all-meetings', 
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
    )
  },
  { 
    name: 'Transcripts', 
    href: '/dashboard/transcripts', 
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    )
  },
  {
    name: 'Recordings',
    href: '/dashboard/recordings',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    )
  },
  {
    name: 'AI Assistant',
    href: '/dashboard/rag',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    )
  },
  {
    name: 'Profile',
    href: '/dashboard/profile',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    )
  },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarMinimized, setSidebarMinimized] = useState(true);
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  // Reset image error when user profile picture changes
  useEffect(() => {
    setImageError(false);
  }, [user?.profile_picture]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--bg-primary)' }}>
        <div className="flex flex-col items-center gap-4 animate-fade-in">
          <div className="relative">
            <div className="animate-spin rounded-full h-12 w-12 border-2 border-t-transparent" style={{ borderColor: 'var(--orange-primary)', borderTopColor: 'transparent' }}></div>
            <div className="absolute inset-0 rounded-full blur-xl animate-pulse" style={{ backgroundColor: 'var(--orange-primary)', opacity: 0.2 }}></div>
          </div>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Sidebar for desktop */}
      <aside className={`hidden lg:fixed lg:inset-y-0 lg:flex lg:flex-col transition-all duration-300 ${sidebarMinimized ? 'lg:w-20' : 'lg:w-[280px]'}`} style={{ backgroundColor: 'var(--sidebar-bg)', borderRight: '1px solid var(--sidebar-border)' }}>
        <div className="flex grow flex-col overflow-y-auto">
          {/* Sidebar Header */}
          <div className={`flex transition-all duration-300 ${sidebarMinimized ? 'flex-col items-center justify-center gap-3 px-3 py-4' : 'flex-row items-center justify-between gap-4 px-4 py-5'}`} style={{ borderBottom: '1px solid var(--border-primary)' }}>
            {/* Logo + Title */}
            <Link href="/dashboard" className={`flex items-center transition-transform hover:scale-105 ${sidebarMinimized ? 'flex-col gap-0 w-full justify-center' : 'gap-3 flex-1 min-w-0'}`} title="Go to Dashboard">
              <DigitalTwinLogo size={sidebarMinimized ? 40 : 36} showShadow={false} />
              {!sidebarMinimized && (
                <h1 
                  className="text-lg font-normal whitespace-nowrap" 
                  style={{ color: 'var(--text-primary)', margin: 0 }}
                >
                  Digital Twin
                </h1>
              )}
            </Link>
            
            {/* Controls */}
            <div className={`flex flex-shrink-0 ${sidebarMinimized ? 'flex-col items-center gap-2 w-full' : 'flex-row gap-2 ml-auto pl-4'}`}>
              <div className={`rounded-lg flex items-center justify-center border transition-all duration-200 hover:bg-[var(--bg-tertiary)] hover:border-[var(--orange-primary)] flex-shrink-0 ${sidebarMinimized ? 'w-10 h-10' : 'w-9 h-9'}`} style={{ borderColor: 'var(--border-primary)' }}>
                <ThemeToggle />
              </div>
              <button
                onClick={() => setSidebarMinimized(!sidebarMinimized)}
                className={`rounded-lg flex items-center justify-center border transition-all duration-200 hover:bg-[var(--bg-tertiary)] hover:border-[var(--orange-primary)] flex-shrink-0 ${sidebarMinimized ? 'w-10 h-10' : 'w-9 h-9'}`}
                style={{ borderColor: 'var(--border-primary)', color: 'var(--text-secondary)' }}
                title={sidebarMinimized ? 'Expand sidebar' : 'Minimize sidebar'}
                aria-label={sidebarMinimized ? 'Expand sidebar' : 'Minimize sidebar'}
              >
                <svg 
                  className={`w-5 h-5 transition-transform duration-300 ${sidebarMinimized ? 'rotate-180' : ''}`} 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                </svg>
              </button>
            </div>
          </div>
          
          {/* Navigation */}
          <nav className="flex flex-1 flex-col py-5">
            <ul role="list" className="flex flex-1 flex-col gap-y-2">
              <li>
                <ul role="list" className="space-y-1">
                  {navigation.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                      <li key={item.name}>
                        <Link
                          href={item.href}
                          className={`group flex items-center ${sidebarMinimized ? 'justify-center py-4 px-0' : 'gap-x-3 px-5 py-3'} text-[15px] font-normal transition-all duration-200 relative`}
                          style={{
                            backgroundColor: isActive ? 'var(--sidebar-item-active-bg)' : 'transparent',
                            color: isActive ? 'var(--sidebar-item-active-text)' : 'var(--text-secondary)',
                            boxShadow: isActive ? 'var(--shadow-sm)' : 'none',
                            borderRight: isActive && !sidebarMinimized ? '3px solid var(--orange-primary)' : 'none',
                            borderLeft: isActive && sidebarMinimized ? '3px solid var(--orange-primary)' : 'none'
                          }}
                          onMouseEnter={(e) => {
                            if (!isActive) {
                              e.currentTarget.style.backgroundColor = 'var(--sidebar-item-hover)';
                              e.currentTarget.style.color = 'var(--text-primary)';
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!isActive) {
                              e.currentTarget.style.backgroundColor = 'transparent';
                              e.currentTarget.style.color = 'var(--text-secondary)';
                            }
                          }}
                          title={sidebarMinimized ? item.name : undefined}
                        >
                          <span className={`flex-shrink-0 ${sidebarMinimized ? 'w-6 h-6' : 'w-5 h-5'}`}>
                            {item.icon}
                          </span>
                          {!sidebarMinimized && <span>{item.name}</span>}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </li>
            </ul>
          </nav>

          {/* User profile section */}
          <div className="mt-auto" style={{ padding: '16px', borderTop: '1px solid var(--border-primary)' }}>
            {sidebarMinimized ? (
              <div className="flex flex-col items-center" style={{ gap: '12px', padding: '12px 8px' }}>
                <div className="flex items-center justify-center">
                  {user?.profile_picture && !imageError ? (
                    <img
                      className="rounded-full object-cover border-2"
                      style={{ 
                        width: '40px', 
                        height: '40px',
                        minWidth: '40px',
                        minHeight: '40px',
                        borderColor: 'var(--border-primary)',
                        flexShrink: 0
                      }}
                      src={user.profile_picture}
                      alt={user.full_name}
                      title={user.full_name}
                      referrerPolicy="no-referrer"
                      onError={() => setImageError(true)}
                    />
                  ) : (
                    <div 
                      className="rounded-full flex items-center justify-center border-2" 
                      style={{ 
                        width: '40px',
                        height: '40px',
                        minWidth: '40px',
                        minHeight: '40px',
                        background: 'linear-gradient(135deg, #D97757, #E07856)',
                        borderColor: 'var(--border-primary)',
                        flexShrink: 0
                      }} 
                      title={user?.full_name}
                    >
                      <span style={{ fontSize: '16px', fontWeight: 600, color: 'white' }}>
                        {user?.full_name?.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  )}
                </div>
                <button
                  onClick={logout}
                  className="w-10 h-10 flex items-center justify-center rounded-lg border transition-all duration-200 hover:bg-[var(--bg-tertiary)] hover:border-[var(--orange-primary)]"
                  style={{ borderColor: 'var(--border-primary)', color: 'var(--text-secondary)' }}
                  title="Logout"
                  aria-label="Logout"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                </button>
              </div>
            ) : (
              <div 
                className="flex items-center rounded-lg cursor-pointer transition-all duration-200"
                style={{ 
                  gap: '12px', 
                  padding: '12px',
                  border: '1px solid var(--border-primary)'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                {user?.profile_picture && !imageError ? (
                  <img
                    className="rounded-full object-cover border-2"
                    style={{ 
                      width: '40px',
                      height: '40px',
                      minWidth: '40px',
                      minHeight: '40px',
                      borderColor: 'var(--border-primary)',
                      flexShrink: 0
                    }}
                    src={user.profile_picture}
                    alt={user.full_name}
                    referrerPolicy="no-referrer"
                    onError={() => setImageError(true)}
                  />
                ) : (
                  <div 
                    className="rounded-full flex items-center justify-center border-2" 
                    style={{ 
                      width: '40px',
                      height: '40px',
                      minWidth: '40px',
                      minHeight: '40px',
                      background: 'linear-gradient(135deg, #D97757, #E07856)',
                      borderColor: 'var(--border-primary)',
                      flexShrink: 0
                    }}
                  >
                    <span style={{ fontSize: '16px', fontWeight: 600, color: 'white' }}>
                      {user?.full_name?.charAt(0).toUpperCase()}
                    </span>
                  </div>
                )}
                <div className="flex-1 min-w-0" style={{ overflow: 'hidden' }}>
                  <p className="truncate" style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)', margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {user?.full_name}
                  </p>
                  <p className="truncate" style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0, marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {user?.email}
                  </p>
                </div>
                <button
                  onClick={logout}
                  className="w-5 h-5 flex-shrink-0 transition-colors"
                  style={{ color: 'var(--text-tertiary)' }}
                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--orange-primary)'}
                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-tertiary)'}
                  title="Logout"
                  aria-label="Logout"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

  {/* Mobile header */}
  <div className="sticky top-0 z-40 flex items-center gap-x-6 bg-card border-b border-border px-4 py-4 shadow-sm lg:hidden">
        <button
          type="button"
          className="-m-2.5 p-2.5 text-muted-foreground lg:hidden"
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          <span className="sr-only">Open sidebar</span>
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>
        <div className="flex-1 text-sm font-semibold leading-6 text-foreground">
          {navigation.find(item => item.href === pathname)?.name || 'Dashboard'}
        </div>
        {/* mobile theme toggle */}
        <div className="ml-2">
          <ThemeToggle />
        </div>

        {user?.profile_picture && !imageError ? (
          <img
            className="h-8 w-8 rounded-full ring-2 ring-border"
            src={user.profile_picture}
            alt={user.full_name}
            referrerPolicy="no-referrer"
            onError={() => setImageError(true)}
          />
        ) : user ? (
          <div className="h-8 w-8 rounded-full flex items-center justify-center ring-2 ring-border" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
            <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
              {user.full_name?.charAt(0).toUpperCase()}
            </span>
          </div>
        ) : null}
      </div>

      {/* Desktop controls removed from fixed position; rendered inside page header to avoid overlap with CTAs */}

      {/* Main content */}
      <main className={`transition-all duration-300 ${sidebarMinimized ? 'lg:pl-20' : 'lg:pl-[280px]'}`}>
        <div className="px-4 py-8 sm:px-6 lg:px-8 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}
