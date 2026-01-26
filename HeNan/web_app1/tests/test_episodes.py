"""
子集管理接口测试
测试 /api/dramas/{drama_id}/episodes 相关接口
"""
import pytest
from conftest import assert_success_response, assert_error_response


class TestEpisodesQuery:
    """子集查询测试"""
    
    def test_get_episodes_drama_not_found(self, client):
        """测试获取不存在剧集的子集列表"""
        response = client.get("/api/dramas/999999999/episodes")
        # 即使剧集不存在，也应该返回空列表而不是404
        data = assert_success_response(response)
        assert data["data"] == []


class TestEpisodesCRUD:
    """子集CRUD测试（需要先创建版权数据）"""
    
    def test_create_episode_drama_not_found(self, client):
        """测试为不存在的剧集创建子集"""
        response = client.post("/api/dramas/999999999/episodes", json={
            "节目名称": "测试子集"
        })
        assert response.status_code == 404
    
    def test_create_episode_missing_name(self, client, tracker, copyright_data):
        """测试创建子集缺少名称"""
        # 先创建一个版权数据以获取 drama_id
        copyright_data["media_name"] = f"{copyright_data['media_name']}_episode_test"
        response = client.post("/api/copyright", json=copyright_data)
        
        if response.status_code == 200:
            data = response.json()
            copyright_id = data["data"]["copyright_id"]
            tracker.add_copyright(copyright_id)
            
            # 获取一个 drama_id
            drama_ids = data["data"]["drama_ids"]
            if drama_ids:
                drama_id = list(drama_ids.values())[0]
                
                # 尝试创建缺少名称的子集
                response = client.post(f"/api/dramas/{drama_id}/episodes", json={
                    "时长": "600"
                })
                assert response.status_code == 400
    
    def test_update_episode_not_found(self, client):
        """测试更新不存在的子集"""
        response = client.put("/api/dramas/999999999/episodes/999999999", json={
            "节目名称": "更新的名称"
        })
        assert response.status_code == 404
    
    def test_delete_episode_not_found(self, client):
        """测试删除不存在的子集"""
        response = client.delete("/api/dramas/999999999/episodes/999999999")
        assert response.status_code == 404
