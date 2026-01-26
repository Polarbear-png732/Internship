"""
客户管理接口测试
测试 /api/customers 相关接口
"""
import pytest
from conftest import assert_success_response


class TestCustomers:
    """客户管理测试类"""
    
    def test_get_customers_success(self, client):
        """测试获取客户列表"""
        response = client.get("/api/customers")
        data = assert_success_response(response)
        
        # 验证返回数据结构
        assert "data" in data
        customers = data["data"]
        assert isinstance(customers, list)
        
        # 验证至少有一个客户
        assert len(customers) > 0, "客户列表不应为空"
        
        # 验证客户数据结构
        first_customer = customers[0]
        required_fields = ["customer_id", "customer_code", "customer_name", "drama_count"]
        for field in required_fields:
            assert field in first_customer, f"客户数据缺少字段: {field}"
    
    def test_get_customers_contains_known_customers(self, client):
        """验证客户列表包含已知的客户"""
        response = client.get("/api/customers")
        data = assert_success_response(response)
        
        customers = data["data"]
        customer_codes = [c["customer_code"] for c in customers]
        
        # 验证包含主要客户
        expected_customers = ["henan_mobile", "shandong_mobile", "jiangsu_newmedia"]
        for code in expected_customers:
            assert code in customer_codes, f"客户列表应包含 {code}"
    
    def test_get_customers_drama_count_is_number(self, client):
        """验证剧集数量是数字类型"""
        response = client.get("/api/customers")
        data = assert_success_response(response)
        
        for customer in data["data"]:
            assert isinstance(customer["drama_count"], int), "drama_count 应为整数"
            assert customer["drama_count"] >= 0, "drama_count 不应为负数"
