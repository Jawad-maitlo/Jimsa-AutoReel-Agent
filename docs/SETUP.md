# Setup and configuration

## Required software

Use 64-bit Windows 10 or 11 with enough disk space for source media, exports, and AI models.

1. Install Python 3.11 or 3.12 from python.org. Enable PATH during installation.
2. Install Node.js 20 LTS from nodejs.org.
3. Install FFmpeg. One option is `winget install Gyan.FFmpeg`. Open a new terminal after installation so PATH updates.
4. Run `setup_windows.bat` from the extracted project root.

The setup script stops on missing Python, Node.js, FFmpeg, or FFprobe. It does not download Ollama or social credentials.

## Environment variables

Copy `.env.example` to `.env` (the setup script does this automatically). Common settings:

| Variable | Default | Purpose |
|---|---|---|
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Local API binding |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Development CORS origin |
| `MAX_UPLOAD_MB` | `4096` | Per-file upload limit |
| `WHISPER_MODEL` | `base` | faster-whisper model |
| `WHISPER_DEVICE` | `cpu` | `cpu`, `cuda`, or supported auto mode |
| `WHISPER_COMPUTE_TYPE` | `int8` | CPU-friendly default |
| `OLLAMA_ENDPOINT` | `http://127.0.0.1:11434` | Local Ollama API |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Configurable, not preinstalled |
| `STORAGE_DIR` | project `storage` | Mutable media/model/database root |
| `PUBLIC_MEDIA_BASE_URL` | blank | Public HTTPS mapping for Instagram |

Settings changed in the UI are persisted in SQLite and override corresponding runtime values on restart. Credentials remain in `.env` rather than the database.

## Ollama

Install Ollama from its official site, then run:

```bat
ollama pull qwen2.5:7b
ollama serve
```

You may use another Qwen model by changing **Settings → Ollama model name** and pulling that exact model. The app checks `/api/tags` and requests structured JSON from `/api/chat`. Connection, missing-model, timeout, malformed JSON, and out-of-range timestamp failures trigger the deterministic fallback; the resulting highlights are labelled `fallback`.

## faster-whisper

Model files download on first transcription into `storage/models`. This can take time and requires internet access for the initial download. Later runs reuse the local model. CPU/int8 is the reliable default. CUDA requires a compatible NVIDIA environment and faster-whisper runtime; it is not configured automatically.

Transcripts are stored in SQLite and reused. Use the force query parameter through the API only when a deliberate retranscription is needed.

## Production-style local mode

`start_production_windows.bat` serves the built `dist/` frontend through FastAPI at port 8000. Rebuild with `npm run build` after frontend changes. Development mode instead uses Vite on port 5173 and proxies `/api` to port 8000.

## Optional container

A Dockerfile is included for technical users:

```bash
docker build -t jimsa-autoreel .
docker run --rm -p 8000:8000 -v jimsa-storage:/app/storage jimsa-autoreel
```

The Windows batch workflow is the primary supported path. Docker is optional and does not provide access to an Ollama service on your host unless you configure its endpoint separately.
