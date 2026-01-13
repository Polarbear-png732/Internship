-- 修复 copyright_content 表的外键约束（如果字段已存在但约束未添加）

USE operation_management;

-- 添加外键约束（级联删除：删除版权信息时自动删除对应的剧集和子集）
-- 如果约束已存在会报错，忽略即可
ALTER TABLE copyright_content
ADD CONSTRAINT fk_copyright_drama 
FOREIGN KEY (drama_id) REFERENCES drama_main(drama_id) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- 添加客户外键约束
ALTER TABLE copyright_content
ADD CONSTRAINT fk_copyright_customer 
FOREIGN KEY (customer_id) REFERENCES customer(customer_id) 
ON DELETE RESTRICT ON UPDATE CASCADE;

