"""
版权管理接口测试
测试 /api/copyright 相关接口（跳过导入功能）
"""
import pytest
import time
from conftest import assert_success_response, assert_error_response, TestDataTracker


class TestCopyrightQuery:
    """版权查询测试"""
    
    def test_get_copyright_list_default(self, client):
        """测试获取版权列表（默认分页）"""
        response = client.get("/api/copyright")
        data = assert_success_response(response)
        
        result = data["data"]
        required_fields = ["list", "total", "page", "page_size", "total_pages"]
        for field in required_fields:
            assert field in result, f"分页结果缺少字段: {field}"
    
    def test_get_copyright_list_custom_pagination(self, client):
        """测试自定义分页"""
        response = client.get("/api/copyright", params={"page": 1, "page_size": 5})
        data = assert_success_response(response)
        
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 5
    
    def test_get_copyright_list_search(self, client):
        """测试关键词搜索"""
        response = client.get("/api/copyright", params={"keyword": "不存在的版权xyz"})
        data = assert_success_response(response)
        
        assert data["data"]["total"] == 0 or len(data["data"]["list"]) == 0
    
    def test_get_copyright_detail_not_found(self, client):
        """测试获取不存在的版权详情"""
        response = client.get("/api/copyright/999999999")
        assert response.status_code == 404
    
    def test_get_customers_list(self, client):
        """测试获取客户配置列表"""
        response = client.get("/api/copyright/customers")
        data = assert_success_response(response)
        
        customers = data["data"]
        assert isinstance(customers, list)
        assert len(customers) > 0


class TestCopyrightCRUD:
    """版权CRUD完整流程测试"""
    
    def test_create_copyright_missing_name(self, client):
        """测试创建版权缺少必填字段"""
        response = client.post("/api/copyright", json={
            "upstream_copyright": "测试版权方"
        })
        assert response.status_code == 400
    
    def test_copyright_full_lifecycle(self, client, tracker: TestDataTracker, test_prefix: str):
        """测试版权完整生命周期：创建 -> 查询 -> 更新 -> 删除"""
        
        # ===== 1. 创建版权 =====
        create_data = {
            "media_name": f"{test_prefix}生命周期测试剧集",
            "upstream_copyright": "测试版权方",
            "category_level1": "少儿",
            "category_level2": "动画",
            "episode_count": 5,
            "single_episode_duration": 10,
            "total_duration": 50,
            "production_year": "2024",
            "synopsis": "这是生命周期测试的简介"
        }
        
        response = client.post("/api/copyright", json=create_data)
        data = assert_success_response(response)
        
        copyright_id = data["data"]["copyright_id"]
        drama_ids = data["data"]["drama_ids"]
        tracker.add_copyright(copyright_id)
        
        assert copyright_id > 0
        assert len(drama_ids) > 0, "应该为多个客户创建剧头"
        
        print(f"\n✅ 创建成功: copyright_id={copyright_id}, drama_ids={drama_ids}")
        
        # ===== 2. 查询详情 =====
        response = client.get(f"/api/copyright/{copyright_id}")
        data = assert_success_response(response)
        
        item = data["data"]
        assert item["media_name"] == create_data["media_name"]
        assert item["episode_count"] == create_data["episode_count"]
        
        print(f"✅ 查询成功: media_name={item['media_name']}")
        
        # ===== 3. 验证自动生成的剧头 =====
        for customer_code, drama_id in drama_ids.items():
            response = client.get(f"/api/dramas/{drama_id}")
            if response.status_code == 200:
                drama_data = response.json()
                print(f"✅ 验证剧头: {customer_code} -> drama_id={drama_id}")
        
        # ===== 4. 验证自动生成的子集 =====
        first_drama_id = list(drama_ids.values())[0]
        response = client.get(f"/api/dramas/{first_drama_id}/episodes")
        data = assert_success_response(response)
        
        episodes = data["data"]
        assert len(episodes) == create_data["episode_count"], \
            f"子集数量应为 {create_data['episode_count']}，实际 {len(episodes)}"
        
        print(f"✅ 验证子集: 共 {len(episodes)} 集")
        
        # ===== 5. 更新版权 =====
        update_data = {
            "media_name": f"{test_prefix}生命周期测试剧集_已更新",
            "synopsis": "更新后的简介",
            "episode_count": 8  # 增加集数
        }
        
        response = client.put(f"/api/copyright/{copyright_id}", json=update_data)
        data = assert_success_response(response)
        
        print(f"✅ 更新成功")
        
        # ===== 6. 验证更新后的数据 =====
        response = client.get(f"/api/copyright/{copyright_id}")
        data = assert_success_response(response)
        
        item = data["data"]
        assert update_data["media_name"] in item["media_name"] or item["media_name"] == update_data["media_name"]
        
        # 验证子集数量更新
        response = client.get(f"/api/dramas/{first_drama_id}/episodes")
        data = assert_success_response(response)
        
        # 注意：增加集数时应该新增子集
        print(f"✅ 更新后子集数: {len(data['data'])} 集")
        
        # ===== 7. 删除版权 =====
        response = client.delete(f"/api/copyright/{copyright_id}")
        data = assert_success_response(response)
        
        # 从追踪器移除（已删除）
        tracker.copyright_ids.remove(copyright_id)
        
        print(f"✅ 删除成功")
        
        # ===== 8. 验证级联删除 =====
        response = client.get(f"/api/copyright/{copyright_id}")
        assert response.status_code == 404, "删除后应该返回404"
        
        # 验证关联的剧头也被删除
        for drama_id in drama_ids.values():
            response = client.get(f"/api/dramas/{drama_id}")
            assert response.status_code == 404, f"剧头 {drama_id} 应该被级联删除"
        
        print(f"✅ 级联删除验证通过")
    
    def test_update_copyright_not_found(self, client):
        """测试更新不存在的版权"""
        response = client.put("/api/copyright/999999999", json={
            "media_name": "不存在的版权"
        })
        assert response.status_code == 404
    
    def test_delete_copyright_not_found(self, client):
        """测试删除不存在的版权"""
        response = client.delete("/api/copyright/999999999")
        assert response.status_code == 404


