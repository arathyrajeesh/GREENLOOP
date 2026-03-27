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
        self.planned_path = None # Cache for the worker's today's route
        
        # All authenticated users join the admin_tracking group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        if self.user.role == 'HKS_WORKER':
            active_workers = cache.get("active_workers", set())
            if not isinstance(active_workers, set):
                active_workers = set()
            active_workers.add(self.user.id)
            cache.set("active_workers", active_workers)
            
            # Pre-load planned path for deviation check
            await self.load_planned_path()

        await self.accept()

    from channels.db import database_sync_to_async

    @database_sync_to_async
    def get_todays_route_path(self):
        from apps.routes.models import Route
        from django.utils import timezone
        route = Route.objects.filter(hks_worker=self.user, route_date=timezone.now().date()).first()
        return route.planned_path if route else None

    async def load_planned_path(self):
        self.planned_path = await self.get_todays_route_path()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        lat = data.get("latitude")
        lon = data.get("longitude")
        
        if lat is not None and lon is not None:
            deviated = False
            if self.user.role == 'HKS_WORKER' and self.planned_path:
                from django.contrib.gis.geos import Point
                current_point = Point(float(lon), float(lat), srid=4326)
                
                # GIS handles distance calculation. 
                # Note: distance is in units of the SRID (degrees for 4326).
                # For 500m, we can use a rough approximation (0.0045 degrees approx)
                # or transform to a metric projection. 
                # For simplicity and given the task context, we will use a rough 0.0045 degree check 
                # OR use the GEOS distance if transformed.
                # Let's use a safe 0.005 degree threshold (~550m equatorial) or a more precise one if available.
                distance = self.planned_path.distance(current_point)
                if distance > 0.0045: # ~500m
                    deviated = True

            pos_data = {
                "user_id": str(self.user.id),
                "name": self.user.name,
                "latitude": float(lat),
                "longitude": float(lon),
                "deviated": deviated,
                "timestamp": timezone.now().isoformat()
            }
            cache.set(f"worker_pos:{self.user.id}", pos_data, timeout=3600)
            
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
