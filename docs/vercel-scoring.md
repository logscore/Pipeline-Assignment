# ML scoring on Vercel (Next.js + Python)

This repo works best on Vercel as **two projects**:

1. A **frontend** project rooted at `web/` for the Next.js app.
2. A **backend** project rooted at the repo root for the Python API.

That split avoids mixing Next.js and Python deployment roots in the same Vercel project.

## Current architecture

| Project | Root Directory | Runtime | Route |
|--------|----------------|---------|-------|
| Frontend | `web` | Node.js / Next.js | calls backend with `fetch()` |
| Backend | repo root | Python / FastAPI | `/api/inference/run` |

The frontend scoring button uses a Next.js server action that sends an authenticated POST request to the backend.

## Backend deployment

The backend deployment root is the repo root because that is where these files live:

- `api/inference/run.py`
- `requirements.txt`
- `vercel.json`
- `.python-version`

The inference API is a FastAPI app exposed at:

- `/api/inference/run`

There is also an optional cron route at:

- `/api/cron/pipeline`

## Frontend deployment

The frontend deployment root is `web`.

The scoring action in `web/app/scoring/actions.ts` expects:

- `INFERENCE_FUNCTION_URL=https://your-backend-project.vercel.app/api/inference/run`
- `INFERENCE_API_SECRET=<shared secret>`

Use the same `INFERENCE_API_SECRET` value in both projects.
Leave the backend project publicly reachable and secure it with that shared secret instead of Vercel Deployment Protection.

## Required environment variables

### Backend project

- `DATABASE_URL`
- `INFERENCE_API_SECRET`
- `LATE_DELIVERY_DECISION_THRESHOLD` (optional, defaults to `0.5`)
- `CRON_SECRET` (optional, only if you use `/api/cron/pipeline`)

### Frontend project

- `INFERENCE_FUNCTION_URL`
- `INFERENCE_API_SECRET`

## Why this works

- The backend project is auto-detected as Python because the repo root contains `requirements.txt` and `api/*.py`.
- The frontend project is auto-detected as Next.js because `web/` contains `package.json`.
- The frontend does not shell out to Python. It calls the Python backend over HTTP.

## Verification checklist

1. Deploy the backend project from the repo root.
2. Open `https://your-backend-project.vercel.app/api/inference/run`.
3. Confirm you get JSON saying the inference endpoint is healthy.
4. Deploy the frontend project from `web/`.
5. Set `INFERENCE_FUNCTION_URL` in the frontend project to the full backend URL.
6. Click the scoring button and confirm `order_predictions` updates.
