/**
 * Custom hook for automatic calendar synchronization and meeting updates
 */

import { useEffect, useRef, useCallback } from 'react';
import { calendarService, meetingService } from '@/lib/api';
import type { Meeting } from '@/lib/api/types';

interface UseAutoSyncOptions {
  onMeetingsUpdate?: (meetings: Meeting[]) => void;
  onSyncSuccess?: (eventsSynced: number) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
  syncInterval?: number; // in milliseconds, default 1000 (1 second)
}

export function useAutoSync({
  onMeetingsUpdate,
  onSyncSuccess,
  onError,
  enabled = true,
  syncInterval = 1000
}: UseAutoSyncOptions) {
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isRunningRef = useRef(false);
  const lastSyncRef = useRef<number>(0);
  const meetingsHashRef = useRef<string>('');

  // Function to create a hash of meetings for comparison
  const createMeetingsHash = (meetings: Meeting[]): string => {
    return JSON.stringify(meetings.map(m => ({
      id: m.id,
      title: m.title,
      status: m.status,
      start_time: m.start_time,
      end_time: m.end_time,
      updated_at: m.updated_at
    })));
  };

  const syncCalendarAndUpdateMeetings = useCallback(async () => {
    if (isRunningRef.current || !enabled) return;
    
    isRunningRef.current = true;
    
    try {
      // Perform calendar sync (silently, don't show alerts)
      const syncResult = await calendarService.sync();
      
      // Only call onSyncSuccess if events were actually synced
      if (syncResult.events_synced > 0 && onSyncSuccess) {
        onSyncSuccess(syncResult.events_synced);
      }
      
      // Always fetch latest meetings after sync
      const meetings = await meetingService.getAll();
      
      // Check if meetings have changed by comparing hash
      const newHash = createMeetingsHash(meetings);
      if (newHash !== meetingsHashRef.current) {
        meetingsHashRef.current = newHash;
        if (onMeetingsUpdate) {
          onMeetingsUpdate(meetings);
        }
      }
      
      lastSyncRef.current = Date.now();
      
    } catch (error) {
      console.error('Auto-sync error:', error);
      if (onError && error instanceof Error) {
        onError(error);
      }
    } finally {
      isRunningRef.current = false;
    }
  }, [enabled, onMeetingsUpdate, onSyncSuccess, onError]);

  const startAutoSync = useCallback(() => {
    if (intervalRef.current) return; // Already running
    
    // Initial sync
    syncCalendarAndUpdateMeetings();
    
    // Set up interval
    intervalRef.current = setInterval(() => {
      syncCalendarAndUpdateMeetings();
    }, syncInterval);
    
    console.log(`🔄 Auto-sync started (interval: ${syncInterval}ms)`);
  }, [syncCalendarAndUpdateMeetings, syncInterval]);

  const stopAutoSync = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
      console.log('⏹️ Auto-sync stopped');
    }
  }, []);

  const forceSync = useCallback(() => {
    syncCalendarAndUpdateMeetings();
  }, [syncCalendarAndUpdateMeetings]);

  // Start/stop auto-sync based on enabled flag
  useEffect(() => {
    if (enabled) {
      startAutoSync();
    } else {
      stopAutoSync();
    }

    return () => {
      stopAutoSync();
    };
  }, [enabled, startAutoSync, stopAutoSync]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopAutoSync();
    };
  }, [stopAutoSync]);

  return {
    isRunning: !!intervalRef.current,
    lastSync: lastSyncRef.current,
    forceSync,
    startAutoSync,
    stopAutoSync
  };
}