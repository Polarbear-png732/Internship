"""
Selenium UI 自动化测试运行脚本
运行所有 Selenium 测试并生成报告
"""
import subprocess
import sys
import os
import time
import socket


def check_server_running(host="127.0.0.1", port=8000):
    """检查服务器是否在运行"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0


def start_server():
    """启动 FastAPI 服务器"""
    # 获取项目路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    web_app_dir = os.path.dirname(current_dir)
    venv_python = os.path.join(os.path.dirname(os.path.dirname(web_app_dir)), ".venv", "Scripts", "python.exe")
    
    if not os.path.exists(venv_python):
        print(f"❌ 找不到 Python 解释器: {venv_python}")
        return None
    
    print(f"🚀 正在启动服务器...")
    process = subprocess.Popen(
        [venv_python, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=web_app_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    
    # 等待服务器启动
    for i in range(30):
        time.sleep(1)
        if check_server_running():
            print(f"✅ 服务器启动成功（等待了 {i+1} 秒）")
            return process
        if process.poll() is not None:
            print(f"❌ 服务器启动失败")
            stdout, stderr = process.communicate()
            print(f"stdout: {stdout.decode('utf-8', errors='ignore')}")
            print(f"stderr: {stderr.decode('utf-8', errors='ignore')}")
            return None
    
    print("❌ 服务器启动超时")
    return None


def main():
    """主函数"""
    print("=" * 60)
    print("🧪 Selenium UI 自动化测试")
    print("=" * 60)
    
    # 检查依赖
    try:
        import selenium
        print(f"✅ Selenium 版本: {selenium.__version__}")
    except ImportError:
        print("❌ 请先安装 Selenium:")
        print("   pip install selenium")
        return 1
    
    try:
        import pytest
        print(f"✅ Pytest 版本: {pytest.__version__}")
    except ImportError:
        print("❌ 请先安装 Pytest:")
        print("   pip install pytest")
        return 1
    
    # 检查服务器
    server_process = None
    if check_server_running():
        print("✅ 服务器已在运行 (http://127.0.0.1:8000)")
    else:
        print("⚠️ 服务器未运行，正在启动...")
        server_process = start_server()
        if not server_process:
            print("❌ 无法启动服务器，请手动启动后重试")
            print("   cd web_app1 && python -m uvicorn main:app --reload")
            return 1
    
    print()
    print("=" * 60)
    print("🏃 开始运行测试...")
    print("=" * 60)
    
    # 获取测试目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 运行测试
    pytest_args = [
        "-v",                           # 详细输出
        "-s",                           # 显示 print 输出
        "--tb=short",                   # 简短的错误追踪
        "-x",                           # 遇到第一个错误就停止（可选，调试时有用）
        "--html=selenium_report.html",  # 生成 HTML 报告
        "--self-contained-html",        # 自包含的 HTML 报告
        current_dir,                    # 测试目录
    ]
    
    # 检查是否安装了 pytest-html
    try:
        import pytest_html
        print(f"✅ pytest-html 版本: {pytest_html.__version__}")
    except ImportError:
        print("⚠️ pytest-html 未安装，将不生成 HTML 报告")
        pytest_args = [arg for arg in pytest_args if "html" not in arg]
    
    try:
        result = pytest.main(pytest_args)
    finally:
        # 关闭服务器（如果是我们启动的）
        if server_process:
            print()
            print("🛑 正在关闭服务器...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
                print("✅ 服务器已关闭")
            except subprocess.TimeoutExpired:
                server_process.kill()
                print("⚠️ 强制关闭服务器")
    
    print()
    print("=" * 60)
    if result == 0:
        print("🎉 所有测试通过！")
    else:
        print(f"❌ 测试完成，返回码: {result}")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    sys.exit(main())
