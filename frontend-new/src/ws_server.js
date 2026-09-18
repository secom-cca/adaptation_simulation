import { WebSocketServer, WebSocket } from 'ws'

const wss = new WebSocketServer({ port: 3001 })

wss.on('listening', () => {
  console.log('WebSocket server is running on ws://localhost:3001')
})

wss.on('connection', (ws) => {
  console.log('Client connected')

  ws.on('message', (message) => {
    const text = message.toString()
    console.log('Received:', text)

    try {
      JSON.parse(text)
    } catch {
      console.warn('Ignored non-JSON WebSocket message:', text)
      return
    }

    for (const client of wss.clients) {
      if (client !== ws && client.readyState === WebSocket.OPEN) {
        client.send(text)
      }
    }
  })

  ws.on('close', () => {
    console.log('Client disconnected')
  })
})
