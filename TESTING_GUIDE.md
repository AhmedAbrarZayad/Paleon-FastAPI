# 🚀 Testing Your Paleon Backend

## Prerequisites Checklist

Before testing, make sure you have:

- ✅ **Redis** running on `localhost:6379`
- ✅ **Supabase** credentials set in `.env` file
- ✅ **OpenAI API key** set in `.env` file
- ✅ All Python dependencies installed (`pip install -r requirements.txt`)

---

## Step 1: Start Redis (if not running)

Redis must be running for Celery and rate limiting to work.

**Check if Redis is running:**
```powershell
redis-cli ping
```
If it returns `PONG`, Redis is running ✅

**If Redis is not running:**
- Download and start Redis for Windows
- Or use Docker: `docker run -d -p 6379:6379 redis`

---

## Step 2: Start Celery Worker

Open **Terminal 1** and run:

```powershell
celery -A app.celery_config worker --loglevel=info --pool=solo
```

You should see:
```
-------------- celery@YOUR-COMPUTER v5.x.x
---- **** ----- 
--- * ***  * -- Windows-10.x.x
-- * - **** --- 
- ** ---------- 

[tasks]
  . app.celery_task.classify_images_task

[2025-10-29 10:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2025-10-29 10:00:00,000: INFO/MainProcess] mingle: searching for neighbors
[2025-10-29 10:00:00,000: INFO/MainProcess] mingle: all alone
[2025-10-29 10:00:00,000: INFO/MainProcess] celery@YOUR-COMPUTER ready.
```

✅ **Celery worker is ready!**

---

## Step 3: Start FastAPI Server

Open **Terminal 2** and run:

```powershell
fastapi dev app/main.py
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

✅ **FastAPI server is ready!**

---

## Step 4: Run Tests

Open **Terminal 3** and run the comprehensive test:

```powershell
python test_auth_flow.py
```

This will test:
1. ✅ User Registration
2. ✅ User Login
3. ✅ Get Current User (`/auth/me`)
4. ✅ Create API Key
5. ✅ Async Image Classification
6. ✅ Check Classification Result
7. ✅ Get User Jobs
8. ✅ Rate Limiting (optional)

---

## Step 5: Manual Testing with Browser

### Open API Documentation:
```
http://localhost:8000/docs
```

This opens **Swagger UI** where you can:
- See all endpoints
- Test them interactively
- View request/response schemas

### Test Flow in Swagger:

1. **Register a new user:**
   - Click on `POST /auth/register`
   - Click "Try it out"
   - Enter:
     ```json
     {
       "email": "user@example.com",
       "username": "testuser",
       "password": "password123"
     }
     ```
   - Click "Execute"
   - Copy the `access_token` from response

2. **Authenticate in Swagger:**
   - Click the green "Authorize" button at top
   - Enter: `Bearer YOUR_ACCESS_TOKEN`
   - Click "Authorize"

3. **Test Classification:**
   - Click on `POST /classify-async/`
   - Click "Try it out"
   - Upload an image file
   - Click "Execute"
   - Copy the `job_id` from response

4. **Check Result:**
   - Click on `GET /result/{job_id}`
   - Enter the `job_id`
   - Click "Execute"
   - Keep checking until `status` is "completed"

---

## Expected Results

### ✅ Successful Registration:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "testuser",
    "tier": "free",
    "created_at": "2025-10-29T10:00:00"
  }
}
```

### ✅ Successful Classification Job:
```json
{
  "success": true,
  "job_id": "abc123...",
  "status": "pending",
  "message": "Classification job queued",
  "request_id": "def456",
  "rate_limit": {
    "limit": 3,
    "current": 1,
    "remaining": 2,
    "reset_at": "2025-10-30T00:00:00"
  }
}
```

### ✅ Completed Classification:
```json
{
  "status": "completed",
  "job_id": "abc123...",
  "result": {
    "fossil_name": "Tyrannosaurus Rex Tooth",
    "scientific_name": "Tyrannosaurus rex",
    "age": "Late Cretaceous (68-66 million years ago)",
    "confidence": "High"
  },
  "processing_time_ms": 3500
}
```

---

## Troubleshooting

### ❌ "Connection refused" error:
- Make sure FastAPI server is running on port 8000
- Check if another app is using port 8000

### ❌ Celery task stays "pending":
- Make sure Celery worker is running
- Check Redis connection: `redis-cli ping`
- Check Celery logs for errors

### ❌ "Rate limit exceeded":
- Free tier: 3 requests per day
- Wait 24 hours or upgrade tier in database
- Reset manually: `redis-cli FLUSHDB`

### ❌ GPT-4 Vision returns None:
- Check OpenAI API key in `.env`
- Check OpenAI API quota/billing
- Celery will auto-retry (max 3 times)

### ❌ Supabase errors:
- Check `.env` file has correct credentials:
  - `SUPABASE_URL`
  - `SUPABASE_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
- Check Supabase tables exist

---

## Quick Health Check

Run this in PowerShell to check all services:

```powershell
# Check Redis
redis-cli ping

# Check FastAPI
curl http://localhost:8000/

# Check if Celery worker can connect to Redis
celery -A app.celery_config inspect ping
```

---

## Next Steps

After successful testing:

1. ✅ Test OAuth sign-in from Flutter app
2. ✅ Test with real fossil images
3. ✅ Monitor rate limiting
4. ✅ Set up production environment variables
5. ✅ Deploy to production (Railway/Render/Fly.io)

---

**Happy Testing! 🧪🦴**
