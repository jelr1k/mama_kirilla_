from __future__ import annotations

import difflib
import json
import re
import unicodedata
from copy import deepcopy
from pathlib import Path

from core.app_paths import ALIASES_FILE, ensure_application_dirs

try:
    import pymorphy3
except ImportError:  # pragma: no cover - dependency is declared in requirements
    pymorphy3 = None

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None

CATEGORIES = ("applications", "files", "folders", "actions")
DEFAULT_ACTION_ALIASES = {
    "launch": [
        "открой", "открыть", "открывай", "запусти", "запустить", "запускай",
        "включи", "включить", "включай", "стартуй", "стартовать",
        "вруби", "врубить", "врубай", "подними", "поднимать", "разверни", "разворачивать"
    ],
    "close": [
        "закрой", "закрыть", "закрывай", "останови", "остановить", "останавливай",
        "выключи", "выключить", "выключай", "заверши", "завершить", "завершай",
        "выруби", "вырубить", "вырубай", "прибей", "прибить", "прибивай",
        "убей", "убить", "убивай", "затуши", "затушить", "потуши", "потушить", "туши",
        "погаси", "погасить", "грохни", "грохнуть", "прикончи", "прикончить"
    ],
    "search": [
        "найди", "найти", "поищи", "поискать", "ищи", "искать",
        "отыщи", "отыскать", "разыщи", "разыскать",
        "покажи", "показать", "где находится", "где лежит", "расположение", "местоположение"
    ],
    "read": ["прочитай", "прочесть", "прочитать", "прочти", "читай", "читать", "зачитай", "зачитать", "озвучь", "озвучить"],
    "delete": ["удали", "удалить", "удаляй", "стереть", "сотри", "стирай", "убери", "убрать", "убирай", "сноси", "снести"],
    "status": ["проверь", "проверить", "проверяй", "статус"],
    "minimize": ["сверни", "свернуть", "сворачивай"],
}

ACTION_LEMMAS = {
    "launch": {
        "открыть", "открывать", "запустить", "запускать", "врубить", "врубать",
        "включить", "включать", "стартовать", "развернуть", "разворачивать", "поднять", "поднимать"
    },
    "close": {
        "закрыть", "закрывать", "вырубить", "вырубать", "выключить", "выключать",
        "остановить", "останавливать", "прибить", "прибивать", "убить", "убивать",
        "затушить", "затушивать", "потушить", "тушить", "погасить", "гасить", "завершить", "завершать", "грохнуть", "прикончить"
    },
    "search": {"найти", "искать", "поискать", "сыскать"},
    "read": {"прочитать", "читать", "прочесть", "зачитать", "озвучить"},
    "delete": {"удалить", "удалять", "стереть", "стирать", "сносить", "снести", "убрать", "убирать"},
    "status": {"проверить", "проверять", "статус"},
    "minimize": {"свернуть", "сворачивать"},
}

# Часто используемые названия, для которых есть устойчивое русское произношение.
# Намеренно не пытаемся переводить любой английский filename: автоматический
# «переводчик названий» быстро превращается в генератор лингвистического мусора.
AUTO_RUSSIAN_ALIASES = {
    "steam": "стим",
    "telegram": "телеграм",
    "telegram desktop": "телеграм",
    "discord": "дискорд",
    "minecraft": "майнкрафт",
    "prism launcher": "призм",
    "geometry dash": "геометрия дэш",
    "google chrome": "гугл хром",
    "chrome": "хром",
    "mozilla firefox": "мозилла файрфокс",
    "firefox": "файрфокс",
    "visual studio code": "вс код",
    "visual studio": "вижуал студио",
    "notepad": "ноутпад",
    "spotify": "спотифай",
    "vlc": "влс",
    "obs": "обс",
    "blender": "блендер",
    "blockbench": "блокбенч",
    "code": "код",
    "notepad++": "ноутпад плюс плюс",
    "yandex": "яндекс",
    "yandex browser": "яндекс браузер",
    "opera": "опера",
    "opera gx": "опера гх",
    "epic games": "эпик геймс",
    "epic games launcher": "эпик геймс",
    "battle.net": "батлнет",
    "battlenet": "батлнет",
    "calculator": "калькулятор",
    "calc": "калькулятор",
    "explorer": "проводник",
    "taskmgr": "диспетчер задач",
}

