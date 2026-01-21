-- 从备份恢复数据脚本
-- 创建时间: 2026-01-21
-- 用途: 从备份表恢复数据到原表
--
-- 前提条件：必须先执行过 backup_before_truncate.sql
--
-- 执行方式：
-- PowerShell: Get-Content sql\restore_from_backup.sql | mysql -u root -p operation_management
-- CMD: mysql -u root -p operation_management < sql\restore_from_backup.sql

USE operation_management;

-- 检查备份表是否存在
SELECT '========== 检查备份表 ==========' AS info;
SELECT 
    TABLE_NAME,
    TABLE_ROWS
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'operation_management'
AND TABLE_NAME IN ('copyright_content_backup', 'drama_main_backup', 'drama_episode_backup');

-- 禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;

-- 清空原表
TRUNCATE TABLE drama_episode;
TRUNCATE TABLE drama_main;
TRUNCATE TABLE copyright_content;

-- 从备份恢复数据
INSERT INTO copyright_content SELECT * FROM copyright_content_backup;
INSERT INTO drama_main SELECT * FROM drama_main_backup;
INSERT INTO drama_episode SELECT * FROM drama_episode_backup;

-- 重新启用外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 显示恢复统计
SELECT '========== 恢复完成统计 ==========' AS info;
SELECT 
    'copyright_content' AS table_name, 
    COUNT(*) AS row_count,
    '版权方数据表' AS description
FROM copyright_content
UNION ALL
SELECT 
    'drama_main' AS table_name, 
    COUNT(*) AS row_count,
    '剧集主表（剧头）' AS description
FROM drama_main
UNION ALL
SELECT 
    'drama_episode' AS table_name, 
    COUNT(*) AS row_count,
    '剧集子集表' AS description
FROM drama_episode;

-- 提示信息
SELECT '✓ 数据恢复完成！' AS message;
SELECT '备份表仍然保留，如需删除请手动执行 DROP TABLE' AS note;
