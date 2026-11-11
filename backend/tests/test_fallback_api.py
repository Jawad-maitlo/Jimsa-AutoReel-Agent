from app.database import SessionLocal
from app.models import Transcript, TranscriptSegment, Video


def test_fallback_highlight_api_without_ollama(client, project):
    with SessionLocal() as db:
        video = Video(project_id=project["id"], original_name="talk.mp4", file_path="talk.mp4", file_size=100,
                      duration=60, width=1280, height=720, has_audio=True)
        db.add(video); db.flush()
        transcript = Transcript(video_id=video.id, model="test", language="en", text="A complete test transcript")
        db.add(transcript); db.flush()
        for i, text in enumerate(["Here is the secret to better editing.", "Keep the complete story together.", "Why? Context makes the idea useful.", "You can apply this lesson today."]):
            db.add(TranscriptSegment(transcript_id=transcript.id, start=i * 10, end=i * 10 + 9, text=text))
        db.commit(); video_id = video.id
    response = client.post(f"/api/videos/{video_id}/highlights?prefer_llm=false&count=2")
    assert response.status_code == 200, response.text
    highlights = response.json()
    assert highlights and all(item["analysis_method"] == "fallback" for item in highlights)
    assert all(item["transcript_excerpt"] for item in highlights)
    assert all(item["start"] < item["end"] <= 60 for item in highlights)
