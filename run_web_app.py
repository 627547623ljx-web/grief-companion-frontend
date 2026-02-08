"""
启动情感支持聊天机器人Web应用
"""
import os
import sys
import subprocess
import threading
import time
import webbrowser


def install_dependencies():
    """安装项目依赖"""
    print("正在检查并安装项目依赖...")
    
    try:
        import flask
        import gradio
        import numpy
        print("依赖已存在，无需安装")
    except ImportError:
        print("正在安装依赖包...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("依赖安装完成")


def start_flask_app():
    """启动Flask应用"""
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_app"))
    subprocess.check_call([sys.executable, "app.py"])


def open_browser():
    """在浏览器中打开应用"""
    time.sleep(3)  # 等待服务器启动
    print("正在打开浏览器...")
    webbrowser.open("http://localhost:5000")


def main():
    print("="*60)
    print("正在启动情感支持聊天机器人Web应用...")
    print("="*60)
    
    # 安装依赖
    install_dependencies()
    
    # 在新线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    print("\n应用将在 http://localhost:5000 上运行")
    print("请在浏览器中查看应用")
    print("按 Ctrl+C 停止服务器\n")
    
    # 启动Flask应用
    start_flask_app()


if __name__ == "__main__":
    main()