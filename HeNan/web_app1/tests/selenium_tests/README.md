# Selenium UI 自动化测试

这是一个基于 Selenium WebDriver 的 UI 自动化测试套件，模拟真实用户在浏览器中的点击、输入等操作。

## 📁 文件结构

```
selenium_tests/
├── conftest.py              # Pytest 配置和 fixtures
├── pages.py                 # 页面对象模型 (Page Object Model)
├── test_ui.py               # UI 测试用例
├── run_selenium_tests.py    # 测试运行脚本
└── README.md                # 本文档
```

## 🔧 环境要求

### 1. Python 依赖

```bash
pip install selenium pytest pytest-html
```

### 2. WebDriver

测试默认使用 **Microsoft Edge**（Windows 预装浏览器）。Edge WebDriver 通常会自动下载。

如果需要使用 Chrome：
1. 安装 Chrome 浏览器
2. 修改 `conftest.py` 中的 `TestConfig.BROWSER = "chrome"`

## 🚀 运行测试

### 方式一：使用运行脚本（推荐）

```bash
cd d:\ioeyu\Internship\HeNan\web_app1\tests\selenium_tests
python run_selenium_tests.py
```

脚本会自动：
- 检查服务器是否运行，如未运行则自动启动
- 运行所有 UI 测试
- 生成 HTML 测试报告

### 方式二：直接使用 pytest

先确保服务器已启动：
```bash
cd d:\ioeyu\Internship\HeNan\web_app1
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

然后运行测试：
```bash
cd tests\selenium_tests
pytest -v -s test_ui.py
```

### 方式三：运行特定测试

```bash
# 运行导航测试
pytest -v test_ui.py::TestNavigation

# 运行单个测试
pytest -v test_ui.py::TestNavigation::test_navigate_to_customer_list

# 运行包含特定关键字的测试
pytest -v -k "navigation"
```

## ⚙️ 配置选项

编辑 `conftest.py` 中的 `TestConfig` 类：

```python
class TestConfig:
    BASE_URL = "http://127.0.0.1:8000"  # 测试目标 URL
    IMPLICIT_WAIT = 10                   # 隐式等待（秒）
    EXPLICIT_WAIT = 15                   # 显式等待（秒）
    PAGE_LOAD_TIMEOUT = 30               # 页面加载超时（秒）
    HEADLESS = False                     # True = 无头模式（不显示浏览器）
    BROWSER = "edge"                     # "edge" 或 "chrome"
    WINDOW_SIZE = (1920, 1080)           # 浏览器窗口大小
```

### 无头模式

设置 `HEADLESS = True` 可以在后台运行测试（不显示浏览器窗口），适合 CI/CD 环境。

## 📋 测试用例概览

### TestProvinceExport - 各省份剧头导出测试（7省份）

同一测试类内共享浏览器窗口，优化测试体验。

| 序号 | 测试方法 | 省份 | 搜索关键词 |
|------|----------|------|-----------|
| 01 | `test_01_henan_mobile` | 河南移动 | 小猪 |
| 02 | `test_02_shandong_mobile` | 山东移动 | 汪汪队 |
| 03 | `test_03_gansu_mobile` | 甘肃移动 | 熊出没 |
| 04 | `test_04_jiangsu_newmedia` | 江苏新媒体 | 小猪佩奇\n汪汪队（批量） |
| 05 | `test_05_zhejiang_mobile` | 浙江移动 | 贝乐虎 |
| 06 | `test_06_xinjiang_telecom` | 新疆电信 | 王者荣耀 |
| 07 | `test_07_jiangxi_mobile` | 江西移动 | 小伴龙 |

### TestDramaHeaderPage - 剧头管理测试
- ✅ `test_search_input_exists` - 搜索框存在
- ✅ `test_search_drama` - 搜索剧集

### TestCopyrightPage - 版权页面测试
- ✅ `test_page_loads` - 页面加载
- ✅ `test_table_displays_data` - 表格显示数据
- ✅ `test_search_function` - 搜索功能
- ✅ `test_import_button_opens_modal` - 导入按钮
- ✅ `test_add_button_opens_modal` - 添加按钮
- ✅ `test_export_button` - 导出按钮
- ✅ `test_pagination_exists` - 分页功能

### TestResponsiveUI - 响应式 UI 测试
- ✅ `test_sidebar_visible_on_large_screen` - 大屏侧边栏
- ✅ `test_table_scrollable` - 表格可滚动

### TestUserInteractions - 用户交互测试
- ✅ `test_hover_on_nav_button` - 悬停效果
- ✅ `test_search_with_enter_key` - Enter 键搜索
- ✅ `test_click_outside_modal_closes_it` - 点击外部关闭模态框

### TestEndToEndWorkflow - 端到端测试
- ✅ `test_complete_navigation_flow` - 完整导航流程
- ✅ `test_search_workflow` - 搜索工作流

### TestErrorHandling - 错误处理测试
- ✅ `test_empty_search` - 空搜索
- ✅ `test_special_characters_in_search` - 特殊字符搜索
- ✅ `test_very_long_search` - 超长搜索词

## 🏗️ 页面对象模型 (POM)

测试使用页面对象模型设计模式，将页面元素和操作封装在 `pages.py` 中：

```python
# 使用示例
from pages import HomePage, CustomerListPage

def test_example(driver):
    home = HomePage(driver)
    home.load()  # 加载首页
    
    nav = home.get_nav()  # 获取导航栏
    nav.go_to_copyright_management()  # 导航到版权页面
    
    copyright_page = CopyrightPage(driver)
    copyright_page.search("小猪佩奇")  # 搜索
```

## 📊 测试报告

运行测试后会生成 `selenium_report.html` 报告文件，包含：
- 测试通过/失败统计
- 每个测试的详细结果
- 失败测试的错误信息

## 🐛 常见问题

### 1. WebDriver 找不到

```
selenium.common.exceptions.WebDriverException: Message: 'msedgedriver' executable needs to be in PATH
```

**解决方案**：
- 确保 Edge 浏览器已安装
- 或安装 Chrome 并修改配置使用 Chrome

### 2. 服务器连接失败

```
ConnectionRefusedError: [WinError 10061]
```

**解决方案**：
```bash
cd d:\ioeyu\Internship\HeNan\web_app1
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. 元素找不到

如果测试因元素找不到而失败，可能是：
- 页面加载太慢 → 增加 `IMPLICIT_WAIT` 和 `EXPLICIT_WAIT`
- 元素 ID/选择器变化 → 更新 `pages.py` 中的定位器

## 🔄 扩展测试

添加新测试时：

1. 如需新页面，在 `pages.py` 中添加页面类
2. 在 `test_ui.py` 中添加测试用例
3. 遵循命名规范：`test_功能描述`

```python
class TestNewFeature:
    """新功能测试"""
    
    def test_new_button_works(self, driver, server):
        """测试新按钮功能"""
        home = HomePage(driver)
        home.load()
        # 添加测试逻辑
        assert True
```
