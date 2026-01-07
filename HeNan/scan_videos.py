"""
扫描指定文件夹下的视频，输出时长（秒）、大小（KB/MB）。
依赖：本机已安装 ffprobe（通常随 ffmpeg 安装）。
"""

import json
import subprocess
from pathlib import Path
from typing import Iterable, List, Dict

# 修改为要扫描的视频目录
TARGET_DIR = Path(r"C:\\Users\\ioeyu\\Videos\\OBS")

# 支持的视频扩展名
VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv"}


def get_duration_seconds(video_path: Path) -> float:
    """用 ffprobe 获取视频时长（秒）。失败时返回 0。"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            str(video_path),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=True,  # noqa: S603
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return 0.0


def scan_videos(directory: Path) -> List[Dict[str, float]]:
    rows = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in VIDEO_EXTS:
            continue

        size_bytes = path.stat().st_size
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024
        duration = get_duration_seconds(path)

        rows.append(
            {
                "file": str(path),
                "duration_sec": round(duration, 2),
                "size_kb": round(size_kb, 2),
                "size_mb": round(size_mb, 2),
            }
        )
    return rows


def print_table(rows: Iterable[Dict[str, float]]) -> None:
    print(f"{'File':60} {'Duration(s)':>12} {'Size(KB)':>12} {'Size(MB)':>12}")
    for row in rows:
        print(
            f"{row['file'][:60]:60} "
            f"{row['duration_sec']:12} "
            f"{row['size_kb']:12} "
            f"{row['size_mb']:12}"
        )


if __name__ == "__main__":
    data = scan_videos(TARGET_DIR)
    print_table(data)
