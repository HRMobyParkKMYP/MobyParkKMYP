Parking Management API – Documentation
--------------------------------------

Base URL:
http://localhost:8000


======================================
1. Authentication
======================================

POST /register
Register a new user.
Body (JSON):
{
  "username": "johndoe",
  "password": "secret",
  "name": "John Doe"
}
Responses:
- 201 Created → "User created"
- 200 OK → "Username already taken"


POST /login
Login user and create a session token.
Body (JSON):
{
  "username": "johndoe",
  "password": "secret"
}
Responses:
- 200 OK → { "message": "User logged in", "session_token": "<token>" }
- 401 Unauthorized → "Invalid credentials" or "User not found"


GET /logout
Terminate a user session.
Headers:
Authorization: <session_token>
Responses:
- 200 OK → "User logged out"
- 400 Bad Request → "Invalid session token"


======================================
2. User Profile
======================================

GET /profile
Get current user profile.
Headers: Authorization: <session_token>
Response Example:
{ "username": "johndoe", "name": "John Doe", "role": "USER" }

PUT /profile
Update profile (name, password).
Body:
{ "name": "John Updated", "password": "newpassword" }
Response: 200 OK → "User updated successfully"


======================================
3. Parking Lots
======================================

POST /parking-lots (ADMIN only)
Create a parking lot.
Body:
{
  "name": "Central Parking",
  "location": "Main Street",
  "capacity": 100,
  "reserved": 0,
  "tariff": 2.5,
  "daytariff": 20
}
Response: 201 Created → "Parking lot saved under ID: <id>"

GET /parking-lots
List all parking lots.

GET /parking-lots/{id}
Get details of one parking lot.

PUT /parking-lots/{id} (ADMIN)
Update parking lot by id.

DELETE /parking-lots/{id} (ADMIN)
Delete parking lot.


Parking Lot Sessions
--------------------
POST   /parking-lots/{id}/sessions/start  → Start parking session
POST   /parking-lots/{id}/sessions/stop   → Stop parking session
GET    /parking-lots/{id}/sessions        → List sessions (admin gets all, user gets own)
GET    /parking-lots/{id}/sessions/{sid}  → Get session details
DELETE /parking-lots/{id}/sessions/{sid}  → Delete session (ADMIN only)


======================================
4. Reservations
======================================

POST /reservations
Create reservation.
Body:
{
  "licenseplate": "ABC-123",
  "startdate": "2025-09-20 08:00",
  "enddate": "2025-09-20 18:00",
  "parkinglot": "1"
}
Response:
- 201 Created → Reservation JSON
- 404 Not Found (if parking lot not found)

PUT /reservations/{id}
Update reservation.

GET /reservations/{id}
Get reservation details (only owner or ADMIN).

DELETE /reservations/{id}
Delete reservation (owner or ADMIN).


======================================
5. Vehicles
======================================

POST /vehicles
Register new vehicle.
Body:
{
  "name": "My Car",
  "license_plate": "XYZ-999"
}
Response: 201 Created → Vehicle JSON

GET /vehicles
Get all vehicles of logged-in user.
(Admin can use /vehicles/{username} to get another user’s.)

PUT /vehicles/{plate_id}
Update vehicle name.

DELETE /vehicles/{plate_id}
Remove vehicle.

POST /vehicles/{id}/entry
Register entry in parking lot.
Body:
{ "parkinglot": "1" }

GET /vehicles/{id}/reservations
List reservations for vehicle (currently empty list).

GET /vehicles/{id}/history
Get vehicle history (currently empty list).


======================================
6. Payments
======================================

POST /payments
Make a payment.
Body:
{ "transaction": "tx123", "amount": 20 }

POST /payments/refund (ADMIN only)
Refund a payment.
Body:
{ "amount": 20, "coupled_to": "tx123" }

PUT /payments/{transaction}
Validate/complete transaction.
Body:
{ "t_data": { "method": "card" }, "validation": "<hash>" }

GET /payments
Get payments of logged-in user.

GET /payments/{username} (ADMIN)
Get payments of another user.


======================================
7. Billing
======================================

GET /billing
Get billing information (user’s own history, sessions, owed amounts, balance).

GET /billing/{username} (ADMIN)
Get billing history for other user.


======================================
Notes & Issues
======================================
- Users are stored in a list, must append instead of add.
- Some validations use wrong comparisons (<0 instead of ==0).
- Datetime objects may not serialize to JSON unless converted to string.
- Vehicle reservations and history endpoints return empty lists (incomplete).
- Payment object user field differs (username vs initiator).