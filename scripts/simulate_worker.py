import asyncio
import websockets
import json
import sys

async def simulate():
    token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc0NTg5NjIyLCJpYXQiOjE3NzQ1ODg3MjIsImp0aSI6IjY0YTg3ODU2YTQzNTRlMmNhZjJiOTY3MDdiNjgwODk5IiwidXNlcl9pZCI6IjlhZTNmZDYzLTRjNjItNGExMC04ZmY3LWFmODhjOGQ2MzM5YiJ9.l-E9jI3pNcN_mSXjJDxed9Co9SEOIMNxIWfBEfnCtOc'
    uri = 'ws://daphne:8001/ws/tracking/?token=' + token
    
    try:
        async with websockets.connect(uri) as ws:
            # 1. On Route
            print("Sending 'On Route' coordinates...")
            await ws.send(json.dumps({'latitude': 10.51, 'longitude': 76.91}))
            await asyncio.sleep(5)
            
            # 2. Deviated (>500m)
            print("Sending 'Deviated' coordinates...")
            await ws.send(json.dumps({'latitude': 10.55, 'longitude': 76.95}))
            await asyncio.sleep(60) # Keep connection alive for observation
    except Exception as e:
        print(f"Simulation error: {e}")

if __name__ == "__main__":
    asyncio.run(simulate())
