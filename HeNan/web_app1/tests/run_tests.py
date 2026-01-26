"""
测试运行入口脚本
可以直接运行此脚本执行所有测试
"""
import subprocess
import sys
import os

def main():
    # 切换到测试目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("=" * 60)
    print("🧪 Web App 自动化测试")
    print("=" * 60)
    print()
    
    # 检查 pytest 是否安装
    try:
        import pytest
    except ImportError:
        print("❌ pytest 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "httpx"])
        import pytest
    
    # 运行测试
    args = [
        "-v",           # 详细输出
        "--tb=short",   # 简短的错误追踪
        "-s",           # 显示print输出
        "--durations=10",  # 显示最慢的10个测试
    ]
    
    # 如果有命令行参数，追加
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])
    
    exit_code = pytest.main(args)
    
    print()
    print("=" * 60)
    if exit_code == 0:
        print("✅ 所有测试通过！")
    else:
        print(f"❌ 测试失败，退出码: {exit_code}")
    print("=" * 60)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
