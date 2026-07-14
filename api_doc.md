# Palm Recognition System - API Documentation

This documentation covers **every** endpoint in the system, organized by application roles: Public/Auth, Mobile App (User), Hardware Device (Raspberry Pi), and Web Admin (Admin).

**Base URL:** `https://api.phoudthasone.com/api/v1`

---

## Standard Error Format
Whenever an API request fails (e.g., 400 Bad Request, 401 Unauthorized, 404 Not Found), the backend will always return a predictable JSON structure. 

**Important:** The `message` field is designed to be highly user-friendly and can be directly displayed to the end-user in a UI pop-up or SnackBar. Technical database errors (like `err.Error()`) are intentionally hidden from this JSON response and are instead logged securely in the backend terminal.

**Example Error Response:**
```json
{
  "code": 400,
  "status": "Bad Request",
  "message": "Your phone number or password is incorrect."
}
```

---

## 1. Authentication & Public Workflow

These endpoints are public and do not require any authentication headers. They are used for onboarding new users and acquiring access tokens.

### 1.0 Health Check (Hello World)
* **Use for:** Testing if the API server is up and running.
* **GET** `/`
* **Response (200 OK):**
  ```text
  hello world
  ```

### 1.1 Register a new account
* **Use for:** Allowing a new employee to create an account in the system using their phone number.
* **POST** `/auth/register`
* **Body:**
  ```json
  {
    "phone": "0812345678",
    "password": "securepassword",
    "full_name": "Jane Doe",
    "email": "jane@example.com"
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "code": 201,
    "status": "Created",
    "message": "User registered successfully",
    "data": {
      "user": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "full_name": "Jane Doe",
        "role": "employee",
        "is_palm_registered": false
      },
      "access_token": "eyJhbGciOi...",
      "refresh_token": "eyJhbGciOi..."
    }
  }
  ```

### 1.2 Login
* **Use for:** Authenticating an existing user and issuing a new JWT access token and refresh token.
* **POST** `/auth/login`
* **Body:**
  ```json
  {
    "phone": "0812345678",
    "password": "securepassword"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Login successful",
    "data": {
      "user": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "full_name": "Jane Doe",
        "role": "employee",
        "is_palm_registered": false
      },
      "access_token": "eyJhbGciOi...",
      "refresh_token": "eyJhbGciOi..."
    }
  }
  ```

### 1.3 Refresh Token
* **Use for:** Issuing a new access token when the current one expires, without requiring the user to log in again.
* **POST** `/auth/refresh`
* **Body:**
  ```json
  {
    "refresh_token": "eyJhbGciOi..."
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Token refreshed successfully",
    "data": {
      "access_token": "new_eyJhbGciOi...",
      "refresh_token": "new_eyJhbGciOi..."
    }
  }
  ```

---

## 2. Mobile App (User) APIs

These endpoints are used by the mobile application for normal employees.
*Requires Header: `Authorization: Bearer <access_token>`*

### 2.1 Get My Profile
* **Use for:** Retrieving the logged-in user's profile information to display on the mobile app dashboard.
* **GET** `/me`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Profile retrieved successfully",
    "data": {
      "user": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "employee_code": "EMP-001",
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "0812345678",
        "role": "employee",
        "department": "IT",
        "status": "active",
        "is_palm_registered": true,
        "created_at": "2026-06-03T10:00:00Z",
        "updated_at": "2026-06-03T10:00:00Z"
      }
    }
  }
  ```

### 2.2 Change Password
* **Use for:** Allowing users to securely update their account password from the settings menu.
* **PATCH** `/me/password`
* **Body:** 
  ```json
  {
    "old_password": "currentpassword",
    "new_password": "newpassword123"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Password changed successfully",
    "data": null
  }
  ```

### 2.3 View My Attendance
* **Use for:** Fetching a paginated history of the user's check-ins and check-outs for their personal records.
* **GET** `/me/attendance?page=1&limit=30&start_date=2026-06-01&end_date=2026-06-07`
  * `start_date` (optional): Filter records from this date (YYYY-MM-DD).
  * `end_date` (optional): Filter records up to this date (YYYY-MM-DD).
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Attendance history retrieved successfully",
    "data": [
      {
         "id": "att-123",
         "attendance_date": "2026-06-03T00:00:00Z",
         "check_in_time": "2026-06-03T08:00:00Z",
         "check_out_time": "2026-06-03T17:00:00Z",
         "status": "present",
         "device_name": "Main Entrance Scanner",
         "device_code": "DEV-001"
      }
    ],
    "meta": {
      "pagination": { "page": 1, "limit": 30, "total": 1 }
    }
  }
  ```

