"""
页面对象模型 (Page Object Model)
封装页面元素定位和操作方法，提高测试可维护性
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time


class BasePage:
    """页面基类"""
    
    def __init__(self, driver, wait_timeout=15):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_timeout)
    
    def find_element(self, locator):
        """查找单个元素"""
        return self.wait.until(EC.presence_of_element_located(locator))
    
    def find_elements(self, locator):
        """查找多个元素"""
        return self.driver.find_elements(*locator)
    
    def click(self, locator):
        """点击元素"""
        element = self.wait.until(EC.element_to_be_clickable(locator))
        try:
            element.click()
        except:
            self.driver.execute_script("arguments[0].click();", element)
    
    def type_text(self, locator, text, clear_first=True):
        """输入文本"""
        element = self.wait.until(EC.visibility_of_element_located(locator))
        if clear_first:
            element.clear()
        element.send_keys(text)
    
    def get_text(self, locator):
        """获取元素文本"""
        element = self.wait.until(EC.visibility_of_element_located(locator))
        return element.text
    
    def is_element_visible(self, locator, timeout=5):
        """检查元素是否可见"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
            return True
        except TimeoutException:
            return False
    
    def wait_for_loading(self, timeout=10):
        """等待页面加载完成"""
        time.sleep(0.5)  # 等待 AJAX 开始
        try:
            # 等待"加载中..."文字消失
            WebDriverWait(self.driver, timeout).until_not(
                EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "加载中...")
            )
        except:
            pass
    
    def scroll_to(self, locator):
        """滚动到指定元素"""
        element = self.find_element(locator)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    
    def take_screenshot(self, name):
        """保存截图"""
        import os
        screenshots_dir = os.path.join(os.path.dirname(__file__), "..", "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        filepath = os.path.join(screenshots_dir, f"{name}_{int(time.time())}.png")
        self.driver.save_screenshot(filepath)
        return filepath


class NavigationBar(BasePage):
    """侧边栏导航组件"""
    
    # 导航按钮定位器
    BTN_CUSTOMER_LIST = (By.ID, "nav-customer-list")
    BTN_COPYRIGHT_MANAGEMENT = (By.ID, "nav-copyright-management")
    BTN_PLACEHOLDER = (By.ID, "nav-placeholder")
    
    # 页面容器定位器
    PAGE_CUSTOMER_LIST = (By.ID, "customer-list-page")
    PAGE_DRAMA_HEADER = (By.ID, "drama-header-management-page")
    PAGE_COPYRIGHT = (By.ID, "copyright-management-page")
    PAGE_PLACEHOLDER = (By.ID, "placeholder-page")
    
    def go_to_customer_list(self):
        """导航到注入表管理页面"""
        self.click(self.BTN_CUSTOMER_LIST)
        self.wait_for_loading()
        return CustomerListPage(self.driver)
    
    def go_to_copyright_management(self):
        """导航到版权方数据页面"""
        self.click(self.BTN_COPYRIGHT_MANAGEMENT)
        self.wait_for_loading()
        return CopyrightPage(self.driver)
    
    def go_to_placeholder(self):
        """导航到占位页面"""
        self.click(self.BTN_PLACEHOLDER)
        return self
    
    def get_active_nav_button(self):
        """获取当前激活的导航按钮"""
        buttons = [
            self.BTN_CUSTOMER_LIST,
            self.BTN_COPYRIGHT_MANAGEMENT,
            self.BTN_PLACEHOLDER
        ]
        for btn_locator in buttons:
            try:
                element = self.driver.find_element(*btn_locator)
                if "bg-blue-600" in element.get_attribute("class"):
                    return element
            except:
                pass
        return None


class CustomerListPage(BasePage):
    """业务列表页面（注入表管理）"""
    
    # 页面标题
    PAGE_TITLE = (By.XPATH, "//h2[text()='业务列表']")
    
    # 表格
    TABLE_BODY = (By.ID, "customer-table-body")
    TABLE_ROWS = (By.CSS_SELECTOR, "#customer-table-body tr")
    
    # 业务名称列（第一列）
    CUSTOMER_NAMES = (By.CSS_SELECTOR, "#customer-table-body tr td:first-child")
    
    # 查看按钮（每行的操作按钮）
    VIEW_BUTTONS = (By.CSS_SELECTOR, "#customer-table-body tr button")
    
    def is_loaded(self):
        """检查页面是否加载完成"""
        return self.is_element_visible(self.PAGE_TITLE)
    
    def get_customer_count(self):
        """获取业务数量"""
        self.wait_for_loading()
        rows = self.find_elements(self.TABLE_ROWS)
        # 排除"加载中..."行
        return len([r for r in rows if "加载中" not in r.text])
    
    def get_customer_names(self):
        """获取所有业务名称"""
        self.wait_for_loading()
        elements = self.find_elements(self.CUSTOMER_NAMES)
        return [el.text for el in elements if el.text and "加载中" not in el.text]
    
    def click_view_button(self, index=0):
        """点击指定行的查看按钮"""
        self.wait_for_loading()
        buttons = self.find_elements(self.VIEW_BUTTONS)
        if index < len(buttons):
            button = buttons[index]
            self.driver.execute_script("arguments[0].click();", button)
            self.wait_for_loading()
            return DramaHeaderPage(self.driver)
        return None
    
    def click_customer_by_name(self, name):
        """点击指定名称的业务"""
        self.wait_for_loading()
        rows = self.find_elements(self.TABLE_ROWS)
        for row in rows:
            if name in row.text:
                buttons = row.find_elements(By.TAG_NAME, "button")
                if buttons:
                    self.driver.execute_script("arguments[0].click();", buttons[0])
                    self.wait_for_loading()
                    return DramaHeaderPage(self.driver)
        return None


class DramaHeaderPage(BasePage):
    """剧头管理页面"""
    
    # 页面标题
    PAGE_TITLE = (By.XPATH, "//h2[text()='剧头管理']")
    
    # 搜索框（普通单行）
    SEARCH_INPUT = (By.ID, "header-search-input")
    SEARCH_BUTTON = (By.XPATH, "//button[contains(@onclick, 'searchDramaHeaderDirect')]")
    
    # 搜索框（江苏多行文本框）
    SEARCH_TEXTAREA = (By.ID, "header-search-textarea")
    JIANGSU_SEARCH_CONTAINER = (By.ID, "jiangsu-search-container")
    
    # 搜索结果
    SEARCH_RESULT = (By.ID, "header-search-result")
    
    # 批量选择区域
    BATCH_SELECTION_AREA = (By.ID, "batch-selection-area")
    SELECTED_COUNT = (By.ID, "selected-count")
    BTN_SELECT_ALL = (By.XPATH, "//button[contains(@onclick, 'selectAllDramas')]")
    BTN_CLEAR_ALL = (By.XPATH, "//button[contains(@onclick, 'clearAllSelections')]")
    BTN_BATCH_EXPORT = (By.ID, "batch-export-btn")
    
    # 剧集选择列表
    DRAMA_SELECTION_LIST = (By.ID, "drama-selection-list")
    DRAMA_CHECKBOXES = (By.CSS_SELECTOR, "#drama-selection-list input[type='checkbox']")
    
    def is_loaded(self):
        """检查页面是否加载完成"""
        return self.is_element_visible(self.PAGE_TITLE)
    
    def is_jiangsu_mode(self):
        """检查是否为江苏模式（多行文本框）"""
        try:
            container = self.driver.find_element(*self.JIANGSU_SEARCH_CONTAINER)
            return "hidden" not in container.get_attribute("class")
        except:
            return False
    
    def search(self, keyword):
        """执行搜索"""
        if self.is_jiangsu_mode():
            self.type_text(self.SEARCH_TEXTAREA, keyword)
        else:
            self.type_text(self.SEARCH_INPUT, keyword)
        
        # 点击搜索按钮
        buttons = self.driver.find_elements(By.XPATH, "//button")
        for btn in buttons:
            if "搜索" in btn.text:
                self.driver.execute_script("arguments[0].click();", btn)
                break
        
        self.wait_for_loading()
        time.sleep(1)  # 等待结果渲染
    
    def get_search_result(self):
        """获取搜索结果"""
        try:
            result = self.driver.find_element(*self.SEARCH_RESULT)
            if "hidden" not in result.get_attribute("class"):
                return result.text
        except:
            pass
        return None
    
    def is_batch_selection_visible(self):
        """检查批量选择区域是否可见"""
        try:
            area = self.driver.find_element(*self.BATCH_SELECTION_AREA)
            return "hidden" not in area.get_attribute("class")
        except:
            return False
    
    def get_selected_count(self):
        """获取已选择的剧集数量"""
        text = self.get_text(self.SELECTED_COUNT)
        # 提取数字 "已选择 X 个" -> X
        import re
        match = re.search(r'\d+', text)
        return int(match.group()) if match else 0
    
    def select_all_dramas(self):
        """全选剧集"""
        self.click(self.BTN_SELECT_ALL)
        time.sleep(0.5)
    
    def clear_all_selections(self):
        """清空选择"""
        self.click(self.BTN_CLEAR_ALL)
        time.sleep(0.5)
    
    def click_batch_export(self):
        """点击批量导出"""
        self.click(self.BTN_BATCH_EXPORT)
        time.sleep(2)  # 等待下载


class CopyrightPage(BasePage):
    """版权方数据页面"""
    
    # 页面标题
    PAGE_TITLE = (By.XPATH, "//h2[text()='版权信息']")
    
    # 搜索
    SEARCH_INPUT = (By.ID, "copyright-search-input")
    SEARCH_BUTTON = (By.XPATH, "//button[contains(@onclick, 'searchCopyrightContent')]")
    
    # 操作按钮
    BTN_IMPORT = (By.XPATH, "//button[contains(@onclick, 'openImportModal')]")
    BTN_EXPORT = (By.XPATH, "//button[contains(@onclick, 'exportCopyrightData')]")
    BTN_ADD = (By.XPATH, "//button[contains(@onclick, 'openAddCopyrightModal')]")
    
    # 表格
    TABLE_BODY = (By.ID, "copyright-table-body")
    TABLE_ROWS = (By.CSS_SELECTOR, "#copyright-table-body tr")
    
    # 分页
    PAGINATION = (By.ID, "copyright-pagination")
    PAGINATION_BUTTONS = (By.CSS_SELECTOR, "#copyright-pagination button")
    
    # 模态框
    IMPORT_MODAL = (By.ID, "import-modal")
    ADD_MODAL = (By.ID, "add-copyright-modal")
    EDIT_MODAL = (By.ID, "edit-copyright-modal")
    
    def is_loaded(self):
        """检查页面是否加载完成"""
        return self.is_element_visible(self.PAGE_TITLE)
    
    def search(self, keyword):
        """搜索版权内容"""
        self.type_text(self.SEARCH_INPUT, keyword)
        self.click(self.SEARCH_BUTTON)
        self.wait_for_loading()
        time.sleep(1)
    
    def get_table_row_count(self):
        """获取表格行数"""
        self.wait_for_loading()
        rows = self.find_elements(self.TABLE_ROWS)
        return len([r for r in rows if "加载中" not in r.text and r.text.strip()])
    
    def get_table_data(self):
        """获取表格数据"""
        self.wait_for_loading()
        rows = self.find_elements(self.TABLE_ROWS)
        data = []
        for row in rows:
            if "加载中" not in row.text and row.text.strip():
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    data.append([cell.text for cell in cells])
        return data
    
    def click_import(self):
        """点击导入按钮"""
        self.click(self.BTN_IMPORT)
        time.sleep(0.5)
        return self
    
    def click_export(self):
        """点击导出按钮"""
        self.click(self.BTN_EXPORT)
        time.sleep(2)  # 等待下载
        return self
    
    def click_add(self):
        """点击添加按钮"""
        self.click(self.BTN_ADD)
        time.sleep(0.5)
        return self
    
    def is_import_modal_visible(self):
        """检查导入模态框是否可见"""
        try:
            modal = self.driver.find_element(*self.IMPORT_MODAL)
            return "hidden" not in modal.get_attribute("class")
        except:
            return False
    
    def is_add_modal_visible(self):
        """检查添加模态框是否可见"""
        try:
            modal = self.driver.find_element(*self.ADD_MODAL)
            return "hidden" not in modal.get_attribute("class")
        except:
            return False
    
    def go_to_page(self, page_number):
        """翻页"""
        buttons = self.find_elements(self.PAGINATION_BUTTONS)
        for btn in buttons:
            if btn.text == str(page_number):
                self.driver.execute_script("arguments[0].click();", btn)
                self.wait_for_loading()
                return self
        return None
    
    def click_edit_button(self, row_index=0):
        """点击编辑按钮"""
        rows = self.find_elements(self.TABLE_ROWS)
        if row_index < len(rows):
            # 找到操作列的编辑按钮
            row = rows[row_index]
            buttons = row.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if "编辑" in btn.text or "edit" in btn.get_attribute("class").lower():
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)
                    return self
        return None
    
    def click_delete_button(self, row_index=0):
        """点击删除按钮"""
        rows = self.find_elements(self.TABLE_ROWS)
        if row_index < len(rows):
            row = rows[row_index]
            buttons = row.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if "删除" in btn.text:
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)
                    return self
        return None


