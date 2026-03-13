"""
客户管理路由模块
提供客户（省份运营商）的查询和管理功能，支持多客户配置驱动的业务逻辑
"""
from fastapi import APIRouter, HTTPException
import pymysql
from database import get_db
from config import CUSTOMER_CONFIGS

router = APIRouter(prefix="/api/customers", tags=["客户管理"])


@router.get("")
def get_customers():
    """获取客户列表（从配置读取）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            customers = []
            for code, config in CUSTOMER_CONFIGS.items():
                if not config.get('is_enabled', True):
                    continue
                
                # 统计该客户的剧头数量
                cursor.execute(
                    "SELECT COUNT(*) as count FROM drama_main WHERE customer_code = %s",
                    (code,)
                )
                result = cursor.fetchone()
                drama_count = result['count'] if result else 0
                
                customers.append({
                    'customer_id': code,  # 使用 code 作为 ID
                    'customer_code': code,
                    'customer_name': config['name'],
                    'drama_count': drama_count,
                    'remark': f"导出格式: {', '.join(config.get('export_sheets', []))}"
                })
            
            return {"code": 200, "message": "success", "data": customers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
