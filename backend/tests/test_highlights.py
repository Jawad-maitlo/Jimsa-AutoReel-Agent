from app.models import TranscriptSegment
from app.services.highlights import fallback_highlights, make_title
from app.services.captions import build_srt, editable_srt, format_srt_time, suggest_metadata


def segments():
    texts = [
        "Today I want to tell you a story about a mistake.",
        "I spent weeks editing every clip by hand.",
        "It was exhausting and the results were inconsistent.",
        "Then I discovered a simple system that changed everything.",
        "The secret is to keep the complete thought together.",
        "Why does this work? Because the viewer has context.",
        "You can start with one long recording today.",
        "Remember to review every clip before publishing.",
    ]
    return [TranscriptSegment(id=i + 1, transcript_id=1, start=i * 6.0, end=(i + 1) * 6.0 - 0.4, text=text) for i, text in enumerate(texts)]


def test_fallback_is_grounded_and_ordered():
    result = fallback_highlights(segments(), 48, count=3, min_length=12, max_length=30)
    assert 1 <= len(result) <= 3
    assert result == sorted(result, key=lambda item: item.start)
    for item in result:
        assert item.start < item.end <= 48
        assert item.transcript_excerpt
        assert item.analysis_method == "fallback"
        assert 0 <= item.confidence <= 1
        assert item.title


def test_fallback_empty_transcript_returns_no_fake_content():
    assert fallback_highlights([], 60) == []


def test_srt_offsets_and_formatting():
    result = build_srt(segments()[2:4], start=12, end=24)
    assert "00:00:00,000 --> 00:00:05,600" in result
    assert "exhausting" in result
    assert format_srt_time(62.25) == "00:01:02,250"


def test_metadata_uses_source_excerpt():
    result = suggest_metadata("A useful editing lesson", "The secret editing system saves editing time")
    assert "secret editing system" in result["description"]
    assert "#editing" in result["hashtags"]


def test_edited_srt_controls_rendered_text_and_trim_offset():
    captions = "1\n00:00:01,000 --> 00:00:03,000\nOriginal words"
    result = editable_srt(captions.replace("Original words", "My edited caption"), start=0.5, end=4)
    assert "00:00:00,500 --> 00:00:02,500" in result
    assert "My edited caption" in result
    assert "Original words" not in result


def test_legacy_caption_lines_remain_renderable():
    result = editable_srt("[00:00:01,000] First\n[00:00:02,000] Second", start=1, end=3)
    assert "00:00:00,000 --> 00:00:01,000" in result
    assert "First" in result and "Second" in result


def test_invalid_or_out_of_range_captions_fail_visibly():
    import pytest
    with pytest.raises(ValueError, match="Invalid captions"):
        editable_srt("Words without timestamps", 0, 3)
    with pytest.raises(ValueError, match="overlap"):
        editable_srt("1\n00:00:05,000 --> 00:00:06,000\nLater", 0, 3)
