# 多客户扩展方案文档

## 一、背景

当前系统按河南移动需求开发，现需支持山东移动、甘肃移动、江苏新媒体等多个客户，各客户的剧头表、子集表字段结构不同。

**核心需求**：
- 同一条版权数据可能被多个省份使用
- 各省份需要不同格式的剧头/子集
- 新增版权时自动为所有客户生成
- 新增客户时能批量补全已有版权数据
- 支持导出各客户格式的Excel注入表

---

## 二、各客户字段需求对比

### 2.1 剧头字段对比

| 字段 | 河南移动 | 山东移动 | 甘肃移动 | 江苏新媒体 | 说明 |
|------|:-------:|:-------:|:-------:|:--------:|------|
| 剧头id/序号 | 剧头id | 剧头id | 剧头id | vod_no(序号) | 江苏用序号 |
| sId | ✗ | ✗ | ✗ | ✓(自动生成) | 江苏独有 |
| appId | ✗ | ✗ | ✗ | ✓(固定=2) | 江苏独有 |
| 剧集名称 | ✓ | ✓ | ✓ | seriesName | |
| 作者列表/导演 | 作者列表 | 导演 | 导演 | director | 字段名不同 |
| 清晰度 | ✓ | ✓ | ✓ | ✗ | 江苏无 |
| 语言 | ✓ | ✓ | ✓ | language | |
| 主演 | ✓ | ✓ | ✓ | actorDisplay | |
| 内容类型/一级分类 | 内容类型 | 一级分类 | 一级分类 | pgmCategory | |
| 上映年份 | ✓ | ✓ | ✓ | releaseYear | |
| 关键字 | ✓ | ✗ | ✗ | ✗ | 河南独有 |
| 评分 | ✓ | ✓ | ✓ | rating | |
| 推荐语 | ✓ | ✗ | ✗ | ✗ | 河南独有 |
| 总集数 | ✓ | ✓ | ✓ | volumnCount | |
| 产品分类 | ✓ | ✓ | ✓ | ✗ | 江苏无 |
| 竖图 | ✓ | ✓ | ✓ | ✗ | 江苏用图片表 |
| 横图 | ✓ | ✓ | ✓ | ✗ | 江苏用图片表 |
| 描述/简介 | ✓ | ✓ | ✓ | description | |
| 版权 | ✓ | ✗ | ✗ | ✗ | 河南独有 |
| 二级分类 | ✓(河南) | ✓(山东) | ✓ | pgmSedClass | |
| 国家地区 | ✗ | ✓ | ✓ | originalCountry | |
| 是否多集 | ✗ | ✓ | ✓ | ✗ | |
| 单集时长 | ✗ | ✓ | ✓ | ✗ | |
| 编剧 | ✗ | ✓ | ✓ | ✗ | |
| 版权开始时间 | ✗ | ✓ | ✓ | ✗ | |
| 版权结束时间 | ✗ | ✓ | ✓ | ✗ | |
| 是否付费 | ✗ | ✓ | ✗ | ✗ | 山东独有 |
| seriesFlag | ✗ | ✗ | ✗ | ✓(固定=1) | 江苏独有 |
| sortName | ✗ | ✗ | ✗ | ✓(拼音缩写) | 江苏独有 |
| programType | ✗ | ✗ | ✗ | ✓(维高绘本) | 江苏独有 |

### 2.2 子集字段对比

