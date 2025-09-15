## - function  
## ~ description  
## > returns/gives back  
## = found issues  


# class - RequestHandler(BaseHTTPRequestHandler):  

- do_POST(self):  
~ Handles POST requests. Uses `if self.path == ...` to route towards different actions: `/register`, `/login`, `/parking-lots`, `/reservations`, `/vehicles`, `/payments`. Parses JSON via `self.rfile.read` and validates fields. Performs session checks for authentication-required routes.  
> Nothing explicitly returned (side effect: HTTP response written via `self.wfile.write`).  
=  
- Repeats `json.loads(... content-length ...)` a lot -> duplicate logic.  
- Sends HTTP `200 OK` but actually writes an error message instead of proper error code (e.g., username taken = should be `409 Conflict`, not `200`).  
- Error handling inconsistent: sometimes `401`, sometimes `403`, sometimes `200`.  
- Password hashed only with MD5 -> insecure for storage.  
- Uses `users.add` instead of `append` (likely a bug, since `users` is probably a list).  
- Login only checks first user due to wrong placement of `return`.  
- Validation checks sometimes incorrect, e.g. checks `if len(filtered) < 0` instead of `== 0`.  
- Times are stored as `datetime.now().strftime` strings -> makes audits and calculations harder.  

---

- do_PUT(self):  
~ Handles PUT requests. Used to modify `parking-lots`, update `/profile`, update `reservations`, rename/change `vehicles`, and mark transactions in `/payments`. Requires session validation.  
> Success or failure message as HTTP response (JSON where relevant).  
=  
- No type hinting or schema validation.  
- `save_user_data(data)` for profile overwrites potentially whole dataset instead of updating a single user.  
- Payment validation relies on manual hash comparison but does not prevent replay attacks.  
- In several cases, overwrites entities entirely -> potential loss of data fields.  

---

- do_DELETE(self):  
~ Handles DELETE requests. Deletes parking lots, reservations (authorized by user or ADMIN), and vehicles. Also deletes parking lot sessions if numeric ID provided.  
> Success or error JSON/strings.  
=  
- Reservation delete tries to reference `reservations[rid]["parkinglot"]` after deleting `reservations[rid]` -> runtime error.  
- Deleting sessions requires FULL path correctness -> otherwise vague errors.  
- No soft delete/logging for audit.  

---

- do_GET(self):  
~ Handles GET requests. Supports `/profile`, `/logout`, `/parking-lots`, `/reservations`, `/payments`, `/billing`, `/vehicles`. Provides retrieval of user session profile, parking lots & sessions, reservations, payment history, vehicle history, billing calculation.  
> JSON responses with requested objects.  
=  
- In `/parking-lots/{id}/sessions`, variable `session_user` missing before use.  
- Payment checking: code expects `"username"` field in payment objects, but payments store `"initiator"` instead -> payments may never match properly.  
- Incorrect/inconsistent role checks (expects `role == 'ADMIN'` instead of checking more robust privileges).  
- Returns complete user object (profile) including hashed password when calling `/profile`.  
- Billing relies heavily on external `session_calculator`, but no safeguard if file/data missing.  


---

# Used libraries/imports  

- json
- hashlib
- uuid
- from datetime: datetime
- from http.server: HTTPServer, BaseHTTPRequestHandler
- from storage_utils: load_json, save_data, save_user_data, load_parking_lot_data, save_parking_lot_data, save_reservation_data, load_reservation_data, load_payment_data, save_payment_data
- from session_manager: add_session, remove_session, get_session
- session_calculator as sc

---

# Main Findings:  
- No type hinting -> readability + static checking difficult.  
- Always encrypts password only inside request-handling blocks, not centralised.  
- Inconsistent HTTP codes (returns `200` even for clear errors).  
- Insecure password hashing (MD5, no salt, no stretching).  
- Data persistence fragile (JSON overrides without atomicity or concurrency handling).  
- Errors & validation scattered instead of centralized.  
- Returns hashed passwords in `/profile` response.  
- Multiple logical flaws (bad `return` placement, `len(filtered) < 0`, reservation decrement after delete).  

---

# Recommendations:  
1. Refactor RequestHandler: split into modular methods instead of one giant `if self.path...`. Easier to maintain.  
2. Use secure password hashing: switch to `bcrypt` or `argon2`.  
3. Fix HTTP status codes:  
   - `200` = only on success  
   - `400` = invalid input/missing fields  
   - `401` = unauthorized/no session  
   - `403` = forbidden role  
   - `404` = entity not found  
   - `409` = conflict (e.g., username taken).  
4. Centralize request parsing & error handling -> utility helper to load JSON, validate fields, respond uniformly.  
5. Never expose password hashes in API responses.  
6. Fix reservation delete bug (reference parkinglot before deleting reservation).  
7. Add type hints & schemas (e.g., using `pydantic` or `dataclasses`).  
8. Improve session/token security: add expiry, secure storage.  
9. Use proper database (SQLite/PostgreSQL) instead of flat JSON -> safer for concurrency & scaling.  
10. Add logging & error monitoring for auditing (esp. for financial transactions/payments).  
