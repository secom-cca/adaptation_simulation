# ws_server.py
import asyncio
import websockets

connected_clients = set()

async def handler(websocket):
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            print("[RECEIVED from Python test_ws_send]", message)
    finally:
        connected_clients.remove(websocket)

async def main():
    async with websockets.serve(handler, "localhost", 3001):
        print("WebSocket server running on ws://localhost:3001")
        await asyncio.Future()  # 永遠に待つ

if __name__ == "__main__":
    asyncio.run(main())
