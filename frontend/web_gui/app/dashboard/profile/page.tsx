'use client';

import { useEffect, useState } from 'react';
import { userService } from '@/lib/api';
import type { User, UserUpdate } from '@/lib/api/types';

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editForm, setEditForm] = useState<UserUpdate>({});
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    loadProfile();
  }, []);

  // Reset image error when user data changes
  useEffect(() => {
    setImageError(false);
  }, [user?.profile_picture]);

  const loadProfile = async () => {
    setIsLoading(true);
    try {
      const data = await userService.getMe();
      setUser(data);
      setEditForm({
        full_name: data.full_name,
        email: data.email,
        bot_name: data.bot_name,
      });
    } catch (error) {
      console.error('Failed to load profile:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const updatedUser = await userService.updateMe(editForm);
      setUser(updatedUser);
      setIsEditing(false);
    } catch (error) {
      alert('Failed to update profile: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="relative">
          <div
            className="animate-spin rounded-full h-12 w-12 border-2"
            style={{ borderColor: 'var(--color-primary)', borderTopColor: 'transparent' }}
          ></div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="text-center py-12">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
          <svg className="w-8 h-8 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm text-muted-foreground">Unable to load profile</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between" style={{ marginBottom: '32px' }}>
        <div className="flex-1 min-w-0">
          <h1 className="page-title" style={{ color: 'var(--text-primary)', fontSize: '36px', fontWeight: 700 }}>
            Profile
          </h1>
          <p className="page-subtitle" style={{ marginBottom: '0', color: 'var(--text-secondary)' }}>
            Manage your account settings and preferences
          </p>
        </div>
        <div className="mt-6 flex md:mt-0 md:ml-4">
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="btn btn-primary px-4 py-2.5 text-sm"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit Profile
            </button>
          )}
        </div>
      </div>

      {/* Profile Card */}
      <div style={{ background: 'transparent' }}>
        {/* Header with avatar */}
        <div className="border rounded-xl" style={{ padding: '32px', backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)', marginBottom: '16px' }}>
          <div className="flex items-center" style={{ gap: '24px' }}>
            {user.profile_picture && !imageError ? (
              <img
                src={user.profile_picture}
                alt={user.full_name}
                className="rounded-full ring-4 ring-background shadow-xl object-cover"
                style={{ width: '120px', height: '120px' }}
                referrerPolicy="no-referrer"
                onError={() => setImageError(true)}
              />
            ) : (
              <div className="rounded-full gradient-primary flex items-center justify-center ring-4 ring-background shadow-xl" style={{ width: '120px', height: '120px' }}>
                <span className="text-5xl font-bold text-white">
                  {user.full_name.charAt(0).toUpperCase()}
                </span>
              </div>
            )}
            <div className="flex-1">
              <h3 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                {user.full_name}
              </h3>
              <p className="mt-2 text-sm flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                {user.email}
              </p>
              <div style={{ marginTop: '12px' }}>
                <span 
                  className="inline-flex items-center rounded-full text-xs font-medium"
                  style={{
                    backgroundColor: user.is_active ? 'var(--orange-info-bg)' : 'var(--bg-tertiary)',
                    color: user.is_active ? 'var(--orange-primary)' : 'var(--text-tertiary)',
                    padding: '4px 10px'
                  }}
                >
                  <span 
                    className="rounded-full mr-1.5" 
                    style={{ 
                      width: '6px', 
                      height: '6px',
                      backgroundColor: user.is_active ? 'var(--orange-primary)' : 'var(--text-tertiary)'
                    }}
                  ></span>
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {isEditing ? (
          /* Edit Form */
          <form onSubmit={handleSave} className="space-y-6 border rounded-xl" style={{ padding: '32px', backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)' }}>
            <div className="space-y-5">
              <div>
                <label htmlFor="full_name" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                  Full Name
                </label>
                <input
                  type="text"
                  id="full_name"
                  value={editForm.full_name || ''}
                  onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                  className="input w-full"
                />
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                  Email Address
                </label>
                <input
                  type="email"
                  id="email"
                  value={editForm.email || ''}
                  onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                  className="input w-full"
                />
              </div>

              <div>
                <label htmlFor="bot_name" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                  Bot Name
                </label>
                <input
                  type="text"
                  id="bot_name"
                  value={editForm.bot_name || ''}
                  onChange={(e) => setEditForm({ ...editForm, bot_name: e.target.value })}
                  placeholder="My AI Assistant"
                  className="input w-full"
                />
                <p className="mt-2 text-xs text-muted-foreground">
                  Default name for your bot in meetings
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-border">
              <button
                type="button"
                onClick={() => {
                  setIsEditing(false);
                  setEditForm({
                    full_name: user.full_name,
                    email: user.email,
                    bot_name: user.bot_name,
                  });
                }}
                className="btn btn-outline px-4 py-2.5 text-sm"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSaving}
                className="btn btn-primary px-4 py-2.5 text-sm"
              >
                {isSaving ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                    Saving...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Save Changes
                  </>
                )}
              </button>
            </div>
          </form>
        ) : (
          /* Profile Details */
          <div>
            <dl className="space-y-4">
              {/* Full Name */}
              <div 
                className="flex items-center gap-4 rounded-lg border transition-colors hover:shadow-sm"
                style={{ 
                  backgroundColor: 'var(--bg-secondary)',
                  padding: '20px',
                  borderColor: 'var(--border-primary)',
                  borderWidth: '1px'
                }}
              >
                <div 
                  className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: 'var(--orange-info-bg)' }}
                >
                  <svg className="w-5 h-5" style={{ color: 'var(--orange-primary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <dt className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-tertiary)' }}>Full name</dt>
                  <dd className="mt-1 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {user.full_name}
                  </dd>
                </div>
              </div>
              
              {/* Email */}
              <div 
                className="flex items-center gap-4 rounded-lg border transition-colors hover:shadow-sm"
                style={{ 
                  backgroundColor: 'var(--bg-secondary)',
                  padding: '20px',
                  borderColor: 'var(--border-primary)',
                  borderWidth: '1px'
                }}
              >
                <div 
                  className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: 'var(--orange-info-bg)' }}
                >
                  <svg className="w-5 h-5" style={{ color: 'var(--orange-primary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <dt className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-tertiary)' }}>Email address</dt>
                  <dd className="mt-1 text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                    {user.email}
                  </dd>
                </div>
              </div>
              
              {/* Bot Name */}
              <div 
                className="flex items-center gap-4 rounded-lg border transition-colors hover:shadow-sm"
                style={{ 
                  backgroundColor: 'var(--bg-secondary)',
                  padding: '20px',
                  borderColor: 'var(--border-primary)',
                  borderWidth: '1px'
                }}
              >
                <div 
                  className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: 'var(--orange-info-bg)' }}
                >
                  <svg className="w-5 h-5" style={{ color: 'var(--orange-primary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <dt className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-tertiary)' }}>Bot name</dt>
                  <dd className="mt-1 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {user.bot_name || <span style={{ color: 'var(--text-tertiary)' }} className="italic">Not set</span>}
                  </dd>
                </div>
              </div>

              {/* Member Since */}
              {user.created_at && (() => {
                try {
                  const date = new Date(user.created_at);
                  if (!isNaN(date.getTime())) {
                    return (
                      <div 
                        className="flex items-center gap-4 rounded-lg border transition-colors hover:shadow-sm"
                        style={{ 
                          backgroundColor: 'var(--bg-secondary)',
                          padding: '20px',
                          borderColor: 'var(--border-primary)',
                          borderWidth: '1px'
                        }}
                      >
                        <div 
                          className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center"
                          style={{ backgroundColor: 'var(--orange-info-bg)' }}
                        >
                          <svg className="w-5 h-5" style={{ color: 'var(--orange-primary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <dt className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Member since</dt>
                          <dd className="mt-1 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                            {date.toLocaleDateString('en-US', { 
                              month: 'short', 
                              day: 'numeric',
                              year: 'numeric'
                            })}
                          </dd>
                        </div>
                      </div>
                    );
                  }
                } catch (e) {
                  return null;
                }
                return null;
              })()}
            </dl>
          </div>
        )}
      </div>

      {/* Account Settings */}
      <div className="border rounded-xl p-6" style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)' }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: 'var(--orange-info-bg)' }}>
            <svg className="w-5 h-5" style={{ color: 'var(--orange-primary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
              Account Settings
            </h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Additional settings and preferences
            </p>
          </div>
        </div>
        <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          <p>Coming soon: Notification preferences, privacy settings, and more customization options.</p>
        </div>
      </div>
    </div>
  );
}
