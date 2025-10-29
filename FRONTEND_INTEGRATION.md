# Paleon Backend — Frontend Integration Guide

This document explains how to integrate the Paleon FastAPI backend with your frontend (Flutter or any HTTP client). It includes authentication flows, endpoint reference with examples (curl + Flutter/Dart), rate-limiting behavior, file upload guidance, job polling patterns, RAG-specific notes, and troubleshooting tips.

---

## Table of contents

- Overview
- Environment / Base URLs
- Authentication
  - Email/password (register & login)
  - OAuth (Supabase Google sign-in)
  - API Keys (create/manage)
  - How to send auth credentials in requests
- Endpoints (detailed)
  - POST /auth/register
  - POST /auth/login
  - POST /auth/oauth/signin
  - GET /auth/me
  - POST /auth/api-keys
  - GET /auth/api-keys
  - POST /classify-async/
  - GET /result/{job_id}
  - GET /jobs
  - GET /health
- File upload rules
- Rate limiting & headers
- Polling pattern & best practices
- Error handling & status codes
- RAG (Retrieval-Augmented Generation) notes for frontend
- Security & production tips
- Example Flutter/Dart snippets
- cURL examples
- Troubleshooting

---

## Overview

Paleon backend is an async FastAPI service that accepts user authentication (Supabase-backed), persists user profiles in Supabase, enqueues image classification jobs (Celery + Redis), and returns classification results when complete. The classification uses a RAG pipeline and GPT-4 Vision. Long-running processing is performed in background workers — the frontend submits images and polls for job completion.

This guide helps a frontend developer implement authentication, submit images, handle rate limits, and retrieve results.

---

## Environment / Base URLs

- Local development: `http://localhost:8000`
- Production: set by deploy (e.g. `https://paleon-backend.onrender.com` or Railway/Render domain)

Always use HTTPS in production.

---

## Authentication

There are two ways to authenticate users:

1. JWT (preferred for interactive users)
   - Register with `/auth/register` (email/password)
   - Login with `/auth/login` to receive a JWT access token
   - Use the JWT in the Authorization header for protected endpoints

2. OAuth via Supabase (Google sign-in)
   - The frontend obtains a Supabase access token (from Supabase Auth SDK) after Google sign-in
   - Send that token to `/auth/oauth/signin` as a Bearer token in the Authorization header
   - The backend verifies it with Supabase, creates/updates the profile, and returns a JWT

3. API Keys (machine-to-machine / programmatic)
   - Create API keys using `POST /auth/api-keys` (requires JWT auth)
   - The returned plain API key is shown only once (store it securely in the client or backend)
   - API keys are hashed before saving. If you want to use API keys for requests, ask the backend team for the exact header format — by default, the backend accepts JWT bearer tokens for endpoints.

### Sending Authentication

- JWT token: `Authorization: Bearer <access_token>`
- Supabase access token (for `/auth/oauth/signin`): `Authorization: Bearer <supabase_token>`
- API Key (if supported): typically `Authorization: ApiKey <your_key>` or a custom header `x-api-key: <your_key>` — confirm with backend.

---

## Endpoints (detailed)

Note: All endpoints that require auth use the `Authorization` header with a Bearer token.

### POST /auth/register

Register a new user (email/password).

- URL: `POST /auth/register`
- Body (JSON):
  ```json
  {
    "email": "user@example.com",
    "username": "myusername",
    "password": "strongpassword"
  }
  ```
- Success (201): returns `TokenResponse` with `access_token` and `user` object.
- Errors: 400 for weak password or existing user, 500 on server error.

### POST /auth/login

Login using email/password.

- URL: `POST /auth/login`
- Body (JSON):
  ```json
  {
    "email": "user@example.com",
    "password": "strongpassword"
  }
  ```
- Success (200): returns `TokenResponse` with `access_token` and `user` object.
- Errors: 401 invalid credentials

### POST /auth/oauth/signin

Exchange a Supabase OAuth access token (from frontend Google sign-in) for a backend JWT.

- URL: `POST /auth/oauth/signin`
- Headers:
  - `Authorization: Bearer <supabase_access_token>`
- Success (200): returns `TokenResponse` with backend `access_token` and `user` object.
- Errors: 401 invalid/expired Supabase token

