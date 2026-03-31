# GreenLoop Admin API Library for Flutter Integration

This documentation outlines the essential API endpoints for the GreenLoop Admin Frontend.

## 🔗 1. Authentication
Endpoints for signing in and managing admin sessions.

- **Admin Login**
  - `POST /api/v1/auth/admin-login/`
  - Body: `{"username": "admin_username", "password": "password"}`
  - Returns: `{"token": "access_token", "refresh": "refresh_token", "user": {...}}`

- **Token Refresh**
  - `POST /api/v1/auth/token/refresh/`
  - Body: `{"refresh": "refresh_token"}`

- **Logout**
  - `POST /api/v1/auth/logout/`
  - Note: Invalidate the token on the frontend and call this to notify the backend.

---

## 📊 2. Dashboard & Stats
Real-time summary data for the admin overview.

- **Dashboard Statistics**
  - `GET /api/v1/dashboard/stats/`
  - Query Params: `range` (e.g., `7d`, `30d`)
  - Response: Includes `kpis` (pickups_today, active_workers, pending_complaints, total_waste_kg), `weekly_trend`, `ward_comparison`, and `nps_stats`.

- **Live Worker Locations**
  - `GET /api/v1/sync/active_locations/`
  - Note: Used for showing worker movements on a map.

---

## 👥 3. User & Staff Management
CRUD operations for managers, workers, and residents.

- **List All Users**
  - `GET /api/v1/users/`
  - Supports filtering by `role` (ADMIN, HKS_WORKER, RECYCLER, RESIDENT).

- **Create Worker/Recycler**
  - `POST /api/v1/users/create-worker/`
  - Body: `{"username": "w1", "email": "w1@gl.com", "password": "...", "name": "Worker One", "role": "HKS_WORKER", "ward": 1}`

- **Attendance Logs**
  - `GET /api/v1/attendance/`

---

## 🚜 4. Field Operations (Pickups & Wards)
Manage collection zones and the master ledger of pickups.

- **Wards List**
  - `GET /api/v1/wards/`
  - Returns: GeoJSON FeatureCollection of all wards.

- **Create Ward**
  - `POST /api/v1/wards/`
  - Body (GeoJSON Feature):
    ```json
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[76.0, 10.0], [77.0, 10.0], [77.0, 11.0], [76.0, 11.0], [76.0, 10.0]]]
      },
      "properties": {
        "name": "Ward Name",
        "number": 1,
        "location": {
          "type": "Point",
          "coordinates": [76.5, 10.5]
        }
      }
    }
    ```
  - Note: Only accessible to admins. `number` must be unique.

- **Ward Details & Management**
  - `GET /api/v1/wards/<id>/`: Get specific ward boundary and details.
  - `PATCH /api/v1/wards/<id>/`: Update name, number, or boundaries.
  - `GET /api/v1/wards/<id>/workers/`: List all workers currently assigned to this ward.
  - `POST /api/v1/wards/<id>/assign_workers/`: Batch assign/unassign workers.
    - Body: `{"worker_ids": ["uuid-1", "uuid-2"]}`

- **All Pickups**
  - `GET /api/v1/pickups/`
  - Filter by `status` (pending, completed, cancelled) or `ward`.

- **Pickup Slots**
  - `GET /api/v1/pickup-slots/`
  - Manage timing and capacity for resident bookings.

---

## 🔍 5. Contamination Review Queue
Quality Control for waste segregation.

- **Review Queue**
  - `GET /api/review-queue/`
  - Returns pickups flagged by AI that need human confirmation.

- **Confirm Contamination**
  - `POST /api/pickups/<id>/confirm/`
  - Applies penalty points to the resident.

- **Override as Clean**
  - `POST /api/pickups/<id>/override-clean/`
  - Marks the AI flag as a False Positive.

---

## 🎁 6. Rewards & Incentives
Program management and redemption requests.

- **Reward Redemptions**
  - `GET /api/v1/reward-redemptions/`
  - View all user requests for prizes.
  - `PATCH /api/v1/reward-redemptions/<id>/`: Update status to 'DELIVERED'.

- **Reward Items Management**
  - `GET /api/v1/reward-items/`
  - Create or edit items in the catalog.

- **Global Reward Settings**
  - `GET /api/v1/reward-settings/`
  - Edit base points and penalty rules.

---

## 🚛 7. Recycler Ledger
Sales records and material catalogs.

- **Material Prices**
  - `GET /api/v1/recycler/materials/`
  - View/Edit current market prices per kg.

- **Sales History**
  - `GET /api/v1/recycler/purchases/`
  - See what recyclers bought from the ULB.

---

## 📑 8. Reports & Feedback
Deep analytics and user sentiment.

- **Ward Reports**
  - `GET /api/v1/ward-reports/`
  - Performance comparisons between wards.

- **NPS Survey Summary**
  - `GET /api/v1/nps/summary/`
  - High-level resident satisfaction metrics.

---

### Integration Guide for Flutter
1. **Interceptor**: Add a Dio interceptor to attach the `Authorization: Bearer <TOKEN>` header to every request.
2. **Models**: Map JSON responses to Dart classes using `json_serializable`.
3. **State Management**: Use `Bloc` or `Provider` to keep the dashboard stats synced.