class EditDramaModal(BasePage):
    """编辑剧集信息模态框"""
    
    MODAL = (By.ID, "edit-modal")
    BTN_CLOSE = (By.XPATH, "//div[@id='edit-modal']//button[contains(@onclick, 'closeEditModal')]")
    BTN_SAVE = (By.XPATH, "//button[contains(text(), '保存')]")
    
    # 表单字段
    INPUT_DRAMA_NAME = (By.ID, "edit-drama-name")
    INPUT_AUTHOR = (By.ID, "edit-author-list")
    INPUT_RESOLUTION = (By.ID, "edit-resolution")
    INPUT_LANGUAGE = (By.ID, "edit-language")
    INPUT_ACTORS = (By.ID, "edit-actors")
    INPUT_CONTENT_TYPE = (By.ID, "edit-content-type")
    INPUT_RELEASE_YEAR = (By.ID, "edit-release-year")
    INPUT_KEYWORDS = (By.ID, "edit-keywords")
    INPUT_RATING = (By.ID, "edit-rating")
    INPUT_TOTAL_EPISODES = (By.ID, "edit-total-episodes")
    
    def is_visible(self):
        """检查模态框是否可见"""
        try:
            modal = self.driver.find_element(*self.MODAL)
            return "hidden" not in modal.get_attribute("class")
        except:
            return False
    
    def close(self):
        """关闭模态框"""
        self.click(self.BTN_CLOSE)
        time.sleep(0.3)
    
    def fill_form(self, **kwargs):
        """填写表单"""
        field_map = {
            'drama_name': self.INPUT_DRAMA_NAME,
            'author': self.INPUT_AUTHOR,
            'resolution': self.INPUT_RESOLUTION,
            'language': self.INPUT_LANGUAGE,
            'actors': self.INPUT_ACTORS,
            'content_type': self.INPUT_CONTENT_TYPE,
            'release_year': self.INPUT_RELEASE_YEAR,
            'keywords': self.INPUT_KEYWORDS,
            'rating': self.INPUT_RATING,
            'total_episodes': self.INPUT_TOTAL_EPISODES,
        }
        
        for key, value in kwargs.items():
            if key in field_map and value is not None:
                self.type_text(field_map[key], str(value))
    
    def save(self):
        """保存"""
        self.click(self.BTN_SAVE)
        time.sleep(1)


class HomePage(BasePage):
    """首页入口"""
    
    APP_CONTAINER = (By.ID, "app")
    HEADER_TITLE = (By.ID, "header-title")
    
    def __init__(self, driver, base_url="http://127.0.0.1:8000"):
        super().__init__(driver)
        self.base_url = base_url
    
    def load(self):
        """加载首页"""
        self.driver.get(self.base_url)
        self.wait.until(EC.presence_of_element_located(self.APP_CONTAINER))
        self.wait_for_loading()
        return self
    
    def is_loaded(self):
        """检查首页是否加载完成"""
        return self.is_element_visible(self.APP_CONTAINER)
    
    def get_nav(self):
        """获取导航栏组件"""
        return NavigationBar(self.driver)
    
    def get_header_title(self):
        """获取页面标题"""
        return self.get_text(self.HEADER_TITLE)