| 字段 | 河南移动 | 山东移动 | 甘肃移动 | 江苏新媒体 | 说明 |
|------|:-------:|:-------:|:-------:|:--------:|------|
| 子集id/序号 | 子集id | 子集id | 子集id | vod_info_no | |
| 剧头关联 | drama_id | ✗ | ✗ | vod_no(剧头序号) | |
| sId/pId | ✗ | ✗ | ✗ | ✓ | 江苏独有 |
| 节目名称 | ✓ | ✓ | ✓ | programName | 江苏带HD后缀 |
| 媒体拉取地址 | FTP(.ts) | HTTP(.m3u8) | FTP(.ts) | fileURL(相对路径) | 格式不同 |
| 媒体类型 | ✓ | ✗ | ✗ | type(固定=1) | |
| 编码格式 | ✓ | ✗ | ✗ | ✗ | 河南独有 |
| 集数 | ✓ | ✓ | ✓ | volumnCount | |
| 时长 | ✓(HHMMSS00) | ✓(分钟) | ✗ | duration(HH:MM:SS) | 格式不同 |
| 文件大小 | ✓ | ✗ | ✗ | ✗ | 河南独有 |
| md5 | ✗ | ✓ | ✓ | ✗ | |
| 是否付费 | ✗ | ✓ | ✗ | ✗ | 山东独有 |
| 片头跳过时间点 | ✗ | ✓ | ✗ | ✗ | 山东独有 |
| 片尾跳过时间点 | ✗ | ✓ | ✗ | ✗ | 山东独有 |
| bitRateType | ✗ | ✗ | ✗ | ✓(固定=8) | 江苏独有 |
| mediaSpec | ✗ | ✗ | ✗ | ✓(固定值) | 江苏独有 |

### 2.3 江苏新媒体特有：图片表

| 字段 | 说明 |
|------|------|
| picture_no | 序号 |
| vod_no | 剧头序号 |
| sId | 剧头Id |
| picId | 图片Id |
| type | 类型(0=竖图, 1=横图) |
| sequence | 排序(1, 2) |
| fileURL | 文件地址(相对路径) |

**注意**：江苏新媒体需要生成3个sheet：剧头、子集、图片

---

### 2.4 URL模板对比

| 客户 | 竖图URL | 横图URL |
|------|---------|---------|
| 河南移动 | `http://36.133.168.235:18181/img/{abbr}_st.jpg` | `http://36.133.168.235:18181/img/{abbr}_ht.jpg` |
| 山东移动 | `http://120.27.12.82:28080/img/sdyd/{abbr}01.jpg` | `http://120.27.12.82:28080/img/sdyd/{abbr}02.jpg` |
| 甘肃移动 | `http://120.27.12.82:28080/img/gsyd/{abbr}01.jpg` | `http://120.27.12.82:28080/img/gsyd/{abbr}02.jpg` |
| 江苏新媒体 | `/img/{abbr}/0.jpg` (相对路径) | `/img/{abbr}/1.jpg` (相对路径) |

| 客户 | 媒体拉取地址模板 |
|------|-----------------|
| 河南移动 | `ftp://ftpmediazjyd:rD2q0y1M5eI@36.133.168.235:2121/media/hnyd/{dir}/{abbr}/{abbr}{ep:03d}.ts` |
| 山东移动 | `http://120.27.12.82:28080/hls/sdyd/{abbr}/{abbr}{ep:03d}/index.m3u8` |
| 甘肃移动 | `ftp://ftpmedia:rD2q0y!M5eI2@36.133.168.235:2121/media/gsyd/{dir}/{abbr}/{abbr}{ep:03d}.ts` |
| 江苏新媒体 | `/vod/{abbr}/{abbr}{ep:02d}.ts` (相对路径) |

### 2.5 内容目录映射对比

| 客户 | 一级分类 → 目录 |
|------|----------------|
| 河南移动 | 儿童→shaoer, 教育→mqxt, 电竞→rywg |
| 山东移动 | 电竞→dianjing (固定) |
| 甘肃移动 | 体育→dianjing, 教育→jiaoyu, 动漫→dongman |
| 江苏新媒体 | 无目录区分 |

### 2.6 产品分类映射对比

| 客户 | 一级分类 → 产品分类 |
|------|-------------------|
| 河南移动 | 教育→1, 电竞→2, 其他→3 |
| 山东移动 | 电竞→1 (固定) |
| 甘肃移动 | 教育→1, 体育→2, 动漫→3 |
| 江苏新媒体 | 无产品分类字段 |


---

## 三、导出Excel模板格式

### 3.1 河南移动

**剧头表列**：剧头id, 剧集名称, 作者列表, 清晰度, 语言, 主演, 内容类型, 上映年份, 关键字, 评分, 推荐语, 总集数, 产品分类, 竖图, 描述, 横图, 版权, 二级分类

**子集表列**：子集id, 节目名称, 媒体拉取地址, 媒体类型, 编码格式, 集数, 时长, 文件大小

### 3.2 山东移动

