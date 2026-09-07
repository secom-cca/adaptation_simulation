import { WebSocketServer } from 'ws';

// ポート3001でサーバーを作成
const wss = new WebSocketServer({ port: 3001 });

wss.on('listening', () => {
    console.log('✅ WebSocket server is running on ws://localhost:3001');
});

wss.on('connection', (ws) => {
    console.log('📡 Client connected');

    ws.on('message', (message) => {
        console.log('📩 Received:', message.toString());
        // おうむ返し
        ws.send(`Server received: ${message}`);
    });

    ws.on('close', () => {
        console.log('❌ Client disconnected');
    });
});