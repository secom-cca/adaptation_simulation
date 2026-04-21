/**
 * 全局应用配置文件
 * 统一管理前端和后端的URL配置
 * 
 * 代码交接时，只需修改此文件中的production配置即可
 */
window.APP_CONFIG = {
    // 环境检测
    ENVIRONMENT: (function() {
        const hostname = window.location.hostname;
        return (hostname === 'localhost' || hostname === '127.0.0.1') ? 'development' : 'production';
    })(),
    
    // URL配置
    URLS: {
        development: {
            BACKEND_HTTP: 'http://localhost:8000',
            BACKEND_WS: 'ws://localhost:8000',
            FRONTEND: 'http://localhost:3000',
            EXTERNAL_WS: 'ws://localhost:3001'
        },
        production: {
            // 🔧 代码交接时，只需修改以下3个URL
            BACKEND_HTTP: 'https://web-production-5fb04.up.railway.app',
            BACKEND_WS: 'wss://web-production-5fb04.up.railway.app',
            FRONTEND: 'https://climate-adaptation-backend.vercel.app',
            EXTERNAL_WS: 'wss://web-production-5fb04.up.railway.app'  // 如果有外部WebSocket服务
        }
    },
    
    // 获取当前环境的后端HTTP URL
    getBackendUrl: function() {
        return this.URLS[this.ENVIRONMENT].BACKEND_HTTP;
    },
    
    // 获取当前环境的WebSocket URL
    getWebSocketUrl: function() {
        return this.URLS[this.ENVIRONMENT].BACKEND_WS;
    },
    
    // 获取外部WebSocket URL
    getExternalWebSocketUrl: function() {
        return this.URLS[this.ENVIRONMENT].EXTERNAL_WS;
    },
    
    // 获取前端URL
    getFrontendUrl: function() {
        return this.URLS[this.ENVIRONMENT].FRONTEND;
    },
    
    // 调试信息
    getDebugInfo: function() {
        return {
            environment: this.ENVIRONMENT,
            hostname: window.location.hostname,
            backendUrl: this.getBackendUrl(),
            webSocketUrl: this.getWebSocketUrl(),
            frontendUrl: this.getFrontendUrl()
        };
    }
};

// 在控制台输出配置信息（便于调试）
console.log('🔧 APP_CONFIG loaded:', window.APP_CONFIG.getDebugInfo());
