-- 确保客户端使用正确的字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 删除已存在的数据库（如果存在），以便重新创建
DROP DATABASE IF EXISTS operation_management;

-- 创建数据库
CREATE DATABASE IF NOT EXISTS operation_management DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE operation_management;

-- 1. 剧集主表：使用JSON字段存储动态属性
CREATE TABLE IF NOT EXISTS drama_main (
    drama_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '剧集ID，自增主键',
    drama_name VARCHAR(500) NOT NULL COMMENT '剧集名称',
    dynamic_properties JSON DEFAULT NULL COMMENT '动态属性，存储不同剧集的所有属性',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT='剧集主表，使用JSON存储动态属性';

-- 2. 剧集子集表：使用JSON字段存储动态属性
CREATE TABLE IF NOT EXISTS drama_episode (
    episode_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '集数ID，自增主键',
    drama_id INT NOT NULL COMMENT '关联的剧集ID',
    episode_name VARCHAR(500) NOT NULL COMMENT '节目名称（集数名称）',
    dynamic_properties JSON DEFAULT NULL COMMENT '动态属性，存储不同集数的所有属性',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (drama_id) REFERENCES drama_main(drama_id) ON DELETE CASCADE ON UPDATE CASCADE,
    KEY idx_drama_episode (drama_id, episode_name) COMMENT '按剧集和集数名称排序的索引'
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT='剧集子集表，使用JSON存储动态属性';