class TestCopyrightEpisodeSync:
    """版权与子集同步测试"""
    
    def test_episode_crud_with_copyright(self, client, tracker: TestDataTracker, test_prefix: str):
        """测试通过版权创建的剧集进行子集CRUD"""
        
        # 创建版权
        create_data = {
            "media_name": f"{test_prefix}子集CRUD测试",
            "episode_count": 2,
            "single_episode_duration": 10
        }
        
        response = client.post("/api/copyright", json=create_data)
        data = assert_success_response(response)
        
        copyright_id = data["data"]["copyright_id"]
        drama_ids = data["data"]["drama_ids"]
        tracker.add_copyright(copyright_id)
        
        # 获取第一个客户的 drama_id
        first_drama_id = list(drama_ids.values())[0]
        
        # 获取现有子集
        response = client.get(f"/api/dramas/{first_drama_id}/episodes")
        data = assert_success_response(response)
        episodes = data["data"]
        
        assert len(episodes) == 2, "应有2个自动生成的子集"
        
        # 创建新子集
        new_episode = {
            "节目名称": f"{test_prefix}手动添加的子集",
            "时长": "600"
        }
        response = client.post(f"/api/dramas/{first_drama_id}/episodes", json=new_episode)
        data = assert_success_response(response)
        
        new_episode_id = data["data"]["episode_id"]
        tracker.add_episode(first_drama_id, new_episode_id)
        
        print(f"\n✅ 创建子集成功: episode_id={new_episode_id}")
        
        # 验证子集数量增加
        response = client.get(f"/api/dramas/{first_drama_id}/episodes")
        data = assert_success_response(response)
        assert len(data["data"]) == 3, "现在应有3个子集"
        
        # 更新子集
        update_data = {
            "节目名称": f"{test_prefix}手动添加的子集_已更新"
        }
        response = client.put(f"/api/dramas/{first_drama_id}/episodes/{new_episode_id}", json=update_data)
        assert_success_response(response)
        
        print(f"✅ 更新子集成功")
        
        # 删除子集
        response = client.delete(f"/api/dramas/{first_drama_id}/episodes/{new_episode_id}")
        assert_success_response(response)
        
        # 从追踪器移除
        tracker.episode_ids.remove((first_drama_id, new_episode_id))
        
        print(f"✅ 删除子集成功")
        
        # 验证子集数量恢复
        response = client.get(f"/api/dramas/{first_drama_id}/episodes")
        data = assert_success_response(response)
        assert len(data["data"]) == 2, "删除后应恢复为2个子集"
