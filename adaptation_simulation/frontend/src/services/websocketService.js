// WebSocket服务层
import { WEBSOCKET_LOG_URL, WEBSOCKET_REALSENSE_URL } from '../config/appConfig';

export class WebSocketService {
  constructor() {
    this.logSocket = null;
    this.realSenseSocket = null;
  }

  // 连接日志WebSocket
  connectLogSocket() {
    try {
      this.logSocket = new WebSocket(WEBSOCKET_LOG_URL);
      
      this.logSocket.onopen = () => {
        console.log("✅ Log WebSocket connected");
      };
      
      this.logSocket.onerror = (e) => {
        console.error("Log WebSocket error", e);
      };
      
      return this.logSocket;
    } catch (error) {
      console.error("Failed to connect log WebSocket:", error);
      return null;
    }
  }

  // 连接RealSense WebSocket
  connectRealSenseSocket(onMessage) {
    try {
      this.realSenseSocket = new WebSocket(WEBSOCKET_REALSENSE_URL);
      
      this.realSenseSocket.onopen = () => {
        console.log("✅ RealSense WebSocket connected");
      };

      this.realSenseSocket.onmessage = onMessage;
      
      this.realSenseSocket.onerror = (err) => {
        console.error("❌ RealSense WebSocket error", err);
      };

      this.realSenseSocket.onclose = () => {
        console.warn("⚠️ RealSense WebSocket closed");
      };
      
      return this.realSenseSocket;
    } catch (error) {
      console.error("Failed to connect RealSense WebSocket:", error);
      return null;
    }
  }

  // 发送日志消息
  sendLogMessage(message) {
    if (this.logSocket && this.logSocket.readyState === WebSocket.OPEN) {
      this.logSocket.send(JSON.stringify(message));
    }
  }

  // 关闭连接
  closeConnections() {
    if (this.logSocket) {
      this.logSocket.close();
    }
    if (this.realSenseSocket) {
      this.realSenseSocket.close();
    }
  }
}

export default WebSocketService;