### 2.4 Manage Enrolled Palms
* **Use for:** Viewing which hands (left/right) the user has successfully registered in the system, or revoking a template.
* **GET** `/me/palm-templates`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Palm templates retrieved successfully",
    "data": [
      {
        "id": "tpl-123",
        "user_id": "user-uuid",
        "hand_side": "right",
        "embedding_dim": 128,
        "model_version": "v1.0",
        "threshold": 0.82,
        "status": "active",
        "registered_device_id": "device-uuid",
        "created_at": "2026-06-01T12:00:00Z",
        "updated_at": "2026-06-01T12:00:00Z",
        "revoked_at": null,
        "registered_device_name": "Main Entrance Scanner",
        "registered_device_code": "DEV-001"
      }
    ]
  }
  ```
  *(Note: If the user has no enrolled palm templates, `data` will return an empty array `[]` instead of `null`.)*



---

## 3. Pairing Flow (Mobile App <-> Device)

These endpoints facilitate the secure enrollment process where the mobile app "pairs" with the physical scanner.
*Requires Header: `Authorization: Bearer <access_token>`*

### 3.1 Scan QR Code
* **Use for:** When the mobile app scans the QR code on the physical device's screen, it validates the session.
* **POST** `/pairing/scan`
* **Body:** 
  ```json
  {
    "session_token": "a1b2c3d4e5f6..."
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Pairing session scanned",
    "data": {
      "device": {
        "id": "device-uuid",
        "device_code": "DEV-001",
        "device_name": "Main Entrance Scanner",
        "location_name": "Front Door",
        "status": "active",
        "created_at": "2026-06-01T12:00:00Z",
        "updated_at": "2026-06-01T12:00:00Z"
      },
      "purpose": "enrollment"
    }
  }
  ```

### 3.2 Approve Pairing (Admin Only)
* **Use for:** An Administrator taps "Confirm" on their device and inputs the employee's `employee_code` to securely link the hardware session to that specific employee, authorizing it to read their palm.
* **POST** `/admin/pairing/approve`
* **Requires Role:** `admin`
* **Body:** 
  ```json
  {
    "session_token": "abc123xyz...",
    "hand_side": "right",
    "employee_code": "EMP001"
  }
  ```
  *(Note: `hand_side` must be exactly `"left"` or `"right"`. The system enforces a maximum of 1 active template per hand side per user.)*
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Enrollment approved. The employee can now place their palm on the device.",
    "data": null
  }
  ```

---

## 4. Hardware Device APIs (Raspberry Pi)

These endpoints are consumed EXCLUSIVELY by the physical palm scanners. 
*Authenticates using `device_code` in the JSON body. No JWT required.*

### 4.1 Device Heartbeat
* **Use for:** Periodic ping from the device to the server to prove it is online and functioning properly.
* **POST** `/devices/heartbeat`
* **Body:** `{"device_code": "DEV-001"}`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Heartbeat successful",
    "data": null
  }
  ```

### 4.2 Create Pairing Session (Generate QR)
* **Use for:** The device requests a secure QR code session to display on its screen so a user can scan it for enrollment.
* **POST** `/devices/pairing-sessions`
* **Body:** `{"device_code": "DEV-001", "purpose": "enrollment"}`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Pairing session created successfully",
    "data": {
      "session_id": "session-uuid",
      "session_token": "a1b2c3d4e5f6...",
      "expires_at": "2026-06-04T10:05:00Z"
    }
  }
  ```

