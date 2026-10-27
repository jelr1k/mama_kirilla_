from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import time
from typing import Any
import winreg

import psutil

logger = logging.getLogger("jarvis.steam")

# \u0411\u0430\u0437\u043e\u0432\u044b\u0435 \u0430\u043b\u0438\u0430\u0441\u044b \u0434\u043b\u044f \u043f\u043e\u043f\u0443\u043b\u044f\u0440\u043d\u044b\u0445 \u0438\u0433\u0440
COMMON_GAME_ALIASES: dict[str, list[str]] = {
    "730": [
        "cs", "cs2", "csgo", "cs go", "counter strike", "counter-strike",
        "\u043a\u0441", "\u043a\u04412", "\u043a\u0441 2", "\u043a\u0441 \u0433\u043e",
        "\u043a\u0441\u043e\u0447\u043a\u0430", "\u043a\u0441\u043e\u0447\u043a\u0443",
        "\u043a\u043e\u043d\u0442\u0440\u0430", "\u043a\u043e\u043d\u0442\u0440\u0443",
        "\u043a\u043e\u043d\u0442\u0440 \u0441\u0442\u0440\u0430\u0439\u043a",
    ],
    "570": [
        "dota", "dota2", "dota 2",
        "\u0434\u043e\u0442\u0430", "\u0434\u043e\u0442\u0443", "\u0434\u043e\u0442\u043a\u0430",
        "\u0434\u043e\u0442\u043a\u0443", "\u0434\u043e\u0442\u0430 2", "\u0434\u043e\u0442\u0443 2",
    ],
    "1091500": [
        "cyberpunk", "cyberpunk 2077",
        "\u043a\u0438\u0431\u0435\u0440\u043f\u0430\u043d\u043a", "\u043a\u0438\u0431\u0435\u0440\u043f\u0430\u043d\u043a 2077",
    ],
    "292030": [
        "witcher", "witcher 3", "the witcher 3",
        "\u0432\u0435\u0434\u044c\u043c\u0430\u043a", "\u0432\u0435\u0434\u044c\u043c\u0430\u043a\u0430",
        "\u0432\u0435\u0434\u044c\u043c\u0430\u043a 3",
    ],
    "271590": [
        "gta", "gta 5", "gta v", "gta5",
        "\u0433\u0442\u0430", "\u0433\u0442\u0430 5", "\u0433\u0442\u04305", "\u0433\u0442\u0430 \u0432",
    ],
    "252490": [
        "rust", "\u0440\u0430\u0441\u0442",
    ],
    "578080": [
        "pubg", "pubg battlegrounds", "\u043f\u0430\u0431\u0433", "\u043f\u0443\u0431\u0433",
    ],
    "1172470": [
        "apex", "apex legends", "\u0430\u043f\u0435\u043a\u0441",
    ],
    "359550": [
        "r6", "rainbow six", "siege", "\u0440\u0430\u0434\u0443\u0433\u0430", "\u0440\u0430\u0434\u0443\u0433\u0443", "\u0441\u0438\u0434\u0436",
    ],
    "892970": [
        "valheim", "\u0432\u0430\u043b\u0445\u0435\u0439\u043c",
    ],
    "105600": [
        "terraria", "\u0442\u0435\u0440\u0440\u0430\u0440\u0438\u044f", "\u0442\u0435\u0440\u0440\u0430\u0440\u0438\u044e",
    ],
    "489830": [
        "skyrim", "\u0441\u043a\u0430\u0439\u0440\u0438\u043c",
    ],
}

# \u0421\u043b\u0443\u0436\u0435\u0431\u043d\u044b\u0435 \u043f\u0430\u043a\u0435\u0442\u044b Steam, \u043a\u043e\u0442\u043e\u0440\u044b\u0435 \u043d\u0435 \u044f\u0432\u043b\u044f\u044e\u0442\u0441\u044f \u0438\u0433\u0440\u0430\u043c\u0438
IGNORED_STEAM_APPIDS = {
    228980,  # Steamworks Common Redistributables
    228990,
    1070560, # Steam Linux Runtime
    1391110,
    1628350,
}


