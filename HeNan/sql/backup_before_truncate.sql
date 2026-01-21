-- 清空前备份数据脚本
-- 创建时间: 2026-01-21
-- 用途: 在清空表之前备份数据到临时表
--
-- 执行方式：
-- PowerShell: Get-Content sql\backup_before_truncate.sql | mysql -u root -p operation_management
-- CMD: mysql -u root -p operation_management < sql\backup_before_truncate.sql

USE operation_management;

-- 创建备份表（如果已存在则先删除）
DROP TABLE IF EXISTS copyright_content_backup;
DROP TABLE IF EXISTS drama_main_backup;
DROP TABLE IF EXISTS drama_episode_backup;

-- 备份版权方数据表
CREATE TABLE copyright_content_backup AS SELECT * FROM copyright_content;

-- 备份剧集主表
CREATE TABLE drama_main_backup AS SELECT * FROM drama_main;

-- 备份剧集子集表
CREATE TABLE drama_episode_backup AS SELECT * FROM drama_episode;

-- 显示备份统计
SELECT 'Backup Statistics' AS info;
SELECT 
    'copyright_content_backup' AS backup_table, 
    COUNT(*) AS row_count
FROM copyright_content_backup
UNION ALL
SELECT 
    'drama_main_backup' AS backup_table, 
    COUNT(*) AS row_count
FROM drama_main_backup
UNION ALL
SELECT 
    'drama_episode_backup' AS backup_table, 
    COUNT(*) AS row_count
FROM drama_episode_backup;

-- 提示信息
SELECT 'Backup completed successfully!' AS message;
