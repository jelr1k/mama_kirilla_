from __future__ import annotations

from copy import deepcopy
import json
import logging
import os
from pathlib import Path
import re
from typing import Any

from core.app_paths import PROTOCOLS_FILE, RESOURCE_ROOT, ensure_application_dirs

logger = logging.getLogger("jarvis.protocols_manager")

DEFAULT_PROTOCOLS = [{'id': 'morning', 'name': 'Доброе утро', 'description': 'Утренний запуск: выставляет громкость на 100%, открывает Opera GX, Discord и Steam, озвучивает время и погоду.', 'phrases': ['доброе утро', 'протокол доброе утро', 'джарвис доброе утро'], 'open_apps': ['opera', 'discord', 'steam'], 'close_mode': 'none', 'close_apps': [], 'volume_mode': 'max', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': False, 'briefing': True, 'response_text': 'Доброе утро, сэр. Все системы готовы к работе.'}, {'id': 'lockdown', 'name': 'Защита (Блокировка)', 'description': 'Ставит воспроизведение на паузу и блокирует экран Windows.', 'phrases': ['защита', 'протокол защита', 'заблокируй пк', 'терминал защита', 'протокол блокировка'], 'open_apps': [], 'close_mode': 'none', 'close_apps': [], 'volume_mode': 'none', 'pause_media': True, 'lock_screen': True, 'clean_recycle_bin': False, 'briefing': False, 'response_text': 'Блокирую терминал. До вашего возвращения, сэр.'}, {'id': 'cinema', 'name': 'Кино', 'description': 'Выставляет громкость на 100%, открывает Opera GX. Закрывает игры, Discord и Steam остаются открытыми.', 'phrases': ['кино', 'протокол кино', 'режим кино', 'время кино'], 'open_apps': ['opera'], 'close_mode': 'cinema', 'close_apps': [], 'volume_mode': 'max', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': False, 'briefing': False, 'response_text': 'Протокол «Кино» активирован, сэр. Громкость на 100%, браузер открыт. Discord и Steam сохранены.'}, {'id': 'game', 'name': 'Игра', 'description': 'Запускает Discord и Steam. Закрывает браузер и программы для освобождения ресурсов.', 'phrases': ['игра', 'протокол игра', 'режим игра', 'время играть'], 'open_apps': ['discord', 'steam'], 'close_mode': 'game', 'close_apps': [], 'volume_mode': 'none', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': False, 'briefing': False, 'response_text': 'Игровой протокол активирован, сэр. Браузер и программы закрыты, Steam и Discord на связи.'}, {'id': 'clean_desk', 'name': 'Чистый стол', 'description': 'Очищает корзину Windows без всплывающих окон.', 'phrases': ['чистый стол', 'протокол чистый стол', 'очистка', 'протокол очистка'], 'open_apps': [], 'close_mode': 'none', 'close_apps': [], 'volume_mode': 'none', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': True, 'briefing': False, 'response_text': 'Корзина очищена, сэр. Рабочее пространство в полном порядке.'}, {'id': 'work', 'name': 'Работа', 'description': 'Закрывает игры Steam (Wallpaper Engine не трогает). Открывает Opera GX, Antigravity и Unlocker.', 'phrases': ['работа', 'протокол работа', 'к работе', 'режим работа'], 'open_apps': ['opera', 'antigravity', 'unlocker'], 'close_mode': 'steam_games', 'close_apps': [], 'volume_mode': 'none', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': False, 'briefing': False, 'response_text': 'Протокол «Работа» активирован, сэр. Игра закрыта, рабочие инструменты готовы.'}, {'id': 'default', 'name': 'Дефолт (Обычный режим)', 'description': 'Возвращает системную громкость на 100% и рапортует о возврате в стандартное состояние.', 'phrases': ['дефолт', 'верни как обычно', 'обычный режим', 'сброс режима', 'стандартный режим'], 'open_apps': [], 'close_mode': 'none', 'close_apps': [], 'volume_mode': 'max', 'pause_media': False, 'lock_screen': False, 'clean_recycle_bin': False, 'briefing': False, 'response_text': 'Стандартный режим восстановлен, сэр. Все системы в исходном состоянии.'}]


class ProtocolsManager:
    """Управление пользовательскими профилями и сценариями протоколов JARVIS."""

    def __init__(self, file_path: Path | None = None, event_bus=None):
        self.file_path = file_path or PROTOCOLS_FILE
        self.event_bus = event_bus
        self.data: dict[str, Any] = {}
        self.load()

    def _default_data(self) -> dict[str, Any]:
        return {
            "active_profile": "default",
            "profiles": {
                "default": {
                    "name": "Основной (Тони)",
                    "protocols": deepcopy(DEFAULT_PROTOCOLS),
                },
                "guest": {
                    "name": "Гость",
                    "protocols": [
                        {
                            "id": "guest_chill",
                            "name": "Отдых",
                            "description": "Запуск браузера для гостя, комфортная громкость.",
                            "phrases": ["отдых", "протокол отдых", "гость"],
                            "open_apps": ["opera"],
                            "close_mode": "none",
                            "close_apps": [],
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
        ensure_application_dirs()
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info("protocols_saved path=%s", self.file_path)
            if self.event_bus:
                self.event_bus.emit("protocols.changed", self.data)
        except Exception:
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
        if copy_from_active:
            active_id = self.get_active_profile()
            protocols = deepcopy(self.data["profiles"].get(active_id, {}).get("protocols", []))
        else:
            protocols = deepcopy(DEFAULT_PROTOCOLS)

        self.data.setdefault("profiles", {})[profile_id] = {
            "name": name,
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

    # --- Управление протоколами активного профиля ---

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

        proto_id = str(protocol_data.get("id") or "").strip()
        if not proto_id:
            # Сгенерировать id из названия
            name = str(protocol_data.get("name") or "protocol").strip()
            proto_id = re.sub(r"[^\w]+", "_", name.lower()).strip("_") or "protocol"
            counter = 1
            existing_ids = {p.get("id") for p in protocols}
            candidate = proto_id
            while candidate in existing_ids:
                counter += 1
                candidate = f"{proto_id}_{counter}"
            proto_id = candidate

        protocol_data["id"] = proto_id

        # Проверить, существует ли уже
        found_idx = None
        for idx, item in enumerate(protocols):
            if item.get("id") == proto_id:
                found_idx = idx
                break

        if found_idx is not None:
            protocols[found_idx] = deepcopy(protocol_data)
        else:
            protocols.append(deepcopy(protocol_data))

        self.save()
        return proto_id

    def delete_protocol(self, protocol_id: str, profile_id: str | None = None) -> bool:
        pid = profile_id or self.get_active_profile()
        protocols = self.data.get("profiles", {}).get(pid, {}).get("protocols", [])
        initial_len = len(protocols)
        self.data["profiles"][pid]["protocols"] = [p for p in protocols if p.get("id") != protocol_id]
        if len(self.data["profiles"][pid]["protocols"]) < initial_len:
            self.save()
            return True
        return False

    def find_protocol_by_phrase(self, text: str) -> dict[str, Any] | None:
        """Ищет протокол активного профиля по фразе активации."""
        clean_text = re.sub(r"[^\w\s]+", " ", text)
        normalized = " ".join(clean_text.lower().strip().split())
        for proto in self.get_protocols():
            for phrase in proto.get("phrases", []):
                clean_phrase = re.sub(r"[^\w\s]+", " ", phrase)
                p_norm = " ".join(clean_phrase.lower().strip().split())
                if normalized == p_norm:
                    return deepcopy(proto)
                # Поддержка префиксов 'протокол' и 'джарвис'
                if normalized in (f"протокол {p_norm}", f"джарвис {p_norm}", f"режим {p_norm}"):
                    return deepcopy(proto)
        return None