**剧头表列**：剧头id, 剧集名称, 导演, 清晰度, 总集数, 主演, 一级分类, 二级分类, 国家地区, 上映年份, 语言, 竖版大海报地址, 横版海报地址, 产品分类, 描述, 是否多集, 单集时长（分）, 评分, 编剧, 版权开始时间, 版权结束时间, 是否付费

**子集表列**：子集id, 节目名称, 媒体拉取地址, md5, 时长（分）, 集数, 是否付费, 片头跳过时间点（整数秒）, 片尾跳过时间点（整数秒）

### 3.3 甘肃移动

**剧头表列**：剧头id, 剧集名称, 导演, 清晰度, 总集数, 主演, 一级分类, 二级分类, 国家地区, 上映年份, 语言, 竖版大海报地址, 横版海报地址, 产品分类, 描述, 是否多集, 单集时长（分）, 评分, 编剧, 版权开始时间, 版权结束时间, 集数

**子集表列**：子集id, 节目名称, 媒体拉取地址, 集数, md5值

### 3.4 江苏新媒体（3个sheet）

**剧头表列**：vod_no, sId, appId, seriesName, volumnCount, description, seriesFlag, sortName, programType, releaseYear, language, rating, originalCountry, pgmCategory, pgmSedClass, director, actorDisplay

**子集表列**：vod_info_no, vod_no, sId, pId, programName, volumnCount, type, fileURL, duration, bitRateType, mediaSpec

**图片表列**：picture_no, vod_no, sId, picId, type, sequence, fileURL

---

## 四、数据模型设计

### 4.1 核心问题

同一条版权数据需要为多个客户生成不同格式的剧头/子集：

```
copyright_content (1条，媒体名称="汪汪队立大功")
    │
    ├── drama_main (id=101, customer_code='henan_mobile')
    │       └── drama_episode × N (河南格式)
    │
    ├── drama_main (id=102, customer_code='shandong_mobile')
    │       └── drama_episode × N (山东格式)
    │
    ├── drama_main (id=103, customer_code='gansu_mobile')
    │       └── drama_episode × N (甘肃格式)
    │
    └── drama_main (id=104, customer_code='jiangsu_newmedia')
            └── drama_episode × N (江苏格式)
            └── drama_picture × N (江苏图片，可选)
```

### 4.2 数据库改动

```sql
-- 1. drama_main 表增加客户标识
ALTER TABLE drama_main ADD COLUMN customer_code VARCHAR(50) DEFAULT 'henan_mobile' COMMENT '客户代码';
ALTER TABLE drama_main ADD INDEX idx_customer_code (customer_code);

-- 2. copyright_content 表改为存多个drama_id（JSON格式）
ALTER TABLE copyright_content 
    CHANGE COLUMN drama_id drama_ids JSON COMMENT '各客户的剧头ID，如{"henan_mobile":101,"shandong_mobile":102}';

-- 3. 可选：江苏新媒体需要图片表（或存入dynamic_properties）
CREATE TABLE drama_picture (
    picture_id INT PRIMARY KEY AUTO_INCREMENT,
    drama_id INT NOT NULL,
    picture_type TINYINT COMMENT '0=竖图, 1=横图',
    sequence INT DEFAULT 1,
    file_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_drama_id (drama_id)
);

-- 4. 可选：客户配置表
CREATE TABLE customer_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_code VARCHAR(50) NOT NULL UNIQUE COMMENT '客户代码',
    customer_name VARCHAR(100) NOT NULL COMMENT '客户名称',
    is_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    config_json JSON COMMENT '客户配置（字段、URL模板等）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```


---

## 五、业务流程设计

### 5.1 整体流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                       版权数据管理系统                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                                                │
│  │ 新增版权数据 │──→ 遍历所有已启用客户 ──→ 自动生成各客户剧头/子集  │
│  └─────────────┘                                                │
│                                                                 │
│  ┌─────────────┐                                                │
│  │ 新增客户配置 │──→ 遍历所有版权数据 ──→ 批量补全该客户剧头/子集    │
│  └─────────────┘                                                │
│                                                                 │
│  ┌─────────────┐                                                │
│  │ 更新版权数据 │──→ 同步更新所有关联的剧头/子集                   │
│  └─────────────┘                                                │
│                                                                 │
│  ┌─────────────┐                                                │
│  │ 删除版权数据 │──→ 同步删除所有关联的剧头/子集                   │
│  └─────────────┘                                                │
│                                                                 │
│  ┌─────────────┐                                                │
│  │ 导出注入表   │──→ 选择客户 ──→ 按客户格式生成Excel              │
│  └─────────────┘                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 新增版权数据流程

