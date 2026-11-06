from __future__ import annotations

import pytest
from core.protocols_manager import ProtocolsManager
from services.command_router import CommandRouter


@pytest.fixture
def protocols_mgr(tmp_path):
    return ProtocolsManager(file_path=tmp_path / "protocols.json")


def test_natural_speech_protocol_matching(protocols_mgr):
    test_cases = [
        # Утренний брифинг
        ("доброе утро", "morning"),
        ("протокол доброе утро", "morning"),
        ("джарвис доброе утро", "morning"),
        ("кириешка доброе утро", "morning"),
        ("включи доброе утро", "morning"),
        ("запусти протокол доброе утро", "morning"),
        ("вруби доброе утро", "morning"),

        # Кино
        ("кино", "cinema"),
        ("протокол кино", "cinema"),
        ("режим кино", "cinema"),
        ("кириешка протокол кино", "cinema"),
        ("джарвис включи протокол кино", "cinema"),
        ("включи режим кино", "cinema"),
        ("активируй кино", "cinema"),
        ("поставь кино", "cinema"),

        # Игра
        ("игра", "game"),
        ("режим игра", "game"),
        ("протокол игра", "game"),
        ("включи игру", "game"),
        ("запусти режим игра", "game"),
        ("вруби игру", "game"),
        ("время играть", "game"),

        # Защита / Блокировка
        ("защита", "lockdown"),
        ("протокол защита", "lockdown"),
        ("активируй защиту", "lockdown"),
        ("включи защиту", "lockdown"),
        ("блокировка", "lockdown"),
        ("кириешка заблокируй пк", "lockdown"),

        # Работа
        ("работа", "work"),
        ("протокол работа", "work"),
        ("режим работа", "work"),
        ("запусти работу", "work"),
        ("переключи на работу", "work"),
        ("к работе", "work"),

        # Чистый стол
        ("чистый стол", "clean_desk"),
        ("протокол чистый стол", "clean_desk"),
        ("сделай чистый стол", "clean_desk"),
        ("очистка", "clean_desk"),
        ("запусти очистку", "clean_desk"),

        # Дефолт
        ("дефолт", "default"),
        ("обычный режим", "default"),
        ("верни как обычно", "default"),
        ("сброс режима", "default"),
    ]

    for phrase, expected_id in test_cases:
        matched = protocols_mgr.find_protocol_by_phrase(phrase)
        assert matched is not None, f"Phrase '{phrase}' was not matched to any protocol!"
        assert matched["id"] == expected_id, f"Phrase '{phrase}' matched '{matched['id']}', expected '{expected_id}'"


def test_non_protocol_commands_do_not_match(protocols_mgr):
    non_protocol_phrases = [
        "запусти кс2",
        "включи vpn",
        "открой youtube",
        "поставь таймер на 5 минут",
        "сколько времени",
        "сыграй музыку",
        "найди файл отчет",
    ]

    for phrase in non_protocol_phrases:
        matched = protocols_mgr.find_protocol_by_phrase(phrase)
        assert matched is None, f"Phrase '{phrase}' falsely matched protocol '{matched['id']}'"


def test_punctuation_and_case_insensitivity(protocols_mgr):
    phrases = [
        ("Кириешка, протокол Кино!", "cinema"),
        ("Джарвис, включи режим Игра...", "game"),
        ("  АКТИВИРУЙ ЗАЩИТУ!!!  ", "lockdown"),
        ("доброе утро???", "morning"),
    ]

    for phrase, expected_id in phrases:
        matched = protocols_mgr.find_protocol_by_phrase(phrase)
        assert matched is not None, f"Phrase '{phrase}' failed matching"
        assert matched["id"] == expected_id
