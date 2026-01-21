# 新增客户配置指南

## 概述

本系统采用**配置驱动**的设计，新增客户只需要在 `web_app1/config.py` 中添加配置，无需修改业务逻辑代码。

## 新增客户步骤

### 步骤1: 准备客户信息

在开始之前，需要准备以下信息：

1. **客户基本信息**
   - 客户名称（如：河北移动）
   - 客户代码（如：hebei_mobile）
   - 客户简称（如：hbyd）

2. **剧头字段配置**
   - 需要导出哪些字段
   - 字段的中文列名
   - 字段的数据来源（固定值/版权数据/计算值）

3. **子集字段配置**
   - 需要导出哪些字段
   - 字段的中文列名
   - 字段的数据来源

4. **URL模板**
   - 图片URL格式（竖图、横图）
   - 媒体URL格式

5. **映射配置**
   - 内容目录映射（content_dir_map）
   - 产品分类映射（product_category_map）
   - 一级分类映射（category_level1_map，可选）

### 步骤2: 修改 `web_app1/config.py`

在 `CUSTOMER_CONFIGS` 字典中添加新客户配置。

#### 2.1 基本配置模板

```python
'hebei_mobile': {  # 客户代码（唯一标识）
    'name': '河北移动',  # 客户名称
    'code': 'hbyd',  # 客户简称（用于URL等）
    'is_enabled': True,  # 是否启用
    'export_sheets': ['剧头', '子集'],  # 导出的工作表
    
    # 剧头字段配置
    'drama_columns': [
        # ... 字段配置
    ],
    
    # 子集字段配置
    'episode_columns': [
        # ... 字段配置
    ],
    
    # URL模板
    'image_url': {
        'vertical': 'http://example.com/img/{abbr}_v.jpg',
        'horizontal': 'http://example.com/img/{abbr}_h.jpg',
    },
    'media_url_template': 'http://example.com/media/{dir}/{abbr}/{abbr}{ep:03d}.ts',
    
    # 映射配置
    'content_dir_map': {'教育': 'edu', '_default': 'default'},
    'product_category_map': {'教育': 1, '_default': 0},
},
```

#### 2.2 字段配置详解

**剧头字段配置类型**：

1. **数据库字段**（直接映射）
```python
{'col': '剧头id', 'field': 'drama_id'}
{'col': '剧集名称', 'field': 'drama_name'}
```

2. **固定值**
```python
{'col': '清晰度', 'value': 1}
{'col': '版权', 'value': 1}
```

3. **从版权数据取值**
```python
{'col': '导演', 'source': 'director', 'default': '暂无'}
{'col': '总集数', 'source': 'episode_count', 'default': 0}
```

4. **带后缀**
```python
{'col': '描述', 'source': 'synopsis', 'suffix': '内容来源：XXX'}
```

5. **日期格式化**
```python
{'col': '版权开始时间', 'source': 'copyright_start_date', 'format': 'datetime'}
```

6. **特殊类型**
```python
# 图片URL
{'col': '竖图', 'type': 'image', 'image_type': 'vertical'}
{'col': '横图', 'type': 'image', 'image_type': 'horizontal'}

# 产品分类
{'col': '产品分类', 'type': 'product_category'}

# 是否多集
{'col': '是否多集', 'type': 'is_multi_episode'}

# 总时长（秒）
{'col': '总时长（秒）', 'type': 'total_duration_seconds'}

# 拼音缩写
{'col': '拼音缩写', 'type': 'pinyin_abbr'}

# 序号（导出时生成）
{'col': 'vod_no', 'type': 'sequence'}
```

**子集字段配置类型**：

1. **数据库字段**
```python
{'col': '子集id', 'field': 'episode_id'}
{'col': '节目名称', 'field': 'episode_name'}
```

2. **固定值**
```python
{'col': '媒体类型', 'value': 1}
{'col': '编码格式', 'value': 1}
```

