const WebSocket = require('ws');

const wss = new WebSocket.Server({ port: 3001 }, () => {
  console.log("✅ WebSocket サーバーがポート 3001 で起動しました");
});

wss.on('connection', (ws) => {
  console.log('🔌 クライアントが接続しました');

  ws.on('message', (message) => {
    console.log('📨 受信:', message.toString());

    // 全クライアントにブロードキャスト（必要なら）
    wss.clients.forEach((client) => {
      if (client !== ws && client.readyState === WebSocket.OPEN) {
        client.send(message.toString());
      }
    });
  });

  ws.on('close', () => {
    console.log('❌ クライアントが切断しました');
  });
});
