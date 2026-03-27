import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from django.utils import timezone

class TrackingConsumer(AsyncWebsocketConsumer):
    """
    Consumer for real-time GPS tracking.
    HKS Workers send their coordinates.
    Admins receive broadcasts of all worker positions.
    """
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        self.group_name = "admin_tracking"
        
        # All authenticated users join the admin_tracking group (admins to listen, workers to broadcast)
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # If worker, track them as active
        if self.user.role == 'HKS_WORKER':
            active_workers = cache.get("active_workers", set())
            if not isinstance(active_workers, set):
                active_workers = set()
            active_workers.add(self.user.id)
            cache.set("active_workers", active_workers)

        await self.accept()

    async def disconnect(self, close_code):
        if self.user and not self.user.is_anonymous:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            
            # Remove from active workers
            if self.user.role == 'HKS_WORKER':
                active_workers = cache.get("active_workers", set())
                if isinstance(active_workers, set) and self.user.id in active_workers:
                    active_workers.remove(self.user.id)
                    cache.set("active_workers", active_workers)

    async def receive(self, text_data):
        """
        Received coordinates from a worker.
        Broadcasts to the group and updates Redis cache.
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        lat = data.get("latitude")
        lon = data.get("longitude")
        
        if lat is not None and lon is not None:
            # Update latest position in Redis for REST fallback
            pos_data = {
                "user_id": str(self.user.id),
                "name": self.user.name,
                "latitude": float(lat),
                "longitude": float(lon),
                "timestamp": timezone.now().isoformat()
            }
            cache.set(f"worker_pos:{self.user.id}", pos_data, timeout=3600) # 1 hour expiry
            
            # Broadcast to the tracking group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "worker_location_update",
                    "data": pos_data
                }
            )

    async def worker_location_update(self, event):
        """
        Handler for worker_location_update messages.
        Admins will receive this and see it on their live map.
        """
        # Broadcast the data to the client if they are an admin
        if self.user.role == 'ADMIN':
            await self.send(text_data=json.dumps(event["data"]))
