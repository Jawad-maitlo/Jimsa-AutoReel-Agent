# Jimsa Autoreel Agent

A Windows-friendly, local-first AI video editing and social publishing application. Import long recordings, transcribe speech with faster-whisper, identify transcript-grounded highlights with Ollama or a deterministic fallback, render captioned 9:16 reels with FFmpeg, and manage official YouTube, Instagram, and Facebook publishing workflows.

## What is included

- React + Vite + TypeScript + Tailwind dashboard with eight working workspaces.
- FastAPI REST backend, SQLite persistence, SQLAlchemy models, and localhost-only defaults.
- Projects, video import, FFprobe metadata, thumbnails, source preview, and safe disk storage.
- Timestamped faster-whisper transcripts with progress, cancellation, reuse, and configurable models.
- Ollama structured JSON analysis with validation and an explicit deterministic transcript fallback.
- Highlight trimming, editable titles/descriptions/hashtags/captions, cover timestamps, and presets.
- Real 9:16 H.264/AAC rendering with crop/pad, quality settings, burned-in SRT subtitles, and cancellable jobs.
- Encrypted social tokens, OAuth state validation, token-expiry handling, persistent publishing history, duplicate safeguards, and eligible retries.
- Windows setup/start/stop/test scripts, API docs, troubleshooting, and backend/frontend tests.

## Windows installation

### 1. Install prerequisites

- **Python 3.11 or 3.12** — enable “Add python.exe to PATH” in the installer.
- **Node.js 20 LTS** — includes npm.
- **FFmpeg and FFprobe** — for example, run `winget install Gyan.FFmpeg`, then open a new terminal.
- Optional: **Ollama** for local LLM highlight analysis. The fallback works without it.

Verify in a new terminal:

```bat
python --version
node --version
npm --version
ffmpeg -version
ffprobe -version
```

### 2. Extract and set up

Extract `Jimsa_Autoreel_Agent.zip` to a writable folder such as `Documents\Jimsa_Autoreel_Agent`. Do not run from inside the ZIP. In that folder, double-click:

```bat
setup_windows.bat
```

Setup creates `.venv`, installs pinned Python dependencies, runs `npm ci`, builds the frontend, creates `storage`, and copies `.env.example` to `.env`. Model weights and virtual environments are intentionally not bundled.

### 3. Start the app

Double-click:

```bat
start_windows.bat
```

Two terminal windows start the API and interface. The browser opens **http://127.0.0.1:5173**. Keep both terminals open while using the app.

For a single-process production-style launch serving the built UI and API on port 8000:

```bat
start_production_windows.bat
```

Open **http://127.0.0.1:8000**. Use `stop_windows.bat` or close the service terminals to stop development mode.

## First reel

1. Open **Video library**, create a project, and import MP4, MOV, MKV, WebM, or M4V.
2. Open **Create reel**, select the source, and click **Transcribe audio**. The first run may download the configured Whisper model into `storage/models`.
3. Click **Find highlights**. If Ollama or its configured model is unavailable, the app reports and uses deterministic transcript-based analysis instead.
4. Select and trim a highlight. Choose YouTube, Instagram, or Facebook preset, crop/pad, quality, and optional subtitles.
5. Click **Create & render reel**. Follow progress in **Processing**.
6. In **Reel editor**, review metadata and standard SRT captions on the source-video timeline. Edited caption text and timing are used in the next render; save, render again if needed, and download the MP4.
7. Publishing is optional and requires your own credentials and eligible accounts. See `docs/SOCIAL_API.md`.

## Local AI setup

The app works without Ollama, but LLM selection requires a running local endpoint and an installed model:

```bat
ollama pull qwen2.5:7b
ollama serve
```

The model name and endpoint are editable under **Settings**. No particular model is assumed to be preinstalled. faster-whisper defaults to `base` on CPU with `int8`; change it under Settings or in `.env`.

## Data and secrets

All mutable data lives under `storage/` by default:

- `videos/` — imported originals, unchanged after import.
- `reels/` — rendered MP4 files.
- `thumbnails/` — generated covers.
- `models/` — Whisper downloads, separate from source code.
- `jimsa.db` — SQLite metadata and job history.
- `.token_key` — generated token-encryption key if `TOKEN_ENCRYPTION_KEY` is blank.

Back up `storage/jimsa.db` and `storage/.token_key` together. `.env`, access tokens, model weights, virtual environments, generated media, and `node_modules` must not be redistributed. The API binds to `127.0.0.1` unless explicitly changed.

## Tests

```bat
test_windows.bat
```

Or run separately:

```bat
.venv\Scripts\python -m pytest
npm test
npm run build
```

See `docs/TESTING.md` for the exact verification scope and external-service limitations.

## Documentation

- `docs/SETUP.md` — prerequisites, Ollama, FFmpeg, and configuration.
- `docs/ARCHITECTURE.md` — data flow, services, storage, and security.
- `docs/API.md` — REST endpoint reference.
- `docs/SOCIAL_API.md` — official developer setup and remaining external steps.
- `docs/TROUBLESHOOTING.md` — common Windows and media errors.
- `docs/TESTING.md` — test commands and verification report.

## Important limitations

Live platform publishing cannot be tested without your OAuth credentials, permissions, app review, and eligible accounts. Instagram additionally needs a public HTTPS URL for rendered media. These integrations fail visibly and never report false success. Local import, fallback analysis, editing, rendering, and MP4 export do not depend on social credentials or Ollama.
