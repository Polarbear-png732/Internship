"""
pytest 配置文件
提供测试客户端、测试数据管理等公共 fixtures

使用 httpx 直接请求运行中的服务器（需要先启动服务）
"""
import pytest
import sys
import os
import time
from typing import Generator, Dict, Any, List
import httpx


# 服务器地址（需要先启动服务）
BASE_URL = "http://127.0.0.1:8000"


class HttpClient:
    """HTTP 客户端封装，模拟 TestClient 接口"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        # 完全禁用代理，使用 trust_env=False
        self._client = httpx.Client(timeout=30.0, trust_env=False)
    
    def get(self, path: str, **kwargs):
        return self._client.get(f"{self.base_url}{path}", **kwargs)
    
    def post(self, path: str, **kwargs):
        return self._client.post(f"{self.base_url}{path}", **kwargs)
    
    def put(self, path: str, **kwargs):
        return self._client.put(f"{self.base_url}{path}", **kwargs)
    
    def delete(self, path: str, **kwargs):
        return self._client.delete(f"{self.base_url}{path}", **kwargs)
    
    def close(self):
        self._client.close()


# ============================================================
# 测试客户端
# ============================================================

@pytest.fixture(scope="session")
def client() -> Generator[HttpClient, None, None]:
    """创建测试客户端（整个测试会话共享）"""
    c = HttpClient(BASE_URL)
    
    # 检查服务是否可用（尝试多次）
    max_retries = 3
    for i in range(max_retries):
        try:
            response = c.get("/api/customers")
            if response.status_code == 200:
                print(f"\n✅ 服务器连接成功")
                break
            elif response.status_code >= 500:
                # 可能是数据库问题，但服务器在运行
                print(f"\n⚠️ 服务器返回 {response.status_code}，继续测试...")
                break
        except httpx.ConnectError as e:
            if i < max_retries - 1:
                print(f"\n⏳ 等待服务器启动... ({i+1}/{max_retries})")
                time.sleep(2)
            else:
                pytest.exit(f"❌ 无法连接到服务器 {BASE_URL}，请先启动服务：\n   cd web_app1 && python main.py")
    
    yield c
    c.close()


# ============================================================
# 测试数据标识
# ============================================================

@pytest.fixture(scope="session")
def test_prefix() -> str:
    """生成唯一的测试数据前缀，用于标识测试数据"""
    return f"__TEST_{int(time.time())}__"


# ============================================================
# 测试数据清理追踪
# ============================================================

class TestDataTracker:
    """追踪测试过程中创建的数据，用于清理"""
    
    def __init__(self):
        self.copyright_ids: List[int] = []
        self.drama_ids: List[int] = []
        self.episode_ids: List[tuple] = []  # (drama_id, episode_id)
    
    def add_copyright(self, copyright_id: int):
        self.copyright_ids.append(copyright_id)
    
    def add_drama(self, drama_id: int):
        self.drama_ids.append(drama_id)
    
    def add_episode(self, drama_id: int, episode_id: int):
        self.episode_ids.append((drama_id, episode_id))
    
    def cleanup(self, client: TestClient):
        """清理所有追踪的测试数据"""
        # 先删除版权（会级联删除关联的剧集和子集）
        for copyright_id in reversed(self.copyright_ids):
            try:
                client.delete(f"/api/copyright/{copyright_id}")
            except Exception:
                pass
        
        # 清理可能遗留的子集
        for drama_id, episode_id in reversed(self.episode_ids):
            try:
                client.delete(f"/api/dramas/{drama_id}/episodes/{episode_id}")
            except Exception:
                pass
        
        # 清理可能遗留的剧集
        for drama_id in reversed(self.drama_ids):
            try:
                client.delete(f"/api/dramas/{drama_id}")
            except Exception:
                pass
        
        # 清空追踪列表
        self.copyright_ids.clear()
        self.drama_ids.clear()
        self.episode_ids.clear()


@pytest.fixture(scope="session")
def tracker() -> TestDataTracker:
    """测试数据追踪器"""
    return TestDataTracker()


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_all_tests(client: TestClient, tracker: TestDataTracker):
    """在所有测试结束后自动清理测试数据"""
    yield
    print("\n🧹 清理测试数据...")
    tracker.cleanup(client)
    print("✅ 测试数据清理完成")


# ============================================================
# 测试数据工厂
# ============================================================

@pytest.fixture
def copyright_data(test_prefix: str) -> Dict[str, Any]:
    """生成测试用的版权数据"""
    return {
        "media_name": f"{test_prefix}测试剧集",
        "upstream_copyright": "测试版权方",
        "category_level1": "少儿",
        "category_level2": "动画",
        "category_level1_henan": "少儿",
        "category_level2_henan": "动画",
        "episode_count": 3,
        "single_episode_duration": 10,
        "total_duration": 30,
        "production_year": "2024",
        "production_region": "中国",
        "language": "普通话",
        "language_henan": "简体中文",
        "synopsis": "这是一个测试剧集的简介",
        "keywords": "测试,自动化"
    }


@pytest.fixture
def episode_data(test_prefix: str) -> Dict[str, Any]:
    """生成测试用的子集数据"""
    return {
        "节目名称": f"{test_prefix}测试子集",
        "时长": "600",
        "简介": "测试子集简介"
    }


# ============================================================
# 辅助函数
# ============================================================

def assert_success_response(response, expected_code: int = 200):
    """断言响应成功"""
    assert response.status_code == expected_code, f"期望状态码 {expected_code}，实际 {response.status_code}: {response.text}"
    data = response.json()
    assert data.get("code") == 200, f"响应 code 不为 200: {data}"
    return data


def assert_error_response(response, expected_status: int):
    """断言响应错误"""
    assert response.status_code == expected_status, f"期望状态码 {expected_status}，实际 {response.status_code}"
