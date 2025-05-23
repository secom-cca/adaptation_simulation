# test_ws_send.py
import asyncio
import websockets
import json

async def send_mock_data():
    uri = "ws://localhost:3001"
    data = {
        "agricultural_RnD_cost": 10,
        "transportation_invest": 5,
        "simulate": True
    }
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps(data))
        print("[MOCK SENT]", data)

asyncio.run(send_mock_data())
