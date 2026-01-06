## 环境记录

- 操作系统：Windows 10（当前开发机）
- Python：推荐 3.10 或更高（本项目使用 `FastAPI` + `pandas` + `pymysql` + `openpyxl`）
- MySQL：推荐 8.0（字符集 `utf8mb4`，端口默认 3306）
- Node/前端：静态页无需构建，直接通过 FastAPI 提供；如需本地调试，可使用任意现代浏览器

### Python 依赖
- fastapi
- uvicorn
- pandas
- pymysql
- openpyxl

安装示例：
```
pip install fastapi uvicorn pandas pymysql openpyxl
```

### 数据库
- MySQL 8.0，`operation_management` 库，字符集 `utf8mb4`
- 连接配置在 `web_app/main.py` 的 `DB_CONFIG` 中（host/port/user/password/database）

> 如实际环境版本不同，请按需调整，这里给出推荐版本便于统一。