### 4.3 Check Pairing Status
* **Use for:** The device polls this endpoint while showing the QR code to check if the user has approved the session on their phone yet.
* **GET** `/devices/pairing-sessions/:session_id/status`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Session status retrieved",
    "data": {
      "status": "approved"
    }
  }
  ```

### 4.4 Enroll Palm
* **Use for:** The device uploads the extracted mathematical embedding data of the palm to permanently link it to the user.
* **POST** `/devices/palm/enroll`
* **Body:**
  ```json
  {
    "device_code": "DEV-001",
    "session_token": "a1b2c3d4e5f6...",
    "model_version": "v1.0",
    "embedding_dim": 128,
    "embeddings": [[0.12, 0.44]],
    "liveness_passed": true,
    "quality_score": 0.98
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Palm enrolled successfully",
    "data": {
      "template_id": "template-uuid"
    }
  }
  ```

### 4.5 Identify Palm (No Attendance)
* **Use for:** Strictly searching the database to find which user matches the scanned palm embedding (without clocking them in or out).
* **POST** `/devices/palm/identify`
* **Body:**
  ```json
  {
    "device_code": "DEV-001",
    "model_version": "v1.0",
    "embedding_dim": 128,
    "embeddings": [[0.12, 0.44]],
    "liveness_passed": true,
    "quality_score": 0.98
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Palm identified successfully",
    "data": {
      "user": {
        "id": "user-uuid",
        "full_name": "Jane Doe"
      }
    }
  }
  ```

### 4.6 Process Attendance (Check In/Out)
* **Use for:** The main operational flow. The device scans a palm, identifies the user, and automatically clocks them IN or OUT based on their current status.
* **POST** `/devices/attendance/palm`
* **Body:**
  ```json
  {
    "device_code": "DEV-001",
    "model_version": "v1.0",
    "embedding_dim": 128,
    "embeddings": [[0.12, 0.44]],
    "liveness_passed": true,
    "quality_score": 0.98
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Check-in successful",
    "data": {
      "action": "check_in",
      "user": {
        "id": "user-uuid",
        "full_name": "Jane Doe"
      }
    }
  }
  ```

---

## 5. Web Admin APIs

These endpoints power the Admin Dashboard.
*Requires Header: `Authorization: Bearer <access_token>`*
*Requires Role: `admin`*

### 5.1 Dashboard Summary
* **Use for:** Fetching high-level statistics for the admin dashboard (total users, devices, active templates, and today's check-ins).
* **GET** `/admin/dashboard/summary`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Dashboard summary retrieved successfully",
    "data": {
      "total_users": 150,
      "total_devices": 5,
      "active_palm_templates": 120,
      "check_ins_today": 85
    }
  }
  ```

### 5.2 User Management
* **Use for:** Listing all employees in the system for the admin panel.
* **GET** `/admin/users`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Users retrieved successfully",
    "data": [
      {
        "id": "user-uuid",
        "employee_code": "EMP-001",
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "role": "employee",
        "status": "active",
        "is_palm_registered": true
      }
    ]
  }
  ```

* **Use for:** Searching for specific users by name or code.
* **GET** `/admin/users/search?q=John`
* **Response (200 OK):** (Same array of users as above).

* **Use for:** Viewing details for a specific user.
* **GET** `/admin/users/:id`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "User retrieved successfully",
    "data": {
        "id": "user-uuid",
        "employee_code": "EMP-001",
        "full_name": "Jane Doe",
        "status": "active",
        "is_palm_registered": true
    }
  }
  ```

* **Use for:** Admin directly creating an employee account from the dashboard.
* **POST** `/admin/users`
* **Body:** `{"phone": "0811111111", "full_name": "John", "password": "pass", "role": "employee"}`
* **Response (201 Created):**
  ```json
  {
    "code": 201,
    "status": "Created",
    "message": "User created successfully",
    "data": { "id": "user-uuid" }
  }
  ```

* **Use for:** Modifying employee details or changing their department.
* **PATCH** `/admin/users/:id`
* **Body:** `{"full_name": "Jane", "department": "HR", "status": "active"}`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "User updated successfully",
    "data": {
      "id": "user-uuid",
      "department": "HR"
    }
  }
  ```

* **Use for:** Completely removing an employee from the system.
* **DELETE** `/admin/users/:id`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "User deleted successfully",
    "data": null
  }
  ```

