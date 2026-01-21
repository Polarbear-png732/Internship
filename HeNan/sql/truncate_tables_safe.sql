-- 安全清空剧头表、子集表、版权信息表的数据
-- 创建时间: 2026-01-21
-- 用途: 清空测试数据或重置数据库
-- 
-- ⚠️ 警告：此操作将永久删除所有数据，无法恢复！
-- 
-- 使用前请确保：
-- 1. 已备份重要数据
-- 2. 确认要清空的是正确的数据库
-- 3. 了解此操作的影响
--
-- 执行方式：
-- PowerShell: Get-Content sql\truncate_tables_safe.sql | mysql -u root -p operation_management
-- CMD: mysql -u root -p operation_management < sql\truncate_tables_safe.sql

-- 使用数据库
USE operation_management;

-- 显示当前数据统计（清空前）
SELECT 'Before Truncate - Data Statistics' AS info;
SELECT 
    'drama_episode' AS table_name, 
    COUNT(*) AS row_count
FROM drama_episode
UNION ALL
SELECT 
    'drama_main' AS table_name, 
    COUNT(*) AS row_count
FROM drama_main
UNION ALL
SELECT 
    'copyright_content' AS table_name, 
    COUNT(*) AS row_count
FROM copyright_content;

-- 禁用外键检查（避免删除时的外键约束问题）
SET FOREIGN_KEY_CHECKS = 0;

-- 清空剧集子集表（必须先清空，因为有外键约束）
TRUNCATE TABLE drama_episode;

-- 清空剧集主表（剧头表）
TRUNCATE TABLE drama_main;

-- 清空版权方数据表
TRUNCATE TABLE copyright_content;

-- 重新启用外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 显示清空后的数据统计
SELECT 'After Truncate - Data Statistics' AS info;
SELECT 
    'drama_episode' AS table_name, 
    COUNT(*) AS row_count
FROM drama_episode
UNION ALL
SELECT 
    'drama_main' AS table_name, 
    COUNT(*) AS row_count
FROM drama_main
UNION ALL
SELECT 
    'copyright_content' AS table_name, 
    COUNT(*) AS row_count
FROM copyright_content;

-- 提示信息
SELECT 'Data truncated successfully!' AS message;
SELECT 'Auto-increment IDs have been reset to 1' AS note;
