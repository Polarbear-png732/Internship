# 数据清空脚本使用说明

## 脚本列表

### 1. `truncate_tables.sql` - 快速清空脚本
**用途**: 快速清空三个表的所有数据

**清空的表**:
- `drama_episode` - 剧集子集表
- `drama_main` - 剧集主表（剧头表）
- `copyright_content` - 版权方数据表

**特点**:
- 简单快速
- 自动重置自增ID
- 无备份

### 2. `truncate_tables_safe.sql` - 安全清空脚本（推荐）
**用途**: 带统计信息的安全清空

**特点**:
- 显示清空前后的数据统计
- 包含详细的警告信息
- 自动处理外键约束
- 推荐日常使用

### 3. `backup_before_truncate.sql` - 备份脚本
**用途**: 清空前备份数据

**特点**:
- 创建备份表（`*_backup`）
- 保留原始数据
- 可用于数据恢复

### 4. `restore_from_backup.sql` - 恢复脚本
**用途**: 从备份恢复数据

**特点**:
- 从备份表恢复数据
- 自动处理外键约束
- 显示恢复统计

## 使用方法

### 方法1: 快速清空（无备份）

```powershell
# PowerShell
Get-Content sql\truncate_tables_safe.sql | mysql -u root -p operation_management

# 或使用 CMD
cmd /c "mysql -u root -p operation_management < sql\truncate_tables_safe.sql"
```

### 方法2: 安全清空（带备份）

**步骤1: 备份数据**
```powershell
Get-Content sql\backup_before_truncate.sql | mysql -u root -p operation_management
```

**步骤2: 清空数据**
```powershell
Get-Content sql\truncate_tables_safe.sql | mysql -u root -p operation_management
```

**步骤3: 如需恢复**
```powershell
Get-Content sql\restore_from_backup.sql | mysql -u root -p operation_management
```

### 方法3: 使用MySQL客户端

```bash
mysql -u root -p operation_management
```

然后在MySQL客户端中：
```sql
source sql/truncate_tables_safe.sql;
```

## 注意事项

### ⚠️ 重要警告

1. **数据不可恢复**: `TRUNCATE` 操作会永久删除数据，无法通过事务回滚
2. **自增ID重置**: 清空后，自增ID会重置为1
3. **外键约束**: 脚本会自动处理外键约束，但请确保没有其他表引用这些数据
4. **生产环境**: 在生产环境使用前，务必先备份数据

### 📋 清空前检查清单

- [ ] 确认要清空的是正确的数据库（`operation_management`）
- [ ] 确认当前没有重要数据需要保留
- [ ] 如有重要数据，先执行备份脚本
- [ ] 确认没有其他应用正在使用这些数据
- [ ] 通知相关人员（如果是共享环境）

### 🔄 清空后的影响

1. **版权方数据表** (`copyright_content`)
   - 所有版权数据被删除
   - ID从1重新开始
   - 需要重新导入数据

2. **剧集主表** (`drama_main`)
   - 所有剧头数据被删除
   - drama_id从1重新开始
   - 关联的子集也会被删除

3. **剧集子集表** (`drama_episode`)
   - 所有子集数据被删除
   - episode_id从1重新开始

## 常见问题

### Q1: 清空后如何重新导入数据？

**A**: 使用Excel导入功能
```
1. 访问 http://localhost:8000
2. 点击"批量导入"
3. 上传Excel文件（如 tables/精确匹配版权方数据.xlsx）
4. 确认导入
```

### Q2: 如何只清空某一个表？

**A**: 修改脚本，注释掉不需要清空的表
```sql
-- TRUNCATE TABLE drama_episode;  -- 注释掉不清空
TRUNCATE TABLE drama_main;
TRUNCATE TABLE copyright_content;
```

### Q3: 清空后自增ID没有重置？

**A**: 使用 `TRUNCATE` 会自动重置，如果使用 `DELETE` 则需要手动重置：
```sql
ALTER TABLE copyright_content AUTO_INCREMENT = 1;
ALTER TABLE drama_main AUTO_INCREMENT = 1;
ALTER TABLE drama_episode AUTO_INCREMENT = 1;
```

### Q4: 出现外键约束错误？

**A**: 确保脚本中包含了外键检查的禁用和启用：
```sql
SET FOREIGN_KEY_CHECKS = 0;
-- 清空操作
SET FOREIGN_KEY_CHECKS = 1;
```

### Q5: 如何验证数据已清空？

**A**: 执行查询
```sql
SELECT COUNT(*) FROM copyright_content;
SELECT COUNT(*) FROM drama_main;
SELECT COUNT(*) FROM drama_episode;
```

所有结果应该为 0。

## 备份策略建议

### 开发环境
- 定期备份（每周）
- 清空前可选备份

### 测试环境
- 清空前必须备份
- 保留最近3次备份

### 生产环境
- **禁止使用清空脚本**
- 使用专业的备份工具
- 定期全量备份 + 增量备份

## 相关文件

- `create_database.sql` - 数据库创建脚本
- `alter_add_premiere_date_author.sql` - 字段添加脚本
- `backup_20260121.sql` - 历史备份文件

## 技术支持

如有问题，请联系开发团队。

---

**最后更新**: 2026-01-21  
**版本**: 1.0
