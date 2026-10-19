from agent.api.sessions import ChatSessions, to_messages


def test_to_messages_filters_tool_items_and_supports_content_parts():
    messages = to_messages(
        [
            {"role": "system", "content": "ignored"},
            {"role": "assistant", "type": "function_call", "content": "ignored"},
            {
                "role": "user",
                "content": [{"text": "hello"}, {"text": " world"}, "ignored"],
            },
            {"role": "assistant", "content": "answer"},
            {"role": "assistant", "content": []},
            "not a message",
        ]
    )
    assert [message.model_dump() for message in messages] == [
        {"role": "user", "text": "hello world"},
        {"role": "assistant", "text": "answer"},
    ]


def test_chat_sessions_index_activity_and_ownership(tmp_path):
    sessions = ChatSessions(tmp_path / "sessions.sqlite")
    assert sessions.key("user", "thread") == "user:thread"
    assert sessions.owns("user", "thread") is False

    long_title = "x" * 100
    sessions.touch("user", "thread", long_title)
    sessions.touch("user", "thread", "later message")
    sessions.touch("other", "thread", "other user")

    threads = sessions.threads("user")
    assert len(threads) == 1
    assert threads[0].session_id == "thread"
    assert threads[0].title == long_title[:80]
    assert threads[0].created_at.tzinfo is not None
    assert threads[0].updated_at.tzinfo is not None
    assert sessions.owns("user", "thread") is True
    assert sessions.owns("other", "thread") is True
    assert sessions.owns("user", "missing") is False


async def test_empty_session_has_no_messages(tmp_path):
    sessions = ChatSessions(tmp_path / "sessions.sqlite")
    assert await sessions.messages("user", "new") == []
