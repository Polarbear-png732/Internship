-- 版权结构简化迁移（2026-03-09）
-- 目标：
-- 1) 删除客户授权明细表 copyright_customer_license
-- 2) 删除版权表中的河南/山东专用分类列
-- 3) 新增运营商列 operator_name（位于介质名称之后）

USE operation_management;

-- 1) 新增运营商列（已存在则跳过）
SET @add_operator_sql = (
    SELECT IF(
        EXISTS(
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'copyright_content'
              AND COLUMN_NAME = 'operator_name'
        ),
        'SELECT "operator_name already exists"',
        'ALTER TABLE copyright_content ADD COLUMN operator_name VARCHAR(100) NULL COMMENT "运营商（如河南移动、山东移动）" AFTER media_name'
    )
);
PREPARE stmt_add_operator FROM @add_operator_sql;
EXECUTE stmt_add_operator;
DEALLOCATE PREPARE stmt_add_operator;

-- 2) 删除不再使用的分类列（存在才删）
SET @drop_cat1_hn_sql = (
    SELECT IF(
        EXISTS(
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'copyright_content'
              AND COLUMN_NAME = 'category_level1_henan'
        ),
        'ALTER TABLE copyright_content DROP COLUMN category_level1_henan',
        'SELECT "category_level1_henan already dropped"'
    )
);
PREPARE stmt_drop_cat1_hn FROM @drop_cat1_hn_sql;
EXECUTE stmt_drop_cat1_hn;
DEALLOCATE PREPARE stmt_drop_cat1_hn;

SET @drop_cat2_hn_sql = (
    SELECT IF(
        EXISTS(
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'copyright_content'
              AND COLUMN_NAME = 'category_level2_henan'
        ),
        'ALTER TABLE copyright_content DROP COLUMN category_level2_henan',
        'SELECT "category_level2_henan already dropped"'
    )
);
PREPARE stmt_drop_cat2_hn FROM @drop_cat2_hn_sql;
EXECUTE stmt_drop_cat2_hn;
DEALLOCATE PREPARE stmt_drop_cat2_hn;

SET @drop_cat2_sd_sql = (
    SELECT IF(
        EXISTS(
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'copyright_content'
              AND COLUMN_NAME = 'category_level2_shandong'
        ),
        'ALTER TABLE copyright_content DROP COLUMN category_level2_shandong',
        'SELECT "category_level2_shandong already dropped"'
    )
);
PREPARE stmt_drop_cat2_sd FROM @drop_cat2_sd_sql;
EXECUTE stmt_drop_cat2_sd;
DEALLOCATE PREPARE stmt_drop_cat2_sd;

-- 3) 删除客户授权明细表
DROP TABLE IF EXISTS copyright_customer_license;

-- 4) 将唯一约束从 media_name 调整为 (media_name, operator_name)
SET @drop_old_unique_sql = (
    SELECT IF(
        EXISTS(
            SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'copyright_content'
              AND INDEX_NAME = 'idx_media_name_unique'
        ),
        'ALTER TABLE copyright_content DROP INDEX idx_media_name_unique',
        'SELECT "idx_media_name_unique already dropped"'
    )
);
PREPARE stmt_drop_old_unique FROM @drop_old_unique_sql;
EXECUTE stmt_drop_old_unique;
DEALLOCATE PREPARE stmt_drop_old_unique;

SET @add_media_operator_unique_sql = (
    SELECT IF(
        EXISTS(
            SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'copyright_content'
              AND INDEX_NAME = 'uk_media_operator'
        ),
        'SELECT "uk_media_operator already exists"',
        'ALTER TABLE copyright_content ADD UNIQUE KEY uk_media_operator (media_name, operator_name)'
    )
);
PREPARE stmt_add_media_operator_unique FROM @add_media_operator_unique_sql;
EXECUTE stmt_add_media_operator_unique;
DEALLOCATE PREPARE stmt_add_media_operator_unique;

SET @add_media_name_idx_sql = (
    SELECT IF(
        EXISTS(
            SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'copyright_content'
              AND INDEX_NAME = 'idx_media_name'
        ),
        'SELECT "idx_media_name already exists"',
        'ALTER TABLE copyright_content ADD INDEX idx_media_name (media_name)'
    )
);
PREPARE stmt_add_media_name_idx FROM @add_media_name_idx_sql;
EXECUTE stmt_add_media_name_idx;
DEALLOCATE PREPARE stmt_add_media_name_idx;

-- 5) language_henan 字段下线：直接删除（存在才执行）

SET @drop_language_henan_sql = (
    SELECT IF(
        EXISTS(
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'copyright_content'
              AND COLUMN_NAME = 'language_henan'
        ),
        'ALTER TABLE copyright_content DROP COLUMN language_henan',
        'SELECT "language_henan already dropped"'
    )
);
PREPARE stmt_drop_language_henan FROM @drop_language_henan_sql;
EXECUTE stmt_drop_language_henan;
DEALLOCATE PREPARE stmt_drop_language_henan;

-- 6) 清空业务数据：保留 video_scan_result，清空其它所有表
-- 说明：通过游标逐表执行单条 TRUNCATE，避免 PREPARE 执行多语句导致 1064
DROP PROCEDURE IF EXISTS truncate_tables_except_video_scan_result;

DELIMITER $$
CREATE PROCEDURE truncate_tables_except_video_scan_result()
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE v_table_name VARCHAR(255);

    DECLARE cur CURSOR FOR
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_TYPE = 'BASE TABLE'
          AND TABLE_NAME <> 'video_scan_result'
        ORDER BY TABLE_NAME;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    SET FOREIGN_KEY_CHECKS = 0;

    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO v_table_name;
        IF done = 1 THEN
            LEAVE read_loop;
        END IF;

        SET @truncate_one_sql = CONCAT('TRUNCATE TABLE `', v_table_name, '`');
        PREPARE stmt_truncate_one FROM @truncate_one_sql;
        EXECUTE stmt_truncate_one;
        DEALLOCATE PREPARE stmt_truncate_one;
    END LOOP;
    CLOSE cur;

    SET FOREIGN_KEY_CHECKS = 1;
END$$
DELIMITER ;

CALL truncate_tables_except_video_scan_result();
DROP PROCEDURE IF EXISTS truncate_tables_except_video_scan_result;