```python
@router.post("/api/copyright")
async def create_copyright(data: Dict[str, Any]):
    """创建版权数据，自动为所有启用的客户生成剧头/子集"""
    
    # 1. 插入版权数据
    cursor.execute("INSERT INTO copyright_content (...) VALUES (...)")
    copyright_id = cursor.lastrowid
    
    # 2. 获取所有启用的客户
    enabled_customers = get_enabled_customers()
    # ['henan_mobile', 'shandong_mobile', 'gansu_mobile', 'jiangsu_newmedia']
    
    drama_ids = {}
    
    # 3. 为每个客户生成剧头+子集
    for customer_code in enabled_customers:
        drama_id = create_drama_for_customer(data, customer_code)
        drama_ids[customer_code] = drama_id
    
    # 4. 更新版权表的关联关系
    cursor.execute(
        "UPDATE copyright_content SET drama_ids = %s WHERE id = %s",
        (json.dumps(drama_ids), copyright_id)
    )
    
    return {"code": 200, "data": {"copyright_id": copyright_id, "drama_ids": drama_ids}}
```

### 5.3 新增客户时批量补全流程

```python
@router.post("/api/customer/batch-generate")
async def batch_generate_for_customer(customer_code: str):
    """为新客户批量生成所有版权数据的剧头/子集"""
    
    cursor.execute("SELECT * FROM copyright_content")
    all_copyrights = cursor.fetchall()
    
    generated_count = 0
    
    for copyright_data in all_copyrights:
        drama_ids = json.loads(copyright_data['drama_ids'] or '{}')
        
        if customer_code in drama_ids:
            continue  # 已存在，跳过
        
        # 为该客户生成剧头+子集
        drama_id = create_drama_for_customer(copyright_data, customer_code)
        drama_ids[customer_code] = drama_id
        
        cursor.execute(
            "UPDATE copyright_content SET drama_ids = %s WHERE id = %s",
            (json.dumps(drama_ids), copyright_data['id'])
        )
        generated_count += 1
    
    return {"message": f"已为 {customer_code} 生成 {generated_count} 条剧头数据"}
```

### 5.4 导出注入表流程

```python
@router.get("/api/export/{customer_code}")
async def export_injection_table(customer_code: str):
    """导出指定客户格式的注入表Excel"""
    
    config = CUSTOMER_CONFIGS[customer_code]
    
    # 查询该客户的所有剧头数据
    cursor.execute(
        "SELECT * FROM drama_main WHERE customer_code = %s",
        (customer_code,)
    )
    dramas = cursor.fetchall()
    
    # 根据客户配置生成Excel
    if customer_code == 'jiangsu_newmedia':
        # 江苏需要3个sheet
        return generate_jiangsu_excel(dramas, config)
    else:
        # 其他客户2个sheet
        return generate_standard_excel(dramas, config)
```


---

## 六、配置结构设计

### 6.1 客户配置示例

