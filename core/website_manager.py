from __future__ import annotations

import json
import logging
import re
import urllib.parse
from copy import deepcopy
from pathlib import Path

from core.app_paths import WEBSITES_FILE, ensure_application_dirs

logger = logging.getLogger("jarvis.websites")

COMMON_WEBSITE_ALIASES: dict[str, list[str]] = {
    "youtube": ["ютуб", "youtube", "ютюб"],
    "vk": ["вк", "vk", "вконтакте"],
    "github": ["гитхаб", "github", "гит"],
    "twitch": ["твич", "twitch"],
    "kinopoisk": ["кинопоиск", "kinopoisk"],
    "steam": ["магазин стим", "стим стор"],
    "rutube": ["рутуб", "rutube"],
    "yandex": ["яндекс", "yandex", "яру"],
    "ya": ["яндекс", "yandex", "яру"],
    "reddit": ["реддит", "reddit"],
    "habr": ["хабр", "habr"],
    "telegram": ["телеграм", "телега", "тг"],
    "discord": ["дискорд", "дс"],
    "google": ["гугл", "гугол", "google"],
    "wikipedia": ["вики", "википедия", "wikipedia"],
}

DEFAULT_WEBSITES = [
    {
        "id": "youtube",
        "name": "YouTube",
        "url": "https://www.youtube.com",
        "aliases": ["ютуб", "youtube", "ютюб"],
    },
    {
        "id": "vk",
        "name": "ВКонтакте",
        "url": "https://vk.com",
        "aliases": ["вк", "vk", "вконтакте"],
    },
    {
        "id": "github",
        "name": "GitHub",
        "url": "https://github.com",
        "aliases": ["гитхаб", "github", "гит"],
    },
    {
        "id": "twitch",
        "name": "Twitch",
        "url": "https://www.twitch.tv",
        "aliases": ["твич", "twitch"],
    },
    {
        "id": "kinopoisk",
        "name": "Кинопоиск",
        "url": "https://www.kinopoisk.ru",
        "aliases": ["кинопоиск", "kinopoisk"],
    },
    {
        "id": "steam",
        "name": "Steam Store",
        "url": "https://store.steampowered.com",
        "aliases": ["магазин стим", "стим стор"],
    },
    {
        "id": "rutube",
        "name": "RuTube",
        "url": "https://rutube.ru",
        "aliases": ["рутуб", "rutube"],
    },
    {
        "id": "yandex",
        "name": "Яндекс",
        "url": "https://ya.ru",
        "aliases": ["яндекс", "yandex"],
    },
]

# Простая таблица транслитерации латиницы в кириллицу для авто-алиасов доменов
_LAT_TO_CYR = {
    "shch": "щ", "sh": "ш", "ch": "ч", "zh": "ж", "th": "т", "ph": "ф",
    "kh": "х", "ts": "ц", "ya": "я", "yu": "ю", "yo": "ё", "qu": "кв",
    "a": "а", "b": "б", "c": "к", "d": "д", "e": "е", "f": "ф", "g": "г",
    "h": "х", "i": "и", "j": "дж", "k": "к", "l": "л", "m": "м", "n": "н",
    "o": "о", "p": "п", "q": "к", "r": "р", "s": "с", "t": "т", "u": "у",
    "v": "в", "w": "в", "x": "кс", "y": "и", "z": "з",
}


def transliterate_latin_to_cyrillic(text: str) -> str:
    """Грубая транслитерация для автогенерации русских алиасов с латиницы."""
    clean = text.lower().strip()
    result = []
    i = 0
    n = len(clean)
    while i < n:
        matched = False
        for k in sorted(_LAT_TO_CYR.keys(), key=len, reverse=True):
            if clean.startswith(k, i):
                result.append(_LAT_TO_CYR[k])
                i += len(k)
                matched = True
                break
        if not matched:
            result.append(clean[i])
            i += 1
    return "".join(result)


