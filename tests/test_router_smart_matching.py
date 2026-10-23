from __future__ import annotations

import tempfile
from unittest.mock import Mock

from core.alias_manager import AliasManager
from core.target_resolver import TargetResolver
from services.command_router import CommandRouter


def test_resolve_action_particles_and_lemmas():
    am = AliasManager()
    
    # Hyphenated particles
    assert am.resolve_action("открой-ка стим") == ("launch", "стим")
    assert am.resolve_action("закрой-ка телеграм") == ("close", "телеграм")
    assert am.resolve_action("вруби-ка спотифай") == ("launch", "спотифай")
    
    # Conversational verbs and filler words
    assert am.resolve_action("открой мне стим") == ("launch", "стим")
    assert am.resolve_action("потуши дискорд") == ("close", "дискорд")
    assert am.resolve_action("закрой нахуй стим") == ("close", "стим")
    assert am.resolve_action("запустишь стим") == ("launch", "стим")
    assert am.resolve_action("открывай стим") == ("launch", "стим")


def test_custom_and_slang_aliases_resolution():
    with tempfile.TemporaryDirectory() as directory:
        am = AliasManager(path=directory + "/aliases.json")
        am.data.setdefault("applications", {})["Discord.lnk"] = {
            "aliases": ["Discord", "хуй бобра", "дс"]
        }
        tr = TargetResolver(am)

        # Exact slang alias
        target, err = tr.resolve("дс", ("applications",))
        assert target == "Discord.lnk"
        assert err is None

        # Exact custom alias
        target, err = tr.resolve("хуй бобра", ("applications",))
        assert target == "Discord.lnk"
        assert err is None

        # Inflection / genitive case
        target, err = tr.resolve("хуя бобра", ("applications",))
        assert target == "Discord.lnk"
        assert err is None

        # Typo with high confidence fuzzy match (score >= 0.82)
        target, err = tr.resolve("хуй бабра", ("applications",))
        assert target == "Discord.lnk"
        assert err is None


def test_command_router_distinguishes_commands_from_free_chat():
    am = AliasManager()
    cfg = {"tools": {"launch_application": True, "close_application": True}}
    router = CommandRouter(config=cfg, ollama_manager=Mock(), alias_manager=am)

    # System command recognized (does not return None)
    act = router._resolve_action("открой-ка мне блокнот")
    assert act is not None
    assert act[0] == "launch"

    # Free conversational text returns None (passed directly to LLM)
    assert router._resolve_action("расскажи анекдот") is None
    assert router._resolve_action("как сварить пельмени") is None
    assert router._resolve_action("почему трава зеленая") is None
