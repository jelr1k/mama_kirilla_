from __future__ import annotations

import logging
import time
from typing import Any

import psutil

try:
    import winreg
except ImportError:
    winreg = None

logger = logging.getLogger("jarvis.system")


def _get_cpu_name() -> str:
    if winreg is not None:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
                if name:
                    return name
        except Exception:
            pass
    return "AMD Ryzen Processor"


def _get_gpu_name() -> str:
    if winreg is not None:
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000",
            ) as key:
                name = winreg.QueryValueEx(key, "DriverDesc")[0].strip()
                if name:
                    return name
        except Exception:
            pass
    return "AMD Radeon RX 6500 XT"


def get_system_telemetry(**_kwargs: Any) -> dict[str, Any]:
    """Возвращает информацию о текущей нагрузке и ресурсах ПК."""
    try:
        cpu_pct = psutil.cpu_percent(interval=0.05)
        vm = psutil.virtual_memory()
        boot = psutil.boot_time()
        uptime_secs = int(max(0, time.time() - boot))
        hours, mins = divmod(uptime_secs // 60, 60)

        cpu_name = _get_cpu_name()
        gpu_name = _get_gpu_name()

        disks = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                free_gb = round(usage.free / (1024 ** 3), 1)
                total_gb = round(usage.total / (1024 ** 3), 1)
                mp = partition.mountpoint.rstrip("\\")
                disks.append(f"{mp} ({free_gb} ГБ свободно из {total_gb} ГБ)")
            except (PermissionError, OSError):
                continue

        ram_used_gb = round(vm.used / (1024 ** 3), 1)
        ram_total_gb = round(vm.total / (1024 ** 3), 1)
        proc_count = len(psutil.pids())

        lines = [
            "Состояние системы:",
            f"• Процессор: {cpu_name} (загрузка: {cpu_pct}%)",
            f"• Видеокарта: {gpu_name}",
            f"• Оперативная память: {ram_used_gb} / {ram_total_gb} ГБ ({vm.percent}%)",
        ]
        if disks:
            lines.append(f"• Диски: {', '.join(disks)}")
        lines.append(f"• Аптайм: {hours} ч. {mins} мин. (процессов: {proc_count})")

        content = "\n".join(lines)
        return {
            "success": True,
            "system_telemetry": True,
            "content": content,
            "cpu_percent": cpu_pct,
            "cpu_name": cpu_name,
            "gpu_name": gpu_name,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
            "ram_percent": vm.percent,
            "uptime_hours": hours,
            "uptime_minutes": mins,
            "process_count": proc_count,
        }
    except Exception as exc:
        logger.exception("get_system_telemetry_failed")
        return {
            "success": False,
            "error": f"Не удалось получить телеметрию системы: {exc}",
        }
