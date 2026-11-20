from __future__ import annotations

from copy import deepcopy
import json
import logging
import os
from pathlib import Path
import re
import threading
from typing import Any
import uuid

from core.app_paths import PROTOCOLS_FILE, RESOURCE_ROOT, ensure_application_dirs

logger = logging.getLogger("jarvis.protocols_manager")

DEFAULT_PROTOCOLS = [{'id': 'morning', 'name': 'Доброе утро', 'description': 'Утренний запуск: выставляет громкость на 100%, открывает Opera GX, Discord и Steam, озвучивает время и погоду.', 'phrases': ['доброе утро', 'протокол доброе утро', 'подъем'], 'open_apps': ['opera', 'discord', 'steam'], 'close_mode': 'none', 'close_apps': [], 'volume_mode': 'max', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': False, 'briefing': True, 'response_text': 'Доброе утро, сэр. Все системы готовы к работе.'}, {'id': 'lockdown', 'name': 'Защита (Блокировка)', 'description': 'Ставит воспроизведение на паузу и блокирует экран Windows.', 'phrases': ['защита', 'протокол защита', 'заблокируй пк', 'терминал защита', 'протокол блокировка'], 'open_apps': [], 'close_mode': 'none', 'close_apps': [], 'volume_mode': 'none', 'pause_media': True, 'lock_screen': True, 'clean_recycle_bin': False, 'briefing': False, 'response_text': 'Блокирую терминал. До вашего возвращения, сэр.'}, {'id': 'cinema', 'name': 'Кино', 'description': 'Выставляет громкость на 100%, открывает Opera GX. Закрывает игры, Discord и Steam остаются открытыми.', 'phrases': ['кино', 'протокол кино', 'режим кино', 'время кино'], 'open_apps': ['opera'], 'close_mode': 'cinema', 'close_apps': [], 'volume_mode': 'max', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': False, 'briefing': False, 'response_text': 'Протокол «Кино» активирован, сэр. Громкость на 100%, браузер открыт. Discord и Steam сохранены.'}, {'id': 'game', 'name': 'Игра', 'description': 'Запускает Discord и Steam. Закрывает браузер и программы для освобождения ресурсов.', 'phrases': ['игра', 'протокол игра', 'режим игра', 'время играть'], 'open_apps': ['discord', 'steam'], 'close_mode': 'game', 'close_apps': [], 'volume_mode': 'none', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': False, 'briefing': False, 'response_text': 'Игровой протокол активирован, сэр. Браузер и программы закрыты, Steam и Discord на связи.'}, {'id': 'clean_desk', 'name': 'Чистый стол', 'description': 'Очищает корзину Windows без всплывающих окон.', 'phrases': ['чистый стол', 'протокол чистый стол', 'очистка', 'протокол очистка'], 'open_apps': [], 'close_mode': 'none', 'close_apps': [], 'volume_mode': 'none', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': True, 'briefing': False, 'response_text': 'Корзина очищена, сэр. Рабочее пространство в полном порядке.'}, {'id': 'work', 'name': 'Работа', 'description': 'Закрывает игры Steam (Wallpaper Engine не трогает). Открывает Opera GX, Antigravity и Unlocker.', 'phrases': ['работа', 'протокол работа', 'к работе', 'режим работа'], 'open_apps': ['opera', 'antigravity', 'unlocker'], 'close_mode': 'steam_games', 'close_apps': [], 'volume_mode': 'none', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': False, 'briefing': False, 'response_text': 'Протокол «Работа» активирован, сэр. Игра закрыта, рабочие инструменты готовы.'}, {'id': 'default', 'name': 'Дефолт (Обычный режим)', 'description': 'Возвращает системную громкость на 100% и рапортует о возврате в стандартное состояние.', 'phrases': ['дефолт', 'верни как обычно', 'обычный режим', 'сброс режима', 'стандартный режим'], 'open_apps': [], 'close_mode': 'none', 'close_apps': [], 'volume_mode': 'max', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': False, 'briefing': False, 'response_text': 'Стандартный режим восстановлен, сэр. Все системы в исходном состоянии.'}]


