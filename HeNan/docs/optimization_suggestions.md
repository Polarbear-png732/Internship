# 代码优化建议（局域网小规模使用场景）

## 当前状态
- 后端 main.py: 1306 行
- 前端 main.js: 1004 行
- 功能完整，可正常使用

---

## 一、高优先级优化（提升开发效率）

### 1. 提取重复代码为工具函数

**问题：** JSON 解析代码重复了 7+ 次

```python
# 当前：每次都写这段
if drama['dynamic_properties']:
    if isinstance(drama['dynamic_properties'], str):
        drama['dynamic_properties'] = json.loads(drama['dynamic_properties'])
```

**建议：** 在 main.py 顶部添加工具函数

```python
def parse_json_field(data, field='dynamic_properties'):
    """解析 JSON 字段"""
    if data and data.get(field):
        val = data[field]
        if isinstance(val, str):
            return json.loads(val)
        return val
    return {}

# 使用
dynamic_props = parse_json_field(drama)
```

### 2. 使用 context manager 管理数据库连接

**问题：** 异常时可能不关闭连接

```python
# 当前：手动管理连接
conn = get_db_connection()
try:
    # ... 操作
    conn.close()
except:
    # 连接可能未关闭
    raise
```

**建议：** 添加 context manager

```python
from contextlib import contextmanager

@contextmanager
def get_db():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

# 使用
with get_db() as conn:
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    # ... 操作
    # 自动关闭连接
```

---

## 二、中优先级优化（提升可维护性）

### 3. 拆分 main.py 为多个模块

当前 1306 行代码全在一个文件，建议拆分：

```
web_app1/
├── main.py              # 应用入口（~50行）
├── config.py            # 配置
├── utils.py             # 工具函数
├── routes/
│   ├── customer.py      # 客户 API
│   ├── drama.py         # 剧集 API
│   ├── copyright.py     # 版权 API
│   └── episode.py       # 子集 API
```

### 4. 统一字段映射

**问题：** 中文字段名散落在各处

```python
# 建议：集中定义
DRAMA_FIELD_MAP = {
    'drama_name': '剧集名称',
    'author_list': '作者列表',
    # ...
}
```

---

## 三、低优先级优化（锦上添花）

### 5. 添加简单日志

```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 在关键操作处
logger.info(f"创建剧集: {drama_name}")
logger.error(f"操作失败: {e}")
```

### 6. 前端代码拆分

将 main.js 拆分为：
- api.js - API 调用封装
- render.js - 渲染函数
- main.js - 主逻辑

---

## 四、不建议做的优化

考虑到局域网小规模使用：

1. ❌ 不需要数据库连接池（用户少，当前方式够用）
2. ❌ 不需要复杂的权限系统
3. ❌ 不需要前端框架（Vue/React）重构
4. ❌ 不需要 Docker 容器化

---

## 五、快速实施方案

如果只做一件事，建议：**提取工具函数**

在 main.py 顶部添加：

```python
# ==================== 工具函数 ====================

def parse_json(data, field='dynamic_properties'):
    """解析 JSON 字段，返回字典"""
    if data and data.get(field):
        val = data[field]
        return json.loads(val) if isinstance(val, str) else val
    return {}

def build_drama_dict(drama, props=None):
    """构建剧头数据字典"""
    if props is None:
        props = parse_json(drama)
    return {
        '剧头id': drama['drama_id'],
        '剧集名称': drama['drama_name'],
        '作者列表': props.get('作者列表', ''),
        '清晰度': props.get('清晰度', 0),
        '语言': props.get('语言', ''),
        '主演': props.get('主演', ''),
        '内容类型': props.get('内容类型', ''),
        '上映年份': props.get('上映年份', 0),
        '关键字': props.get('关键字', ''),
        '评分': props.get('评分', 0.0),
        '推荐语': props.get('推荐语', ''),
        '总集数': props.get('总集数', 0),
        '产品分类': props.get('产品分类', 0),
        '竖图': props.get('竖图', ''),
        '描述': props.get('描述', ''),
        '横图': props.get('横图', ''),
        '版权': props.get('版权', 0),
        '二级分类': props.get('二级分类', '')
    }

def build_episode_dict(episode, props=None):
    """构建子集数据字典"""
    if props is None:
        props = parse_json(episode)
    return {
        '子集id': episode['episode_id'],
        '节目名称': episode['episode_name'],
        '媒体拉取地址': props.get('媒体拉取地址', ''),
        '媒体类型': props.get('媒体类型', 0),
        '编码格式': props.get('编码格式', 0),
        '集数': props.get('集数', 0),
        '时长': props.get('时长', 0),
        '文件大小': props.get('文件大小', 0)
    }
```

这样可以大幅减少重复代码，提高可读性。