EXTRA_RUSSIAN_ALIASES = {
    "discord": ("дс",),
    "telegram": ("телега", "тг"),
    "telegram desktop": ("телега", "тг"),
    "steam": ("стимчик",),
    "spotify": ("споти",),
    "minecraft": ("майн",),
    "geometry dash": ("гд",),
    "blockbench": ("бб",),
    "blender": ("блендер",),
    "visual studio code": ("код", "вскод"),
    "code": ("вскод",),
    "epic games launcher": ("эпики", "эпик"),
    "epic games": ("эпики", "эпик"),
    "opera gx": ("опера гх", "гх"),
    "yandex browser": ("яндекс",),
    "notepad++": ("ноутпад", "нотпад"),
    "taskmgr": ("диспетчер",),
}

_MORPH = None
_CYRILLIC_WORD_RE = re.compile(r"^[а-яё-]+$", re.IGNORECASE)
_COMMAND_FILLER_WORDS = {
    "ну", "давай", "пожалуйста", "плиз", "пж", "блять", "блядь", "бля", "нахуй",
    "нафиг", "нахуя", "сука", "ебать", "ебаный", "ёбаный", "мне", "нам", "ты",
    "по-братски", "пожалуй", "быстро", "живо", "поскорее", "этот", "эту", "это", "ка",
    "кароче", "короче", "по-быстрому", "по-бырому", "живее", "братуха", "родной",
    "дружище", "заебал", "заебала", "чел", "чувак",
}



class AliasError(ValueError):
    """Ошибка пользовательских алиасов."""


