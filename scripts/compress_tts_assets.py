"""Convert prepared WAV assets to Ogg/Opus in place (manifest is updated, old WAV removed)."""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from voice.tts.asset_manager import AudioAssetManager, BUNDLED_TTS_ASSETS_DIR, DEFAULT_OPUS_BITRATE, encode_opus


def main() -> int:
    parser = argparse.ArgumentParser(description="Compress prepared TTS WAV assets to Ogg/Opus.")
    parser.add_argument("--target", choices=("bundled", "appdata"), default="bundled",
                        help="bundled (data/tts/assets) or appdata (default: bundled)")
    parser.add_argument("--bitrate", type=int, default=DEFAULT_OPUS_BITRATE, help="Opus bitrate, bit/s (default: 32000)")
    args = parser.parse_args()

    assets = AudioAssetManager(root_dir=BUNDLED_TTS_ASSETS_DIR) if args.target == "bundled" else AudioAssetManager()
    entries = [item for item in assets.list_prepared_audio() if Path(item["path"]).suffix.lower() == ".wav"]
    print(f"WAV assets to compress: {len(entries)} ({assets.root_dir})")

    before = after = failed = 0
    with tempfile.TemporaryDirectory() as tmp_dir:
        for idx, item in enumerate(entries, start=1):
            source = Path(item["path"])
            try:
                size = source.stat().st_size
                ogg = encode_opus(source, Path(tmp_dir) / f"{idx}.ogg", args.bitrate)
                manifest_entry = assets._manifest[assets._prepared_id(item["voice_id"], item["response_key"])]
                text_key, preview = manifest_entry.get("text_key"), manifest_entry.get("text_preview", "")
                target = assets.register_prepared_file(item["voice_id"], item["response_key"], ogg, text=preview or None)
                # register_prepared_file rebuilds text_key from the preview (truncated to 140 chars): keep the original.
                assets._manifest[assets._prepared_id(item["voice_id"], item["response_key"])]["text_key"] = text_key
                before += size
                after += target.stat().st_size
            except Exception as exc:
                failed += 1
                print(f"[{idx}/{len(entries)}] ERROR ({exc}): {source.name}")
            if idx % 50 == 0 or idx == len(entries):
                print(f"[{idx}/{len(entries)}] {before / 2**20:.1f} MB -> {after / 2**20:.1f} MB")
    assets._write_manifest()
    print(f"Done: compressed={len(entries) - failed}, failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