```python
CUSTOMER_CONFIGS = {
    'henan_mobile': {
        'name': '河南移动',
        'code': 'hnyd',
        'is_enabled': True,
        'export_sheets': ['剧头', '子集'],
        
        # 剧头字段配置
        'drama_columns': [
            {'excel_col': '剧头id', 'db_field': 'drama_id'},
            {'excel_col': '剧集名称', 'db_field': 'drama_name'},
            {'excel_col': '作者列表', 'source': 'director', 'default': '暂无'},
            {'excel_col': '清晰度', 'value': 1},
            {'excel_col': '语言', 'source': 'language_henan'},
            {'excel_col': '主演', 'source': 'cast_members'},
            {'excel_col': '内容类型', 'source': 'category_level1_henan'},
            {'excel_col': '上映年份', 'source': 'production_year'},
            {'excel_col': '关键字', 'source': 'keywords'},
            {'excel_col': '评分', 'source': 'rating'},
            {'excel_col': '推荐语', 'source': 'recommendation'},
            {'excel_col': '总集数', 'source': 'episode_count'},
            {'excel_col': '产品分类', 'type': 'product_category'},
            {'excel_col': '竖图', 'type': 'image', 'image_type': 'vertical'},
            {'excel_col': '描述', 'source': 'synopsis'},
            {'excel_col': '横图', 'type': 'image', 'image_type': 'horizontal'},
            {'excel_col': '版权', 'value': 1},
            {'excel_col': '二级分类', 'source': 'category_level2_henan'},
        ],
        
        # 子集字段配置
        'episode_columns': [
            {'excel_col': '子集id', 'db_field': 'episode_id'},
            {'excel_col': '节目名称', 'db_field': 'episode_name'},
            {'excel_col': '媒体拉取地址', 'type': 'media_url'},
            {'excel_col': '媒体类型', 'value': 1},
            {'excel_col': '编码格式', 'value': 1},
            {'excel_col': '集数', 'type': 'episode_num'},
            {'excel_col': '时长', 'type': 'duration', 'format': 'HHMMSS00'},
            {'excel_col': '文件大小', 'type': 'file_size'},
        ],
        
        # URL模板
        'image_url': {
            'vertical': 'http://36.133.168.235:18181/img/{abbr}_st.jpg',
            'horizontal': 'http://36.133.168.235:18181/img/{abbr}_ht.jpg',
        },
        'media_url_template': 'ftp://ftpmediazjyd:rD2q0y1M5eI@36.133.168.235:2121/media/hnyd/{dir}/{abbr}/{abbr}{ep:03d}.ts',
        
        # 映射配置
        'content_dir_map': {'儿童': 'shaoer', '教育': 'mqxt', '电竞': 'rywg'},
        'product_category_map': {'教育': 1, '电竞': 2, '_default': 3},
    },
    
    'shandong_mobile': {
        'name': '山东移动',
        'code': 'sdyd',
        'is_enabled': True,
        'export_sheets': ['剧头', '子集'],
        
        'drama_columns': [
            {'excel_col': '剧头id', 'db_field': 'drama_id'},
            {'excel_col': '剧集名称', 'db_field': 'drama_name'},
            {'excel_col': '导演', 'source': 'director', 'default': '佚名'},
            {'excel_col': '清晰度', 'value': 1},
            {'excel_col': '总集数', 'source': 'episode_count'},
            {'excel_col': '主演', 'source': 'cast_members', 'default': '佚名'},
            {'excel_col': '一级分类', 'value': '电竞'},
            {'excel_col': '二级分类', 'source': 'category_level2_shandong'},
            {'excel_col': '国家地区', 'source': 'country', 'default': '中国'},
            {'excel_col': '上映年份', 'source': 'production_year'},
            {'excel_col': '语言', 'source': 'language', 'default': '普通话'},
            {'excel_col': '竖版大海报地址', 'type': 'image', 'image_type': 'vertical'},
            {'excel_col': '横版海报地址', 'type': 'image', 'image_type': 'horizontal'},
            {'excel_col': '产品分类', 'value': 1},
            {'excel_col': '描述', 'source': 'synopsis', 'suffix': '内容来源：杭州维高'},
            {'excel_col': '是否多集', 'type': 'is_multi_episode'},
            {'excel_col': '单集时长（分）', 'type': 'total_duration_seconds'},
            {'excel_col': '评分', 'source': 'rating'},
            {'excel_col': '编剧', 'source': 'screenwriter', 'default': '佚名'},
            {'excel_col': '版权开始时间', 'source': 'copyright_start_date', 'format': 'datetime'},
            {'excel_col': '版权结束时间', 'source': 'copyright_end_date', 'format': 'datetime'},
            {'excel_col': '是否付费', 'value': 1},
        ],
        
        'episode_columns': [
            {'excel_col': '子集id', 'db_field': 'episode_id'},
            {'excel_col': '节目名称', 'type': 'episode_name', 'format': '{drama_name}第{ep}集'},
            {'excel_col': '媒体拉取地址', 'type': 'media_url'},
            {'excel_col': 'md5', 'type': 'md5'},
            {'excel_col': '时长（分）', 'type': 'duration', 'format': 'minutes'},
            {'excel_col': '集数', 'type': 'episode_num'},
            {'excel_col': '是否付费', 'value': 1},
            {'excel_col': '片头跳过时间点（整数秒）', 'value': 0},
            {'excel_col': '片尾跳过时间点（整数秒）', 'value': 0},
        ],
        
        'image_url': {
            'vertical': 'http://120.27.12.82:28080/img/sdyd/{abbr}01.jpg',
            'horizontal': 'http://120.27.12.82:28080/img/sdyd/{abbr}02.jpg',
        },
        'media_url_template': 'http://120.27.12.82:28080/hls/sdyd/{abbr}/{abbr}{ep:03d}/index.m3u8',
    },
    
    'gansu_mobile': {
        'name': '甘肃移动',
        'code': 'gsyd',
        'is_enabled': True,
        'export_sheets': ['剧头', '子集'],
        
        # ... 甘肃配置（类似山东）
        
        'image_url': {
            'vertical': 'http://120.27.12.82:28080/img/gsyd/{abbr}01.jpg',
            'horizontal': 'http://120.27.12.82:28080/img/gsyd/{abbr}02.jpg',
        },
        'media_url_template': 'ftp://ftpmedia:rD2q0y!M5eI2@36.133.168.235:2121/media/gsyd/{dir}/{abbr}/{abbr}{ep:03d}.ts',
        'content_dir_map': {'体育': 'dianjing', '教育': 'jiaoyu', '动漫': 'dongman'},
        'product_category_map': {'教育': 1, '体育': 2, '动漫': 3},
    },
    
    'jiangsu_newmedia': {
        'name': '江苏新媒体',
        'code': 'jsnmt',
        'is_enabled': True,
        'export_sheets': ['剧头', '子集', '图片'],  # 3个sheet
        
        'drama_columns': [
            {'excel_col': 'vod_no', 'type': 'sequence'},  # 序号
            {'excel_col': 'sId', 'db_field': 'drama_id'},
            {'excel_col': 'appId', 'value': 2},
            {'excel_col': 'seriesName', 'db_field': 'drama_name'},
            {'excel_col': 'volumnCount', 'source': 'episode_count'},
            {'excel_col': 'description', 'source': 'synopsis'},
            {'excel_col': 'seriesFlag', 'value': 1},
            {'excel_col': 'sortName', 'type': 'pinyin_abbr'},
            {'excel_col': 'programType', 'value': '维高绘本'},
            {'excel_col': 'releaseYear', 'source': 'production_year'},
            {'excel_col': 'language', 'source': 'language', 'default': '国语'},
            {'excel_col': 'rating', 'source': 'rating'},
            {'excel_col': 'originalCountry', 'source': 'country', 'default': '中国'},
            {'excel_col': 'pgmCategory', 'value': '少儿'},
            {'excel_col': 'pgmSedClass', 'value': '启蒙,教育,益智'},
            {'excel_col': 'director', 'source': 'director', 'default': '佚名'},
            {'excel_col': 'actorDisplay', 'source': 'cast_members', 'default': '佚名'},
        ],
        
        'episode_columns': [
            {'excel_col': 'vod_info_no', 'type': 'sequence'},
            {'excel_col': 'vod_no', 'type': 'drama_sequence'},  # 关联剧头序号
            {'excel_col': 'sId', 'db_field': 'drama_id'},
            {'excel_col': 'pId', 'db_field': 'episode_id'},
            {'excel_col': 'programName', 'type': 'episode_name', 'format': '{drama_name} {ep:03d} HD'},
            {'excel_col': 'volumnCount', 'type': 'episode_num'},
            {'excel_col': 'type', 'value': 1},
            {'excel_col': 'fileURL', 'type': 'media_url'},
            {'excel_col': 'duration', 'type': 'duration', 'format': 'HH:MM:SS'},
            {'excel_col': 'bitRateType', 'value': 8},
            {'excel_col': 'mediaSpec', 'value': 'TS-VBR-H.264-8000-1080i-25-MP2-128'},
        ],
        
        'picture_columns': [
            {'excel_col': 'picture_no', 'type': 'sequence'},
            {'excel_col': 'vod_no', 'type': 'drama_sequence'},
            {'excel_col': 'sId', 'db_field': 'drama_id'},
            {'excel_col': 'picId', 'value': None},
            {'excel_col': 'type', 'type': 'picture_type'},  # 0或1
            {'excel_col': 'sequence', 'type': 'picture_sequence'},  # 1或2
            {'excel_col': 'fileURL', 'type': 'image_url'},
        ],
        
        'image_url': {
            'vertical': '/img/{abbr}/0.jpg',
            'horizontal': '/img/{abbr}/1.jpg',
        },
        'media_url_template': '/vod/{abbr}/{abbr}{ep:02d}.ts',
    },
}
```


