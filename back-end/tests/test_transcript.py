"""A stored thread comes back in the shape it streamed, charts included."""

from agent.api.sessions import transcript

CHART = {"series": [{"display_name": "Patient 013", "points": []}], "metrics": []}
WIDGET = {"title": "My heart rate", "kind": "trend", "query": {}, "steps": []}


def user(text: str) -> dict:
    return {"role": "user", "content": text}


def answer(text: str) -> dict:
    return {
        "type": "message",
        "role": "assistant",
        "content": [{"type": "output_text", "text": text}],
    }


def call(call_id: str, name: str) -> dict:
    return {
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": '{"hours": 24}',
    }


def output(call_id: str, result: dict) -> dict:
    # The SDK stores a dict result as its repr.
    return {"type": "function_call_output", "call_id": call_id, "output": str(result)}


def test_tool_results_come_back_as_the_events_they_streamed():
    result = {"summary": "Gluco Score 61", "rows": 1, "chart": CHART, "widget": WIDGET}
    [asked, replied] = transcript(
        [
            user("How am I?"),
            call("c1", "build_my_widget"),
            output("c1", result),
            answer("You are close to your usual."),
        ]
    )
    assert (asked.role, asked.text) == ("user", "How am I?")
    assert [e["type"] for e in replied.events] == [
        "tool_start",
        "tool_end",
        "data",
        "token",
    ]
    start, end, data, token = replied.events
    assert (start["tool"], start["args"]) == ("build_my_widget", {"hours": 24})
    assert (end["call_id"], end["summary"], end["rows"]) == ("c1", "Gluco Score 61", 1)
    assert (data["chart"], data["widget"]) == (CHART, WIDGET)
    assert token["text"] == "You are close to your usual."


def test_a_turn_with_no_answer_does_not_shift_later_charts():
    """A declined turn stores no reply; the next turn's chart stays its own."""
    messages = transcript(
        [
            user("Diagnose me"),  # declined by the guardrail: nothing stored
            user("Show my week"),
            call("c2", "get_my_trend"),
            output("c2", {"summary": "trend", "rows": 7, "chart": CHART}),
            answer("Here is your week."),
        ]
    )
    assert [(m.role, m.text) for m in messages] == [
        ("user", "Diagnose me"),
        ("user", "Show my week"),
        ("assistant", ""),
    ]
    events = messages[-1].events
    assert [e["type"] for e in events] == ["tool_start", "tool_end", "data", "token"]


def test_an_unreadable_tool_result_still_ends_the_call():
    garbled = transcript(
        [
            user("x"),
            call("c3", "query_my_data"),
            {"type": "function_call_output", "call_id": "c3", "output": "not <json>"},
        ]
    )[1]
    assert [e["type"] for e in garbled.events] == ["tool_start", "tool_end"]
    assert garbled.events[1]["summary"] == "not <json>"
