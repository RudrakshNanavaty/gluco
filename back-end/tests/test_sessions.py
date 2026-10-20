from agent.api.sessions import ChatSessions, transcript


def test_transcript_filters_non_messages_and_supports_content_parts():
    messages = transcript(
        [
            {"role": "system", "content": "ignored"},
            {
                "role": "user",
                "content": [{"text": "hello"}, {"text": " world"}, "ignored"],
            },
            {"role": "assistant", "content": "answer"},
            {"role": "assistant", "content": []},
            "not a message",
        ]
    )
    assert [(message.role, message.text) for message in messages] == [
        ("user", "hello world"),
        ("assistant", ""),
    ]
    assert messages[1].events == [{"type": "token", "text": "answer"}]


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
    assert await sessions.transcript("user", "new") == []
