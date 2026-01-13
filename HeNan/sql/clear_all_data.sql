-- 清空所有测试数据（保留表结构）

USE operation_management;

-- 禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;

-- 清空所有表数据
TRUNCATE TABLE drama_episode;
TRUNCATE TABLE drama_main;
TRUNCATE TABLE copyright_content;
TRUNCATE TABLE customer;
TRUNCATE TABLE customer_field_config;

-- 启用外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 显示清空结果
SELECT 'All data cleared successfully!' AS Status;