class AliasManager:
    """Хранилище и resolver пользовательских алиасов.

    Пользовательские данные живут отдельно от исходников в %APPDATA%/Jarvis.
    Exact-match безопасен и детерминирован; fuzzy-match только предлагает
    кандидат, а сохранение нового алиаса всегда требует явного подтверждения.
    """

    def __init__(self, path: str | Path | None = None):
        ensure_application_dirs()
        self.path = Path(path) if path else ALIASES_FILE
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    @staticmethod
    def _morphologize_word(word: str) -> str:
        global _MORPH
        if not _CYRILLIC_WORD_RE.fullmatch(word) or pymorphy3 is None:
            return word
        if _MORPH is None:
            _MORPH = pymorphy3.MorphAnalyzer()
        try:
            return _MORPH.parse(word.lower())[0].normal_form
        except (IndexError, AttributeError, ValueError):
            return word

    @staticmethod
    def normalize_command_text(value: str) -> str:
        """Нормализует текст голосовой команды перед маршрутизацией.

        Схлопывает пробелы и убирает только конечную пунктуацию, которую
        Vosk/Whisper часто добавляют к коротким фразам. Пунктуация внутри
        цели (пути, URL, имени файла и т. п.) не изменяется.
        """
        text = unicodedata.normalize("NFKC", str(value))
        text = " ".join(text.strip().split())
        return text.rstrip(" 	.,!?;:")

    @classmethod
    def _normalize_alias(cls, value: str) -> str:
        text = unicodedata.normalize("NFKC", str(value)).strip().casefold()
        text = text.replace("ё", "е")
        text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
        tokens = [cls._morphologize_word(token) for token in text.split()]
        return " ".join(tokens)

    @staticmethod
    def _normalize_target(value: str) -> str:
        text = unicodedata.normalize("NFKC", str(value)).strip().casefold().replace("ё", "е")
        text = text.replace("\\", "/")
        return re.sub(r"/+/", "/", text)

    @classmethod
    def _key(cls, category: str, value: str) -> str:
        if category == "actions":
            return cls._normalize_alias(value)
        return cls._normalize_target(value)

    @staticmethod
    def _default_data() -> dict:
        return {category: {} for category in CATEGORIES}

    def _load(self) -> dict:
        if not self.path.exists():
            data = self._default_data()
            try:
                self._save(data)
            except OSError:
                pass
            return data

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}

        merged = self._default_data()
        if isinstance(raw, dict):
            for category in CATEGORIES:
                section = raw.get(category)
                if isinstance(section, dict):
                    for target, value in section.items():
                        if isinstance(value, dict):
                            aliases = value.get("aliases", [])
                        else:
                            aliases = value
                        if not isinstance(aliases, list):
                            aliases = []
                        cleaned = []
                        seen = set()
                        for alias in aliases:
                            if not isinstance(alias, str):
                                continue
                            alias = alias.strip()
                            normalized = self._normalize_alias(alias)
                            if alias and normalized and normalized not in seen:
                                cleaned.append(alias)
                                seen.add(normalized)
                        merged[category][str(target)] = {"aliases": cleaned}
        return merged

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def save(self) -> None:
        self._save(self.data)

    def list_objects(self, category: str | None = None) -> list[dict]:
        categories = [category] if category else list(CATEGORIES)
        result = []
        for current in categories:
            if current not in CATEGORIES:
                continue
            for target, entry in self.data[current].items():
                result.append({"category": current, "target": target, "aliases": list(entry.get("aliases", []))})
        return result

    def get_aliases(self, category: str, target: str) -> list[str]:
        entry = self.data.get(category, {}).get(target)
        return list(entry.get("aliases", [])) if entry else []

    def _find_conflict(self, category: str, alias: str, except_target: str | None = None) -> str | None:
        normalized = self._normalize_alias(alias)
        if not normalized:
            return None
        for target, entry in self.data.get(category, {}).items():
            if except_target is not None and target == except_target:
                continue
            if self._normalize_alias(target) == normalized:
                return target
            for existing in entry.get("aliases", []):
                if self._normalize_alias(existing) == normalized:
                    return target
        return None

    def set_aliases(self, category: str, target: str, aliases: list[str]) -> None:
        if category not in CATEGORIES:
            raise AliasError(f"Неизвестный тип алиаса: {category}")
        target = str(target).strip()
        if not target:
            raise AliasError("Целевой объект не может быть пустым.")

        cleaned = []
        seen = set()
        for alias in aliases:
            alias = str(alias).strip()
            normalized = self._normalize_alias(alias)
            if not alias or not normalized or normalized in seen:
                continue
            conflict = self._find_conflict(category, alias, except_target=target)
            if conflict:
                raise AliasError(f"Алиас «{alias}» уже привязан к «{conflict}».")
            cleaned.append(alias)
            seen.add(normalized)

        previous = deepcopy(self.data)
        self.data.setdefault(category, {})[target] = {"aliases": cleaned}
        try:
            self.save()
        except OSError:
            self.data = previous
            raise

    def add_alias(self, category: str, target: str, alias: str) -> None:
        aliases = self.get_aliases(category, target)
        aliases.append(alias)
        self.set_aliases(category, target, aliases)

    def ensure_automatic_aliases(self, category: str, target: str) -> list[str]:
        """Добавляет только безопасные автоматические алиасы, не трогая ручные."""
        if category not in {"applications", "files", "folders"}:
            return self.get_aliases(category, target)

        current = self.get_aliases(category, target)
        result = list(current)
        changed = False
        for alias in self.automatic_aliases(category, target):
            if self._normalize_alias(alias) in {self._normalize_alias(item) for item in result}:
                continue
            conflict = self._find_conflict(category, alias, except_target=target)
            if conflict:
                continue
            result.append(alias)
            changed = True

        if changed:
            self.set_aliases(category, target, result)
        return result

    def remove_object(self, category: str, target: str) -> None:
        if category not in CATEGORIES:
            raise AliasError(f"Неизвестный тип алиаса: {category}")
        self.data.get(category, {}).pop(target, None)
        self.save()

    def resolve(self, category: str, query: str) -> dict:
        if category not in CATEGORIES:
            return {"status": "none"}
        query = str(query).strip()
        if not query:
            return {"status": "none"}

        normalized_alias = self._normalize_alias(query)
        normalized_target = self._normalize_target(query)
        exact = []
        for target, entry in self.data[category].items():
            if self._key(category, target) == (normalized_alias if category == "actions" else normalized_target):
                exact.append(target)
                continue
            if any(self._normalize_alias(alias) == normalized_alias for alias in entry.get("aliases", [])):
                exact.append(target)

        if len(exact) == 1:
            return {"status": "exact", "target": exact[0], "category": category}
        if len(exact) > 1:
            return {"status": "ambiguous", "candidates": exact, "category": category}
        return {"status": "none", "category": category}

    def suggest(self, category: str, query: str, limit: int = 5) -> list[dict]:
        if category not in CATEGORIES:
            return []
        normalized = self._normalize_alias(query)
        if not normalized:
            return []
        choices = []
        for target, entry in self.data[category].items():
            labels = [target, *entry.get("aliases", [])]
            if fuzz is not None:
                best = max(
                    (max(fuzz.ratio(normalized, self._normalize_alias(label)),
                         fuzz.token_sort_ratio(normalized, self._normalize_alias(label))) / 100.0
                     for label in labels),
                    default=0.0,
                )
            else:
                best = max((difflib.SequenceMatcher(None, normalized, self._normalize_alias(label)).ratio() for label in labels), default=0.0)
            choices.append({"target": target, "category": category, "score": best})
        choices.sort(key=lambda item: item["score"], reverse=True)
        return [item for item in choices[:limit] if item["score"] >= 0.72]

    def resolve_any(self, query: str, categories: tuple[str, ...]) -> dict:
        exact = []
        for category in categories:
            result = self.resolve(category, query)
            if result["status"] == "exact":
                exact.append(result)
            elif result["status"] == "ambiguous":
                return result
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            return {"status": "ambiguous", "candidates": [f"{item['category']}: {item['target']}" for item in exact]}
        return {"status": "none"}

    def suggest_any(self, query: str, categories: tuple[str, ...], limit: int = 5) -> list[dict]:
        result = []
        for category in categories:
            result.extend(self.suggest(category, query, limit=limit))
        result.sort(key=lambda item: item["score"], reverse=True)
        return result[:limit]

    def resolve_tool_arguments(self, tool_name: str, arguments: dict) -> tuple[dict, dict | None]:
        """Подменяет пользовательское название на каноническое только при exact-match."""
        mapped = dict(arguments)
        queries = []
        if tool_name in {"find_application", "get_process_status", "close_application", "minimize_application"} and "name" in mapped:
            queries = [("name", ("applications",))]
        elif tool_name == "launch_application" and "target" in mapped:
            queries = [("target", ("applications", "files", "folders"))]
        elif tool_name in {"read_file", "write_file", "delete_file", "rename_file", "copy_file", "move_file", "file_info"} and "path" in mapped:
            queries = [("path", ("files",))]
        elif tool_name == "search_files" and "name" in mapped:
            queries = [("name", ("files", "folders"))]

        for field, categories in queries:
            value = mapped.get(field)
            result = self.resolve_any(value, categories)
            if result["status"] == "exact":
                target = result["target"]
                if tool_name == "search_files":
                    target = Path(target).name
                mapped[field] = target
            elif result["status"] == "ambiguous":
                return mapped, result
        return mapped, None

    def default_aliases(self, category: str, target: str) -> list[str]:
        if category == "actions":
            return list(DEFAULT_ACTION_ALIASES.get(target, []))
        text = str(target).strip()
        normalized = self._normalize_alias(text)
        candidates = [text]
        if category == "applications":
            first = re.split(r"[\s._-]+", text, maxsplit=1)[0]
            if first and self._normalize_alias(first) != normalized:
                candidates.append(first)
        else:
            basename = Path(text.replace("\\", "/")).name
            if basename and self._normalize_alias(basename) != normalized:
                candidates.append(basename)
        return candidates

    def automatic_aliases(self, category: str, target: str) -> list[str]:
        """Возвращает безопасные алиасы для объекта Workspace без участия LLM.

        Всегда добавляется имя без расширения. Русский вариант добавляется
        только для известных приложений/сервисов, чтобы не плодить странные
        автоматические переводы.
        """
        if category not in {"applications", "files", "folders"}:
            return self.default_aliases(category, target)

        text = str(target).strip()
        if not text:
            return []

        path_name = Path(text.replace("\\", "/")).name
        stem = Path(path_name).stem or path_name
        candidates: list[str] = []

        for value in (stem, path_name):
            value = value.strip()
            if value and value not in candidates:
                candidates.append(value)

        if category == "applications":
            key = self._normalize_alias(stem)
            russian = AUTO_RUSSIAN_ALIASES.get(key)
            if russian and russian not in candidates:
                candidates.append(russian)

            # Подключение дополнительных устойчивых сокращений (дс, тг, бб, гх, вскод и др.)
            extra = EXTRA_RUSSIAN_ALIASES.get(key)
            if extra:
                for extra_item in extra:
                    extra_clean = extra_item.strip()
                    if extra_clean and extra_clean not in candidates:
                        candidates.append(extra_clean)

            # Сокращение для многословных названий: Discord Canary -> Discord.
            first = re.split(r"[\s._-]+", stem, maxsplit=1)[0].strip()
            if first and self._normalize_alias(first) != self._normalize_alias(stem):
                if first not in candidates:
                    candidates.append(first)

        return self._unique_aliases(candidates)

    @classmethod
    def _unique_aliases(cls, aliases: list[str]) -> list[str]:
        result = []
        seen = set()
        for alias in aliases:
            normalized = cls._normalize_alias(alias)
            if not alias.strip() or not normalized or normalized in seen:
                continue
            result.append(alias.strip())
            seen.add(normalized)
        return result

    @classmethod
    def default_action_aliases(cls, action: str) -> list[str]:
        return list(DEFAULT_ACTION_ALIASES.get(action, []))

    @staticmethod
    def _is_command_filler(word: str) -> bool:
        return word.casefold().replace("ё", "е") in {
            item.replace("ё", "е") for item in _COMMAND_FILLER_WORDS
        }

    @classmethod
    def _clean_command_target(cls, target: str) -> str:
        words = target.strip(" ,:;.!?-").split()
        while words and cls._is_command_filler(words[0]):
            words.pop(0)
        while words and cls._is_command_filler(words[-1]):
            words.pop()
        return " ".join(words).strip()

    def resolve_action(self, text: str) -> tuple[str, str] | None:
        normalized = self.normalize_command_text(text)
        if not normalized:
            return None
        aliases = []
        for action, defaults in DEFAULT_ACTION_ALIASES.items():
            aliases.extend((alias, action) for alias in defaults)
        for action, entry in self.data["actions"].items():
            aliases.extend((alias, action) for alias in entry.get("aliases", []))
        for alias, action in sorted(aliases, key=lambda item: len(item[0]), reverse=True):
            prefix = alias.strip()
            if not prefix:
                continue
            pattern = rf"^{re.escape(prefix)}(?:-(?:ка|то|де|сь|кась))?(?:,)?\s+(.+)$"
            match = re.match(pattern, normalized, flags=re.IGNORECASE)
            if match:
                target = self._clean_command_target(match.group(1))
                if target:
                    return action, target

        # Разговорная команда может начинаться с мусорных/эмоциональных слов
        # или содержать их между действием и целью:
        # «нахуй закрой стим», «закрой нахуй стим», «закрой стим блять».
        for alias, action in sorted(aliases, key=lambda item: len(item[0]), reverse=True):
            prefix = alias.strip()
            if not prefix:
                continue
            pattern = rf"(?<!\w){re.escape(prefix)}(?:-(?:ка|то|де|сь|кась))?(?!\w)(?:,)?\s+(.+)$"
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if not match:
                continue

            before = normalized[:match.start()].strip(" ,:;.!?-").split()
            if before and not all(self._is_command_filler(word) for word in before):
                continue

            target = self._clean_command_target(match.group(1))
            if target:
                return action, target

        # Морфологический разбор первого значимого слова через ACTION_LEMMAS
        tokens = normalized.split()
        while tokens and self._is_command_filler(tokens[0]):
            tokens.pop(0)
        if tokens:
            first_word = tokens[0].split("-")[0].lower()
            lemma = self._morphologize_word(first_word)
            for action_name, lemmas in ACTION_LEMMAS.items():
                if lemma in lemmas or first_word in lemmas:
                    target = self._clean_command_target(" ".join(tokens[1:]))
                    if target:
                        return action_name, target

        return None
