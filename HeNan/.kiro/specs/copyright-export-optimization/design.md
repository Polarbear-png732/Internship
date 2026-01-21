# 版权数据导出功能优化 - 设计文档

## 1. 设计概述

本设计文档描述如何优化版权数据导出功能，使导出的Excel文件字段顺序与数据库表结构保持一致，并支持新增的 `premiere_date` 和 `author` 字段。

## 2. 架构设计

### 2.1 现有架构

```
用户请求 → FastAPI路由 → 数据库查询 → pandas DataFrame → xlsxwriter → Excel文件
```

### 2.2 核心组件

- **路由函数**：`export_copyright_to_excel()` - 处理导出请求
- **字段映射**：`COPYRIGHT_EXPORT_COLUMNS` - 数据库字段到中文列名的映射
- **Excel引擎**：`xlsxwriter` - 高性能Excel生成

## 3. 数据模型

### 3.1 字段映射字典

```python
COPYRIGHT_EXPORT_COLUMNS = {
    'id': '序号',
    'serial_number': '序号(自定义)',
    'upstream_copyright': '上游版权方',
    'media_name': '介质名称',
    # ... 按数据库表结构顺序排列
    'premiere_date': '首播日期',  # 新增
    'author': '作者',  # 新增
    # ...
}
```

**设计原则**：
- 字典的键顺序与数据库表字段顺序一致
- 使用Python 3.7+ 的字典有序特性
- 键名与数据库字段名完全匹配

### 3.2 列宽配置

```python
col_widths = {
    '序号': 8,
    '序号(自定义)': 12,
    '上游版权方': 15,
    '介质名称': 25,
    # ... 根据内容长度设置
    '首播日期': 12,  # 新增
    '作者': 15,  # 新增
    # ...
}
```

## 4. 详细设计

### 4.1 导出流程

```
1. 接收导出请求
   ↓
2. 查询所有版权数据（ORDER BY id）
   ↓
3. 遍历数据，按字段映射构建导出行
   ↓
4. 创建pandas DataFrame（列顺序由字段映射决定）
   ↓
5. 使用xlsxwriter写入Excel
   ↓
6. 设置列宽和表头格式
   ↓
7. 返回StreamingResponse
```

### 4.2 关键代码逻辑

#### 4.2.1 数据转换

```python
export_data = []
for item in items:
    row = {}
    for db_col, cn_col in COPYRIGHT_EXPORT_COLUMNS.items():
        value = item.get(db_col, '')
        # 截断过长文本
        if value and isinstance(value, str) and len(value) > 100:
            value = value[:100] + '...'
        row[cn_col] = value
    export_data.append(row)
```

**设计要点**：
- 按照 `COPYRIGHT_EXPORT_COLUMNS` 的顺序遍历
- 处理空值和NULL值
- 截断过长文本（>100字符）

#### 4.2.2 DataFrame创建

```python
df = pd.DataFrame(export_data, columns=list(COPYRIGHT_EXPORT_COLUMNS.values()))
```

**设计要点**：
- 显式指定列顺序
- 使用字段映射的值（中文列名）作为列名

#### 4.2.3 Excel格式化

```python
# 设置列宽
for idx, col_name in enumerate(df.columns):
    width = col_widths.get(col_name, 15)
    worksheet.set_column(idx, idx, width)

# 设置表头格式
header_format = workbook.add_format({
    'bold': True,
    'align': 'center',
    'valign': 'vcenter',
    'bg_color': '#4472C4',
    'font_color': 'white',
    'border': 1
})

# 冻结首行
worksheet.freeze_panes(1, 0)
```

## 5. 正确性属性

### 5.1 字段顺序一致性

**属性**：导出Excel的列顺序必须与数据库表字段顺序一致

**验证方法**：
```python
def test_export_column_order():
    """验证导出列顺序与数据库表结构一致"""
    db_fields = get_db_table_columns('copyright_content')
    export_fields = list(COPYRIGHT_EXPORT_COLUMNS.keys())
    
    # 排除 drama_ids, created_at, updated_at
    db_fields_filtered = [f for f in db_fields 
                          if f not in ['drama_ids', 'created_at', 'updated_at']]
    
    assert export_fields == db_fields_filtered
```

### 5.2 数据完整性

**属性**：所有数据库字段都必须导出（除了内部字段）

**验证方法**：
```python
def test_export_data_completeness():
    """验证所有字段都被导出"""
    db_fields = get_db_table_columns('copyright_content')
    export_fields = list(COPYRIGHT_EXPORT_COLUMNS.keys())
    
    # 内部字段不需要导出
    internal_fields = ['drama_ids', 'created_at', 'updated_at']
    
    missing_fields = [f for f in db_fields 
                      if f not in export_fields and f not in internal_fields]
    
    assert len(missing_fields) == 0
```

### 5.3 新增字段支持

**属性**：新增字段必须在正确位置导出

**验证方法**：
```python
def test_new_fields_position():
    """验证新增字段位置正确"""
    export_fields = list(COPYRIGHT_EXPORT_COLUMNS.keys())
    
    # premiere_date 应在 production_year 之后
    premiere_idx = export_fields.index('premiere_date')
    production_idx = export_fields.index('production_year')
    assert premiere_idx == production_idx + 1
    
    # author 应在 cast_members 之后
    author_idx = export_fields.index('author')
    cast_idx = export_fields.index('cast_members')
    assert author_idx == cast_idx + 1
```

## 6. 性能优化

### 6.1 查询优化

- 使用 `SELECT *` 一次性获取所有数据
- 按 `id` 排序，利用主键索引

### 6.2 内存优化

- 截断过长文本（>100字符）
- 使用 `BytesIO` 内存流，避免临时文件

### 6.3 写入优化

- 使用 `xlsxwriter` 引擎（比 `openpyxl` 快2-3倍）
- 批量设置格式，减少API调用

## 7. 错误处理

### 7.1 数据库错误

```python
try:
    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM copyright_content ORDER BY id")
        items = cursor.fetchall()
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

### 7.2 Excel生成错误

```python
try:
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # ... Excel生成逻辑
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Excel生成失败: {str(e)}")
```

## 8. 测试策略

### 8.1 单元测试

- 测试字段映射顺序
- 测试数据转换逻辑
- 测试列宽配置

### 8.2 集成测试

- 测试完整导出流程
- 测试不同数据量（0条、1条、1000条）
- 测试特殊字符和长文本

### 8.3 性能测试

- 测试1000条数据导出时间
- 测试内存占用
- 测试并发导出

## 9. 部署说明

### 9.1 代码变更

- 修改 `web_app1/routers/copyright.py` 中的 `COPYRIGHT_EXPORT_COLUMNS` 和 `col_widths`
- 无需修改数据库结构（已完成）
- 无需修改API接口

### 9.2 验证步骤

1. 重启FastAPI服务
2. 访问 `/api/copyright/export` 接口
3. 下载Excel文件
4. 验证字段顺序和内容

## 10. 维护指南

### 10.1 添加新字段

当数据库表新增字段时：

1. 在 `COPYRIGHT_EXPORT_COLUMNS` 中添加字段映射（按表结构顺序）
2. 在 `col_widths` 中添加列宽配置
3. 运行测试验证

### 10.2 修改字段顺序

如果需要调整字段顺序：

1. 修改数据库表结构
2. 更新 `COPYRIGHT_EXPORT_COLUMNS` 字典顺序
3. 运行测试验证

## 11. 相关文档

- [需求文档](requirements.md)
- [任务列表](tasks.md)
- [数据库表结构](../../sql/create_database.sql)
