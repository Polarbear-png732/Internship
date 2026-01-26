"""
剧集管理接口测试
测试 /api/dramas 相关接口
"""
import pytest
from conftest import assert_success_response, assert_error_response


class TestDramasQuery:
    """剧集查询测试"""
    
    def test_get_dramas_default_pagination(self, client):
        """测试获取剧集列表（默认分页）"""
        response = client.get("/api/dramas")
        data = assert_success_response(response)
        
        # 验证分页结构
        result = data["data"]
        required_fields = ["list", "total", "page", "page_size", "total_pages"]
        for field in required_fields:
            assert field in result, f"分页结果缺少字段: {field}"
        
        # 验证默认值
        assert result["page"] == 1
        assert result["page_size"] == 10
    
    def test_get_dramas_custom_pagination(self, client):
        """测试自定义分页参数"""
        response = client.get("/api/dramas", params={"page": 2, "page_size": 5})
        data = assert_success_response(response)
        
        result = data["data"]
        assert result["page"] == 2
        assert result["page_size"] == 5
    
    def test_get_dramas_filter_by_customer(self, client):
        """测试按客户筛选剧集"""
        response = client.get("/api/dramas", params={"customer_code": "henan_mobile"})
        data = assert_success_response(response)
        
        # 所有返回的剧集应属于河南移动
        for drama in data["data"]["list"]:
            assert drama.get("customer_code") == "henan_mobile"
    
    def test_get_dramas_search_keyword(self, client):
        """测试关键词搜索"""
        response = client.get("/api/dramas", params={"keyword": "测试不存在的剧集xyz"})
        data = assert_success_response(response)
        
        # 搜索不存在的关键词，结果应为空
        assert data["data"]["total"] == 0 or len(data["data"]["list"]) == 0
    
    def test_get_dramas_invalid_page(self, client):
        """测试无效分页参数"""
        # page_size 超过限制
        response = client.get("/api/dramas", params={"page_size": 1000})
        assert response.status_code == 422  # FastAPI 参数验证错误


class TestDramasDetail:
    """剧集详情测试"""
    
    def test_get_drama_detail_not_found(self, client):
        """测试获取不存在的剧集"""
        response = client.get("/api/dramas/999999999")
        assert response.status_code == 404
    
    def test_get_drama_by_name_not_found(self, client):
        """测试按名称查询不存在的剧集"""
        response = client.get("/api/dramas/by-name", params={
            "name": "完全不存在的剧集名称xyz",
            "customer_code": "henan_mobile"
        })
        assert response.status_code == 404


class TestDramasColumns:
    """客户列配置测试"""
    
    def test_get_customer_columns_success(self, client):
        """测试获取客户列配置"""
        response = client.get("/api/dramas/columns/henan_mobile")
        data = assert_success_response(response)
        
        result = data["data"]
        assert result["customer_code"] == "henan_mobile"
        assert "drama_columns" in result
        assert "episode_columns" in result
        assert isinstance(result["drama_columns"], list)
        assert isinstance(result["episode_columns"], list)
    
    def test_get_customer_columns_not_found(self, client):
        """测试获取不存在的客户列配置"""
        response = client.get("/api/dramas/columns/unknown_customer")
        assert response.status_code == 404


class TestDramasBatchQuery:
    """批量查询测试"""
    
    def test_batch_query_empty_list(self, client):
        """测试批量查询空列表"""
        response = client.post("/api/dramas/batch-query", json={
            "drama_names": [],
            "customer_code": "henan_mobile"
        })
        assert response.status_code == 400
    
    def test_batch_query_not_found(self, client):
        """测试批量查询不存在的剧集"""
        response = client.post("/api/dramas/batch-query", json={
            "drama_names": ["不存在的剧集A", "不存在的剧集B"],
            "customer_code": "henan_mobile"
        })
        data = assert_success_response(response)
        
        # 所有剧集都应该未找到
        results = data["data"]["results"]
        assert all(not r["found"] for r in results)
        assert data["data"]["not_found"] == 2


class TestDramasDelete:
    """剧集删除测试"""
    
    def test_delete_drama_not_found(self, client):
        """测试删除不存在的剧集"""
        response = client.delete("/api/dramas/999999999")
        assert response.status_code == 404
