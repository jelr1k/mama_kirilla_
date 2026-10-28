from __future__ import annotations

from chat.conversation import Conversation
from chat.message import Message
from llm.request import ChatRequest
from llm.response import GenerationStats, StreamChunk
from llm.statistics import calculate_stats, ns_to_s
from services.chat_service import ChatService


def test_conversation_round_trip_preserves_ollama_metadata():
    conversation = Conversation()
    conversation.add("user", "Hello")
    conversation.add_ollama_message({
        "role": "assistant",
        "content": "Hi",
        "tool_calls": [{"function": {"name": "read_file"}}],
    })

    assert conversation.as_ollama_messages() == [
        {"role": "user", "content": "Hello"},
        {
            "role": "assistant",
            "content": "Hi",
            "tool_calls": [{"function": {"name": "read_file"}}],
        },
    ]


def test_chat_request_has_safe_defaults():
    request = ChatRequest(model="test", messages=[])

    assert request.model == "test"
    assert request.thinking is False
    assert request.temperature == 0.7
    assert request.tools == []


def test_stream_chunk_and_generation_stats_are_framework_independent():
    stats = GenerationStats(model="test", total_tokens=3)
    chunk = StreamChunk(text="hello", done=True, stats=stats)

    assert chunk.text == "hello"
    assert chunk.done
    assert chunk.stats is stats


def test_statistics_convert_nanoseconds_and_calculate_speed():
    assert ns_to_s(2_000_000_000) == 2.0

    result = calculate_stats(
        {
            "model": "test",
            "total_duration": 3_000_000_000,
            "load_duration": 500_000_000,
            "prompt_eval_duration": 500_000_000,
            "eval_duration": 1_000_000_000,
            "prompt_eval_count": 10,
            "eval_count": 20,
        },
        elapsed_to_first_token=0.25,
        thinking=False,
    )

    assert result["total_tokens"] == 30
    assert result["generation_speed_tps"] == 20.0
    assert result["ttft_s"] == 0.25


def test_chat_confirmation_parser_uses_explicit_answers():
    assert ChatService._parse_confirmation("да") is True
    assert ChatService._parse_confirmation("  OK  ") is True
    assert ChatService._parse_confirmation("нет") is False
    assert ChatService._parse_confirmation("может быть") is None


def test_chat_argument_normalizer_handles_dict_and_json():
    assert ChatService._normalize_arguments({"path": "a"}) == {"path": "a"}
    assert ChatService._normalize_arguments('{"path": "a"}') == {"path": "a"}
    assert ChatService._normalize_arguments("not json") == {}
    assert ChatService._normalize_arguments(123) == {}


def test_chat_service_injects_system_prompt_into_request():
    from unittest.mock import Mock
    tasks = Mock()
    captured_request = []
    tasks.submit.side_effect = lambda fn, req: captured_request.append(req) or Mock()

    service = ChatService(Mock(),
        config={
            "model": "qwen2.5:7b",
            "system_prompt": "You are JARVIS.",
            "temperature": 0.7,
            "context_length": 4096,
            "max_tokens": 128,
            "router_only_mode": False,
        },
        task_runner=tasks,
    )
    service.router = Mock()
    service.router.route.return_value = None
    service.router.tools_for_message.return_value = set()
    service.router._normalize_command_text.side_effect = lambda t: t
    service.router._definition_display.return_value = []

    service.send("Привет")

    assert len(captured_request) == 1
    req = captured_request[0]
    assert req.messages[0]["role"] == "system"
    assert "You are JARVIS." in req.messages[0]["content"]
    assert "Текущий контекст системы в реальном времени" in req.messages[0]["content"]
    assert "Время и дата:" in req.messages[0]["content"]
    assert req.messages[1] == {"role": "user", "content": "Привет"}
