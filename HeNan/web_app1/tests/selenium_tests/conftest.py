"""
Selenium UI 自动化测试配置文件
提供 WebDriver 初始化、浏览器设置、页面对象等共享 fixture
"""
import pytest
import time
import subprocess
import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# 测试配置
class TestConfig:
    """测试配置"""
    BASE_URL = "http://127.0.0.1:8000"
    IMPLICIT_WAIT = 10  # 隐式等待时间（秒）
    EXPLICIT_WAIT = 15  # 显式等待时间（秒）
    PAGE_LOAD_TIMEOUT = 30  # 页面加载超时时间（秒）
    HEADLESS = False  # 是否使用无头模式（True=不显示浏览器窗口）
    BROWSER = "edge"  # 浏览器类型: "chrome" 或 "edge"
    WINDOW_SIZE = (1920, 1080)  # 浏览器窗口大小


class ServerManager:
    """FastAPI 服务器管理器"""
    
    def __init__(self):
        self.process = None
        self.started = False
    
    def start(self):
        """启动 FastAPI 服务器"""
        if self.started:
            return
        
        # 检查服务器是否已在运行
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8000))
        sock.close()
        
        if result == 0:
            print("✓ 服务器已在运行")
            self.started = True
            return
        
        # 启动服务器
        web_app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        venv_python = os.path.join(
            os.path.dirname(os.path.dirname(web_app_dir)), 
            ".venv", "Scripts", "python.exe"
        )
        
        print(f"正在启动服务器... (使用 {venv_python})")
        
        self.process = subprocess.Popen(
            [venv_python, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=web_app_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )
        
        # 等待服务器启动
        max_retries = 30
        for i in range(max_retries):
            time.sleep(1)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 8000))
            sock.close()
            if result == 0:
                print(f"✓ 服务器启动成功（等待了 {i+1} 秒）")
                self.started = True
                return
        
        raise RuntimeError("服务器启动超时")
    
    def stop(self):
        """停止 FastAPI 服务器"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            print("✓ 服务器已停止")


# 全局服务器管理器实例
_server_manager = ServerManager()


@pytest.fixture(scope="session")
def server():
    """会话级别的服务器 fixture"""
    _server_manager.start()
    yield _server_manager
    # 注意：不自动停止服务器，因为可能是外部启动的


@pytest.fixture(scope="class")
def driver(server):
    """
    创建 WebDriver 实例
    同一个测试类共享一个浏览器实例，减少频繁打开关闭
    """
    if TestConfig.BROWSER.lower() == "chrome":
        options = ChromeOptions()
        if TestConfig.HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"--window-size={TestConfig.WINDOW_SIZE[0]},{TestConfig.WINDOW_SIZE[1]}")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        driver = webdriver.Chrome(options=options)
    else:
        # 默认使用 Edge（Windows 系统通常预装）
        options = EdgeOptions()
        if TestConfig.HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"--window-size={TestConfig.WINDOW_SIZE[0]},{TestConfig.WINDOW_SIZE[1]}")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        driver = webdriver.Edge(options=options)
    
    # 设置超时
    driver.implicitly_wait(TestConfig.IMPLICIT_WAIT)
    driver.set_page_load_timeout(TestConfig.PAGE_LOAD_TIMEOUT)
    
    yield driver
    
    # 测试类结束后关闭浏览器
    driver.quit()


@pytest.fixture
def wait(driver):
    """显式等待 fixture"""
    return WebDriverWait(driver, TestConfig.EXPLICIT_WAIT)


@pytest.fixture
def home_page(driver):
    """导航到首页"""
    driver.get(TestConfig.BASE_URL)
    # 等待页面加载完成
    WebDriverWait(driver, TestConfig.EXPLICIT_WAIT).until(
        EC.presence_of_element_located((By.ID, "app"))
    )
    return driver


class ElementHelper:
    """元素操作辅助类"""
    
    def __init__(self, driver, wait_timeout=TestConfig.EXPLICIT_WAIT):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_timeout)
    
    def wait_for_element(self, locator, condition="visible"):
        """等待元素出现"""
        if condition == "visible":
            return self.wait.until(EC.visibility_of_element_located(locator))
        elif condition == "clickable":
            return self.wait.until(EC.element_to_be_clickable(locator))
        elif condition == "present":
            return self.wait.until(EC.presence_of_element_located(locator))
        else:
            raise ValueError(f"Unknown condition: {condition}")
    
    def wait_for_elements(self, locator):
        """等待多个元素出现"""
        return self.wait.until(EC.presence_of_all_elements_located(locator))
    
    def wait_for_text(self, locator, text):
        """等待元素包含指定文本"""
        return self.wait.until(EC.text_to_be_present_in_element(locator, text))
    
    def wait_for_loading_complete(self):
        """等待加载完成（检测"加载中..."文字消失）"""
        time.sleep(0.5)  # 短暂等待 AJAX 请求开始
        try:
            self.wait.until_not(
                EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "加载中...")
            )
        except:
            pass  # 如果没有"加载中..."文字，忽略
    
    def safe_click(self, element):
        """安全点击（处理可能的遮挡问题）"""
        try:
            element.click()
        except:
            self.driver.execute_script("arguments[0].click();", element)
    
    def scroll_to_element(self, element):
        """滚动到元素位置"""
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    
    def take_screenshot(self, name):
        """截图"""
        screenshots_dir = os.path.join(os.path.dirname(__file__), "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        filepath = os.path.join(screenshots_dir, f"{name}_{int(time.time())}.png")
        self.driver.save_screenshot(filepath)
        return filepath


@pytest.fixture
def helper(driver):
    """元素操作辅助类 fixture"""
    return ElementHelper(driver)
