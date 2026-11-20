"""Batch pre-generation of prepared WAV assets for static assistant and rofl phrases."""
from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.protocols_manager import DEFAULT_PROTOCOLS
from services import rofl_phrases
from services.chat_service import ROUTER_UNKNOWN_RESPONSES
from voice.tts.asset_manager import AudioAssetManager, BUNDLED_TTS_ASSETS_DIR
from voice.tts.engines.teratts import TeraTTSBackend


DEFAULT_STATIC_PHRASES: tuple[str, ...] = (
    # Медиа и громкость
    "Громкость установлена на максимум (100%).",
    "Звук выключен.",
    "Звук уже выключен.",
    "Звук включен.",
    "Звук уже включен.",
    "Звук переключен (mute/unmute).",
    "Громкость увеличена на 10%.",
    "Громкость уменьшена на 10%.",
    "Воспроизведение переключено (play/pause).",
    "Музыка остановлена.",
    "Включен следующий трек.",
    "Включен предыдущий трек.",
    "Медиа-команда выполнена.",
    # Системные и окно
    "Корзина очищена.",
    "Скриншот экрана сохранён.",
    "Система заблокирована.",
    "Проводник открыт.",
    "Калькулятор Фибоначчи запущен.",
    "История чата очищена.",
    "Чат очищен.",
    "Полностью закрываю приложение.",
    "Сворачиваю окно.",
    "Разворачиваю окно.",
    "Восстанавливаю обычный размер окна.",
    "Какое приложение свернуть?",
    "Ollama Server остановлен.",
    "Приложение запущено.",
    "Приложение не запущено.",
    "Ничего не найдено.",
    "Готово.",
    # Фоллбэки протоколов
    "Протокол не опознан, сэр.",
    "Все системы развёрнуты и готовы к работе, сэр.",
    "Диагностика завершена успешно. Приложения готовы к работе.",
    "С возвращением в строй, сэр. Все протоколы инициализированы.",
    "Утренний запуск завершён. Кофе за вами, сэр.",
)


def collect_phrases(*, include_rofl: bool = True, include_latin: bool = False) -> list[str]:
    """Collect unique static phrases from defaults, protocols, and rofl_phrases."""
    raw: list[str] = list(DEFAULT_STATIC_PHRASES) + list(ROUTER_UNKNOWN_RESPONSES)

    for proto in DEFAULT_PROTOCOLS:
        resp = str(proto.get("response_text") or "").strip()
        if resp:
            raw.append(resp)
    raw.append("Режим отдыха активирован. Браузер открыт, приятного времяпрепровождения.")

    if include_rofl:
        for line in rofl_phrases.NORMAL_LINES:
            if "{" not in line:
                raw.append(line)
        for line in rofl_phrases.DEMON_LINES:
            if "{" not in line:
                raw.append(line)
        for ru_lines, lat_lines in rofl_phrases.ROUTER_LINES.values():
            for line in ru_lines:
                if "{" not in line:
                    raw.append(line)
            if include_latin:
                for line in lat_lines:
                    if "{" not in line:
                        raw.append(line)

    seen: set[str] = set()
    unique: list[str] = []
    for item in raw:
        clean = " ".join(str(item).split()).strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            unique.append(clean)
    return unique


def _make_response_key(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"pregen_{digest}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-generate prepared WAV assets with TeraTTS v2.")
    parser.add_argument("--voice", default="teratts:ru_f1", help="TeraTTS voice id (default: teratts:ru_f1)")
    parser.add_argument("--no-rofl", action="store_true", help="Skip rofl_phrases")
    parser.add_argument("--include-latin", action="store_true", help="Include Latin rofl lines")
    parser.add_argument("--overwrite", action="store_true", help="Re-generate even if already in prepared manifest")
    parser.add_argument(
        "--target",
        choices=("bundled", "appdata"),
        default="bundled",
        help="Where to store generated WAVs: bundled (data/tts/assets) or appdata (default: bundled)",
    )
    args = parser.parse_args()

    phrases = collect_phrases(include_rofl=not args.no_rofl, include_latin=args.include_latin)
    assets = AudioAssetManager(root_dir=BUNDLED_TTS_ASSETS_DIR) if args.target == "bundled" else AudioAssetManager()
    backend = TeraTTSBackend(voice_name=args.voice)

    pending = [
        p for p in phrases
        if args.overwrite or assets.find_prepared_audio_for_text(args.voice, p) is None
    ]
    print(f"Total unique phrases: {len(phrases)}, to generate: {len(pending)}, voice: {args.voice}")
    if not pending:
        print("Everything is already generated.")
        return 0

    t_start = time.perf_counter()
    generated = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        for idx, phrase in enumerate(pending, start=1):
            t0 = time.perf_counter()
            try:
                audio, sr = backend.synthesize(phrase)
                if len(audio) == 0:
                    print(f"[{idx}/{len(pending)}] SKIP empty audio: {phrase[:60]}")
                    continue
                wav_path = tmp_root / f"{idx}.wav"
                assets._write_wav_atomic(wav_path, audio, sr)
                assets.register_prepared_file(args.voice, _make_response_key(phrase), wav_path, text=phrase)
                generated += 1
                dt = time.perf_counter() - t0
                if idx == 1 or idx % 25 == 0 or idx == len(pending):
                    elapsed = time.perf_counter() - t_start
                    print(f"[{idx}/{len(pending)}] ok ({dt:.2f}s, total {elapsed:.1f}s): {phrase[:55]}")
            except Exception as exc:
                failed += 1
                print(f"[{idx}/{len(pending)}] ERROR ({exc}): {phrase[:60]}")

    total_sec = time.perf_counter() - t_start
    print(f"Done in {total_sec:.1f}s: generated={generated}, failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