### GET /auth/me

Get current user profile.

- URL: `GET /auth/me`
- Headers:
  - `Authorization: Bearer <access_token>`
- Success (200): returns `UserResponse`

### POST /auth/api-keys

Create a new API key for the user (only authenticated users can create keys).

- URL: `POST /auth/api-keys`
- Headers: `Authorization: Bearer <access_token>`
- Body (JSON): `{ "name": "My Key" }`
- Success (200): returns `APIKeyResponse` with `key` field containing the plain API key (only on creation). Save this securely.

### GET /auth/api-keys

List API keys for current user.

- URL: `GET /auth/api-keys`
- Headers: `Authorization: Bearer <access_token>`
- Success (200): returns list of keys (without plaintext key)

### POST /classify-async/

Submit 1–5 images for asynchronous classification. This queues the job and returns a `job_id` you can poll later.

- URL: `POST /classify-async/`
- Headers: `Authorization: Bearer <access_token>`
- Body: multipart/form-data with field name `image_files` (can appear multiple times)
  - Example (curl):
    ```bash
    curl -X POST "http://localhost:8000/classify-async/" \
      -H "Authorization: Bearer <ACCESS_TOKEN>" \
      -F "image_files=@/path/to/image1.jpg" \
      -F "image_files=@/path/to/image2.jpg"
    ```
