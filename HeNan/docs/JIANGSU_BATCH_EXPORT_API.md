# 江苏新媒体批量导出API文档

## 📋 概述

江苏新媒体批量导出API允许一次性导出多个剧集的数据到一个Excel文件中，包含剧头、子集、图片三个sheet。

---

## 🔗 API端点

```
POST /api/dramas/export/batch/jiangsu_newmedia
```

---

## 📥 请求参数

### 请求头
```
Content-Type: application/json
```

### 请求体
```json
{
  "drama_names": ["剧集名称1", "剧集名称2", "剧集名称3"]
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| drama_names | array | 是 | 剧集名称列表，至少包含1个剧集名称 |

---

## 📤 响应

### 成功响应
- **状态码**: 200
- **Content-Type**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **响应体**: Excel文件（二进制流）

### 文件名格式
- 单个剧集：`江苏新媒体_{剧集名称}_注入表.xlsx`
- 多个剧集：`江苏新媒体_批量导出_{N}个剧集.xlsx`

### Excel文件结构
包含3个sheet：

1. **剧头** - 剧集主信息
   - 17个字段（vod_no, sId, appId, seriesName等）
   - 序号从1开始连续编号

2. **子集** - 剧集分集信息
   - 11个字段（vod_info_no, vod_no, sId, pId等）
   - 序号从1开始连续编号
   - vod_no关联剧头序号

3. **图片** - 剧集图片信息
   - 7个字段（picture_no, vod_no, sId, picId等）
   - 每个剧集4张图片（type: 0, 1, 2, 99）
   - 序号从1开始连续编号

### 错误响应

#### 400 Bad Request
```json
{
  "detail": "请提供至少一个剧集名称"
}
```

#### 404 Not Found
```json
{
  "detail": "未找到匹配的江苏新媒体剧集。请检查剧集名称是否正确。"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "导出失败: {错误信息}"
}
```

---

## 💡 使用示例

### Python (requests)
```python
import requests

url = "http://localhost:8000/api/dramas/export/batch/jiangsu_newmedia"
payload = {
    "drama_names": [
        "小猪佩奇之冬日特辑",
        "小猪佩奇之校园生活",
        "小猪佩奇之猪爸爸爱猪妈妈"
    ]
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    with open("江苏新媒体_批量导出.xlsx", "wb") as f:
        f.write(response.content)
    print("导出成功！")
else:
    print(f"导出失败: {response.json()}")
```

### cURL
```bash
curl -X POST "http://localhost:8000/api/dramas/export/batch/jiangsu_newmedia" \
  -H "Content-Type: application/json" \
  -d '{
    "drama_names": [
      "小猪佩奇之冬日特辑",
      "小猪佩奇之校园生活"
    ]
  }' \
  --output 江苏新媒体_批量导出.xlsx
```

### JavaScript (Fetch API)
```javascript
fetch('http://localhost:8000/api/dramas/export/batch/jiangsu_newmedia', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    drama_names: [
      '小猪佩奇之冬日特辑',
      '小猪佩奇之校园生活'
    ]
  })
})
.then(response => response.blob())
.then(blob => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = '江苏新媒体_批量导出.xlsx';
  a.click();
});
```

---

## 📝 注意事项

1. **剧集名称必须精确匹配**
   - 剧集名称必须与数据库中的完全一致
   - 区分大小写
   - 包括所有标点符号

2. **只导出江苏新媒体客户的剧集**
   - API只查询 `customer_code = 'jiangsu_newmedia'` 的剧集
   - 其他客户的剧集不会被导出

3. **序号自动生成**
   - 剧头序号（vod_no）从1开始
   - 子集序号（vod_info_no）从1开始
   - 图片序号（picture_no）从1开始
   - 所有序号连续递增

4. **特殊字段处理**
   - `sId` 字段在剧头和子集中留空（None）
   - `pId` 字段在子集中留空（None）
   - 图片的 `picId` 字段留空（None）

5. **Excel格式**
   - 使用江苏新媒体特殊的两行表头格式
   - 第1行：英文字段名
   - 第2行：中文说明
   - 第3行开始：实际数据

---

## 🎯 使用场景

### 场景1：导出单个剧集
```json
{
  "drama_names": ["小猪佩奇之冬日特辑"]
}
```
**用途**: 单独导出一个剧集的完整数据

### 场景2：导出同系列剧集
```json
{
  "drama_names": [
    "小猪佩奇之冬日特辑",
    "小猪佩奇之校园生活",
    "小猪佩奇之猪爸爸爱猪妈妈",
    "小猪佩奇之和朋友一起玩",
    "小猪佩奇之猪爸爸的故事"
  ]
}
```
**用途**: 批量导出同一系列的多个剧集

### 场景3：导出指定剧集列表
```json
{
  "drama_names": [
    "汪汪队立大功精彩集",
    "米奇妙妙屋之米妮篇",
    "爱探险的朵拉第一季"
  ]
}
```
**用途**: 导出不同系列的指定剧集

---

## 🔍 查询可用剧集

如需查看数据库中所有江苏新媒体的剧集，可以使用以下SQL：

```sql
SELECT drama_id, drama_name
FROM drama_main
WHERE customer_code = 'jiangsu_newmedia'
ORDER BY drama_name;
```

或通过API查询：
```
GET /api/dramas?customer_code=jiangsu_newmedia
```

---

## ⚠️ 常见问题

### Q: 为什么导出失败提示"未找到匹配的剧集"？
A: 请检查：
1. 剧集名称是否完全正确（包括标点符号）
2. 该剧集是否属于江苏新媒体客户
3. 数据库中是否存在该剧集

### Q: 可以一次导出多少个剧集？
A: 理论上没有限制，但建议：
- 单次导出不超过100个剧集
- 文件过大可能导致下载超时

### Q: 导出的Excel文件为什么有两行表头？
A: 这是江苏新媒体的特殊格式要求：
- 第1行：英文字段名（用于系统识别）
- 第2行：中文说明（用于人工查看）

### Q: 序号是如何生成的？
A: 序号按照请求中剧集的顺序生成：
- 第1个剧集：vod_no=1
- 第2个剧集：vod_no=2
- 以此类推

### Q: 如果部分剧集不存在会怎样？
A: 
- 只导出存在的剧集
- 控制台会输出警告信息
- 如果所有剧集都不存在，返回404错误

---

## 📚 相关文档

- `web_app1/routers/dramas.py` - API实现代码
- `web_app1/config.py` - 江苏新媒体配置
- `tables/江苏新媒体注入表模版.xlsx` - Excel模板参考
- `docs/add_new_customer_guide.md` - 客户配置指南
