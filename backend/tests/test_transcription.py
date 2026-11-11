import sys
import types
from types import SimpleNamespace
from app.database import SessionLocal
from app.models import Project, Video
from app.services.tasks import TaskContext
from app.services.transcription import transcribe_video


def test_transcription_stores_timestamped_segments(monkeypatch):
    class FakeWhisper:
        def __init__(self, *args, **kwargs):
            pass
        def transcribe(self, *args, **kwargs):
            segments = [SimpleNamespace(start=0.0, end=1.2, text=" Hello world "),
                        SimpleNamespace(start=1.2, end=2.5, text=" A grounded transcript ")]
            return iter(segments), SimpleNamespace(language="en")
    fake_module = types.SimpleNamespace(WhisperModel=FakeWhisper)
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)
    with SessionLocal() as db:
        project = Project(name="Transcription test")
        db.add(project)
        db.flush()
        video = Video(project_id=project.id, original_name="fake.mp4", file_path="fake.mp4", file_size=100,
                      duration=2.5, width=640, height=360, has_audio=True)
        db.add(video)
        db.commit()
        video_id = video.id
    with SessionLocal() as db:
        video = db.get(Video, video_id)
        transcript = transcribe_video(db, video, TaskContext("fake-job"))
        assert transcript.text == "Hello world A grounded transcript"
        assert len(transcript.segments) == 2
        assert transcript.segments[0].start == 0.0
        assert transcript.segments[1].end == 2.5