3. **特殊类型**
```python
# 媒体URL
{'col': '媒体拉取地址', 'type': 'media_url'}

# 集数
{'col': '集数', 'type': 'episode_num'}

# 时长（秒）
{'col': '时长', 'type': 'duration'}

# 时长（分钟）
{'col': '时长（分）', 'type': 'duration_minutes'}

# 时长（HH:MM:SS）
{'col': '时长', 'type': 'duration_hhmmss'}

# 文件大小
{'col': '文件大小', 'type': 'file_size'}

# MD5
{'col': 'md5', 'type': 'md5'}

# 节目名称格式化
{'col': '节目名称', 'type': 'episode_name_format', 'format': '{drama_name}第{ep}集'}
```

#### 2.3 完整示例（参考河南移动）

```python
'hebei_mobile': {
    'name': '河北移动',
    'code': 'hbyd',
    'is_enabled': True,
    'export_sheets': ['剧头', '子集'],
    
    # 剧头字段配置
    'drama_columns': [
        {'col': '剧头id', 'field': 'drama_id'},
        {'col': '剧集名称', 'field': 'drama_name'},
        {'col': '作者列表', 'source': 'director', 'default': '暂无'},
        {'col': '清晰度', 'value': 1},
        {'col': '语言', 'source': 'language_henan', 'default': '简体中文'},
        {'col': '主演', 'source': 'cast_members', 'default': ''},
        {'col': '内容类型', 'source': 'category_level1_henan', 'default': '少儿'},
        {'col': '上映年份', 'source': 'production_year'},
        {'col': '关键字', 'source': 'keywords', 'default': ''},
        {'col': '评分', 'source': 'rating'},
        {'col': '推荐语', 'source': 'recommendation', 'default': ''},
        {'col': '总集数', 'source': 'episode_count', 'default': 0},
        {'col': '产品分类', 'type': 'product_category'},
        {'col': '竖图', 'type': 'image', 'image_type': 'vertical'},
        {'col': '描述', 'source': 'synopsis', 'default': ''},
        {'col': '横图', 'type': 'image', 'image_type': 'horizontal'},
        {'col': '版权', 'value': 1},
        {'col': '二级分类', 'source': 'category_level2_henan', 'default': ''},
    ],
    
    # 子集字段配置
    'episode_columns': [
        {'col': '子集id', 'field': 'episode_id'},
        {'col': '节目名称', 'field': 'episode_name'},
        {'col': '媒体拉取地址', 'type': 'media_url'},
        {'col': '媒体类型', 'value': 1},
        {'col': '编码格式', 'value': 1},
        {'col': '集数', 'type': 'episode_num'},
        {'col': '时长', 'type': 'duration'},
        {'col': '文件大小', 'type': 'file_size'},
    ],
    
    # URL模板
    'image_url': {
        'vertical': 'http://example.com/img/{abbr}_st.jpg',
        'horizontal': 'http://example.com/img/{abbr}_ht.jpg',
    },
    'media_url_template': 'ftp://user:pass@example.com/media/hbyd/{dir}/{abbr}/{abbr}{ep:03d}.ts',
    
    # 映射配置
    'content_dir_map': {'儿童': 'shaoer', '教育': 'jiaoyu', '_default': 'shaoer'},
    'product_category_map': {'教育': 1, '电竞': 2, '_default': 3},
},
```

### 步骤3: 验证配置

添加配置后，可以通过以下方式验证：

```python
# 在Python中测试
from web_app1.config import CUSTOMER_CONFIGS, get_enabled_customers

# 查看所有客户
print(CUSTOMER_CONFIGS.keys())

# 查看启用的客户
print(get_enabled_customers())

# 查看特定客户配置
print(CUSTOMER_CONFIGS['hebei_mobile'])
```

### 步骤4: 重启服务

修改配置后，需要重启FastAPI服务：

```powershell
# 查找进程
netstat -ano | findstr :8000

# 终止进程
taskkill /F /PID <PID>

# 重新启动
.\.venv\Scripts\Activate.ps1
python web_app1/main.py
```

### 步骤5: 测试新客户