- Constraints:
  - Max images: 5
  - Each file must have image/* Content-Type (e.g. `image/jpeg`, `image/png`)
- Success (200): returns an async response with `job_id`, `status` (`pending`), `request_id`, and `rate_limit` info.

### GET /result/{job_id}

Get classification result for a job.

- URL: `GET /result/{job_id}`
- Headers: `Authorization: Bearer <access_token>`
- Success (200): returns job `status` (`processing` | `completed` | `failed`), `result` (JSON), and metadata (processing time).
- Errors: 403 if the job does not belong to the user, 404 if job not found.

### GET /jobs

List user’s recent classification jobs.

- URL: `GET /jobs?limit=10`
- Headers: `Authorization: Bearer <access_token>`
- Success (200): returns list of jobs

### GET /health

A simple health endpoint used by load-balancers.

- URL: `GET /health`
- Success (200): `{"status":"healthy"}` (also checks Redis connectivity)

---

## File upload rules

- Multipart form field name: `image_files`
- Max files: 5
- Max file size: Respect environment / reverse-proxy limits. (Recommend keeping uploads < 10MB per image for performance)
- Accepted content-types: `image/jpeg`, `image/png`, `image/webp` (fastapi checks `upload_file.content_type`)

---

## Rate limiting

- Implemented per-user per-day limits based on tier (free/pro/enterprise)
- Response when rate limited: HTTP 429 (Too Many Requests)
- The response includes rate-limit metadata headers and body fields: `X-RateLimit-Limit`, `X-RateLimit-Current`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` and a `rate_limit` object in JSON describing `limit`, `current`, `remaining`, `reset_at`.

Frontend should:
- Respect 429 and show a friendly message to the user
- Back off and retry later; don't poll aggressively

---

## Polling pattern & best practices

Classification is asynchronous. Use this approach:

1. Submit images with `POST /classify-async/` → receive `job_id`
2. Poll `GET /result/{job_id}` every few seconds (3–5s) until status `completed` or `failed`
3. Use exponential backoff on failures

Polling example (pseudo-code):
```dart
// Dart pseudo-code
int attempts = 0;
while (attempts < 20) {
  final response = await http.get(Uri.parse('$BASE_URL/result/$jobId'), headers: headers);
  if (response.statusCode == 200) {
    final body = json.decode(response.body);
    if (body['status'] == 'completed') {
      return body['result'];
    } else if (body['status'] == 'failed') {
      throw Exception(body['error']);
    }
  } else if (response.statusCode == 429) {
    // Rate limit encountered — stop or wait until reset
    break;
  }
  await Future.delayed(Duration(seconds: 3 + attempts));
  attempts++;
}
throw Exception('Timeout waiting for classification');
```

Consider using a server-side webhook or websocket in the future to push results instead of polling.

---

## Error handling & status codes

- 200 OK — successful
- 201 Created — resource created (register)
- 400 Bad Request — validation failure
- 401 Unauthorized — missing/invalid token
- 403 Forbidden — trying to access another user’s resource
- 404 Not Found — resource not found
- 429 Too Many Requests — rate limiting
- 500 Server Error — server-side failure

Always parse JSON error body for additional details.

---

## RAG-specific notes for frontend

- RAG (Retrieval-Augmented Generation) powers the classifier. It can be slow on the very first run because the RAG pipeline or LLM client may initialize.
- The backend pre-caches prompts and some RAG artifacts on startup (when possible) to speed the first request. If your deployment uses cold starts, expect the first few requests to take longer.
- Frontend UX suggestions:
  - Show a "Processing..." screen with progress spinner and meaningful messages like "Queued → Processing → Completed"
  - For long-running requests, offer the user the option to be notified (email/push) so they don't have to wait
  - Provide estimated wait time or a queue position if the backend exposes it (not yet implemented)

---

## Security & production tips

- Always use HTTPS in production
- Store `OPENAI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and other secrets in environment variables or a secret manager (Render, Railway, AWS Secrets Manager)
- Enforce CORS to accept requests only from your frontend origin
- Limit file sizes and validate images on upload
- Consider rate-limiting per IP in addition to per-user

---

## Example Flutter/Dart snippets

### 1) Register & Login
```dart
// Register
final response = await http.post(
  Uri.parse('
  '\$BASE_URL/auth/register'),
  headers: {'Content-Type': 'application/json'},
  body: json.encode({
    'email': email,
    'username': username,
    'password': password,
  }),
);

// Login
final loginResp = await http.post(
  Uri.parse('
  '\$BASE_URL/auth/login'),
  headers: {'Content-Type': 'application/json'},
  body: json.encode({
    'email': email,
    'password': password,
  }),
);
final body = json.decode(loginResp.body);
final token = body['access_token'];
```

### 2) Upload images (multipart) using `http` package
```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

Future<String?> submitClassification(List<File> images, String token) async {
  final uri = Uri.parse('
  '\$BASE_URL/classify-async/');
  final request = http.MultipartRequest('POST', uri);
  request.headers['Authorization'] = 'Bearer $token';

  for (var img in images) {
    request.files.add(await http.MultipartFile.fromPath('image_files', img.path));
  }

  final streamedResponse = await request.send();
  final respStr = await streamedResponse.stream.bytesToString();
  if (streamedResponse.statusCode == 200) {
    final jsonResp = json.decode(respStr);
    return jsonResp['job_id'];
  }
  throw Exception('Upload failed: $respStr');
}
```

### 3) Polling for result (Dart)
(See Polling section above for approach)

---

## cURL examples

### Register
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"user","password":"password123"}'
```

### Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

### Submit images
```bash
curl -X POST "http://localhost:8000/classify-async/" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "image_files=@/path/to/image1.jpg" \
  -F "image_files=@/path/to/image2.jpg"
```

### Poll result
```bash
curl -X GET "http://localhost:8000/result/<job_id>" -H "Authorization: Bearer <TOKEN>"
```

---

## Troubleshooting

- 500 on registration: check server logs. If you see `bcrypt` errors, reinstall `passlib` and `bcrypt` with compatible versions (`passlib==1.7.4`, `bcrypt==4.0.1`).
- Celery tasks remain pending: ensure Celery worker is running and connected to Redis; check worker logs.
- Rate limited: respect `X-RateLimit-Reset` and inform users accordingly
- Supabase auth issues: verify `SUPABASE_URL` and keys, and check Supabase logs

---

## Next steps / Enhancements for frontend

- Add server-side push notifications (webhooks or WebSockets) for job completion
- Add retry + backoff UI logic for failed requests
- Implement optimistic UI for queued jobs (show placeholder job immediately)
- Provide `cancel job` endpoint (if needed) and UI to revoke API keys

---

If you want, I can also:
- Generate a smaller `API_REFERENCE.md` with copy-paste curl and request/response for each endpoint
- Create a Postman collection or OpenAPI client examples for Flutter/TypeScript

---

*File generated: `FRONTEND_INTEGRATION.md`*
