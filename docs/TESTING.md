# Testing and verification

## Automated commands

From the project root after setup:

```bat
.venv\Scripts\python -m pytest
npm test
npm run build
```

`test_windows.bat` runs all three. Backend tests use an isolated temporary SQLite database and storage directory. They do not use your normal `storage/jimsa.db` or source library.

## Coverage

Backend tests cover:

- Health, project creation/rename, settings persistence, and database initialization.
- Invalid file-type rejection and missing-audio behavior.
- Real FFmpeg synthetic-video import, FFprobe metadata, thumbnails, and source streaming.
- Real vertical reel rendering with edited burned-in SRT captions, MP4 download, and FFprobe dimension verification.
- Caption trim offsets, legacy caption compatibility, invalid-caption errors, and exported-reel invalidation after edits.
- Failed-render propagation to both the processing job and reel status.
- Timestamped transcription storage with a mocked model runtime.
- Deterministic fallback highlights, grounded excerpts, SRT timing, and metadata generation.
- Token encryption round trip, path escape rejection, and idempotency behavior.
- Missing social credentials, Instagram scheduling rejection, duplicate safeguards, cancellation, simulated platform failure, and confirmation-driven published status.

Frontend Vitest tests cover formatting helpers, progress/status rendering, empty-state actions, and keyboard/modal close behavior.

## Delivery verification report

Final packaging-run results:

- **23 backend tests passed** with pytest.
- **6 frontend tests passed** across 2 Vitest files.
- **ESLint passed** with no errors.
- **Production frontend build passed** with TypeScript and Vite.
- **npm audit reported 0 vulnerabilities**.
- **Production browser smoke test passed** at 1440×1000 and 375×812. All eight workspaces opened, mobile navigation worked, no horizontal overflow remained, and the final clean browser session reported zero console errors.
- Browser-driven editing rendered and downloaded a real 360×640 MP4 with custom SRT text visibly burned into the video; FFprobe confirmed its dimensions.

The delivery environment is Linux. Windows batch scripts were statically inspected but **not executed on Windows**. Docker configuration was inspected but **not built**, because Docker was unavailable in the verification environment.

Real faster-whisper model download/inference and real Ollama inference were **not live-tested**; transcription orchestration uses a mocked model runtime and Ollama-unavailable fallback behavior is tested. Live OAuth, platform uploads, and platform scheduling were **not tested** without developer credentials, permissions, and eligible social accounts. Simulated adapter tests verify local state handling only. The application never marks a social post published without a confirming adapter response.
