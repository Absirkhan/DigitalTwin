/**
 * Real-Time Transcript WebSocket Hook
 *
 * Ultra-low latency hook for streaming live transcripts from meetings.
 *
 * Features:
 * - Automatic reconnection on disconnect
 * - JWT authentication
 * - Buffered updates for performance
 * - Connection status tracking
 */

import { useState, useEffect, useRef, useCallback } from 'react';

export interface TranscriptChunk {
  meeting_id: number;
  speaker: string;
  text: string;
  timestamp: number;
  confidence?: number;
  is_final?: boolean;
}

export interface WebSocketMessage {
  type: string;
  meeting_id: number;
  [key: string]: any;
}

export interface UseRealtimeTranscriptReturn {
  transcript: TranscriptChunk[];
  isConnected: boolean;
  error: string | null;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  clearTranscript: () => void;
  reconnect: () => void;
}

interface UseRealtimeTranscriptOptions {
  enabled?: boolean;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

const WEBSOCKET_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1/realtime';

export function useRealtimeTranscript(
  meetingId: number | null,
  token: string | null,
  options: UseRealtimeTranscriptOptions = {}
): UseRealtimeTranscriptReturn {
  const {
    enabled = true,
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const [transcript, setTranscript] = useState<TranscriptChunk[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldConnectRef = useRef(false);
  const isCleanupRef = useRef(false); // Track if disconnect is from cleanup

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(() => {
    console.log('🔧 [CONNECT] Function called', {
      enabled,
      meetingId,
      token: token ? `${token.substring(0, 20)}...` : null,
      currentReadyState: wsRef.current?.readyState,
      readyStateMap: {
        0: 'CONNECTING',
        1: 'OPEN',
        2: 'CLOSING',
        3: 'CLOSED'
      }[wsRef.current?.readyState ?? -1] || 'NULL'
    });

    // Don't connect if disabled or missing required params
    if (!enabled || !meetingId || !token) {
      console.log('⚠️ [CONNECT] Skipping connection - missing params', {
        enabled,
        meetingId: !!meetingId,
        token: !!token
      });
      setConnectionStatus('disconnected');
      return;
    }

    // Don't connect if already connected or connecting
    if (wsRef.current?.readyState === WebSocket.CONNECTING ||
        wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('⚠️ [CONNECT] Skipping - already connected/connecting', {
        readyState: wsRef.current.readyState
      });
      return;
    }

    shouldConnectRef.current = true;
    setConnectionStatus('connecting');
    setError(null);

    try {
      // Construct WebSocket URL with JWT token
      const wsUrl = `${WEBSOCKET_BASE_URL}/ws/transcript/${meetingId}?token=${encodeURIComponent(token)}`;

      console.log(`🔌 [CONNECT] Creating WebSocket connection`, {
        meetingId,
        baseUrl: WEBSOCKET_BASE_URL,
        fullUrl: wsUrl.substring(0, 100) + '...'
      });

      const ws = new WebSocket(wsUrl);

      console.log('📡 [CONNECT] WebSocket object created', {
        readyState: ws.readyState,
        url: ws.url.substring(0, 100) + '...'
      });

      // ===== CONNECTION OPENED =====
      ws.onopen = () => {
        console.log(`✅ [ONOPEN] WebSocket connection established`, {
          meetingId,
          readyState: ws.readyState,
          url: ws.url.substring(0, 80) + '...',
          protocol: ws.protocol,
          extensions: ws.extensions
        });
        setIsConnected(true);
        setConnectionStatus('connected');
        setError(null);
        reconnectAttempts.current = 0;

        // Send ping to keep connection alive (every 30 seconds)
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            console.log('💓 [PING] Sending keepalive ping');
            ws.send('ping');
          } else {
            console.log('⚠️ [PING] Connection not open, clearing interval', {
              readyState: ws.readyState
            });
            clearInterval(pingInterval);
          }
        }, 30000);
      };

      // ===== MESSAGE RECEIVED =====
      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          // Handle different message types
          switch (message.type) {
            case 'transcript_chunk':
              // Add new transcript chunk
              const chunk: TranscriptChunk = {
                meeting_id: message.meeting_id,
                speaker: message.speaker || 'Unknown',
                text: message.text || '',
                timestamp: message.timestamp || Date.now() / 1000,
                confidence: message.confidence,
                is_final: message.is_final !== false,
              };

              setTranscript((prev) => [...prev, chunk]);

              console.log(
                `📝 Transcript chunk: ${chunk.speaker}: "${chunk.text.substring(0, 50)}..."`
              );
              break;

            case 'connection_established':
              console.log(`✅ Connection confirmed: ${message.message}`);
              break;

            case 'pong':
              // Keepalive response
              break;

            case 'meeting_status':
              console.log(`📊 Meeting status: ${message.status}`);
              break;

            case 'error':
              console.error(`❌ Server error: ${message.error}`);
              setError(message.error);
              break;

            default:
              console.warn(`⚠️ Unknown message type: ${message.type}`, message);
          }
        } catch (err) {
          console.error('❌ Failed to parse WebSocket message:', err);
        }
      };

      // ===== CONNECTION CLOSED =====
      ws.onclose = (event) => {
        console.log(`🔌 [ONCLOSE] WebSocket connection closed`, {
          code: event.code,
          reason: event.reason || '(no reason provided)',
          wasClean: event.wasClean,
          meetingId,
          readyState: ws.readyState,
          closeCodeMeaning: {
            1000: 'Normal closure',
            1001: 'Going away',
            1002: 'Protocol error',
            1003: 'Unsupported data',
            1006: 'Abnormal closure (no close frame)',
            1007: 'Invalid frame payload',
            1008: 'Policy violation',
            1009: 'Message too big',
            1010: 'Mandatory extension missing',
            1011: 'Internal server error',
            1015: 'TLS handshake failed',
            4001: 'Authentication failed',
            4003: 'Unauthorized access'
          }[event.code] || 'Unknown'
        });
        setIsConnected(false);
        setConnectionStatus('disconnected');

        // Auto-reconnect if enabled and should connect
        if (autoReconnect && shouldConnectRef.current) {
          if (reconnectAttempts.current < maxReconnectAttempts) {
            reconnectAttempts.current++;
            console.log(
              `🔄 [RECONNECT] Attempting reconnection (${reconnectAttempts.current}/${maxReconnectAttempts}) in ${reconnectInterval}ms`
            );

            reconnectTimeoutRef.current = setTimeout(() => {
              connect();
            }, reconnectInterval);
          } else {
            console.error('❌ [RECONNECT] Max reconnect attempts reached');
            setError('Connection lost. Please refresh the page.');
            setConnectionStatus('error');
          }
        } else {
          console.log('ℹ️ [RECONNECT] Auto-reconnect disabled or not requested', {
            autoReconnect,
            shouldConnect: shouldConnectRef.current
          });
        }
      };

      // ===== CONNECTION ERROR =====
      ws.onerror = (event) => {
        console.error('❌ [ONERROR] WebSocket error occurred', {
          event,
          type: event.type,
          target: event.target,
          readyState: ws.readyState,
          readyStateText: ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][ws.readyState],
          meetingId,
          url: ws.url.substring(0, 80) + '...',
          timestamp: new Date().toISOString()
        });

        // Log the entire event object for debugging
        console.error('❌ [ONERROR] Full event object:', event);

        setError('WebSocket connection error');
        setConnectionStatus('error');
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('❌ Failed to create WebSocket:', err);
      setError('Failed to connect to real-time transcript');
      setConnectionStatus('error');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meetingId, token]); // Only recreate when meetingId or token changes

  /**
   * Disconnect from WebSocket server
   */
  const disconnect = useCallback(() => {
    console.log('🔌 [DISCONNECT] Function called', {
      hasConnection: !!wsRef.current,
      readyState: wsRef.current?.readyState,
      readyStateText: wsRef.current ? ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][wsRef.current.readyState] : 'NULL'
    });

    shouldConnectRef.current = false;

    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      console.log('🔄 [DISCONNECT] Clearing reconnect timeout');
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close WebSocket connection
    if (wsRef.current) {
      // Skip closing if this is a cleanup call and WebSocket is still connecting
      // This handles React Strict Mode double-mount in development
      if (isCleanupRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
        console.log('⏭️ [DISCONNECT] Skipping close - cleanup during CONNECTING (React Strict Mode)', {
          readyState: wsRef.current.readyState
        });
        return;
      }

      console.log('📪 [DISCONNECT] Closing WebSocket connection', {
        readyState: wsRef.current.readyState,
        isCleanup: isCleanupRef.current
      });
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionStatus('disconnected');
    console.log('✅ [DISCONNECT] Disconnect complete');
  }, []);

  /**
   * Manual reconnect
   */
  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttempts.current = 0;
    setTimeout(() => {
      connect();
    }, 100);
  }, [connect, disconnect]);

  /**
   * Clear transcript history
   */
  const clearTranscript = useCallback(() => {
    setTranscript([]);
  }, []);

  // ===== EFFECTS =====

  /**
   * Connect/disconnect based on dependencies
   */
  useEffect(() => {
    console.log('🔄 [EFFECT] useEffect triggered', {
      enabled,
      meetingId,
      hasToken: !!token,
      tokenPreview: token ? `${token.substring(0, 20)}...` : null
    });

    if (enabled && meetingId && token) {
      console.log('➡️ [EFFECT] Conditions met, calling connect()');
      connect();
    } else {
      console.log('⬅️ [EFFECT] Conditions not met, calling disconnect()', {
        enabled,
        meetingId: !!meetingId,
        token: !!token
      });
      disconnect();
    }

    // Cleanup on unmount
    return () => {
      console.log('🧹 [EFFECT] Cleanup function called (component unmounting or deps changed)');
      isCleanupRef.current = true;
      disconnect();
      isCleanupRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meetingId, token, enabled]); // Don't include connect/disconnect - they cause re-render loop

  return {
    transcript,
    isConnected,
    error,
    connectionStatus,
    clearTranscript,
    reconnect,
  };
}
