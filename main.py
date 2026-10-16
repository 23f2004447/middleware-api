import math
import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

EMAIL = "23f2004447@ds.study.iitm.ac.in"                 # <-- YOUR logged-in email
ASSIGNED_ORIGIN = "https://app-mp00zv.example.com"
EXAM_ORIGIN = "https://exam.sanand.workers.dev"   # <-- from Step 1

RATE_LIMIT = 11      # requests allowed per client...
WINDOW = 10          # ...per this many seconds

app = FastAPI()

hits = defaultdict(deque)    # client id -> timestamps of recent requests


# ---------- Checkpoint 3: rate limiter (innermost) ----------
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_id = request.headers.get("x-client-id")
    if client_id and request.method != "OPTIONS":
        now = time.monotonic()
        q = hits[client_id]

        while q and now - q[0] >= WINDOW:      # forget old requests
            q.popleft()

        if len(q) >= RATE_LIMIT:
            wait = max(1, math.ceil(WINDOW - (now - q[0])))
            return JSONResponse(
                {"detail": "Too many requests"},
                status_code=429,
                headers={"Retry-After": str(wait)},
            )
        q.append(now)

    return await call_next(request)


# ---------- Checkpoint 2: request context (middle) ----------
@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id      # so /ping can read it

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------- Checkpoint 1: CORS (outermost, added LAST) ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ASSIGNED_ORIGIN, EXAM_ORIGIN],   # exact list, no "*"
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type"],
    expose_headers=["X-Request-ID", "Retry-After"],
)


# ---------- The endpoint ----------
@app.get("/ping")
def ping(request: Request):
    return {"email": EMAIL, "request_id": request.state.request_id}
