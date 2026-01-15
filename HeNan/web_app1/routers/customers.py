from fastapi import APIRouter, HTTPException
import pymysql
from database import get_db

router = APIRouter(prefix="/api/customers", tags=["客户管理"])


@router.get("")
async def get_customers():
    """获取客户列表"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("""
                SELECT customer_id, customer_name, customer_code, remark, created_at, updated_at
                FROM customer ORDER BY created_at DESC
            """)
            customers = cursor.fetchall()
            
            for customer in customers:
                cursor.execute("SELECT COUNT(*) as count FROM drama_main WHERE customer_id = %s", 
                             (customer['customer_id'],))
                result = cursor.fetchone()
                customer['drama_count'] = result['count'] if result else 0
            
            return {"code": 200, "message": "success", "data": customers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