class WebsiteManager:
    """Управляет базой сайтов и их алиасов с сохранением в JSON."""

    def __init__(self, file_path: Path | None = None, event_bus=None):
        self.file_path = file_path or WEBSITES_FILE
        self.event_bus = event_bus
        self._websites: list[dict] = []
        self._alias_map: dict[str, str] = {}
        self.load()

    @staticmethod
    def normalize_url(url: str) -> str:
        url = url.strip()
        if not url:
            return ""
        if not re.match(r"^https?://", url, flags=re.IGNORECASE):
            return f"https://{url}"
        return url

    @classmethod
    def generate_auto_aliases(cls, url: str, name: str = "") -> list[str]:
        """Генерирует умные автоалиасы на основе URL и имени сайта."""
        aliases = []
        raw_candidates = []

        if name:
            raw_candidates.append(name.strip())

        parsed = urllib.parse.urlparse(cls.normalize_url(url))
        hostname = (parsed.hostname or "").lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]

        parts = [p for p in hostname.split(".") if p and p not in {"com", "ru", "org", "net", "io", "tv", "me", "su", "app"}]
        if parts:
            domain_core = parts[-1]  # например "youtube" из "music.youtube.com"
            raw_candidates.append(domain_core)
            if len(parts) > 1:
                raw_candidates.append(" ".join(parts))

        for cand in raw_candidates:
            clean = cand.lower().strip()
            if not clean:
                continue
            if clean not in aliases:
                aliases.append(clean)

            # Проверка по известным сервисам
            if clean in COMMON_WEBSITE_ALIASES:
                for a in COMMON_WEBSITE_ALIASES[clean]:
                    if a not in aliases:
                        aliases.append(a)

            # Транслит с латиницы
            if re.search(r"[a-z]", clean):
                cyr = transliterate_latin_to_cyrillic(clean)
                if cyr and cyr not in aliases:
                    aliases.append(cyr)

        return aliases

    def load(self) -> None:
        ensure_application_dirs()
        if not self.file_path.exists():
            logger.info("websites_file_not_found path=%s using_defaults", self.file_path)
            self._websites = deepcopy(DEFAULT_WEBSITES)
            self.save()
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._websites = data
            else:
                logger.warning("invalid_websites_format using_defaults")
                self._websites = deepcopy(DEFAULT_WEBSITES)
        except Exception:
            logger.exception("failed_to_load_websites path=%s", self.file_path)
            self._websites = deepcopy(DEFAULT_WEBSITES)

        self._rebuild_alias_map()

    def save(self) -> None:
        try:
            ensure_application_dirs()
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._websites, f, ensure_ascii=False, indent=2)
            self._rebuild_alias_map()
            if self.event_bus:
                self.event_bus.publish("websites.updated", {"count": len(self._websites)})
            logger.info("websites_saved count=%d path=%s", len(self._websites), self.file_path)
        except Exception:
            logger.exception("failed_to_save_websites path=%s", self.file_path)

    def _rebuild_alias_map(self) -> None:
        self._alias_map.clear()
        for item in self._websites:
            url = item.get("url", "")
            if not url:
                continue
            name = item.get("name", "").strip().lower()
            if name:
                self._alias_map[name] = url
            for alias in item.get("aliases", []):
                clean_alias = str(alias).strip().lower()
                if clean_alias:
                    self._alias_map[clean_alias] = url

    def get_websites(self) -> list[dict]:
        return deepcopy(self._websites)

    def add_website(self, name: str, url: str, aliases: list[str] | None = None, auto_aliases: bool = True) -> dict:
        norm_url = self.normalize_url(url)
        name_clean = name.strip() or norm_url
        site_id = re.sub(r"[^\w-]", "", name_clean.lower().replace(" ", "-")) or f"site-{len(self._websites) + 1}"

        final_aliases = list(aliases or [])
        if auto_aliases:
            generated = self.generate_auto_aliases(norm_url, name_clean)
            for gen in generated:
                if gen not in final_aliases:
                    final_aliases.append(gen)

        new_item = {
            "id": site_id,
            "name": name_clean,
            "url": norm_url,
            "aliases": final_aliases,
        }
        self._websites.append(new_item)
        self.save()
        return new_item

    def update_website(self, site_id: str, name: str, url: str, aliases: list[str]) -> bool:
        for item in self._websites:
            if item.get("id") == site_id:
                item["name"] = name.strip() or item["name"]
                item["url"] = self.normalize_url(url)
                item["aliases"] = [a.strip().lower() for a in aliases if a.strip()]
                self.save()
                return True
        return False

    def delete_website(self, site_id: str) -> bool:
        initial_len = len(self._websites)
        self._websites = [w for w in self._websites if w.get("id") != site_id]
        if len(self._websites) != initial_len:
            self.save()
            return True
        return False

    def reset_to_defaults(self) -> None:
        self._websites = deepcopy(DEFAULT_WEBSITES)
        self.save()

    def resolve_url(self, query: str) -> tuple[dict, str] | None:
        """Ищет сайт по точному совпадению алиаса или нормализованному названию."""
        clean = query.strip().lower()
        if not clean:
            return None

        # 1. Точное попадание в alias map
        if clean in self._alias_map:
            url = self._alias_map[clean]
            for item in self._websites:
                if item.get("url") == url:
                    return item, url
            return {"name": clean, "url": url}, url

        # 2. Нечёткий или частичный поиск
        for item in self._websites:
            if clean == item.get("name", "").lower():
                return item, item["url"]
            for alias in item.get("aliases", []):
                if clean == str(alias).lower():
                    return item, item["url"]

        return None
