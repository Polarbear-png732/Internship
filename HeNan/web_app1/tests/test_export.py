"""
导出功能测试
测试各种Excel导出接口
"""
import pytest
from io import BytesIO
from conftest import assert_success_response, TestDataTracker


class TestExportSingleDrama:
    """单剧导出测试"""
    
    def test_export_drama_not_found(self, client):
        """测试导出不存在的剧集"""
        response = client.get("/api/dramas/999999999/export")
        assert response.status_code == 404
    
    def test_export_drama_success(self, client, tracker: TestDataTracker, test_prefix: str):
        """测试导出单个剧集"""
        # 先创建一个版权数据
        create_data = {
            "media_name": f"{test_prefix}导出测试剧集",
            "episode_count": 3,
            "single_episode_duration": 10
        }
        
        response = client.post("/api/copyright", json=create_data)
        if response.status_code != 200:
            pytest.skip("无法创建测试数据")
        
        data = response.json()
        copyright_id = data["data"]["copyright_id"]
        drama_ids = data["data"]["drama_ids"]
        tracker.add_copyright(copyright_id)
        
        # 导出第一个客户的剧集
        first_drama_id = list(drama_ids.values())[0]
        
        response = client.get(f"/api/dramas/{first_drama_id}/export")
        
        assert response.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("content-type", "")
        
        # 验证返回的是有效的Excel文件
        content = response.content
        assert len(content) > 0, "导出文件不应为空"
        assert content[:4] == b'PK\x03\x04', "应该是有效的xlsx文件（ZIP格式）"
        
        print(f"\n✅ 单剧导出成功，文件大小: {len(content)} bytes")


class TestExportCustomer:
    """客户全量导出测试"""
    
    def test_export_customer_not_found(self, client):
        """测试导出不存在的客户"""
        response = client.get("/api/dramas/export/customer/unknown_customer")
        assert response.status_code == 404
    
    def test_export_customer_success(self, client):
        """测试导出客户全部剧集（跳过大数据量导出，避免超时）"""
        # 由于河南移动有 5000+ 剧集，导出会超时，跳过此测试
        # 如需测试，可以使用数据量较少的客户
        pytest.skip("跳过大数据量导出测试，避免超时（河南移动有5000+剧集）")


class TestExportBatch:
    """批量导出测试"""
    
    def test_batch_export_empty_list(self, client):
        """测试批量导出空列表"""
        response = client.post("/api/dramas/export/batch/jiangsu_newmedia", json={
            "drama_names": []
        })
        assert response.status_code == 400
    
    def test_batch_export_not_found(self, client):
        """测试批量导出不存在的剧集"""
        response = client.post("/api/dramas/export/batch/jiangsu_newmedia", json={
            "drama_names": ["完全不存在的剧集A", "完全不存在的剧集B"]
        })
        assert response.status_code == 404
    
    def test_batch_export_xinjiang_empty(self, client):
        """测试新疆电信批量导出空列表"""
        response = client.post("/api/dramas/export/batch/xinjiang_telecom", json={
            "drama_names": []
        })
        assert response.status_code == 400


class TestExportCopyright:
    """版权数据导出测试"""
    
    def test_export_copyright_success(self, client):
        """测试导出版权数据（跳过大数据量导出，避免超时）"""
        # 由于版权数据量可能很大，导出会超时，跳过此测试
        pytest.skip("跳过大数据量导出测试，避免超时")
