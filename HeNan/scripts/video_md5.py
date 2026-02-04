import hashlib
import os
import csv
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def get_file_md5(file_path):
    """计算单个文件的 MD5 值"""
    md5_hash = hashlib.md5()
    try:
        # 增加块大小至 128KB 进一步提升大文件读取效率
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(131072), b""):
                md5_hash.update(byte_block)
        return str(file_path.name), md5_hash.hexdigest(), "成功"
    except Exception as e:
        return str(file_path.name), "", f"错误: {e}"

def main():
    # --- 配置区域 ---
    output_csv = "video_md5_report.csv"
    
    # 扩充后缀名列表
    video_extensions = {
        '.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.rmvb', 
        '.ts', '.m2ts', '.m4v', '.3gp', '.webm', '.vob', '.asf', '.m3u8'
    }
    # ---------------

    while True:
        print("请输入要扫描的视频目录路径（例如：C:/Users/ioeyu/Videos），输入 'exit' 退出：")
        target_folder = input().strip()
        if target_folder.lower() == 'exit':
            print("退出程序。")
            break
        if not target_folder:
            print("错误：目录路径不能为空，请重新输入。")
            continue
        
        folder = Path(target_folder)
        if not folder.exists():
            print(f"错误：路径不存在 -> {target_folder}，请重新输入。")
            continue

        # 递归搜索所有匹配后缀的文件
        video_files = [
            p for p in folder.rglob('*') 
            if p.suffix.lower() in video_extensions and p.is_file()
        ]

        total_files = len(video_files)
        if total_files == 0:
            print("未发现指定格式的视频文件，请重新输入目录。")
            continue

        print(f"共发现 {total_files} 个视频，正在调用多核性能计算...")

        results = []
        # 使用 ProcessPoolExecutor 充分利用多核 CPU
        with ProcessPoolExecutor() as executor:
            # 使用 enumerate 只是为了显示简单的进度提示
            for i, res in enumerate(executor.map(get_file_md5, video_files), 1):
                results.append(res)
                if i % 5 == 0 or i == total_files:
                    print(f"进度: {i}/{total_files} ({(i/total_files)*100:.1f}%)", end='\r')

        # 写入 CSV
        try:
            with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["文件名", "MD5值", "状态"])
                writer.writerows(results)
            
            print(f"\n\n处理完成！结果保存在: {os.path.abspath(output_csv)}")
        except PermissionError:
            print(f"\n\n错误：无法写入 {output_csv}，请检查该文件是否在 Excel 中打开。")
        
        print("\n" + "="*50 + "\n")  # 分隔符

if __name__ == "__main__":
    main()