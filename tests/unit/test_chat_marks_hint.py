from app.api.routes_chat import _marks_hint


def test_one_mark_is_extremely_concise():
    hint = _marks_hint(1)
    assert "one or two lines" in hint


def test_ten_marks_is_detailed():
    hint = _marks_hint(10)
    assert "detailed" in hint.lower()


def test_none_returns_empty():
    assert _marks_hint(None) == ""


def test_unusual_mark_value_still_scales():
    hint = _marks_hint(20)
    assert "20" in hint
