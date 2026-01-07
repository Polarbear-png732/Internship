# 运营管理平台

基于 FastAPI 的剧集信息管理系统，提供剧集查询、子集信息查看和 Excel 导出功能。

## 功能特性

- 📺 剧集列表浏览（支持分页和搜索）
- 🔍 剧集详细信息查询
- 📋 子集信息查看
- 📊 Excel 数据导出

## 技术栈

- **后端**: FastAPI
- **数据库**: MySQL (pymysql)
- **数据处理**: pandas, openpyxl
- **前端**: HTML5, CSS3, JavaScript (原生)

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置数据库

在 `main.py` 中修改数据库连接配置：

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'your_password',
    'database': 'operation_management',
    'charset': 'utf8mb4'
}
```

## 运行应用

```bash
# 方式1: 直接运行
python main.py

# 方式2: 使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

启动后访问：http://localhost:8000

## API 接口

### 获取剧集列表
```
GET /api/dramas?keyword={keyword}&page={page}&page_size={page_size}
```

### 获取剧集详情
```
GET /api/dramas/{drama_id}
```

### 获取子集列表
```
GET /api/dramas/{drama_id}/episodes
```

### 搜索剧集
```
GET /api/dramas/search/{drama_name}
```

### 导出Excel
```
GET /api/export/{drama_name}
```

## 项目结构

```
web_app1/
├── main.py              # FastAPI 应用主文件
├── index.html           # 前端页面
├── requirements.txt     # Python 依赖
├── README.md           # 说明文档
└── static/
    ├── css/
    │   └── style.css   # 样式文件
    └── js/
        └── main.js     # JavaScript 文件
```

## 使用说明

1. **剧集管理页面**: 浏览所有剧集，支持搜索和分页
2. **剧集查询页面**: 通过完整剧集名称精确查询
3. **查看详情**: 点击"查看详情"按钮查看剧集完整信息和所有子集
4. **导出Excel**: 在详情页面或查询结果页面点击"导出Excel"按钮

## 注意事项

- 确保 MySQL 数据库已启动并包含 `operation_management` 数据库
- 确保数据库中存在相应的表结构（参考 `sql/create_database.sql`）
- Excel 文件会导出到 `excel/` 目录下
