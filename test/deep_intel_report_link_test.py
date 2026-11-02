from types import SimpleNamespace

from agents.deep_intel.orchestrator import _append_report_location


def _event(tool_text: str | None, result_content: list | None = None):
    messages = []
    if tool_text is not None:
        messages.append({"role": "user", "content": [{"toolResult": {"status": "success", "content": [{"text": tool_text}]}}]})
    result = SimpleNamespace(message={"content": result_content if result_content is not None else [{"text": "summary"}]})
    return SimpleNamespace(result=result, agent=SimpleNamespace(messages=messages))


def test_appends_real_url_from_tool_result():
    url = "https://b.s3.amazonaws.com/k.html?X-Amz-Signature=abc&X-Amz-Expires=86400"
    event = _event(str({"saved_path": "/tmp/reports/a.html", "report_url": url}))
    _append_report_location(event)
    assert url in event.result.message["content"][-1]["text"]
    assert "/tmp/reports/a.html" in event.result.message["content"][-1]["text"]


def test_states_unavailable_when_url_is_none():
    event = _event('{"saved_path": "/tmp/reports/a.html", "report_url": null}')
    _append_report_location(event)
    assert "not available" in event.result.message["content"][-1]["text"]


def test_no_tool_call_leaves_result_untouched():
    event = _event(None)
    _append_report_location(event)
    assert event.result.message["content"] == [{"text": "summary"}]
