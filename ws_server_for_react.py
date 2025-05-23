import asyncio
import websockets
import json

connected = set()

async def handler(websocket):  # ← path を削除
    print("[WS] React connected")
    connected.add(websocket)
    try:
        async for message in websocket:
            print("[WS RECEIVED]", message)
    except websockets.exceptions.ConnectionClosed:
        print("[WS] Disconnected")
    finally:
        connected.remove(websocket)

async def broadcast(data):
    if connected:
        message = json.dumps(data)
        await asyncio.gather(*(ws.send(message) for ws in connected))
        print("[WS SENT]", message)
    else:
        print("[WS] No clients connected")

async def main():
    async with websockets.serve(handler, "localhost", 3001):  # ← context managerに変更
        print("[WS] Server started at ws://localhost:3001")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
