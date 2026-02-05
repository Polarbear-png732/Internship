-- 运营管理平台数据库结构
-- 创建时间: 2026-01-14

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 删除已存在的数据库（如果存在），以便重新创建
DROP DATABASE IF EXISTS operation_management;

-- 创建数据库
CREATE DATABASE IF NOT EXISTS operation_management 
DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE operation_management;

-- ============================================
-- 1. 剧集主表：存储剧头信息，使用JSON字段存储动态属性
-- ============================================
CREATE TABLE drama_main (
    drama_id INT NOT NULL AUTO_INCREMENT COMMENT '剧集ID，自增主键',
    customer_id INT DEFAULT NULL COMMENT '客户ID（可为空，空表示所有客户可见）',
    customer_code VARCHAR(50) DEFAULT 'henan_mobile' COMMENT '客户代码（henan_mobile/shandong_mobile/gansu_mobile/jiangsu_newmedia）',
    drama_name VARCHAR(500) NOT NULL COMMENT '剧集名称',
    dynamic_properties JSON DEFAULT NULL COMMENT '动态属性，存储剧集的所有属性',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (drama_id),
    KEY fk_drama_customer (customer_id),
    KEY idx_customer_code (customer_code),
    KEY idx_customer_code_drama_name (customer_code, drama_name(100)) COMMENT '客户代码+剧名复合索引，优化批量查询'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='剧集主表，使用JSON存储动态属性';

-- ============================================
-- 2. 剧集子集表：存储每集信息，使用JSON字段存储动态属性
-- ============================================
CREATE TABLE drama_episode (
    episode_id INT NOT NULL AUTO_INCREMENT COMMENT '集数ID，自增主键',
    drama_id INT NOT NULL COMMENT '关联的剧集ID',
    episode_name VARCHAR(500) NOT NULL COMMENT '节目名称（集数名称）',
    dynamic_properties JSON DEFAULT NULL COMMENT '动态属性，存储每集的所有属性',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (episode_id),
    KEY idx_drama_episode (drama_id, episode_name) COMMENT '按剧集和集数名称排序的索引',
    CONSTRAINT drama_episode_ibfk_1 FOREIGN KEY (drama_id) REFERENCES drama_main(drama_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='剧集子集表，使用JSON存储动态属性';

-- ============================================
-- 3. 版权方数据表：存储版权方内容信息
-- ============================================
CREATE TABLE copyright_content (
    id INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    drama_ids JSON DEFAULT NULL COMMENT '各客户的剧头ID，如{"henan_mobile":101,"shandong_mobile":102}',
    serial_number INT DEFAULT NULL COMMENT '序号',
    upstream_copyright VARCHAR(200) DEFAULT NULL COMMENT '上游版权方',
    media_name VARCHAR(500) DEFAULT NULL COMMENT '介质名称',
    category_level1 VARCHAR(100) DEFAULT NULL COMMENT '一级分类',
    category_level2 VARCHAR(100) DEFAULT NULL COMMENT '二级分类',
    category_level1_henan VARCHAR(100) DEFAULT NULL COMMENT '一级分类-河南标准',
    category_level2_henan VARCHAR(100) DEFAULT NULL COMMENT '二级分类-河南标准',
    episode_count INT DEFAULT NULL COMMENT '集数',
    single_episode_duration DECIMAL(10,2) DEFAULT NULL COMMENT '单集时长',
    total_duration DECIMAL(10,2) DEFAULT NULL COMMENT '总时长',
    production_year INT DEFAULT NULL COMMENT '出品年代',
    premiere_date VARCHAR(100) DEFAULT NULL COMMENT '首播日期',
    authorization_region VARCHAR(200) DEFAULT NULL COMMENT '授权区域',
    authorization_platform VARCHAR(200) DEFAULT NULL COMMENT '授权平台',
    cooperation_mode VARCHAR(100) DEFAULT NULL COMMENT '合作方式',
    production_region VARCHAR(200) DEFAULT NULL COMMENT '制作地区',
    language VARCHAR(100) DEFAULT NULL COMMENT '语言',
    language_henan VARCHAR(100) DEFAULT NULL COMMENT '语言-河南标准',
    country VARCHAR(100) DEFAULT NULL COMMENT '国别',
    director VARCHAR(500) DEFAULT NULL COMMENT '导演',
    screenwriter VARCHAR(500) DEFAULT NULL COMMENT '编剧',
    cast_members TEXT COMMENT '主演/嘉宾/主持人',
    author VARCHAR(500) DEFAULT NULL COMMENT '作者',
    recommendation TEXT COMMENT '推荐语',
    synopsis TEXT COMMENT '简介',
    keywords VARCHAR(500) DEFAULT NULL COMMENT '关键字',
    video_quality VARCHAR(100) DEFAULT NULL COMMENT '视频质量（标清/高清/4K/3D/杜比）',
    license_number VARCHAR(200) DEFAULT NULL COMMENT '发行许可编号/备案号',
    rating DECIMAL(3,1) DEFAULT NULL COMMENT '评分',
    exclusive_status VARCHAR(50) DEFAULT NULL COMMENT '独家/非独',
    copyright_start_date VARCHAR(100) DEFAULT NULL COMMENT '版权开始时间',
    copyright_end_date VARCHAR(100) DEFAULT NULL COMMENT '版权结束时间',
    category_level2_shandong VARCHAR(100) DEFAULT NULL COMMENT '二级分类-山东标准',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY idx_media_name_unique (media_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='版权方数据库表';

-- ============================================
-- 4. 视频扫描结果表：存储扫描的视频文件信息
-- ============================================
CREATE TABLE video_scan_result (
    id INT NOT NULL AUTO_INCREMENT,
    source_folder VARCHAR(255) DEFAULT NULL COMMENT '来源文件夹',
    source_file VARCHAR(255) DEFAULT NULL COMMENT '来源文件（剧集名）',
    file_name VARCHAR(500) DEFAULT NULL COMMENT '文件名称',
    pinyin_abbr VARCHAR(100) DEFAULT NULL COMMENT '拼音缩写（如 xcm01）',
    duration_seconds DECIMAL(10,2) DEFAULT NULL COMMENT '时长（秒）',
    duration_formatted VARCHAR(20) DEFAULT NULL COMMENT '时长格式化（HHMMSS00）',
    size_bytes BIGINT DEFAULT NULL COMMENT '大小（字节）',
    md5 VARCHAR(32) DEFAULT NULL COMMENT 'MD5哈希值',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_source_file (source_file),
    KEY idx_file_name (file_name(255)),
    KEY idx_pinyin_abbr (pinyin_abbr),
    KEY idx_md5 (md5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='视频扫描结果';
