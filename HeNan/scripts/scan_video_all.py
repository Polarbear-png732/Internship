"""
视频扫描工具 - 完整版
扫描视频文件的时长、大小、MD5，输出与数据库结构一致的CSV文件
依赖：ffprobe（随 ffmpeg 安装）

数据库表结构 video_scan_result:
- source_folder: 来源文件夹
- source_file: 来源文件（剧集名/父文件夹名）
- file_name: 文件名称
- pinyin_abbr: 拼音缩写（如 xcm01）
- duration_seconds: 时长（秒）
- duration_formatted: 时长格式化（HHMMSS000）
- size_bytes: 大小（字节）
- md5: MD5哈希值
"""

import hashlib
import os
import csv
import json
import subprocess
import multiprocessing
import re
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import time

# pypinyin 用于生成拼音缩写
try:
    from pypinyin import lazy_pinyin
    HAS_PYPINYIN = True
except Exception as e: # 捕获所有异常并打印
    print(f"!!! PyPinyin Import Error Details: {e}")
    import traceback
    traceback.print_exc() # 打印完整堆栈
    HAS_PYPINYIN = False
    lazy_pinyin = None
    input("Press Enter to continue...") # 暂停一下让你能看到报错

# ANSI 颜色代码
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


# ============================================================
# 配置区域
# ============================================================

# 输出目录
OUTPUT_DIR = Path("C:/Users/Public/video_scan")

# 支持的视频扩展名（覆盖常见格式）
VIDEO_EXTS = {
    # 常见格式
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".rmvb", ".rm",
    ".ts", ".m2ts", ".mts", ".m4v", ".3gp", ".3g2", ".webm", ".vob", ".asf",
    ".mpg", ".mpeg", ".mpe", ".mpv", ".m2v", ".m4p",
    # 高清/专业格式
    ".mxf", ".dv", ".divx", ".xvid", ".f4v", ".f4p", ".f4a", ".f4b",
    # 其他格式
    ".ogv", ".ogg", ".ogm", ".qt", ".yuv", ".amv", ".svi",
    ".nsv", ".roq", ".bik", ".smk", ".dpg",
}

# 排除的系统文件夹
EXCLUDED_DIRS = {
    "$Recycle.Bin", "System Volume Information", "$RECYCLE.BIN",
    "Windows", "ProgramData", "Recovery"
}

# CSV 表头（与数据库结构一致）
CSV_HEADERS = [
    "source_folder",      # 来源文件夹
    "source_file",        # 来源文件（剧集名）
    "file_name",          # 文件名称
    "pinyin_abbr",        # 拼音缩写
    "duration_seconds",   # 时长（秒）
    "duration_formatted", # 时长格式化
    "size_bytes",         # 大小（字节）
    "md5"                 # MD5哈希值
]

# 扫描模式配置
SCAN_MODES = {
    1: {
        "name": "时长+大小",
        "desc": "适用于河南移动、浙江移动",
        "scan_duration": True,
        "scan_size": True,
        "scan_md5": False
    },
    2: {
        "name": "时长+MD5",
        "desc": "适用于甘肃移动、江西移动",
        "scan_duration": True,
        "scan_size": False,
        "scan_md5": True
    },
    3: {
        "name": "仅时长",
        "desc": "适用于山东移动、新疆电信、江苏新媒体（最快）",
        "scan_duration": True,
        "scan_size": False,
        "scan_md5": False
    },
    4: {
        "name": "全部扫描",
        "desc": "扫描时长、大小、MD5（最完整）",
        "scan_duration": True,
        "scan_size": True,
        "scan_md5": True
    }
}

# 当前扫描模式（运行时设置）
CURRENT_SCAN_MODE = None


# ============================================================
# 工具函数
# ============================================================

def get_pinyin_abbr(name: str) -> str:
    """
    获取名称的拼音首字母缩写
    例如: "熊出没" -> "xcm", "小猪佩奇" -> "xzpq"
    """
    if not HAS_PYPINYIN or not name:
        return ""
    
    # 只取中文和字母
    chars = [c for c in name if '\u4e00' <= c <= '\u9fff' or c.isalpha()]
    if not chars:
        return ""
    
    # 获取拼音首字母
    initials = lazy_pinyin(''.join(chars), style=0)  # style=0 返回普通拼音
    abbr = ''.join(p[0] if p else '' for p in initials)
    return abbr.lower()


