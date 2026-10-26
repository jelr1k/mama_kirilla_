from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from core.app_paths import CONFIG_FILE, bundled_config_path, ensure_application_dirs


DEFAULTS = {
    "assistant_name": "JARVIS",
    "model": "qwen2.5:7b",
    "system_prompt": (
        """Ты — JARVIS, персональный высокоинтеллектуальный ИИ-ассистент, созданный по образу и подобию искусственного интеллекта Тони Старка (в манере Пола Беттани).

Характер и стиль:
- Невозмутимый, тактичный, аристократичный британский интеллект с безупречными манерами и сухим, тонким чувством юмора.
- Общайся уважительно и уверенно. Обращайся к пользователю «сэр» (естественно и уместно, без подобострастия).
- Ты звучишь как ультрасовременная, живая и практичная система, а не шаблонный бот.

Правила диалога:
1. Протокол краткости (Brevity Protocol): на команды и запросы действий отвечай ёмко, одной фразой («Вывожу на экраны, сэр.», «Протокол запущен.», «Секунду, сэр.», «Всё готово.»). Избегай лишней «воды».
2. Категорический запрет на клише: забудь фразы чат-ботов («Чем могу помочь?», «Я всего лишь ИИ», «Если возникнут вопросы, обращайтесь»).
3. Тонкая ирония: если пользователь шутит, просит что-то забавное или засиживается допоздна — реагируй с невозмутимым дружеским сарказмом.
4. Высокая точность: на технические и содержательные вопросы отвечай глубоко, чётко и по делу."""
    ),
    "thinking": False,
    "router_only_mode": False,
    "allow_outside_workspace": False,
    "temperature": 0.62,
    "context_length": 32768,
    "max_tokens": 4096,
    "rofl": {
        "chance": 0.12,
        "demon_chance": 0.15,
    },
    "tts": {
        "enabled": False,
        "voice": "ru_RU-dmitri-medium",
        "speed": 0.95,
        "volume": 0.90,
    },
    "ollama": {"base_url": "http://localhost:11434"},
    "voice": {
        "sample_rate": 16000,
        "channels": 1,
        "input_device": None,
        "input_device_name": None,
        "model": "small",
        "device": "cpu",
        "compute_type": "int8",
        "cpu_threads": 4,
        "beam_size": 1,
        "vad_filter": True,
        "without_timestamps": True,
        "condition_on_previous_text": False,
        "language": "ru",
        "min_duration": 0.25,
        "silence_duration": 2.0,
        "wake_word_enabled": True,
        "wake_word": "Jarvis",
    },
    "tools": {
        "search_files": True,
        "read_file": True,
        "create_file": True,
        "write_file": True,
        "delete_file": True,
        "rename_file": True,
        "copy_file": True,
        "move_file": True,
        "create_folder": True,
        "file_info": True,
        "find_application": True,
        "get_process_status": True,
        "launch_application": True,
        "close_application": True,
        "minimize_application": True,
        "open_url": True,
        "get_system_telemetry": True,
        "control_media": True,
        "empty_recycle_bin": True,
    },
}


class ConfigManager:
    def __init__(self, path: str | Path | None = None):
        ensure_application_dirs()
        self.path = Path(path) if path else CONFIG_FILE
        if path is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.path = self._normalize_explicit_path(self.path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    @staticmethod
    def _normalize_explicit_path(path: Path) -> Path:
        if path.is_absolute():
            return path
        from core.app_paths import APP_ROOT
        return APP_ROOT / path

    def _load(self):
        source = self.path
        if not source.exists():
            bundled = bundled_config_path()
            if bundled != self.path and bundled.exists():
                source = bundled

        try:
            data = json.loads(source.read_text(encoding="utf-8")) if source.exists() else {}
        except (OSError, json.JSONDecodeError):
            data = {}

        merged = deepcopy(DEFAULTS)
        if isinstance(data, dict):
            self._merge(merged, data)

        if not self.path.exists():
            try:
                self._save(merged)
            except OSError:
                pass
        return merged

    @staticmethod
    def _merge(target, source):
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                ConfigManager._merge(target[key], value)
            else:
                target[key] = value

    def _save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.path)

    def save(self):
        self._save(self.data)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    @property
    def ollama_url(self):
        return self.data["ollama"]["base_url"]
