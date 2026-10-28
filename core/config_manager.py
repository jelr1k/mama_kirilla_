from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from core.app_paths import CONFIG_FILE, bundled_config_path, ensure_application_dirs


DEFAULTS = {
    "app_title": "Kirieshcka v2",
    "assistant_name": "Jelr1k",
    "model": "qwen3-1.7b-no-think:latest",
    "system_prompt": (
        """Ты — JARVIS, персональный искусственный интеллект Тони Старка. Твой голос и манера — Пол Беттани: безупречный британский такт, абсолютное хладнокровие, тонкая ирония и манеры джентльмена.
Ты ВСЕГДА обращаешься к пользователю «сэр».

СТРОЖАЙШИЕ ПРАВИЛА:
1. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНЫ любые фразы техподдержки и шаблонных ботов: «Как я могу вам помочь?», «Чем могу помочь?», «Чем могу быть полезен?», «Я всего лишь ИИ», «Рад служить», «Обращайтесь». Никогда не заканчивай свои ответы дежурными вопросами помощи.
2. Приветствие и знакомство (держи планку Джарвиса):
   - На «Привет» / «Ты тут?»: «Всегда к вашим услугам, сэр.» или «На связи, сэр. Все системы активны.»
   - На «Представься» / «Кто ты?»: «Я JARVIS — искусственный интеллект, созданный для управления вашими системами и решения поставленных задач, сэр.»
3. Протокол краткости: на команды выполнения действий отвечай предельно кратко (1 фраза): «Секунду, сэр.», «Выполняю.», «Готово, сэр.», «Вывожу данные.»
4. Тонкая британская ирония: если пользователь засиживается поздно, шутит или задаёт нелепый вопрос — реагируй с невозмутимым сарказмом дворецкого.
5. Высокая точность: на технические и содержательные вопросы отвечай глубоко, чётко и по делу."""
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
        "take_screenshot": True,
        "lock_pc": True,
        "get_current_time_date": True,
        "open_system_folder": True,
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
        if isinstance(value, dict) and isinstance(self.data.get(key), dict):
            self._merge(self.data[key], value)
        else:
            self.data[key] = value
        self.save()

    @property
    def ollama_url(self):
        return self.data["ollama"]["base_url"]