---

## 七、现有代码改造清单

### 7.1 数据库层面

| 改动项 | 说明 | 工作量 |
|--------|------|--------|
| `drama_main` 增加 `customer_code` 字段 | 区分不同客户的剧头 | 5分钟 |
| `copyright_content` 的 `drama_id` 改为 `drama_ids` (JSON) | 支持关联多个剧头 | 5分钟 |
| 可选：新增 `drama_picture` 表 | 江苏新媒体图片数据 | 10分钟 |
| 可选：新增 `customer_config` 表 | 数据库管理客户配置 | 10分钟 |

### 7.2 后端代码

| 文件 | 改造内容 | 工作量 |
|------|---------|--------|
| `config.py` | 添加 CUSTOMER_CONFIGS 多客户配置 | 2小时 |
| `utils.py` | 函数增加 customer_code 参数 | 0.5小时 |
| `routers/copyright.py` | 创建时为所有客户生成剧头/子集 | 3小时 |
| `routers/dramas.py` | 导出时根据客户配置生成Excel | 2小时 |
| 新增 `routers/export.py` | 各客户格式的导出API | 2小时 |
| 新增 `routers/customer.py` | 客户管理、批量生成API | 1小时 |

### 7.3 前端代码

| 文件 | 改造内容 | 工作量 |
|------|---------|--------|
| `index.html` | 添加客户选择、导出按钮 | 1小时 |
| `main.js` | 导出功能、客户切换 | 1小时 |

