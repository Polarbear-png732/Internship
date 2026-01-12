"""
扫描指定文件夹下的视频，输出时长（秒）、大小（B/KB/MB）。
依赖：本机已安装 ffprobe（通常随 ffmpeg 安装）。
单线程顺序扫描，适合机械硬盘。
"""

import json
import subprocess
from pathlib import Path
from typing import List, Dict
import pandas as pd
import os
import time

# 输出Excel文件的目录
OUTPUT_DIR = Path(r"D:\ScanVideo\Result")

# 支持的视频扩展名
VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv", ".ts", ".m4v", ".webm", ".mpg", ".mpeg", ".3gp", ".rm", ".rmvb"}

# 排除的系统文件夹
EXCLUDED_DIRS = {"$Recycle.Bin", "System Volume Information", "$RECYCLE.BIN", "Windows", "ProgramData", "Recovery"}


def get_duration_fast(video_path: Path) -> float:
    """快速获取时长，只读取头部元数据。"""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-read_intervals", "%+#1",
            "-print_format", "json",
            "-show_entries", "format=duration",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", check=True)
        info = json.loads(result.stdout)
        duration = info.get("format", {}).get("duration")
        return float(duration) if duration else 0.0
    except Exception:
        return 0.0


def get_duration_full(video_path: Path) -> float:
    """完整扫描获取时长，用于 TS 等特殊格式。"""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", check=True)
        info = json.loads(result.stdout)
        duration = info.get("format", {}).get("duration")
        return float(duration) if duration else 0.0
    except Exception:
        return 0.0


def get_duration_seconds(video_path: Path) -> float:
    """获取视频时长（秒）。先尝试快速读取，失败则回退到完整扫描。"""
    duration = get_duration_fast(video_path)
    if duration == 0.0:
        duration = get_duration_full(video_path)
    return duration


def format_duration(seconds: float) -> str:
    """将秒转换为指定格式：021020200表示2小时10分20秒200毫秒"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}{minutes:02d}{seconds_part:02d}{milliseconds:03d}"


def get_display_width(text: str) -> int:
    """计算字符串的显示宽度，中文字符计为2个宽度"""
    width = 0
    for char in str(text):
        if '\u4e00' <= char <= '\u9fff' or '\uff00' <= char <= '\uffef':
            width += 2
        else:
            width += 1
    return width


def scan_videos(directory: Path) -> List[Dict]:
    """顺序扫描目录下的视频文件"""
    video_files = sorted([
        p for p in directory.iterdir() 
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    ], key=lambda x: x.name)
    
    rows = []
    for vf in video_files:
        size_bytes = vf.stat().st_size
        size_kb = round(size_bytes / 1024, 2)
        size_mb = round(size_kb / 1024, 2)
        duration = get_duration_seconds(vf)
        duration_formatted = format_duration(duration)
        
        rows.append({
            "文件名称": vf.name,
            "时长（秒）": round(duration, 2),
            "时长": duration_formatted,
            "大小（b）": size_bytes,
            "大小（kb）": size_kb,
            "大小（mb）": size_mb,
        })
    
    return rows


def generate_excel(rows: List[Dict], output_path: Path) -> None:
    """生成Excel文件并自动调整列宽"""
    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        worksheet = writer.sheets['Sheet1']
        
        for column in worksheet.columns:
            max_width = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    cell_width = get_display_width(cell.value)
                    if cell_width > max_width:
                        max_width = cell_width
                except:
                    pass
            worksheet.column_dimensions[column_letter].width = min(max_width + 4, 80)


def find_video_folders(root_dir: Path) -> List[Path]:
    """递归查找所有包含视频文件的文件夹，排除系统文件夹"""
    video_folders = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 排除系统文件夹（修改 dirnames 会影响 os.walk 的递归）
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        
        current_dir = Path(dirpath)
        if any(Path(f).suffix.lower() in VIDEO_EXTS for f in filenames):
            video_folders.append(current_dir)
    return video_folders


def get_relative_output_path(video_folder: Path, root_dir: Path, output_dir: Path) -> Path:
    """计算输出Excel文件的路径，保持原有目录结构，包含盘符"""
    drive = video_folder.drive.replace(":", "")
    relative_path = video_folder.relative_to(root_dir)
    return output_dir / drive / relative_path.parent / f"{video_folder.name}.xlsx"


def main():
    print("=" * 60)
    print("视频扫描工具 (ffprobe 单线程版)")
    print("=" * 60)
    print()
    print(f"输出目录: {OUTPUT_DIR}")
    print("输入 exit 退出程序")
    print()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    while True:
        input_path = input("请输入要扫描的目录路径（如 F:，输入 exit 退出）: ").strip()
        
        if input_path.lower() == 'exit':
            print("程序退出")
            break
        
        if not input_path:
            print("路径不能为空，请重新输入\n")
            continue
        
        target_dir = Path(input_path)
        
        if not target_dir.exists():
            print(f"目录不存在: {target_dir}，请重新输入\n")
            continue
        
        if not target_dir.is_dir():
            print(f"这不是一个目录: {target_dir}，请重新输入\n")
            continue
        
        print(f"\n开始扫描: {target_dir}\n")
        start_time = time.time()
        
        print("正在查找视频文件夹...")
        video_folders = find_video_folders(target_dir)
        print(f"找到 {len(video_folders)} 个包含视频的文件夹\n")
        
        if not video_folders:
            print("没有找到任何视频文件夹\n")
            continue
        
        success_count = 0
        fail_count = 0
        total = len(video_folders)
        
        for i, folder in enumerate(video_folders, 1):
            print(f"[{i}/{total}] 正在处理: {folder}")
            rows = scan_videos(folder)
            
            if not rows:
                print(f"  - 没有找到视频文件，跳过")
                fail_count += 1
                continue
            
            output_path = get_relative_output_path(folder, target_dir, OUTPUT_DIR)
            
            try:
                generate_excel(rows, output_path)
                print(f"  - 找到 {len(rows)} 个视频，Excel已生成: {output_path}")
                success_count += 1
            except Exception as e:
                print(f"  - 生成Excel失败: {e}")
                fail_count += 1
        
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = elapsed_time % 60
        
        print()
        print("=" * 60)
        print(f"本次扫描完成！成功: {success_count}, 跳过/失败: {fail_count}")
        print(f"扫描耗时: {minutes}分{seconds:.2f}秒")
        print(f"结果保存在: {OUTPUT_DIR}")
        print("=" * 60)
        print()


if __name__ == "__main__":
    main()
