"""
扫描指定文件夹下的视频，输出时长（秒）、大小（KB/MB）。
依赖：本机已安装 ffprobe（通常随 ffmpeg 安装）。
"""

import json
import subprocess
from pathlib import Path
from typing import Iterable, List, Dict
import pandas as pd

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


def format_duration(seconds: float) -> str:
    """将秒转换为指定格式：021020200表示2小时10分20秒200毫秒"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}{minutes:02d}{seconds_part:02d}{milliseconds:03d}"


def scan_videos(directory: Path) -> List[Dict]:
    """扫描单个目录下的视频文件"""
    rows = []
    for path in directory.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in VIDEO_EXTS:
            continue

        size_bytes = path.stat().st_size
        size_kb = round(size_bytes / 1024, 2)
        size_mb = round(size_kb / 1024, 2)
        duration = get_duration_seconds(path)
        duration_formatted = format_duration(duration)

        rows.append(
            {
                "文件名称": path.name,
                "时长（秒）": round(duration, 2),
                "时长": duration_formatted,
                "大小（b）": size_bytes,
                "大小（kb）": size_kb,
                "大小（mb）": size_mb,
            }
        )
    return rows


def get_display_width(text: str) -> int:
    """计算字符串的显示宽度，中文字符计为2个宽度"""
    width = 0
    for char in str(text):
        # 中文字符、全角字符占用 2 个宽度
        if '\u4e00' <= char <= '\u9fff' or '\uff00' <= char <= '\uffef':
            width += 2
        else:
            width += 1
    return width


def generate_excel(rows: List[Dict], output_path: Path) -> None:
    """生成Excel文件并自动调整列宽，确保列名和内容完整显示"""
    df = pd.DataFrame(rows)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        worksheet = writer.sheets['Sheet1']
        
        # 自动调整列宽
        for column in worksheet.columns:
            max_width = 0
            column_letter = column[0].column_letter
            
            # 计算每个单元格的显示宽度
            for cell in column:
                try:
                    cell_width = get_display_width(cell.value)
                    if cell_width > max_width:
                        max_width = cell_width
                except:
                    pass
            
            # 设置列宽，加上边距，限制最大宽度
            adjusted_width = min(max_width + 4, 80)
            worksheet.column_dimensions[column_letter].width = adjusted_width


def print_table(rows: Iterable[Dict]) -> None:
    """打印表格，确保列名完整显示"""
    # 调整列宽，确保列名能完整显示
    print(f"{'文件名称':30} {'时长（秒）':>12} {'时长':>12} {'大小（b）':>12} {'大小（kb）':>12} {'大小（mb）':>12}")
    for row in rows:
        print(
            f"{row['文件名称'][:30]:30} "
            f"{row['时长（秒）']:12.2f} "
            f"{row['时长']:12} "
            f"{row['大小（b）']:12} "
            f"{row['大小（kb）']:12.2f} "
            f"{row['大小（mb）']:12.2f}"
        )


if __name__ == "__main__":
    # 扫描TARGET_DIR下的所有二级目录
    for subdir in TARGET_DIR.iterdir():
        if not subdir.is_dir():
            continue
        
        print(f"\n正在处理目录: {subdir.name}")
        
        # 扫描当前目录下的视频文件
        rows = scan_videos(subdir)
        
        if not rows:
            print(f"目录 {subdir.name} 下没有找到视频文件")
            continue
        
        # 打印结果
        print_table(rows)
        
        # 生成Excel文件
        excel_path = TARGET_DIR / f"{subdir.name}.xlsx"
        generate_excel(rows, excel_path)
        print(f"Excel文件已生成: {excel_path}")
    
    print("\n所有目录处理完成！")
