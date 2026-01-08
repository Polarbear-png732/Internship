import os
import requests  # 需要安装: pip install requests

# 配置需要下载的资源
# 注意：Tailwind CDN 版本质上是 JS 脚本，而非 CSS 文件
assets = [
    {
        "url": "https://cdn.tailwindcss.com",
        "filename": "tailwindcss.js", 
        "folder": "static"
    },
    {
        "url": "https://unpkg.com/vue@3/dist/vue.global.js",
        "filename": "vue.global.js",
        "folder": "static"
    }
]

def main():
    print("🚀 开始下载静态资源...")

    # 获取当前脚本所在的绝对目录 (web_app1 目录)
    # 这样无论你在哪里运行命令，都能准确找到 static 目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

    for asset in assets:
        # 拼接绝对路径：当前脚本目录 + static
        target_folder = os.path.join(base_dir, asset["folder"])

        # 创建目录
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
            
        file_path = os.path.join(target_folder, asset["filename"])
        print(f"正在下载: {asset['filename']} ...")
        
        try:
            # 添加 User-Agent 防止被某些 CDN 拦截
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            
            # 使用 requests 发送 GET 请求
            # timeout=10 防止网络卡死
            response = requests.get(asset["url"], headers=headers, timeout=10)
            
            # 检查 HTTP 状态码，如果有错误(如404, 500)会抛出异常
            response.raise_for_status()
            
            # 写入文件
            with open(file_path, 'wb') as out_file:
                out_file.write(response.content)
                
            print(f"✅ 已保存: {file_path}")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求错误 {asset['filename']}: {e}")
        except Exception as e:
            print(f"❌ 文件保存错误 {asset['filename']}: {e}")

    print("\n✨ 下载完成！请更新您的 HTML 文件引用路径。")

if __name__ == "__main__":
    main()