-- 只清空剧集和版权数据，保留客户数据

USE operation_management;

-- 禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;

-- 清空剧集和版权相关表
TRUNCATE TABLE drama_episode;
TRUNCATE TABLE drama_main;
TRUNCATE TABLE copyright_content;

-- 启用外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 显示清空结果
SELECT 'Drama and copyright data cleared, customer data preserved!' AS Status;