---

## 八、工作量汇总

### 方案A：基础多客户支持

| 改动项 | 工作量 |
|--------|--------|
| 数据库改动 | 0.5小时 |
| `config.py` 多客户配置 | 2小时 |
| `utils.py` 改造 | 0.5小时 |
| `routers/copyright.py` 改造 | 3小时 |
| `routers/dramas.py` 改造 | 2小时 |
| 新增导出API | 2小时 |
| 前端基础改动 | 2小时 |
| 测试验证 | 2小时 |
| **总计** | **14小时** |

### 方案B：完整功能（含管理界面）

| 改动项 | 工作量 |
|--------|--------|
| 方案A所有改动 | 14小时 |
| 客户配置管理界面 | 3小时 |
| 批量生成进度显示 | 2小时 |
| 前端动态渲染表格/表单 | 4小时 |
| **总计** | **23小时** |

---

## 九、测试要点

1. **新增版权测试**：创建一条版权数据，验证自动为所有客户生成了剧头/子集
2. **字段格式测试**：验证各客户的剧头字段、子集字段格式正确
3. **URL测试**：验证各客户的图片URL和媒体URL格式正确
4. **映射测试**：验证产品分类、内容目录映射正确
5. **新增客户测试**：添加新客户配置后，执行批量生成，验证补全成功
6. **导出测试**：分别导出4个客户的Excel，验证格式与模板一致
7. **江苏图片表测试**：验证江苏导出包含3个sheet且图片数据正确
8. **更新测试**：更新版权数据，验证所有关联的剧头/子集同步更新
9. **删除测试**：删除版权数据，验证所有关联的剧头/子集同步删除
10. **兼容测试**：验证现有河南移动数据不受影响

---

## 十、实施建议

1. **第一阶段**（2-3天）：
   - 数据库改动
   - config.py 完整配置4个客户
   - copyright.py 核心逻辑改造
   - 基础测试

2. **第二阶段**（1-2天）：
   - 各客户格式的导出API
   - 前端导出功能
   - 完整测试

3. **第三阶段**（1天）：
   - 批量补全功能
   - 新增客户时的处理

4. **第四阶段**（可选）：
   - 客户配置管理界面
   - 前端动态化
