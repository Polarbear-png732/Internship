-- ============================================
-- 性能优化索引
-- 创建时间: 2025
-- 说明: 根据实际查询模式添加的性能优化索引
-- ============================================

USE operation_management;

-- ============================================
-- 1. drama_main 表索引优化
-- ============================================

-- 索引1: 按剧名精确查询（用于批量导出按名称查询）
-- 场景: WHERE drama_name = 'xxx' AND customer_code = 'xxx'
CREATE INDEX idx_drama_name ON drama_main(drama_name(100));

-- 索引2: 按创建时间排序（用于分页查询）
-- 场景: ORDER BY created_at DESC LIMIT x OFFSET y
CREATE INDEX idx_created_at ON drama_main(created_at DESC);

-- 索引3: 复合索引 - 客户代码+创建时间（分页查询优化）
-- 场景: WHERE customer_code = 'xxx' ORDER BY created_at DESC
CREATE INDEX idx_customer_created ON drama_main(customer_code, created_at DESC);


-- ============================================
-- 2. drama_episode 表索引优化
-- ============================================

-- 索引1: 批量查询子集时的排序索引
-- 场景: WHERE drama_id IN (...) ORDER BY drama_id, episode_id
-- 注意: drama_id 已有索引，这个复合索引可以避免额外排序
CREATE INDEX idx_drama_episode_order ON drama_episode(drama_id, episode_id);


-- ============================================
-- 3. copyright_content 表索引优化
-- ============================================

-- 索引1: 按介质名称查询（已有唯一索引）
-- 无需额外创建

-- 索引2: 按更新时间排序（用于最近修改记录）
CREATE INDEX idx_copyright_updated ON copyright_content(updated_at DESC);

-- 索引3: 按一级分类筛选
CREATE INDEX idx_category_level1 ON copyright_content(category_level1);


-- ============================================
-- 4. video_scan_result 表索引优化
-- ============================================

-- 索引1: 按来源文件夹查询
-- 场景: WHERE source_folder = 'xxx'
CREATE INDEX idx_source_folder ON video_scan_result(source_folder);


-- ============================================
-- 查看索引使用情况（运维使用）
-- ============================================
-- 分析查询执行计划:
-- EXPLAIN SELECT * FROM drama_main WHERE customer_code = 'henan_mobile' ORDER BY created_at DESC LIMIT 10;
-- EXPLAIN SELECT * FROM drama_episode WHERE drama_id IN (1,2,3) ORDER BY drama_id, episode_id;

-- 查看表索引:
-- SHOW INDEX FROM drama_main;
-- SHOW INDEX FROM drama_episode;
-- SHOW INDEX FROM copyright_content;