* **Use for:** Checking if an employee has already registered their palm in the system.
* **GET** `/admin/users/:user_id/palm-templates`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "User palm templates retrieved successfully",
    "data": [
      {
        "id": "tpl-123",
        "hand_side": "right",
        "status": "active",
        "created_at": "2026-06-01T12:00:00Z",
        "updated_at": "2026-06-01T12:00:00Z"
      }
    ]
  }
  ```

* **Use for:** Revoking/deleting a specific palm template for a user.
* **DELETE** `/admin/users/:user_id/palm-templates/:template_id`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "User palm template deleted successfully",
    "data": null
  }
  ```

### 5.2 Device Management
* **Use for:** Listing all registered physical palm scanners and checking their last seen status.
* **GET** `/admin/devices`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Devices retrieved successfully",
    "data": [
      {
        "id": "device-uuid",
        "device_code": "DEV-001",
        "device_name": "Main Entrance",
        "location_name": "Lobby",
        "status": "active",
        "last_seen_at": "2026-06-04T10:00:00Z"
      }
    ]
  }
  ```

* **Use for:** Registering a newly purchased hardware device into the system.
* **POST** `/admin/devices`
* **Body:** `{"device_code": "DEV-002", "name": "Entrance B", "location": "Lobby"}`
* **Response (201 Created):**
  ```json
  {
    "code": 201,
    "status": "Created",
    "message": "Device created successfully",
    "data": {
      "id": "device-uuid",
      "device_code": "DEV-002"
    }
  }
  ```

* **Use for:** Renaming a device or marking it as inactive for maintenance.
* **PATCH** `/admin/devices/:id`
* **Body:** `{"name": "New Name", "status": "inactive"}`
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Device updated successfully",
    "data": {
      "id": "device-uuid"
    }
  }
  ```

### 5.5 View Global Attendance History
* **Use for:** Fetching a paginated history of all check-ins and check-outs across the entire company.
* **GET** `/admin/attendance?page=1&limit=30&start_date=2026-06-01&end_date=2026-06-07`
  * `start_date` (optional): Filter records from this date (YYYY-MM-DD).
  * `end_date` (optional): Filter records up to this date (YYYY-MM-DD).
* **Response (200 OK):**
  ```json
  {
    "code": 200,
    "status": "OK",
    "message": "Attendance history retrieved successfully",
    "data": [
      {
         "id": "att-123",
         "user_id": "user-uuid",
         "device_id": "device-uuid",
         "attendance_date": "2026-06-03T00:00:00Z",
         "check_in_time": "2026-06-03T08:00:00Z",
         "check_out_time": "2026-06-03T17:00:00Z",
         "status": "present",
         "device_name": "Main Entrance Scanner",
         "device_code": "DEV-001"
      }
    ],
    "meta": {
      "pagination": { "page": 1, "limit": 50, "total": 1000 }
    }
  }
  ```

### 5.6 View Employee Attendance History
* **Use for:** Investigating the attendance history of a specific employee.
* **GET** `/admin/attendance/users/:user_id/history?page=1&limit=30&start_date=2026-06-01&end_date=2026-06-07`
  * `start_date` (optional): Filter records from this date (YYYY-MM-DD).
  * `end_date` (optional): Filter records up to this date (YYYY-MM-DD).
* **Response (200 OK):** (Same format as above, filtered for the specific user ID).

### 5.7 Get Attendance Reports Summary
* **Use for:** Retrieving an aggregated summary of attendance for all employees, used for the monthly reports dashboard.
* **GET** `/admin/reports?month=2026-06&department=Engineering`
  * `month` (optional): The month to generate the report for (YYYY-MM format). Defaults to current month.
  * `department` (optional): Filter results by department name. Defaults to all departments.
* **Response (200 OK):**
```json
{
  "status": "success",
  "message": "Reports retrieved successfully",
  "data": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "user_id": "123e4567-e89b-12d3-a456-426614174000",
      "present": 20,
      "late": 2,
      "incomplete": 0,
      "absent": 1,
      "avgHours": "8h 15m"
    }
  ]
}
```
