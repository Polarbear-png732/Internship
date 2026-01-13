-- 为 copyright_content 表添加 drama_id 和 customer_id 字段，建立关联关系

USE operation_management;

-- 添加 drama_id 字段，关联到 drama_main 表
ALTER TABLE copyright_content 
ADD COLUMN drama_id INT COMMENT '关联的剧集ID' AFTER id,
ADD COLUMN customer_id INT COMMENT '客户ID' AFTER drama_id;

-- 添加外键约束（级联删除：删除版权信息时自动删除对应的剧集和子集）
ALTER TABLE copyright_content
ADD CONSTRAINT fk_copyright_drama 
FOREIGN KEY (drama_id) REFERENCES drama_main(drama_id) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- 添加客户外键约束
ALTER TABLE copyright_content
ADD CONSTRAINT fk_copyright_customer 
FOREIGN KEY (customer_id) REFERENCES customer(customer_id) 
ON DELETE RESTRICT ON UPDATE CASCADE;

-- 添加索引
ALTER TABLE copyright_content
ADD KEY idx_drama_id (drama_id),
ADD KEY idx_customer_id (customer_id);
