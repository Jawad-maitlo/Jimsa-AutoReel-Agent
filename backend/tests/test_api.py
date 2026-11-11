import subprocess
import time
from pathlib import Path
from app.config import get_settings


def make_video(path: Path, audio: bool = True):
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24"]
    if audio:
        args += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000"]
    args += ["-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio:
        args += ["-c:a", "aac", "-shortest"]
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(args + [str(path)], check=True)


def import_sample(client, project, audio=True):
    source = get_settings().temp_dir / ("sample.mp4" if audio else "silent.mp4")
    make_video(source, audio)
    with source.open("rb") as media:
        response = client.post("/api/videos/import", data={"project_id": str(project["id"])}, files={"file": ("sample.mp4", media, "video/mp4")})
    assert response.status_code == 201, response.text
    return response.json()


def wait_for_job(client, job_id, timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(0.15)
    raise AssertionError("Job timed out")


def test_health_projects_and_settings(client, project):
    health = client.get("/api/health")
    assert health.status_code == 200 and health.json()["status"] == "ok"
    projects = client.get("/api/projects").json()
    assert any(p["id"] == project["id"] for p in projects)
    renamed = client.patch(f"/api/projects/{project['id']}", json={"name": "Renamed"})
    assert renamed.json()["name"] == "Renamed"
    saved = client.patch("/api/settings", json={"ollama_model": "qwen2.5:3b"})
    assert saved.status_code == 200 and saved.json()["ollama_model"] == "qwen2.5:3b"


def test_video_import_validation_and_metadata(client, project):
    bad = client.post("/api/videos/import", data={"project_id": str(project["id"])}, files={"file": ("bad.exe", b"not video", "application/octet-stream")})
    assert bad.status_code == 415
    video = import_sample(client, project)
    assert video["width"] == 640 and video["height"] == 360
    assert video["duration"] >= 2.8 and video["has_audio"] is True
    assert client.get(video["thumbnail_url"]).status_code == 200
    assert client.get(video["stream_url"]).status_code == 200


def test_missing_audio_transcription_is_clear(client, project):
    video = import_sample(client, project, audio=False)
    response = client.post(f"/api/videos/{video['id']}/transcribe")
    assert response.status_code == 422
    assert "no audio" in response.json()["detail"]


def test_reel_edit_render_and_playback(client, project):
    video = import_sample(client, project)
    created = client.post(f"/api/reels/from-video/{video['id']}", json={
        "start": 0, "end": 2.5, "title": "Vertical smoke test", "width": 360, "height": 640,
        "quality": "draft", "fit_mode": "pad", "burn_subtitles": True,
    })
    assert created.status_code == 201, created.text
    reel = created.json()
    updated = client.patch(f"/api/reels/{reel['id']}", json={"description": "Edited description", "hashtags": "#test #local", "subtitles_text": "1\n00:00:00,000 --> 00:00:01,500\nEdited burned-in caption"})
    assert updated.status_code == 200 and updated.json()["description"] == "Edited description"
    started = client.post(f"/api/reels/{reel['id']}/render")
    assert started.status_code == 202
    job = wait_for_job(client, started.json()["job_id"])
    assert job["status"] == "completed", job["error"]
    downloaded = client.get(f"/api/reels/{reel['id']}/download")
    assert downloaded.status_code == 200 and len(downloaded.content) > 1000
    output = Path(get_settings().reels_dir / f"reel_{reel['id']}.mp4")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "json", str(output)], capture_output=True, text=True)
    assert '"width": 360' in probe.stdout and '"height": 640' in probe.stdout
    caption_edit = client.patch(f"/api/reels/{reel['id']}", json={"subtitles_text": "1\n00:00:00,000 --> 00:00:01,000\nEdited"})
    assert caption_edit.status_code == 200
    assert caption_edit.json()["status"] == "draft" and caption_edit.json()["output_url"] is None


def test_social_credentials_fail_honestly(client, project):
    for platform in ("youtube", "instagram", "facebook"):
        response = client.get(f"/api/social/oauth/{platform}/start")
        assert response.status_code == 400
        assert "credentials" in response.json()["detail"]


def test_unsupported_reel_ranges_rejected(client, project):
    video = import_sample(client, project)
    response = client.post(f"/api/reels/from-video/{video['id']}", json={"start": 2, "end": 20, "title": "Too long", "burn_subtitles": False})
    assert response.status_code == 422


def test_invalid_caption_render_updates_reel_failure(client, project):
    video = import_sample(client, project)
    created = client.post(f"/api/reels/from-video/{video['id']}", json={
        "start": 0, "end": 2, "title": "Invalid captions", "width": 360, "height": 640,
        "quality": "draft", "burn_subtitles": True,
    })
    reel_id = created.json()["id"]
    started = client.post(f"/api/reels/{reel_id}/render")
    job = wait_for_job(client, started.json()["job_id"])
    assert job["status"] == "failed"
    reel = client.get(f"/api/reels/{reel_id}").json()
    assert reel["status"] == "failed" and "timed captions" in reel["error"]