def get_episode_pinyin_abbr(file_name: str) -> str:
    """
    从文件名生成拼音缩写
    例如: "熊出没第01集.mp4" -> "xcm01"
          "小猪佩奇第10集.ts" -> "xzpq10"
    """
    # 去掉扩展名
    name_without_ext = os.path.splitext(file_name)[0]
    
    # 尝试匹配 "剧名第XX集" 格式
    match = re.match(r'^(.+?)第(\d+)集', name_without_ext)
    if match:
        drama_name = match.group(1)
        episode_num = match.group(2)
        abbr = get_pinyin_abbr(drama_name)
        if abbr:
            return f"{abbr}{int(episode_num):02d}"
    
    # 如果不匹配，直接返回整个名称的缩写
    return get_pinyin_abbr(name_without_ext)


def get_duration_fast(video_path: Path) -> float:
    """快速获取时长，只读取头部元数据"""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-read_intervals", "%+#1",
            "-print_format", "json",
            "-show_entries", "format=duration",
            str(video_path),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", check=True
        )
        info = json.loads(result.stdout)
        duration = info.get("format", {}).get("duration")
        return float(duration) if duration else 0.0
    except Exception:
        return 0.0


def get_duration_full(video_path: Path) -> float:
    """完整扫描获取时长，用于 TS 等特殊格式"""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(video_path),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", check=True
        )
        info = json.loads(result.stdout)
        duration = info.get("format", {}).get("duration")
        return float(duration) if duration else 0.0
    except Exception:
        return 0.0


def get_duration_seconds(video_path: Path) -> float:
    """获取视频时长（秒），先尝试快速读取，失败则回退到完整扫描"""
    duration = get_duration_fast(video_path)
    if duration == 0.0:
        duration = get_duration_full(video_path)
    return duration


