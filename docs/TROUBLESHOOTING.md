# Troubleshooting

## “Cannot reach the local API”

Run `start_windows.bat`, confirm the Jimsa API terminal stays open, and visit `http://127.0.0.1:8000/api/health`. If port 8000 is occupied, stop the other process or change `PORT` consistently in `.env` and the frontend development proxy.

## Python or Node is not recognized

Reinstall with PATH enabled, then close and reopen all terminals. `where python`, `where node`, and `where npm` should return paths.

## FFmpeg/FFprobe is not found

Install the full FFmpeg package, open a new terminal, and run both `ffmpeg -version` and `ffprobe -version`. The setup and start scripts check both. Media import and rendering intentionally stop if they are missing.

## Unsupported or corrupted video

Use MP4, MOV, MKV, WebM, or M4V containing a readable video stream. Try remuxing with:

```bat
ffmpeg -i input.mov -c copy repaired.mp4
```

If the file has no audio, video import and silent reel export still work, but transcription and burned-in speech subtitles do not.

## First transcription is slow or appears stalled

The initial run downloads Whisper weights into `storage/models`. Check available disk space and internet access. CPU transcription can also take longer than real time for long videos. Progress appears under Processing. Cancellation stops between segments.

## Ollama is unavailable or model is missing

Start `ollama serve`, then run `ollama list`. Pull the exact model shown in Settings, for example `ollama pull qwen2.5:7b`. Without it, highlights labelled `fallback` still work from the real transcript; no AI success is claimed.

## Burned-in subtitles fail

Check that the trim intersects timestamped transcript segments. Disable subtitles for music/silent clips. FFmpeg builds need libass support for the subtitles filter; standard full Windows builds include it. The error details remain on the failed processing job.

## OAuth callback or permissions fail

Confirm the exact redirect `http://127.0.0.1:8000/api/social/oauth/callback` in the developer app. Check test users, app mode/review, requested scopes, eligible channel/Page/Instagram professional account, and system clock. Never paste long-lived tokens into the UI or source files.

## Instagram cannot fetch the reel

`PUBLIC_MEDIA_BASE_URL` must map to `storage/reels` over public HTTPS, and the exact MP4 must remain available while Instagram processes it. A localhost URL is not publicly accessible. Facebook and YouTube uploads do not use this setting.

## Database/token recovery

Keep `storage/jimsa.db` and `storage/.token_key` together. If the key is lost, encrypted social tokens cannot be recovered; reconnect accounts. Do not delete the database to resolve routine errors.

## Tests

Run `test_windows.bat` and read the first failing section. Media integration tests generate short synthetic clips in the test storage directory and do not modify your source library.
