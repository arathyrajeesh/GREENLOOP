# ULB Tracking Backend API Specification

This document describes the backend services for real-time field operation monitoring.

## 1. GeoJSON Endpoints

These endpoints provide geospatial data in GeoJSON format (RFC 7946).

### Ward Boundaries
- **URL**: `/api/v1/wards/`
- **Method**: `GET`
- **Auth**: Bearer Token (JWT)
- **Response**: FeatureCollection of wards with `boundary` (Polygon) and `location` (Point centroid).

### Pending Pickups
- **URL**: `/api/v1/pickups/`
- **Method**: `GET`
- **Auth**: Bearer Token (JWT)
- **Query Params**: `ward_id` (optional), `status=pending` (recommended)
- **Response**: FeatureCollection of pickups with `location` (Point).
- **Properties**: `waste_type` (dry, wet, hazardous, e-waste, biomedical), `status`, `scheduled_date`.

---

## 2. Real-Time Tracking (WebSockets)

### Connection
- **URL**: `ws://<host>:8001/ws/tracking/`
- **Auth**: JWT required in query string: `?token=<JWT_ACCESS_TOKEN>`

### Outbound Messages (Server -> Client)
The server broadcasts worker location updates to administrators.

**Payload**:
```json
{
    "type": "location_update",
    "worker_id": "uuid",
    "worker_name": "Full Name",
    "latitude": 10.5123,
    "longitude": 76.9123,
    "deviated": false,
    "timestamp": "ISO-8601"
}
```

### Route Deviation Logic
- The backend compares the worker's current location with their `planned_path` (LineString).
- If the distance exceeds **500 meters**, the `deviated` flag is set to `true`.

---

## 3. Worker Simulation
A simulation script is available at `simulate_worker.py` to test the real-time pipeline.
