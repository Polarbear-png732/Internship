"""
剧集数据查询与导出 Web 服务
基于 FastAPI 实现，提供剧集查询和Excel导出功能
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import pymysql
import json
import pandas as pd
from typing import Optional
from pydantic import BaseModel
import os
import tempfile

# 创建FastAPI应用
app = FastAPI(
    title="剧集数据查询系统",
    description="查询剧集信息并导出Excel",
    version="1.0.0"
)

# 配置CORS，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'polarbear',
    'database': 'operation_management',
    'charset': 'utf8mb4'
}

# 剧头数据列名顺序
DRAMA_HEADER_COLUMNS = [
    '剧头id', '剧集名称', '作者列表', '清晰度', '语言', '主演', '内容类型', '上映年份',
    '关键字', '评分', '推荐语', '总集数', '产品分类', '竖图', '描述', '横图', '版权', '二级分类'
]

# 子集数据列名顺序
SUBSET_COLUMNS = [
    '子集id', '节目名称', '媒体拉取地址', '媒体类型', '编码格式', '集数', '时长', '文件大小'
]

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")


def get_db_connection():
    """获取数据库连接"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """返回前端页面"""
    return FileResponse("static/index.html")


@app.get("/api/drama/search")
async def search_drama(name: str = Query(..., description="剧集名称")):
    """
    根据剧集名称查询剧头数据和子集数据
    """
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="剧集名称不能为空")
    
    name = name.strip()
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # 查询剧头数据
        query_header = "SELECT * FROM drama_main WHERE drama_name = %s"
        cursor.execute(query_header, (name,))
        header_result = cursor.fetchone()
        
        if not header_result:
            raise HTTPException(status_code=404, detail=f"未找到剧集 '{name}' 的数据")
        
        # 获取剧头表的列名
        header_columns = [desc[0] for desc in cursor.description]
        header_data = dict(zip(header_columns, header_result))
        
        # 解析dynamic_properties JSON
        dynamic_props = json.loads(header_data['dynamic_properties']) if header_data['dynamic_properties'] else {}
        
        # 构建剧头数据字典
        drama_header = {
            '剧头id': header_data['drama_id'],
            '剧集名称': header_data['drama_name'],
            '作者列表': dynamic_props.get('作者列表', ''),
            '清晰度': dynamic_props.get('清晰度', 0),
            '语言': dynamic_props.get('语言', ''),
            '主演': dynamic_props.get('主演', ''),
            '内容类型': dynamic_props.get('内容类型', ''),
            '上映年份': dynamic_props.get('上映年份', 0),
            '关键字': dynamic_props.get('关键字', ''),
            '评分': dynamic_props.get('评分', 0.0),
            '推荐语': dynamic_props.get('推荐语', ''),
            '总集数': dynamic_props.get('总集数', 0),
            '产品分类': dynamic_props.get('产品分类', 0),
            '竖图': dynamic_props.get('竖图', ''),
            '描述': dynamic_props.get('描述', ''),
            '横图': dynamic_props.get('横图', ''),
            '版权': dynamic_props.get('版权', 0),
            '二级分类': dynamic_props.get('二级分类', '')
        }
        
        # 查询子集数据
        query_subset = "SELECT * FROM drama_episode WHERE drama_id = %s ORDER BY episode_id"
        cursor.execute(query_subset, (header_data['drama_id'],))
        subset_results = cursor.fetchall()
        
        # 获取子集表的列名
        subset_columns_db = [desc[0] for desc in cursor.description]
        
        subset_list = []
        for i, subset_result in enumerate(subset_results, 1):
            subset_dict = dict(zip(subset_columns_db, subset_result))
            
            # 解析dynamic_properties JSON
            subset_dynamic_props = json.loads(subset_dict['dynamic_properties']) if subset_dict['dynamic_properties'] else {}
            
            # 构建子集数据字典
            subset_data = {
                '子集id': i,
                '节目名称': subset_dict['episode_name'],
                '媒体拉取地址': subset_dynamic_props.get('媒体拉取地址', ''),
                '媒体类型': subset_dynamic_props.get('媒体类型', 0),
                '编码格式': subset_dynamic_props.get('编码格式', 0),
                '集数': subset_dynamic_props.get('集数', 0),
                '时长': subset_dynamic_props.get('时长', 0),
                '文件大小': subset_dynamic_props.get('文件大小', 0)
            }
            subset_list.append(subset_data)
        
        return {
            "success": True,
            "data": {
                "drama_header": drama_header,
                "episodes": subset_list,
                "episode_count": len(subset_list)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询出错: {str(e)}")
    finally:
        conn.close()


@app.get("/api/drama/list")
async def list_dramas():
    """
    获取所有剧集名称列表（用于搜索建议）
    """
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT drama_id, drama_name FROM drama_main ORDER BY drama_id")
        results = cursor.fetchall()
        
        dramas = [{"id": row[0], "name": row[1]} for row in results]
        
        return {
            "success": True,
            "data": dramas,
            "total": len(dramas)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询出错: {str(e)}")
    finally:
        conn.close()


@app.get("/api/drama/export")
async def export_drama(name: str = Query(..., description="剧集名称")):
    """
    导出剧集数据为Excel文件
    """
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="剧集名称不能为空")
    
    name = name.strip()
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # 查询剧头数据
        query_header = "SELECT * FROM drama_main WHERE drama_name = %s"
        cursor.execute(query_header, (name,))
        header_result = cursor.fetchone()
        
        if not header_result:
            raise HTTPException(status_code=404, detail=f"未找到剧集 '{name}' 的数据")
        
        # 获取剧头表的列名
        header_columns = [desc[0] for desc in cursor.description]
        header_data = dict(zip(header_columns, header_result))
        
        # 解析dynamic_properties JSON
        dynamic_props = json.loads(header_data['dynamic_properties']) if header_data['dynamic_properties'] else {}
        
        # 构建剧头数据字典
        header_dict = {
            '剧头id': '',
            '剧集名称': header_data['drama_name'],
            '作者列表': dynamic_props.get('作者列表', ''),
            '清晰度': dynamic_props.get('清晰度', 0),
            '语言': dynamic_props.get('语言', ''),
            '主演': dynamic_props.get('主演', ''),
            '内容类型': dynamic_props.get('内容类型', ''),
            '上映年份': dynamic_props.get('上映年份', 0),
            '关键字': dynamic_props.get('关键字', ''),
            '评分': dynamic_props.get('评分', 0.0),
            '推荐语': dynamic_props.get('推荐语', ''),
            '总集数': dynamic_props.get('总集数', 0),
            '产品分类': dynamic_props.get('产品分类', 0),
            '竖图': dynamic_props.get('竖图', ''),
            '描述': dynamic_props.get('描述', ''),
            '横图': dynamic_props.get('横图', ''),
            '版权': dynamic_props.get('版权', 0),
            '二级分类': dynamic_props.get('二级分类', '')
        }
        
        # 转换为DataFrame
        header_df = pd.DataFrame([header_dict], columns=DRAMA_HEADER_COLUMNS)
        
        # 查询子集数据
        query_subset = "SELECT * FROM drama_episode WHERE drama_id = %s ORDER BY episode_id"
        cursor.execute(query_subset, (header_data['drama_id'],))
        subset_results = cursor.fetchall()
        
        # 获取子集表的列名
        subset_columns_db = [desc[0] for desc in cursor.description]
        
        subset_data_list = []
        for i, subset_result in enumerate(subset_results, 1):
            subset_dict = dict(zip(subset_columns_db, subset_result))
            
            # 解析dynamic_properties JSON
            subset_dynamic_props = json.loads(subset_dict['dynamic_properties']) if subset_dict['dynamic_properties'] else {}
            
            # 构建子集数据字典
            subset_data = {
                '子集id': '',
                '节目名称': subset_dict['episode_name'],
                '媒体拉取地址': subset_dynamic_props.get('媒体拉取地址', ''),
                '媒体类型': subset_dynamic_props.get('媒体类型', 0),
                '编码格式': subset_dynamic_props.get('编码格式', 0),
                '集数': subset_dynamic_props.get('集数', 0),
                '时长': subset_dynamic_props.get('时长', 0),
                '文件大小': subset_dynamic_props.get('文件大小', 0)
            }
            subset_data_list.append(subset_data)
        
        # 转换为DataFrame
        subset_df = pd.DataFrame(subset_data_list, columns=SUBSET_COLUMNS)
        
        # 创建临时Excel文件
        temp_dir = tempfile.gettempdir()
        filename = f"{name}_数据.xlsx"
        filepath = os.path.join(temp_dir, filename)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            header_df.to_excel(writer, sheet_name='剧头', index=False)
            subset_df.to_excel(writer, sheet_name='子集', index=False)
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出出错: {str(e)}")
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
