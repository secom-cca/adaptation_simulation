// WebSocket自定义Hook
import { useRef, useEffect } from 'react';
import WebSocketService from '../services/websocketService';

export const useWebSocket = () => {
  const wsServiceRef = useRef(null);

  useEffect(() => {
    wsServiceRef.current = new WebSocketService();
    
    return () => {
      if (wsServiceRef.current) {
        wsServiceRef.current.closeConnections();
      }
    };
  }, []);

  const connectLogSocket = () => {
    return wsServiceRef.current?.connectLogSocket();
  };

  const connectRealSenseSocket = (onMessage) => {
    return wsServiceRef.current?.connectRealSenseSocket(onMessage);
  };

  const sendLogMessage = (message) => {
    wsServiceRef.current?.sendLogMessage(message);
  };

  return {
    connectLogSocket,
    connectRealSenseSocket,
    sendLogMessage
  };
};