class SteamManager:
    """\u0411\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u044b\u0439 \u043c\u0435\u043d\u0435\u0434\u0436\u0435\u0440 \u0434\u043b\u044f \u0440\u0430\u0431\u043e\u0442\u044b \u0441 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u043d\u044b\u043c\u0438 \u0438\u0433\u0440\u0430\u043c\u0438 Steam.

    \u041f\u0420\u0418\u041d\u0426\u0418\u041f\u042b \u0411\u0415\u0417\u041e\u041f\u0410\u0421\u041d\u041e\u0421\u0422\u0418:
    1. \u0421\u0442\u0440\u043e\u0433\u0438\u0439 Read-Only: \u043d\u0438 \u043f\u0440\u0438 \u043a\u0430\u043a\u0438\u0445 \u0443\u0441\u043b\u043e\u0432\u0438\u044f\u0445 \u043d\u0435 \u043c\u043e\u0434\u0438\u0444\u0438\u0446\u0438\u0440\u0443\u0435\u0442,
       \u043d\u0435 \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u044b\u0432\u0430\u0435\u0442 \u0438 \u043d\u0435 \u0443\u0434\u0430\u043b\u044f\u0435\u0442 \u0444\u0430\u0439\u043b\u044b Steam \u0438 \u0438\u0433\u0440.
    2. \u0422\u043e\u043b\u044c\u043a\u043e \u0440\u0435\u0430\u043b\u044c\u043d\u043e \u0441\u043a\u0430\u0447\u0430\u043d\u043d\u044b\u0435 \u0438\u0433\u0440\u044b: \u043f\u0440\u043e\u0432\u0435\u0440\u044f\u044e\u0442\u0441\u044f StateFlags \u0438
       \u0444\u0438\u0437\u0438\u0447\u0435\u0441\u043a\u043e\u0435 \u043d\u0430\u043b\u0438\u0447\u0438\u0435 \u043f\u0430\u043f\u043a\u0438 \u0438\u0433\u0440\u044b \u0432 steamapps/common.
    3. \u0411\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u044b\u0439 \u0437\u0430\u043f\u0443\u0441\u043a: \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442\u0441\u044f \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u044b\u0439 URL-протокол Windows
       steam://rungameid/<appid> \u0441 \u0436\u0451\u0441\u0442\u043a\u043e\u0439 \u0432\u0430\u043b\u0438\u0434\u0430\u0446\u0438\u0435\u0439 \u0447\u0438\u0441\u043b\u043e\u0432\u043e\u0433\u043e AppID.
    """

    _instance: SteamManager | None = None

    def __init__(self, event_bus=None, steam_root: Path | None = None):
        self.event_bus = event_bus
        self._custom_steam_root = steam_root
        self._cached_games: list[dict[str, Any]] = []
        self._last_scan_time: float = 0.0
        self._scan_ttl: float = 60.0  # \u041a\u044d\u0448 \u043d\u0430 60 \u0441\u0435\u043a\u0443\u043d\u0434
        SteamManager._instance = self

    @classmethod
    def get_instance(cls) -> SteamManager:
        if cls._instance is None:
            cls._instance = SteamManager()
        return cls._instance

    # --- \u041f\u043e\u0438\u0441\u043a \u0438 \u0441\u043a\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 Steam ---

    def find_steam_root(self) -> Path | None:
        """\u0411\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u043e \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u044f\u0435\u0442 \u043a\u0430\u0442\u0430\u043b\u043e\u0433 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0438 Steam \u0447\u0435\u0440\u0435\u0437 \u0440\u0435\u0435\u0441\u0442\u0440 Windows."""
        if self._custom_steam_root and self._custom_steam_root.is_dir():
            return self._custom_steam_root

        # 1. \u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0440\u0435\u0435\u0441\u0442\u0440\u0430 Windows (HKCU \u0438 HKLM)
        for root_key in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for sub_key in (r"Software\Valve\Steam", r"Software\Wow6432Node\Valve\Steam"):
                try:
                    with winreg.OpenKey(root_key, sub_key) as k:
                        val, _ = winreg.QueryValueEx(k, "SteamPath")
                        if val:
                            p = Path(str(val).replace("/", "\\"))
                            if p.is_dir():
                                return p
                except (OSError, WindowsError):
                    pass

        # 2. \u0422\u0438\u043f\u043e\u0432\u044b\u0435 \u043f\u0443\u0442\u0438 \u043d\u0430 \u0434\u0438\u0441\u043a\u0430\u0445
        for candidate in (
            r"C:\Program Files (x86)\Steam",
            r"C:\Steam",
            r"D:\Steam",
            r"E:\Steam",
            r"D:\rzz\steam",
        ):
            p = Path(candidate)
            if p.is_dir():
                return p

        return None

    def get_library_folders(self) -> list[Path]:
        """\u041d\u0430\u0445\u043e\u0434\u0438\u0442 \u0432\u0441\u0435 \u043f\u0430\u043f\u043a\u0438 \u0431\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a Steam (libraryfolders.vdf)."""
        steam_root = self.find_steam_root()
        if not steam_root:
            return []

        libraries = [steam_root]
        vdf_path = steam_root / "steamapps" / "libraryfolders.vdf"
        if vdf_path.is_file():
            try:
                with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                # \u041f\u0430\u0440\u0441\u0438\u043c "path" "<path>"
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith('"path"'):
                        parts = line.split('"')
                        if len(parts) >= 4:
                            raw_p = parts[3].replace("\\\\", "\\")
                            lp = Path(raw_p)
                            if lp.is_dir() and lp not in libraries:
                                libraries.append(lp)
            except Exception as exc:
                logger.debug("libraryfolders_vdf_read_error: %s", exc)

        return libraries

    def scan_installed_games(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """\u0421\u043a\u0430\u043d\u0438\u0440\u0443\u0435\u0442 \u0442\u043e\u043b\u044c\u043a\u043e \u0444\u0430\u043a\u0442\u0438\u0447\u0435\u0441\u043a\u0438 \u0441\u043a\u0430\u0447\u0430\u043d\u043d\u044b\u0435 \u0438 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u043d\u044b\u0435 \u0438\u0433\u0440\u044b Steam."""
        now = time.time()
        if not force_refresh and self._cached_games and (now - self._last_scan_time < self._scan_ttl):
            return list(self._cached_games)

        games: list[dict[str, Any]] = []
        libraries = self.get_library_folders()

        for lib in libraries:
            steamapps = lib / "steamapps"
            if not steamapps.is_dir():
                continue

            try:
                manifest_files = list(steamapps.glob("appmanifest_*.acf"))
            except Exception:
                continue

            for acf in manifest_files:
                try:
                    with open(acf, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()

                    appid_m = re.search(r'"appid"\s+"(\d+)"', text)
                    name_m = re.search(r'"name"\s+"([^"]+)"', text)
                    dir_m = re.search(r'"installdir"\s+"([^"]+)"', text)
                    flags_m = re.search(r'"StateFlags"\s+"(\d+)"', text)

                    if not (appid_m and name_m):
                        continue

                    appid = int(appid_m.group(1))
                    if appid in IGNORED_STEAM_APPIDS:
                        continue

                    name = name_m.group(1).strip()
                    installdir_name = dir_m.group(1).strip() if dir_m else ""
                    flags = int(flags_m.group(1)) if flags_m else 0

                    game_path = steamapps / "common" / installdir_name
                    # \u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430: StateFlags 4 (StateFullyInstalled) \u0418 \u043d\u0430\u043b\u0438\u0447\u0438\u0435 \u043f\u0430\u043f\u043a\u0438
                    is_ready = bool((flags & 4 != 0) or (installdir_name and game_path.is_dir()))
                    if not is_ready:
                        continue

                    games.append({
                        "appid": appid,
                        "name": name,
                        "clean_name": self._clean_game_name(name),
                        "installdir": str(game_path) if game_path.is_dir() else str(steamapps),
                        "launch_url": f"steam://rungameid/{appid}",
                        "state_flags": flags,
                    })
                except Exception as exc:
                    logger.debug("acf_read_error file=%s error=%s", acf, exc)

        # \u0421\u043e\u0440\u0442\u0438\u0440\u0443\u0435\u043c \u043f\u043e \u0438\u043c\u0435\u043d\u0438
        games.sort(key=lambda g: g["name"].lower())
        self._cached_games = games
        self._last_scan_time = now
        logger.info("steam_games_scanned count=%d", len(games))
        return list(games)

    @classmethod
    def _clean_game_name(cls, name: str) -> str:
        cleaned = re.sub(r"[\u2122\u00ae\u00a9]+|\b(?:Edition|Goty|Game of the Year)\b", "", name, flags=re.IGNORECASE)
        cleaned = re.sub(r"[^\w\s]+", " ", cleaned)
        return " ".join(cleaned.lower().split())

    # --- \u041f\u043e\u0438\u0441\u043a \u0438 \u0440\u0430\u0437\u0440\u0435\u0448\u0435\u043d\u0438\u0435 \u0438\u0433\u0440\u044b ---

    def resolve_game(self, query: str) -> dict[str, Any] | None:
        """Находит установленную игру Steam по названию, AppID или алиасу."""
        q_raw = str(query).strip().lower()
        if not q_raw or q_raw in ("steam", "стим", "steam.exe", "стим.exe", "клиент steam", "стим клиент"):
            return None

        # \u0415\u0441\u043b\u0438 \u043f\u0435\u0440\u0435\u0434\u0430\u043d steam:<appid> \u0438\u043b\u0438 steam://rungameid/<appid>
        if q_raw.startswith("steam:"):
            appid_str = q_raw.split(":")[-1].strip()
            if appid_str.isdigit():
                return self.get_game_by_appid(int(appid_str))
        if "rungameid/" in q_raw:
            appid_str = q_raw.split("rungameid/")[-1].strip().split("/")[0]
            if appid_str.isdigit():
                return self.get_game_by_appid(int(appid_str))

        games = self.scan_installed_games()
        if not games:
            return None

        # 1. \u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043f\u043e \u043f\u0440\u044f\u043c\u043e\u043c\u0443 AppID
        if q_raw.isdigit():
            aid = int(q_raw)
            for g in games:
                if g["appid"] == aid:
                    return dict(g)

        # 2. \u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043f\u043e \u0431\u0430\u0437\u0435 \u043f\u043e\u043f\u0443\u043b\u044f\u0440\u043d\u044b\u0445 \u0430\u043b\u0438\u0430\u0441\u043e\u0432 (COMMON_GAME_ALIASES)
        norm_q = self._clean_game_name(q_raw)
        for appid_str, aliases in COMMON_GAME_ALIASES.items():
            if norm_q in aliases or q_raw in aliases:
                aid = int(appid_str)
                for g in games:
                    if g["appid"] == aid:
                        return dict(g)

        # 3. \u0422\u043e\u0447\u043d\u043e\u0435 \u0441\u043e\u0432\u043f\u0430\u0434\u0435\u043d\u0438\u0435 \u043f\u043e \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u044e
        for g in games:
            if g["clean_name"] == norm_q or g["name"].lower() == q_raw:
                return dict(g)

        # 4. Подстрока / начало слова
        if len(norm_q) >= 3 and norm_q not in ("steam", "стим", "game", "игра"):
            for g in games:
                if norm_q in g["clean_name"] or g["clean_name"].startswith(norm_q):
                    return dict(g)

        # 5. Попытка совпадения по отдельным словам
        q_words = [w for w in norm_q.split() if len(w) >= 3 and w not in ("steam", "стим", "game", "игра")]
        if q_words:
            for g in games:
                g_words = g["clean_name"].split()
                if all(any(qw in gw for gw in g_words) for qw in q_words):
                    return dict(g)

        return None

    def get_game_by_appid(self, appid: int) -> dict[str, Any] | None:
        for g in self.scan_installed_games():
            if g["appid"] == appid:
                return dict(g)
        return None

    # --- \u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0437\u0430\u043f\u0443\u0441\u043a\u0430 \u0438 \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u044b\u0439 \u0441\u0442\u0430\u0440\u0442 ---

    def is_game_running(self, game_or_appid: dict[str, Any] | int | str) -> bool:
        """\u041f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u0442, \u0437\u0430\u043f\u0443\u0449\u0435\u043d \u043b\u0438 \u043f\u0440\u043e\u0446\u0435\u0441\u0441 \u0434\u0430\u043d\u043d\u043e\u0439 \u0438\u0433\u0440\u044b \u0432 Windows."""
        game = None
        if isinstance(game_or_appid, dict):
            game = game_or_appid
        elif isinstance(game_or_appid, int) or str(game_or_appid).isdigit():
            game = self.get_game_by_appid(int(game_or_appid))
        else:
            game = self.resolve_game(str(game_or_appid))

        if not game:
            return False

        installdir = game.get("installdir", "")
        folder_name = Path(installdir).name.lower() if installdir else ""
        clean_name = game.get("clean_name", "").lower()

        # Проверяем запущенные процессы
        for proc in psutil.process_iter(["pid", "name", "exe", "cwd"]):
            try:
                exe = (proc.info.get("exe") or "").lower()
                cwd = (proc.info.get("cwd") or "").lower()
                name = (proc.info.get("name") or "").lower()

                # Если полный путь или имя папки игры содержится в exe или cwd процесса
                if (installdir and installdir.lower() in exe) or (folder_name and folder_name in exe) or (folder_name and folder_name in cwd):
                    return True
                # Или если имя exe совпадает с именем игры
                if clean_name and (name.replace(".exe", "") in clean_name):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return False

    def launch_game(self, game_or_appid: dict[str, Any] | int | str) -> dict[str, Any]:
        """\u0411\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u043e \u0438\u043d\u0438\u0446\u0438\u0438\u0440\u0443\u0435\u0442 \u0437\u0430\u043f\u0443\u0441\u043a \u0438\u0433\u0440\u044b \u0447\u0435\u0440\u0435\u0437 \u043e\u0444\u0438\u0446\u0438\u0430\u043b\u044c\u043d\u044b\u0439 Steam URI."""
        game = None
        if isinstance(game_or_appid, dict):
            game = game_or_appid
        elif isinstance(game_or_appid, int) or str(game_or_appid).isdigit():
            game = self.get_game_by_appid(int(game_or_appid))
        else:
            game = self.resolve_game(str(game_or_appid))

        if not game:
            return {"success": False, "error": f"\u0418\u0433\u0440\u0430 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430 \u0441\u0440\u0435\u0434\u0438 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u043d\u044b\u0445 \u0432 Steam: {game_or_appid}"}

        appid = game.get("appid")
        if not appid or not str(appid).isdigit():
            return {"success": False, "error": "\u041d\u0435\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u044b\u0439 AppID \u0438\u0433\u0440\u044b."}

        # \u0411\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u044b\u0439 URL-протокол: steam://rungameid/<appid>
        url = f"steam://rungameid/{appid}"
        logger.info("launching_steam_game name=%r appid=%s url=%s", game.get("name"), appid, url)

        try:
            os.startfile(url)
            if self.event_bus:
                self.event_bus.emit("steam.game_launched", game)
            return {
                "success": True,
                "name": game.get("name"),
                "appid": appid,
                "url": url,
            }
        except Exception as exc:
            logger.exception("steam_launch_failed url=%s", url)
            return {"success": False, "error": f"\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u043f\u0443\u0441\u043a\u0430 Steam: {exc}"}
