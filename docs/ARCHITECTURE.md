# Architecture

## Runtime

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS. `src/context/AppContext.tsx` owns server state and polling; page components call the typed REST helper.
- **Backend:** FastAPI routers under `backend/app/routers`, with Pydantic validation and OpenAPI at `/docs`.
- **Database:** SQLAlchemy 2 and SQLite. Foreign keys and WAL are enabled. Large media remains on disk.
- **Workers:** a bounded thread pool persists generic processing jobs. Transcription and FFmpeg report progress and observe cooperative cancellation.
- **Publishing:** platform adapters run through the same worker system. Publishing jobs have a separate durable status history.

## Request/data flow

1. Upload streams to a UUID filename in `storage/videos` with extension and size checks.
2. FFprobe validates streams and extracts duration, dimensions, frame rate, and audio metadata.
3. faster-whisper creates timestamped segments; SQLAlchemy stores transcript text and segments.
4. Ollama receives timestamped transcript lines. Pydantic validates every returned highlight. Invalid or unavailable LLM analysis falls back to deterministic scoring using only source transcript segments.
5. A reel references source/highlight IDs and editable trim/metadata fields. Rendering writes a temporary MP4 and atomically moves it to `storage/reels` only after FFmpeg exits successfully.
6. Publishing requires an exported reel and connected account. Duplicate active/published destinations are rejected. Only an adapter’s confirmed response sets `published` or platform `scheduled` status.

## Main tables

- `projects`, `videos`, `transcripts`, `transcript_segments`, `highlights`, `reels`
- `processing_jobs` for local worker progress
- `social_accounts` with encrypted token columns
- `publish_jobs` with attempts, errors, idempotency key, platform ID, and timestamps
- `app_settings` for non-secret runtime preferences

Schema creation uses `Base.metadata.create_all` on startup. Version 1 has no destructive migration step. Future schema changes should add explicit migrations rather than dropping user tables.

## Security boundaries

- Localhost binding by default; development CORS is limited to known local origins.
- Upload names are replaced with UUIDs; allowed extensions and byte limits are enforced.
- Every media path read or delete is resolved and checked against its managed storage root.
- FFmpeg/FFprobe use argument arrays, never shell command strings.
- Social access and refresh tokens use Fernet encryption. OAuth uses a random, expiring state value.
- Logs redact common token/secret query patterns. API errors do not return stack traces.
- Original source files are never modified by rendering. Temporary render/SRT files are cleaned up.

## External boundaries

Ollama is optional and local. YouTube uses OAuth and resumable Data API uploads. Instagram uses Graph API containers and requires public media URLs. Facebook uses the three-phase Page Reels upload. No TikTok adapter exists. No unofficial scraping, credential bypass, or hardcoded success path is included.