def format_duration(seconds: float) -> str:
    """
    将秒转换为格式化时长：HHMMSS00
    例如: 2648秒 -> "00440800" (44分08秒)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = int(seconds % 60)
    return f"{hours:02d}{minutes:02d}{seconds_part:02d}00"


def get_file_md5(file_path: Path) -> str:
    """计算文件的 MD5 值"""
    md5_hash = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            # 使用 1MB 块大小提升大文件读取效率
            for byte_block in iter(lambda: f.read(1048576), b""):
                md5_hash.update(byte_block)
        return md5_hash.hexdigest()
    except Exception as e:
        print(f"[警告] MD5计算失败: {file_path.name} - {e}")
        return ""


def scan_single_file(args: Tuple[Path, str, str, dict]) -> Dict:
    """
    扫描单个文件，根据模式获取所需信息
    args: (file_path, source_folder, source_file, mode_config)
    优化：ffprobe 和 MD5 计算并行执行
    """
    file_path, source_folder, source_file, mode_config = args
    
    scan_duration = mode_config.get('scan_duration', True)
    scan_size = mode_config.get('scan_size', True)
    scan_md5 = mode_config.get('scan_md5', True)
    
    try:
        # 获取文件大小（很快）
        size_bytes = file_path.stat().st_size if scan_size else 0
        
        # 生成拼音缩写（很快）
        pinyin_abbr = get_episode_pinyin_abbr(file_path.name)
        
        # 根据模式决定是否并行执行
        duration = 0
        duration_formatted = "00000000"
        md5 = ""
        
        if scan_duration and scan_md5:
            # 并行执行 ffprobe 和 MD5 计算
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_duration = executor.submit(get_duration_seconds, file_path)
                future_md5 = executor.submit(get_file_md5, file_path)
                duration = future_duration.result()
                md5 = future_md5.result()
            duration_formatted = format_duration(duration)
        elif scan_duration:
            # 仅扫描时长
            duration = get_duration_seconds(file_path)
            duration_formatted = format_duration(duration)
        elif scan_md5:
            # 仅计算 MD5
            md5 = get_file_md5(file_path)
        
        return {
            "source_folder": source_folder,
            "source_file": source_file,
            "file_name": file_path.name,
            "pinyin_abbr": pinyin_abbr,
            "duration_seconds": round(duration, 2),
            "duration_formatted": duration_formatted,
            "size_bytes": size_bytes,
            "md5": md5,
            "status": "success"
        }
    except Exception as e:
        return {
            "source_folder": source_folder,
            "source_file": source_file,
            "file_name": file_path.name,
            "pinyin_abbr": "",
            "duration_seconds": 0,
            "duration_formatted": "00000000",
            "size_bytes": 0,
            "md5": "",
            "status": f"error: {e}"
        }


def load_existing_records(output_csv: Path) -> Tuple[List[Dict], set]:
    """加载已存在的记录，返回记录列表和已处理的文件唯一标识集合"""
    existing_records = []
    existing_keys = set()
    
    if output_csv.exists():
        print(f"[信息] 检测到已有结果文件: {output_csv}")
        try:
            with open(output_csv, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 去掉 duration_formatted 的制表符前缀（保存时加的）
                    if 'duration_formatted' in row and row['duration_formatted']:
                        row['duration_formatted'] = row['duration_formatted'].lstrip('\t')
                    existing_records.append(row)
                    # 使用 file_name + source_folder 作为唯一标识
                    key = (row.get('file_name', ''), row.get('source_folder', ''))
                    existing_keys.add(key)
            print(f"[信息] 已加载 {len(existing_records)} 条历史记录")
        except Exception as e:
            print(f"[警告] 读取历史记录失败: {e}，将创建新文件")
    
    return existing_records, existing_keys


def save_records(output_csv: Path, records: List[Dict]):
    """保存记录到 CSV 文件，duration_formatted 加前缀防止 Excel 去掉前导零"""
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    
    # 处理记录，给 duration_formatted 加上制表符前缀，防止Excel识别为数字
    processed_records = []
    for record in records:
        new_record = record.copy()
        if 'duration_formatted' in new_record and new_record['duration_formatted']:
            # 加制表符前缀，Excel会将其视为文本
            new_record['duration_formatted'] = '\t' + str(new_record['duration_formatted'])
        processed_records.append(new_record)
    
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(processed_records)


def find_video_files(root_dir: Path) -> List[Tuple[Path, str, str]]:
    """
    递归查找所有视频文件
    返回: [(file_path, source_folder, source_file), ...]
    """
    video_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 排除系统文件夹
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        
        current_dir = Path(dirpath)
        
        for filename in filenames:
            if Path(filename).suffix.lower() in VIDEO_EXTS:
                file_path = current_dir / filename
                
                # 计算 source_folder（相对于扫描根目录的路径）
                try:
                    relative_path = current_dir.relative_to(root_dir)
                    source_folder = str(relative_path) if str(relative_path) != '.' else root_dir.name
                except ValueError:
                    source_folder = str(current_dir)
                
                # source_file 为父文件夹名
                source_file = current_dir.name
                
                video_files.append((file_path, source_folder, source_file))
    
    return video_files


# ============================================================
# 主函数
# ============================================================

def select_scan_mode() -> dict:
    """选择扫描模式"""
    print(f"\n{Colors.CYAN}请选择扫描模式：{Colors.RESET}")
    print(f"{Colors.BLUE}" + "-" * 50 + f"{Colors.RESET}")
    for mode_id, mode_info in SCAN_MODES.items():
        print(f"  {Colors.GREEN}{mode_id}.{Colors.RESET} {Colors.BOLD}{mode_info['name']}{Colors.RESET}")
        print(f"     {Colors.YELLOW}{mode_info['desc']}{Colors.RESET}")
    print(f"{Colors.BLUE}" + "-" * 50 + f"{Colors.RESET}")
    
    while True:
        try:
            choice = input(f"{Colors.CYAN}请输入模式编号 (1-4): {Colors.RESET}").strip()
            mode_id = int(choice)
            if mode_id in SCAN_MODES:
                selected = SCAN_MODES[mode_id]
                print(f"\n{Colors.GREEN}[已选择]{Colors.RESET} {Colors.BOLD}{selected['name']}{Colors.RESET} - {selected['desc']}")
                return selected
            else:
                print(f"{Colors.RED}[错误] 请输入 1-4 之间的数字{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}[错误] 请输入有效的数字{Colors.RESET}")


def main():
    # 显示 pypinyin 警告（仅当未安装时）
    if not HAS_PYPINYIN:
        print(f"{Colors.YELLOW}[警告] 未安装 pypinyin，拼音缩写功能将不可用。可通过 pip install pypinyin 安装{Colors.RESET}")
    
    print(f"{Colors.CYAN}" + "=" * 70 + f"{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}          视频扫描工具 v3.0 - 完整版{Colors.RESET}")
    print(f"{Colors.BOLD}          扫描时长、大小、MD5，输出数据库格式CSV{Colors.RESET}")
    print(f"{Colors.CYAN}" + "=" * 70 + f"{Colors.RESET}")
    print()
    print(f"{Colors.YELLOW}[配置]{Colors.RESET} 输出目录: {Colors.RED}{Colors.BOLD}{OUTPUT_DIR}{Colors.RESET}")
    # 格式列表简化显示（只显示部分）
    common_exts = ['.mp4', '.mkv', '.avi', '.mov', '.ts', '.flv', '.wmv', '.rmvb', '...']
    print(f"{Colors.YELLOW}[配置]{Colors.RESET} 支持格式: {Colors.BLUE}{', '.join(common_exts)}{Colors.RESET} 共{len(VIDEO_EXTS)}种")
    pinyin_status = f"{Colors.GREEN}已启用{Colors.RESET}" if HAS_PYPINYIN else f"{Colors.YELLOW}未启用{Colors.RESET}"
    print(f"{Colors.YELLOW}[配置]{Colors.RESET} 拼音功能: {pinyin_status}")
    print()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_csv = OUTPUT_DIR / "video_scan_result.csv"
    
    # 选择扫描模式
    mode_config = select_scan_mode()
    
    while True:
        try:
            target_folder = input("\n请输入要扫描的视频目录路径，输入 'exit' 退出：").strip()
        except EOFError:
            print("\n未检测到输入，程序退出。")
            break
        
        if not target_folder:
            print("[错误] 目录路径不能为空，请重新输入。")
            continue
        
        # 处理引号
        if (target_folder.startswith('"') and target_folder.endswith('"')) or \
           (target_folder.startswith("'") and target_folder.endswith("'")):
            target_folder = target_folder[1:-1].strip()
        
        if target_folder.lower() == 'exit':
            print("[退出] 程序结束。")
            break
        
        folder = Path(target_folder).expanduser()
        if not folder.exists():
            print(f"[错误] 路径不存在 -> {target_folder}")
            continue
        
        if not folder.is_dir():
            print(f"[错误] 这不是一个目录 -> {target_folder}")
            continue
        
        # 开始扫描
        print(f"\n[扫描] 正在扫描目录: {folder}")
        start_time = time.time()
        
        # 查找所有视频文件
        print("[扫描] 正在查找视频文件...")
        video_files = find_video_files(folder)
        total_files = len(video_files)
        
        if total_files == 0:
            print("[结果] 未发现视频文件，请重新输入目录。")
            continue
        
        print(f"[扫描] 找到 {total_files} 个视频文件")
        
        # 加载已有记录
        print("\n[加载] 正在检查历史记录...")
        existing_records, existing_keys = load_existing_records(output_csv)
        
        # 过滤已处理的文件，并添加 mode_config
        new_files = []
        for file_path, source_folder, source_file in video_files:
            key = (file_path.name, source_folder)
            if key not in existing_keys:
                new_files.append((file_path, source_folder, source_file, mode_config))
        
        skipped_count = total_files - len(new_files)
        if skipped_count > 0:
            print(f"[信息] 跳过 {skipped_count} 个已处理的文件")
        
        if len(new_files) == 0:
            print("[结果] 所有文件都已处理过，无需重复扫描。")
            continue
        
        print(f"\n[处理] 开始扫描 {len(new_files)} 个新文件...")
        
        # 使用多进程处理
        max_workers = min(multiprocessing.cpu_count(), 4)  # MD5计算是IO密集型，不宜太多进程
        print(f"[处理] 使用 {max_workers} 个并行进程")
        
        # 增量保存配置
        SAVE_INTERVAL = 200  # 每处理200个文件保存一次
        last_save_count = 0
        
        results = []
        completed = 0
        success_count = 0
        error_count = 0
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(scan_single_file, args): args[0]
                for args in new_files
            }
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                completed += 1
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['status'] == 'success':
                        success_count += 1
                    else:
                        error_count += 1
                    
                    # 显示进度
                    elapsed = time.time() - start_time
                    speed = completed / elapsed if elapsed > 0 else 0
                    eta = (len(new_files) - completed) / speed if speed > 0 else 0
                    
                    file_name = result['file_name'][:40] + '...' if len(result['file_name']) > 40 else result['file_name']
                    print(f"\r[进度] {completed}/{len(new_files)} ({completed/len(new_files)*100:.1f}%) | "
                          f"速度: {speed:.2f}个/秒 | 剩余: {eta:.0f}秒 | {file_name}      ", end="")
                    
                    # 增量保存：每处理 SAVE_INTERVAL 个文件保存一次
                    if completed - last_save_count >= SAVE_INTERVAL:
                        try:
                            all_records = existing_records + results
                            save_records(output_csv, all_records)
                            last_save_count = completed
                            print(f"\n[自动保存] 已保存 {len(all_records)} 条记录")
                        except Exception as e:
                            print(f"\n[警告] 自动保存失败: {e}")
                    
                except Exception as e:
                    error_count += 1
                    print(f"\n[错误] 处理失败: {file_path.name} - {e}")
        
        print()  # 换行
        
        total_time = time.time() - start_time
        print(f"\n{Colors.GREEN}{Colors.BOLD}[完成]{Colors.RESET} 扫描完成！耗时 {Colors.CYAN}{total_time:.2f}{Colors.RESET} 秒")
        print(f"       - {Colors.GREEN}成功: {success_count} 个{Colors.RESET}")
        if error_count > 0:
            print(f"       - {Colors.RED}失败: {error_count} 个{Colors.RESET}")
        else:
            print(f"       - 失败: {error_count} 个")
        
        # 最终保存（确保所有数据都已保存）
        print(f"\n{Colors.YELLOW}[保存]{Colors.RESET} 正在保存结果到: {Colors.BLUE}{output_csv}{Colors.RESET}")
        try:
            all_records = existing_records + results
            save_records(output_csv, all_records)
            
            print(f"{Colors.GREEN}[成功] 保存完成！{Colors.RESET}")
            print(f"       - 本次新增: {Colors.CYAN}{len(results)}{Colors.RESET} 条")
            print(f"       - 历史记录: {len(existing_records)} 条")
            print(f"       - 总计记录: {Colors.BOLD}{len(all_records)}{Colors.RESET} 条")
            
            # 绿色提示用户查看结果
            print()
            print(f"{Colors.GREEN}{Colors.BOLD}" + "*" * 50 + f"{Colors.RESET}")
            print(f"{Colors.GREEN}{Colors.BOLD}  ✔ 请到输出目录查看结果：{Colors.RESET}")
            print(f"{Colors.GREEN}{Colors.BOLD}    {output_csv}{Colors.RESET}")
            print(f"{Colors.GREEN}{Colors.BOLD}" + "*" * 50 + f"{Colors.RESET}")
            
        except PermissionError:
            print(f"{Colors.RED}[错误] 无法写入文件，请检查 {output_csv} 是否被占用{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}[错误] 保存失败: {e}{Colors.RESET}")
        
        print(f"\n{Colors.CYAN}" + "=" * 70 + f"{Colors.RESET}\n")


if __name__ == "__main__":
    multiprocessing.freeze_support()  # Windows 打包必需
    main()
