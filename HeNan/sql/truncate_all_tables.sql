-- 清空所有表脚本（用于重新导入数据）
-- 创建时间: 2025-01-21
-- 用途: 清空版权表、剧集表、子集表，准备重新导入数据
-- 
-- ⚠️ 警告：此操作将删除所有数据且不可恢复！
-- ⚠️ 建议：执行前请先备份整个数据库！
-- 
-- 备份数据库命令：
-- mysqldump -u root -p operation_management > backup_operation_management_$(date +%Y%m%d_%H%M%S).sql
-- 
-- 恢复数据库命令：
-- mysql -u root -p operation_management < backup_operation_management_YYYYMMDD_HHMMSS.sql
-- 
-- 执行方式：
-- PowerShell: Get-Content sql\truncate_all_tables.sql | mysql -u root -p operation_management
-- CMD: mysql -u root -p operation_management < sql\truncate_all_tables.sql

USE operation_management;

-- 显示清空前的数据统计
SELECT '========== 清空前数据统计 ==========' AS info;
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

-- 提示确认
SELECT '' AS blank;
SELECT '⚠️  即将清空以下表的所有数据：' AS warning;
SELECT '   1. drama_episode (子集表)' AS table_1;
SELECT '   2. drama_main (剧头表)' AS table_2;
SELECT '   3. copyright_content (版权表)' AS table_3;
SELECT '' AS blank;
SELECT '⚠️  此操作不可逆，所有数据将被永久删除！' AS warning2;
SELECT '⚠️  建议先备份数据库：mysqldump -u root -p operation_management > backup.sql' AS backup_tip;
SELECT '' AS blank;

-- 禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;

-- 清空表（按照外键依赖顺序：子集 → 剧头 → 版权）
TRUNCATE TABLE drama_episode;
TRUNCATE TABLE drama_main;
TRUNCATE TABLE copyright_content;

-- 重新启用外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 验证清空结果
SELECT '========== 清空后数据统计 ==========' AS info;
SELECT 
    'copyright_content' AS table_name, 
    COUNT(*) AS row_count,
    CASE WHEN COUNT(*) = 0 THEN '✓ 已清空' ELSE '✗ 仍有数据' END AS status
FROM copyright_content
UNION ALL
SELECT 
    'drama_main' AS table_name, 
    COUNT(*) AS row_count,
    CASE WHEN COUNT(*) = 0 THEN '✓ 已清空' ELSE '✗ 仍有数据' END AS status
FROM drama_main
UNION ALL
SELECT 
    'drama_episode' AS table_name, 
    COUNT(*) AS row_count,
    CASE WHEN COUNT(*) = 0 THEN '✓ 已清空' ELSE '✗ 仍有数据' END AS status
FROM drama_episode;

-- 显示自增ID重置情况
SELECT '========== 自增ID已重置 ==========' AS info;
SELECT 
    TABLE_NAME,
    AUTO_INCREMENT AS next_id,
    '下一个ID将从1开始' AS note
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'operation_management'
  AND TABLE_NAME IN ('copyright_content', 'drama_main', 'drama_episode')
ORDER BY 
    CASE TABLE_NAME
        WHEN 'copyright_content' THEN 1
        WHEN 'drama_main' THEN 2
        WHEN 'drama_episode' THEN 3
    END;

-- 完成提示
SELECT '' AS blank;
SELECT '========== 操作完成 ==========' AS info;
SELECT '✓ 所有表已清空，自增ID已重置为1' AS success;
SELECT '✓ 现在可以重新导入版权数据' AS next_step;
SELECT '✓ 系统将自动为所有启用的客户生成剧头和子集' AS auto_generate;
SELECT '' AS blank;
SELECT '启用的客户列表：' AS customers_info;
SELECT '  - 河南移动 (henan_mobile)' AS c1;
SELECT '  - 山东移动 (shandong_mobile)' AS c2;
SELECT '  - 甘肃移动 (gansu_mobile)' AS c3;
SELECT '  - 江苏新媒体 (jiangsu_newmedia)' AS c4;
SELECT '  - 浙江移动 (zhejiang_mobile)' AS c5;
SELECT '  - 新疆电信 (xinjiang_telecom)' AS c6;
SELECT '  - 江西移动 (jiangxi_mobile)' AS c7;