1. **创建版权数据**
   - 访问 http://localhost:8000
   - 添加一条版权数据
   - 系统会自动为所有启用的客户（包括新客户）生成剧头和子集

2. **导出剧头子集**
   - 访问剧头子集导出页面
   - 选择新客户
   - 导出Excel验证字段是否正确

3. **检查数据库**
```sql
-- 查看新客户的剧头数据
SELECT * FROM drama_main WHERE customer_code = 'hebei_mobile';

-- 查看新客户的子集数据
SELECT * FROM drama_episode WHERE drama_id IN (
    SELECT drama_id FROM drama_main WHERE customer_code = 'hebei_mobile'
);
```

## 不需要修改的地方

✅ **无需修改业务逻辑代码**：
- `web_app1/routers/copyright.py` - 版权管理路由
- `web_app1/routers/episodes.py` - 剧头子集导出路由
- `web_app1/utils.py` - 工具函数
- `web_app1/services/import_service.py` - 导入服务

✅ **无需修改数据库结构**：
- 使用JSON字段存储动态属性，支持任意字段

✅ **无需修改前端代码**：
- 客户列表自动从配置读取

## 常见问题

### Q1: 如何临时禁用某个客户？

**A**: 将 `is_enabled` 设置为 `False`

```python
'hebei_mobile': {
    'name': '河北移动',
    'code': 'hbyd',
    'is_enabled': False,  # 禁用
    # ...
}
```

### Q2: 如何添加一级分类映射？

**A**: 添加 `category_level1_map` 配置（参考甘肃移动）

```python
'hebei_mobile': {
    # ...
    'category_level1_map': {
        '电竞': '体育',  # 电竞 → 体育
        '动漫': '少儿',  # 动漫 → 少儿
    },
    # ...
}
```

然后在剧头字段配置中添加 `'mapping': True`：

```python
{'col': '一级分类', 'source': 'category_level1', 'mapping': True},
```

### Q3: 如何自定义URL格式？

**A**: 修改 `image_url` 和 `media_url_template`

URL模板支持的占位符：
- `{abbr}` - 介质名称拼音缩写
- `{ep}` - 集数
- `{ep:02d}` - 集数（2位，补0）
- `{ep:03d}` - 集数（3位，补0）
- `{dir}` - 内容目录（从 content_dir_map 映射）

### Q4: 如何添加新的字段类型？

**A**: 需要在 `web_app1/routers/copyright.py` 中的以下函数添加处理逻辑：
- `_build_drama_props_for_customer()` - 剧头字段处理
- `_batch_create_episodes()` - 子集字段处理

### Q5: 如何导出多个工作表？

**A**: 修改 `export_sheets` 配置（参考江苏新媒体）

```python
'hebei_mobile': {
    # ...
    'export_sheets': ['剧头', '子集', '图片'],
    
    # 添加图片字段配置
    'picture_columns': [
        {'col': 'picture_no', 'type': 'sequence'},
        {'col': 'vod_no', 'type': 'drama_sequence'},
        # ...
    ],
}
```

## 配置示例对比

### 简单配置（河南移动）
- 标准字段
- 基本映射
- FTP媒体地址

### 复杂配置（山东移动）
- 带分隔符的字段
- 多种时长格式
- HTTP媒体地址

### 高级配置（甘肃移动）
- 一级分类映射
- 无默认产品分类
- 自定义目录映射

### 特殊配置（江苏新媒体）
- 三个工作表
- 序号自动生成
- 特殊字段格式

## 总结

新增客户的核心步骤：

1. ✅ **只需修改** `web_app1/config.py`
2. ✅ **添加配置** 到 `CUSTOMER_CONFIGS`
3. ✅ **重启服务** 使配置生效
4. ✅ **测试验证** 数据生成和导出

**优势**：
- 配置驱动，无需修改代码
- 支持灵活的字段定制
- 自动处理剧头和子集生成
- 支持多种数据源和格式

---

**最后更新**: 2026-01-21  
**版本**: 1.0
