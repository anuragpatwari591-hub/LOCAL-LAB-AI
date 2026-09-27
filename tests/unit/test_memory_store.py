from app.memory.store import MemoryStore, history_to_chat_messages


def test_conversation_and_message_roundtrip(tmp_path):
    store = MemoryStore(db_path=tmp_path / "memory.db")
    conv_id = store.create_conversation("Test", mode="exam")
    store.add_message(conv_id, "user", "What is a mutex?")
    store.add_message(conv_id, "assistant", "A mutex is a locking primitive.")

    history = store.get_history(conv_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_history_ordered_oldest_first(tmp_path):
    store = MemoryStore(db_path=tmp_path / "memory.db")
    conv_id = store.create_conversation("Order test")
    for i in range(5):
        store.add_message(conv_id, "user", f"message {i}")
    history = store.get_history(conv_id, limit=5)
    assert [h["content"] for h in history] == [f"message {i}" for i in range(5)]


def test_clear_all_wipes_everything(tmp_path):
    store = MemoryStore(db_path=tmp_path / "memory.db")
    project_id = store.create_project("Proj")
    conv_id = store.create_conversation("C", project_id=project_id)
    store.add_message(conv_id, "user", "hi")
    store.add_note("a note", project_id=project_id)

    store.clear_all()

    assert store.list_projects() == []
    assert store.list_conversations() == []


def test_ocr_text_included_in_chat_messages():
    history = [{"role": "user", "content": "explain this error", "ocr_text": "NullPointerException"}]
    messages = history_to_chat_messages(history)
    assert "NullPointerException" in messages[0]["content"]


def test_projects_scope_conversations(tmp_path):
    store = MemoryStore(db_path=tmp_path / "memory.db")
    p1 = store.create_project("P1")
    p2 = store.create_project("P2")
    store.create_conversation("in p1", project_id=p1)
    store.create_conversation("in p2", project_id=p2)

    assert len(store.list_conversations(project_id=p1)) == 1
    assert len(store.list_conversations(project_id=p2)) == 1