class ProtocolsManager:
    """Управление пользовательскими профилями и сценариями протоколов JARVIS."""

    def __init__(self, file_path: Path | None = None, event_bus=None):
        self.file_path = file_path or PROTOCOLS_FILE
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self.data: dict[str, Any] = {}
        self.load()

    @staticmethod
    def _pick_installed_defaults() -> dict[str, Any]:
        """Подбирает дефолтные ключи программ из реально установленного софта."""
        fallback = {
            "browser_key": "opera",
            "browser_label": "браузер",
            "messenger_key": "discord",
            "gaming_key": "steam",
            "work_keys": ["antigravity", "unlocker"],
        }
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return fallback
        try:
            from core.app_indexer import AppIndexer
            suggestions = AppIndexer.get_instance().get_protocol_suggestions(limit=0)
            if not suggestions:
                return fallback

            browsers = [s for s in suggestions if s.get("category") == "browser"]
            # Предпочитаем пользовательский браузер, а не встроенный Edge, если есть выбор
            non_edge = [b for b in browsers if b.get("key") not in ("msedge", "edge")]
            picked_browser = (non_edge or browsers)[0] if browsers else None

            messengers = [s for s in suggestions if s.get("category") == "messenger"]
            picked_messenger = next((m for m in messengers if "discord" in m["key"]), messengers[0] if messengers else None)

            gamings = [s for s in suggestions if s.get("category") == "gaming"]
            picked_gaming = next((g for g in gamings if "steam" in g["key"]), gamings[0] if gamings else None)

            works = [s for s in suggestions if s.get("category") == "work"]
            work_keys = [w["key"] for w in works[:2]]

            return {
                "browser_key": picked_browser["key"] if picked_browser else fallback["browser_key"],
                "browser_label": picked_browser["label"] if picked_browser else fallback["browser_label"],
                "messenger_key": picked_messenger["key"] if picked_messenger else fallback["messenger_key"],
                "gaming_key": picked_gaming["key"] if picked_gaming else fallback["gaming_key"],
                "work_keys": work_keys or fallback["work_keys"],
            }
        except Exception:
            return fallback

    def _build_default_protocols(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return deepcopy(DEFAULT_PROTOCOLS), {
                "browser_key": "opera",
                "browser_label": "Opera GX",
            }
        picked = self._pick_installed_defaults()
        browser_key = picked["browser_key"]
        browser_label = picked["browser_label"]
        messenger_key = picked["messenger_key"]
        gaming_key = picked["gaming_key"]
        work_keys = picked["work_keys"]

        protocols = deepcopy(DEFAULT_PROTOCOLS)
        for proto in protocols:
            pid = proto.get("id")
            if pid == "morning":
                proto["open_apps"] = list(dict.fromkeys([browser_key, messenger_key, gaming_key]))
                proto["description"] = f"Утренний запуск: выставляет громкость на 100%, открывает {browser_label} и базовые приложения, озвучивает время и погоду."
            elif pid == "cinema":
                proto["open_apps"] = [browser_key]
                proto["description"] = f"Выставляет громкость на 100%, открывает {browser_label}. Закрывает игры, мессенджер и лаунчеры остаются открытыми."
            elif pid == "game":
                proto["open_apps"] = list(dict.fromkeys([messenger_key, gaming_key]))
            elif pid == "work":
                proto["open_apps"] = list(dict.fromkeys([browser_key, *work_keys]))
                proto["description"] = f"Закрывает игры Steam (Wallpaper Engine не трогает). Открывает {browser_label} и рабочие инструменты."
        return protocols, picked

    def _default_roles(self, picked: dict[str, Any] | None = None) -> dict[str, str]:
        info = picked or self._pick_installed_defaults()
        work_keys = info.get("work_keys") or ["antigravity"]
        return {
            "browser": str(info.get("browser_key") or "opera"),
            "messenger": str(info.get("messenger_key") or "discord"),
            "gaming": str(info.get("gaming_key") or "steam"),
            "work": str(work_keys[0] if work_keys else "antigravity"),
        }

    def _default_data(self) -> dict[str, Any]:
        default_protocols, picked = self._build_default_protocols()
        guest_browser = picked.get("browser_key", "opera")
        default_roles = self._default_roles(picked)
        return {
            "active_profile": "default",
            "profiles": {
                "default": {
                    "name": "Основной (Тони)",
                    "roles": deepcopy(default_roles),
                    "protocols": default_protocols,
                },
                "guest": {
                    "name": "Гость",
                    "roles": deepcopy(default_roles),
                    "protocols": [
                        {
                            "id": "guest_chill",
                            "name": "Отдых",
                            "description": "Запуск браузера для гостя, комфортная громкость.",
                            "phrases": ["отдых", "протокол отдых", "гость"],
                            "open_apps": [guest_browser],
                            "close_mode": "none",
                            "close_apps": [],
                            "blocked_open_apps": [],
                            "blocked_close_apps": [],
                            "volume_mode": "max",
                            "pause_media": False,
                            "lock_screen": False,
                            "clean_recycle_bin": False,
                            "briefing": False,
                            "response_text": "Режим отдыха активирован. Браузер открыт, приятного времяпрепровождения.",
                        }
                    ],
                },
            },
        }

    def load(self) -> None:
        """Загружает протоколы из файла или создает структуру по умолчанию."""
        with self._lock:
            ensure_application_dirs()

            if self.file_path.is_file():
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        self.data = json.load(f)
                    if "profiles" in self.data and self.data["profiles"]:
                        logger.info("protocols_loaded path=%s count=%d", self.file_path, len(self.data["profiles"]))
                        return
                except Exception:
                    logger.exception("protocols_load_failed, fallback to defaults")

            bundled = RESOURCE_ROOT / "config" / "protocols.json"
            if bundled.is_file():
                try:
                    with open(bundled, "r", encoding="utf-8") as f:
                        self.data = json.load(f)
                        return
                except Exception:
                    pass

            self.data = self._default_data()
            self.save()

    def save(self) -> None:
        """Сохраняет текущую конфигурацию протоколов на диск."""
        with self._lock:
            ensure_application_dirs()
            temp_path = self.file_path.with_name(f".{self.file_path.name}.{uuid.uuid4().hex}.tmp")
            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
                temp_path.replace(self.file_path)
                logger.info("protocols_saved path=%s", self.file_path)
                if self.event_bus:
                    self.event_bus.emit("protocols.changed", self.data)
            except Exception:
                try:
                    if temp_path.exists():
                        temp_path.unlink()
                except OSError:
                    pass
                logger.exception("protocols_save_failed")

    # --- Управление профилями ---

    def list_profiles(self) -> dict[str, str]:
        """Возвращает словарь {id: имя_профиля}."""
        profiles = self.data.get("profiles", {})
        return {pid: pdata.get("name", pid) for pid, pdata in profiles.items()}

    def get_active_profile(self) -> str:
        active = self.data.get("active_profile", "default")
        if active not in self.data.get("profiles", {}):
            active = next(iter(self.data.get("profiles", {"default": {}}).keys()), "default")
            self.data["active_profile"] = active
        return active

    def set_active_profile(self, profile_id: str) -> bool:
        if profile_id in self.data.get("profiles", {}):
            self.data["active_profile"] = profile_id
            self.save()
            return True
        return False

    def add_profile(self, name: str, copy_from_active: bool = True) -> str:
        """Создает новый профиль пользователя."""
        name = name.strip() or "Новый профиль"
        base_id = re.sub(r"[^\w]+", "_", name.lower()).strip("_") or "profile"
        profile_id = base_id
        counter = 1
        while profile_id in self.data.get("profiles", {}):
            counter += 1
            profile_id = f"{base_id}_{counter}"

        protocols = []
        roles: dict[str, str]
        if copy_from_active:
            active_id = self.get_active_profile()
            protocols = deepcopy(self.data["profiles"].get(active_id, {}).get("protocols", []))
            roles = deepcopy(self.get_roles(active_id))
        else:
            protocols, picked = self._build_default_protocols()
            roles = self._default_roles(picked)

        self.data.setdefault("profiles", {})[profile_id] = {
            "name": name,
            "roles": roles,
            "protocols": protocols,
        }
        self.data["active_profile"] = profile_id
        self.save()
        return profile_id

    def delete_profile(self, profile_id: str) -> bool:
        if profile_id == "default":
            return False
        profiles = self.data.get("profiles", {})
        if profile_id in profiles and len(profiles) > 1:
            del profiles[profile_id]
            if self.data.get("active_profile") == profile_id:
                self.data["active_profile"] = next(iter(profiles.keys()))
            self.save()
            return True
        return False

    # --- Управление ролями профиля ---

    def get_roles(self, profile_id: str | None = None) -> dict[str, str]:
        """Возвращает карту ролей активного (или указанного) профиля."""
        pid = profile_id or self.get_active_profile()
        profile = self.data.get("profiles", {}).get(pid, {})
        stored = profile.get("roles") if isinstance(profile, dict) else None
        defaults = self._default_roles()
        if isinstance(stored, dict):
            merged = dict(defaults)
            for k, v in stored.items():
                key = str(k or "").strip().lower()
                val = str(v or "").strip()
                if key and val:
                    merged[key] = val
            return merged
        return defaults

    def set_roles(self, roles: dict[str, str], profile_id: str | None = None) -> dict[str, str]:
        """Обновляет карту ролей профиля и сохраняет на диск."""
        with self._lock:
            pid = profile_id or self.get_active_profile()
            profile = self.data.setdefault("profiles", {}).setdefault(pid, {"name": pid, "protocols": []})
            cleaned: dict[str, str] = {}
            for k, v in (roles or {}).items():
                key = str(k or "").strip().lower()
                val = str(v or "").strip()
                if key and val:
                    cleaned[key] = val
            profile["roles"] = cleaned
            self.save()
            return deepcopy(self.get_roles(pid))

    # --- Управление протоколами активного профиля ---

    @staticmethod
    def _clean_string_list(raw: Any) -> list[str]:
        items = raw if isinstance(raw, list) else str(raw or "").split(",")
        result: list[str] = []
        seen: set[str] = set()
        for item in items:
            val = str(item or "").strip()
            low = val.lower()
            if val and low not in seen:
                seen.add(low)
                result.append(val)
        return result

    def get_protocols(self, profile_id: str | None = None) -> list[dict[str, Any]]:
        pid = profile_id or self.get_active_profile()
        return self.data.get("profiles", {}).get(pid, {}).get("protocols", [])

    def get_protocol_by_id(self, protocol_id: str, profile_id: str | None = None) -> dict[str, Any] | None:
        for p in self.get_protocols(profile_id):
            if p.get("id") == protocol_id:
                return deepcopy(p)
        return None

    def save_protocol(self, protocol_data: dict[str, Any], profile_id: str | None = None) -> str:
        """Добавляет или обновляет протокол в профиле."""
        pid = profile_id or self.get_active_profile()
        profile = self.data.setdefault("profiles", {}).setdefault(pid, {"name": pid, "protocols": []})
        protocols = profile.setdefault("protocols", [])

        proto_payload = deepcopy(protocol_data)
        proto_payload["blocked_open_apps"] = self._clean_string_list(proto_payload.get("blocked_open_apps", []))
        proto_payload["blocked_close_apps"] = self._clean_string_list(proto_payload.get("blocked_close_apps", []))
        if "steps" in proto_payload and not isinstance(proto_payload["steps"], list):
            proto_payload["steps"] = []

        proto_id = str(proto_payload.get("id") or "").strip()
        if not proto_id:
            # Сгенерировать id из названия
            name = str(proto_payload.get("name") or "protocol").strip()
            proto_id = re.sub(r"[^\w]+", "_", name.lower()).strip("_") or "protocol"
            counter = 1
            existing_ids = {p.get("id") for p in protocols}
            candidate = proto_id
            while candidate in existing_ids:
                counter += 1
                candidate = f"{proto_id}_{counter}"
            proto_id = candidate

        proto_payload["id"] = proto_id

        # Проверить, существует ли уже
        found_idx = None
        for idx, item in enumerate(protocols):
            if item.get("id") == proto_id:
                found_idx = idx
                break

        if found_idx is not None:
            protocols[found_idx] = proto_payload
        else:
            protocols.append(proto_payload)

        self.save()
        return proto_id

    def delete_protocol(self, protocol_id: str, profile_id: str | None = None) -> bool:
        with self._lock:
            pid = profile_id or self.get_active_profile()
            profile = self.data.get("profiles", {}).get(pid)
            if not isinstance(profile, dict):
                return False
            protocols = profile.get("protocols", [])
            initial_len = len(protocols)
            filtered = [p for p in protocols if p.get("id") != protocol_id]
            if len(filtered) < initial_len:
                profile["protocols"] = filtered
                self.save()
                return True
            return False

    def find_protocol_by_phrase(self, text: str) -> dict[str, Any] | None:
        """Ищет протокол активного профиля по фразе активации с гибкой поддержкой естественной речи."""
        clean_text = re.sub(r"[^\w\s]+", " ", text.replace("ё", "е").replace("Ё", "Е"))
        normalized = " ".join(clean_text.lower().strip().split())
        if not normalized:
            return None

        candidates = {normalized}

        # 1. Снятие имени ассистента / wake word
        wake_words = r"^(?:джарвис|кириешка|ассистент|jarvis|тони|tony)\s+"
        after_wake = re.sub(wake_words, "", normalized).strip()
        if after_wake:
            candidates.add(after_wake)

        # 2. Снятие глаголов действия
        action_verbs = r"^(?:включи(?:ть)?|запусти(?:ть)?|активируй(?:те)?|активировать|поставь(?:те)?|поставить|вруби(?:ть)?|переключи(?:ть)?(?:\s+на)?|начни(?:те)?|начать|сделай(?:те)?|сделать)\s+"
        for cand in list(candidates):
            after_action = re.sub(action_verbs, "", cand).strip()
            if after_action:
                candidates.add(after_action)

        # 3. Снятие слов режима (протокол, режим, сценарий)
        mode_words = r"^(?:протокол|режим|сценарий)\s+"
        for cand in list(candidates):
            after_mode = re.sub(mode_words, "", cand).strip()
            if after_mode:
                candidates.add(after_mode)

        # 4. Преобразование винительного падежа для женского рода: "защиту" -> "защита", "работу" -> "работа"
        for cand in list(candidates):
            words = cand.split()
            if words and words[-1].endswith("у") and words[-1] != "утро":
                words[-1] = words[-1][:-1] + "а"
                candidates.add(" ".join(words))

        for proto in self.get_protocols():
            for phrase in proto.get("phrases", []):
                clean_phrase = re.sub(r"[^\w\s]+", " ", str(phrase).replace("ё", "е").replace("Ё", "Е"))
                p_norm = " ".join(clean_phrase.lower().strip().split())
                if not p_norm:
                    continue

                p_variants = {p_norm}
                p_no_mode = re.sub(mode_words, "", p_norm).strip()
                if p_no_mode:
                    p_variants.add(p_no_mode)

                if candidates & p_variants:
                    return deepcopy(proto)

        return None
