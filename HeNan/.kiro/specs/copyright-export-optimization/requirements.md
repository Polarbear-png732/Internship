# 版权数据导出功能优化 - 需求文档

## 1. 项目背景

视频内容运营管理平台需要导出版权方数据为Excel文件，供运营人员查看和分析。当前导出功能的字段顺序与数据库表结构不一致，需要进行优化。

## 2. 用户故事

**作为** 运营管理人员  
**我想要** 导出的Excel文件字段顺序与数据库表结构一致  
**以便** 更容易理解和使用导出的数据

## 3. 功能需求

### 3.1 导出字段顺序调整

**需求描述**：导出的Excel文件应按照数据库 `copyright_content` 表的字段顺序排列

**数据库表字段顺序**（共34个字段）：
1. id - 序号
2. serial_number - 序号(自定义)
3. upstream_copyright - 上游版权方
4. media_name - 介质名称
5. category_level1 - 一级分类
6. category_level2 - 二级分类
7. category_level1_henan - 一级分类-河南标准
8. category_level2_henan - 二级分类-河南标准
9. episode_count - 集数
10. single_episode_duration - 单集时长
11. total_duration - 总时长
12. production_year - 出品年代
13. **premiere_date - 首播日期**（新增字段）
14. authorization_region - 授权区域
15. authorization_platform - 授权平台
16. cooperation_mode - 合作方式
17. production_region - 制作地区
18. language - 语言
19. language_henan - 语言-河南标准
20. country - 国别
21. director - 导演
22. screenwriter - 编剧
23. cast_members - 主演/嘉宾/主持人
24. **author - 作者**（新增字段）
25. recommendation - 推荐语
26. synopsis - 简介
27. keywords - 关键字
28. video_quality - 视频质量
29. license_number - 发行许可编号/备案号
30. rating - 评分
31. exclusive_status - 独家/非独
32. copyright_start_date - 版权开始时间
33. copyright_end_date - 版权结束时间
34. category_level2_shandong - 二级分类-山东标准

### 3.2 列宽优化

**需求描述**：根据字段内容长度设置合适的列宽，提升可读性

**列宽设置**：
- 序号类：8-12
- 分类/标签类：10-15
- 名称/标题类：15-25
- 描述/简介类：30-40
- 其他：根据实际内容调整

### 3.3 新增字段支持

**需求描述**：导出功能需要支持新增的两个字段

- `premiere_date`（首播日期）：位于出品年代之后
- `author`（作者）：位于主演/嘉宾/主持人之后

## 4. 验收标准

### 4.1 字段顺序正确性

- [ ] 导出的Excel文件字段顺序与数据库表结构完全一致
- [ ] 所有34个字段都正确导出
- [ ] 新增字段（首播日期、作者）在正确位置

### 4.2 数据完整性

- [ ] 所有版权数据都能正确导出
- [ ] 字段值正确映射到对应列
- [ ] 空值和NULL值正确处理

### 4.3 格式美观性

- [ ] 列宽设置合理，内容可读
- [ ] 表头格式统一（蓝色背景、白色字体、居中对齐）
- [ ] 首行冻结，方便滚动查看

### 4.4 性能要求

- [ ] 导出1000条数据在5秒内完成
- [ ] 导出过程不阻塞其他操作
- [ ] 内存占用合理

## 5. 技术约束

- 使用 `pandas` + `xlsxwriter` 引擎进行Excel生成
- 保持现有API接口不变（`GET /api/copyright/export`）
- 文件名格式：`版权方数据.xlsx`
- 编码：UTF-8

## 6. 非功能需求

### 6.1 兼容性

- 导出的Excel文件兼容 Microsoft Excel 2016+
- 支持 WPS Office
- 支持 LibreOffice Calc

### 6.2 可维护性

- 字段映射配置清晰，易于修改
- 代码注释完整
- 遵循现有代码风格

## 7. 相关文件

- `web_app1/routers/copyright.py` - 导出功能实现
- `sql/create_database.sql` - 数据库表结构定义
- `web_app1/config.py` - 字段配置

## 8. 变更历史

| 日期 | 版本 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 2026-01-21 | 1.0 | 初始版本 | - |
