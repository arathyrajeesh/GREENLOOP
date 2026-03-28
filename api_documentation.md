# GreenLoop API Documentation

This document provides an overview of the GreenLoop API architecture and endpoint categorization.

## Role-Based Categorization
Endpoints are grouped by user role in the Swagger (OpenAPI) documentation to assist frontend developers.

### Roles and Tags
- **Resident**: Endpoints for OTP-based residents (authentication, pickups, complaints, payments).
- **HKS Worker**: Endpoints for workers (check-in/out, GPS tracking, pickup verification, fee collection).
- **Admin**: Endpoints for Ward Admins and ULB officials (dashboard, user management, ward boundaries).
- **Shared / Notifications**: Common utility endpoints accessible by multiple roles.

### Key Endpoints by Role

#### Resident APIs
- `POST /api/v1/accounts/otp/request/`: Request login OTP.
- `POST /api/v1/accounts/otp/verify/`: Verify OTP and get JWT tokens.
- `GET /api/v1/pickups/`: List resident's pickups.
- `POST /api/v1/complaints/`: File a new complaint.

#### HKS Worker APIs
- `POST /api/v1/attendance/worker/`: Attendance check-in with GPS validation.
- `PATCH /api/v1/attendance/worker/`: Attendance check-out.
- `POST /api/v1/pickups/{id}/verify/`: Verify pickup via QR code.
- `GET /api/v1/payments/summary/`: Daily collection summary.

#### Admin APIs
- `GET /api/v1/wards/`: List/manage ward boundaries.
- `GET /api/v1/users/`: User management.
- `GET /api/v1/attendance/`: View overall attendance logs.

---

## Technical Details

### Authentication
The API uses JWT (JSON Web Tokens). Include the token in the `Authorization` header:
`Authorization: Bearer <your_access_token>`

### WebSocket (Real-Time Tracking)
- **URL**: `ws://<host>:8001/ws/tracking/`
- **Auth**: Pass token in query string: `?token=<JWT_ACCESS_TOKEN>`

### OpenAPI Schema
The full API specification is available in Swagger UI at `/api/v1/schema/swagger-ui/` or as a YAML file at `/api/v1/schema/`.
