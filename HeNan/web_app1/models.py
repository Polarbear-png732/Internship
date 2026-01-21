"""
Pydantic 数据模型定义
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal


# ============================================================
# 版权数据模型
# ============================================================

class CopyrightBase(BaseModel):
    """版权数据基础模型"""
    media_name: str = Field(..., min_length=1, max_length=200, description="介质名称")
    upstream_copyright: Optional[str] = Field(None, max_length=100, description="上游版权方")
    category_level1: Optional[str] = Field(None, max_length=50, description="一级分类")
    category_level2: Optional[str] = Field(None, max_length=50, description="二级分类")
    category_level1_henan: Optional[str] = Field(None, max_length=50, description="一级分类-河南")
    category_level2_henan: Optional[str] = Field(None, max_length=50, description="二级分类-河南")
    episode_count: Optional[int] = Field(None, ge=0, le=9999, description="集数")
    single_episode_duration: Optional[float] = Field(None, ge=0, description="单集时长(分钟)")
    total_duration: Optional[float] = Field(None, ge=0, description="总时长(分钟)")
    production_year: Optional[int] = Field(None, ge=1900, le=2100, description="出品年代")
    premiere_date: Optional[str] = Field(None, max_length=100, description="首播日期")
    production_region: Optional[str] = Field(None, max_length=100, description="出品地区")
    language: Optional[str] = Field(None, max_length=50, description="语言")
    language_henan: Optional[str] = Field(None, max_length=50, description="语言-河南")
    country: Optional[str] = Field(None, max_length=50, description="国家")
    director: Optional[str] = Field(None, max_length=200, description="导演")
    screenwriter: Optional[str] = Field(None, max_length=200, description="编剧")
    cast_members: Optional[str] = Field(None, max_length=500, description="主演")
    author: Optional[str] = Field(None, max_length=500, description="作者")
    recommendation: Optional[str] = Field(None, max_length=500, description="推荐语")
    synopsis: Optional[str] = Field(None, max_length=2000, description="简介")
    keywords: Optional[str] = Field(None, max_length=200, description="关键词")
    video_quality: Optional[str] = Field(None, max_length=50, description="视频质量")
    license_number: Optional[str] = Field(None, max_length=100, description="许可证号")
    rating: Optional[float] = Field(None, ge=0, le=10, description="评分")
    exclusive_status: Optional[str] = Field(None, max_length=20, description="独家状态")
    copyright_start_date: Optional[date] = Field(None, description="版权开始日期")
    copyright_end_date: Optional[date] = Field(None, description="版权结束日期")
    category_level2_shandong: Optional[str] = Field(None, max_length=100, description="二级分类-山东")
    authorization_region: Optional[str] = Field(None, max_length=200, description="授权区域")
    authorization_platform: Optional[str] = Field(None, max_length=200, description="授权平台")
    cooperation_mode: Optional[str] = Field(None, max_length=50, description="合作方式")

    class Config:
        from_attributes = True


class CopyrightCreate(CopyrightBase):
    """创建版权数据请求模型"""
    pass


class CopyrightUpdate(BaseModel):
    """更新版权数据请求模型（所有字段可选）"""
    media_name: Optional[str] = Field(None, min_length=1, max_length=200, description="介质名称")
    upstream_copyright: Optional[str] = Field(None, max_length=100, description="上游版权方")
    category_level1: Optional[str] = Field(None, max_length=50, description="一级分类")
    category_level2: Optional[str] = Field(None, max_length=50, description="二级分类")
    category_level1_henan: Optional[str] = Field(None, max_length=50, description="一级分类-河南")
    category_level2_henan: Optional[str] = Field(None, max_length=50, description="二级分类-河南")
    episode_count: Optional[int] = Field(None, ge=0, le=9999, description="集数")
    single_episode_duration: Optional[float] = Field(None, ge=0, description="单集时长(分钟)")
    total_duration: Optional[float] = Field(None, ge=0, description="总时长(分钟)")
    production_year: Optional[int] = Field(None, ge=1900, le=2100, description="出品年代")
    premiere_date: Optional[str] = Field(None, max_length=100, description="首播日期")
    production_region: Optional[str] = Field(None, max_length=100, description="出品地区")
    language: Optional[str] = Field(None, max_length=50, description="语言")
    language_henan: Optional[str] = Field(None, max_length=50, description="语言-河南")
    country: Optional[str] = Field(None, max_length=50, description="国家")
    director: Optional[str] = Field(None, max_length=200, description="导演")
    screenwriter: Optional[str] = Field(None, max_length=200, description="编剧")
    cast_members: Optional[str] = Field(None, max_length=500, description="主演")
    author: Optional[str] = Field(None, max_length=500, description="作者")
    recommendation: Optional[str] = Field(None, max_length=500, description="推荐语")
    synopsis: Optional[str] = Field(None, max_length=2000, description="简介")
    keywords: Optional[str] = Field(None, max_length=200, description="关键词")
    video_quality: Optional[str] = Field(None, max_length=50, description="视频质量")
    license_number: Optional[str] = Field(None, max_length=100, description="许可证号")
    rating: Optional[float] = Field(None, ge=0, le=10, description="评分")
    exclusive_status: Optional[str] = Field(None, max_length=20, description="独家状态")
    copyright_start_date: Optional[date] = Field(None, description="版权开始日期")
    copyright_end_date: Optional[date] = Field(None, description="版权结束日期")
    category_level2_shandong: Optional[str] = Field(None, max_length=100, description="二级分类-山东")
    authorization_region: Optional[str] = Field(None, max_length=200, description="授权区域")
    authorization_platform: Optional[str] = Field(None, max_length=200, description="授权平台")
    cooperation_mode: Optional[str] = Field(None, max_length=50, description="合作方式")

    class Config:
        from_attributes = True


class CopyrightResponse(CopyrightBase):
    """版权数据响应模型"""
    id: int
    drama_ids: Optional[Dict[str, int]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# 通用响应模型
# ============================================================

class ResponseBase(BaseModel):
    """通用响应基础模型"""
    code: int = 200
    message: str = "success"


class PaginatedResponse(ResponseBase):
    """分页响应模型"""
    data: Dict[str, Any]


class UpdateStats(BaseModel):
    """更新统计信息"""
    dramas_updated: int = 0
    episodes_added: int = 0
    episodes_deleted: int = 0
    episodes_updated: int = 0


class CopyrightUpdateResponse(ResponseBase):
    """版权更新响应模型"""
    data: Dict[str, Any]


# ============================================================
# 剧头/子集模型
# ============================================================

class DramaBase(BaseModel):
    """剧头基础模型"""
    drama_name: str = Field(..., min_length=1, max_length=200, description="剧集名称")
    customer_code: str = Field(..., min_length=1, max_length=50, description="客户代码")
    dynamic_properties: Optional[Dict[str, Any]] = Field(None, description="动态属性")

    class Config:
        from_attributes = True


class EpisodeBase(BaseModel):
    """子集基础模型"""
    drama_id: int = Field(..., description="剧头ID")
    episode_name: str = Field(..., min_length=1, max_length=200, description="节目名称")
    dynamic_properties: Optional[Dict[str, Any]] = Field(None, description="动态属性")

    class Config:
        from_attributes = True
