from app.modes.definitions import MODES, get_mode, list_modes

EXPECTED_MODE_IDS = {
    "general", "os_lab", "dbms_oracle", "swe_project",
    "coding", "debug", "exam", "viva", "document",
}


def test_all_required_modes_present():
    assert set(MODES.keys()) == EXPECTED_MODE_IDS


def test_get_mode_falls_back_to_default_for_unknown_id():
    mode = get_mode("does-not-exist")
    assert mode.id == "general"


def test_get_mode_falls_back_to_default_for_none():
    assert get_mode(None).id == "general"


def test_list_modes_returns_all():
    assert len(list_modes()) == len(EXPECTED_MODE_IDS)


def test_exam_mode_prompt_mentions_marks():
    mode = get_mode("exam")
    assert "marks" in mode.system_prompt.lower()


def test_os_lab_mode_warns_about_destructive_commands():
    mode = get_mode("os_lab")
    assert "destructive" in mode.system_prompt.lower() or "rm -rf" in mode.system_prompt
