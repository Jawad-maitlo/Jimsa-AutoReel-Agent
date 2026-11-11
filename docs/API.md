# REST API

The live OpenAPI interface is available at `http://127.0.0.1:8000/docs` while the backend runs. All routes below are prefixed with `/api`.

## System

- `GET /health` — service liveness and version.
- `GET /system/status` — FFmpeg, FFprobe, Ollama, Whisper, storage, and credential-presence checks.
- `GET /settings`, `PATCH /settings` — non-secret model and endpoint configuration.
- `GET /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/cancel` — processing progress and cancellation.

## Projects and videos

- `GET /projects`, `POST /projects`, `PATCH /projects/{id}`, `DELETE /projects/{id}`.
- `GET /videos?project_id=...`.
- `POST /videos/import` — multipart fields `project_id` and `file`.
- `GET /videos/{id}`, `DELETE /videos/{id}`.
- `GET /videos/{id}/stream`, `GET /videos/{id}/thumbnail`.
- `POST /videos/{id}/transcribe?force=false` — returns a processing job or transcript-reuse response.
- `GET /videos/{id}/transcript`.
- `POST /videos/{id}/highlights?prefer_llm=true&count=5`, `GET /videos/{id}/highlights`.
- `PATCH /videos/highlights/{highlight_id}` — validated trim/title/selection update.

## Reels

- `GET /reels?video_id=...`, `GET /reels/{id}`.
- `POST /reels/from-video/{video_id}` — trim, title, preset, dimensions, quality, fit, and subtitle options.
- `PATCH /reels/{id}` — metadata and trim editing. Render-affecting changes invalidate the old export.
- `POST /reels/{id}/render` — asynchronous processing job.
- `GET /reels/{id}/download`, `DELETE /reels/{id}`.

## Social and publishing

- `GET /social/accounts`, `DELETE /social/accounts/{id}`.
- `GET /social/oauth/{platform}/start` where platform is `youtube`, `instagram`, or `facebook`.
- `GET /social/oauth/callback` — registered OAuth redirect; not a manual token endpoint.
- `POST /social/reels/{reel_id}/publish` — body contains `account_id` and optional `scheduled_at`.
- `GET /social/publish-jobs`.
- `POST /social/publish-jobs/{id}/retry`, `POST /social/publish-jobs/{id}/cancel`.

HTTP errors use FastAPI’s `{ "detail": "actionable message" }` shape. Worker errors remain available on the corresponding processing or publishing record.
