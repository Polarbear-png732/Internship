# 数据库备份与恢复指南

## 📋 概述

本指南介绍如何备份和恢复整个 `operation_management` 数据库。

---

## 🔄 备份数据库

### Windows PowerShell 备份命令

```powershell
# 备份到当前目录（带时间戳）
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
mysqldump -u root -p operation_management > "backup_operation_management_$timestamp.sql"

# 备份到指定目录
mysqldump -u root -p operation_management > "D:\backups\operation_management_backup.sql"
```

### Windows CMD 备份命令

```cmd
REM 备份到当前目录
mysqldump -u root -p operation_management > backup_operation_management.sql

REM 备份到指定目录
mysqldump -u root -p operation_management > D:\backups\operation_management_backup.sql
```

### 备份选项说明

```bash
# 完整备份（推荐）
mysqldump -u root -p operation_management > backup.sql

# 仅备份数据结构（不含数据）
mysqldump -u root -p --no-data operation_management > schema_only.sql

# 仅备份数据（不含结构）
mysqldump -u root -p --no-create-info operation_management > data_only.sql

# 压缩备份（节省空间）
mysqldump -u root -p operation_management | gzip > backup.sql.gz
```

---

## 🔙 恢复数据库

### 方法1: 恢复到现有数据库

```powershell
# PowerShell
Get-Content backup_operation_management.sql | mysql -u root -p operation_management

# CMD
mysql -u root -p operation_management < backup_operation_management.sql
```

### 方法2: 先删除再重建数据库（完全恢复）

```sql
-- 1. 登录MySQL
mysql -u root -p

-- 2. 删除现有数据库
DROP DATABASE IF EXISTS operation_management;

-- 3. 重新创建数据库
CREATE DATABASE operation_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 4. 退出MySQL
EXIT;

-- 5. 恢复数据
mysql -u root -p operation_management < backup_operation_management.sql
```

### 恢复压缩备份

```bash
# 解压并恢复
gunzip < backup.sql.gz | mysql -u root -p operation_management
```

---

## 📝 重新导入数据流程

### 完整流程（推荐）

```powershell
# 1. 备份当前数据库
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
mysqldump -u root -p operation_management > "backup_before_reimport_$timestamp.sql"

# 2. 清空所有表
Get-Content sql\truncate_all_tables.sql | mysql -u root -p operation_management

# 3. 重新导入版权数据（通过Web界面）
# 访问 http://localhost:8000
# 使用导入功能上传Excel文件

# 4. 验证数据
# 检查版权数据、剧头、子集是否正确生成
```

### 如果导入失败需要恢复

```powershell
# 恢复之前的备份
Get-Content backup_before_reimport_YYYYMMDD_HHMMSS.sql | mysql -u root -p operation_management
```

---

## 🎯 使用场景

### 场景1: 为所有客户重新生成剧头和子集

```powershell
# 1. 备份数据库
mysqldump -u root -p operation_management > backup_before_regenerate.sql

# 2. 清空表
Get-Content sql\truncate_all_tables.sql | mysql -u root -p operation_management

# 3. 重新导入版权数据
# 系统会自动为所有7个启用的客户生成剧头和子集：
#   - 河南移动 (henan_mobile)
#   - 山东移动 (shandong_mobile)
#   - 甘肃移动 (gansu_mobile)
#   - 江苏新媒体 (jiangsu_newmedia)
#   - 浙江移动 (zhejiang_mobile)
#   - 新疆电信 (xinjiang_telecom)
#   - 江西移动 (jiangxi_mobile)
```

### 场景2: 测试环境重置

```powershell
# 1. 备份生产数据
mysqldump -u root -p operation_management > production_backup.sql

# 2. 清空测试环境
Get-Content sql\truncate_all_tables.sql | mysql -u root -p operation_management

# 3. 导入测试数据
```

### 场景3: 数据迁移

```powershell
# 源服务器：导出数据
mysqldump -u root -p operation_management > migration_data.sql

# 目标服务器：导入数据
mysql -u root -p operation_management < migration_data.sql
```

---

## ⚠️ 重要提示

1. **备份频率建议**：
   - 生产环境：每天自动备份
   - 开发环境：重要操作前手动备份
   - 测试环境：按需备份

2. **备份存储建议**：
   - 保存在数据库服务器之外的位置
   - 定期验证备份文件的完整性
   - 保留多个历史版本（至少7天）

3. **清空表前必须**：
   - ✅ 确认已备份数据库
   - ✅ 确认备份文件可以正常恢复
   - ✅ 通知相关人员（生产环境）

4. **恢复数据后**：
   - 验证数据完整性
   - 检查自增ID是否正确
   - 测试应用功能是否正常

---

## 🔧 自动化备份脚本

### PowerShell 自动备份脚本

创建文件 `backup_database.ps1`：

```powershell
# 数据库自动备份脚本
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "D:\database_backups"
$backupFile = "$backupDir\operation_management_$timestamp.sql"

# 创建备份目录
if (!(Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir
}

# 执行备份
Write-Host "开始备份数据库..."
mysqldump -u root -p operation_management > $backupFile

# 检查备份是否成功
if (Test-Path $backupFile) {
    $fileSize = (Get-Item $backupFile).Length / 1MB
    Write-Host "✓ 备份成功: $backupFile"
    Write-Host "  文件大小: $([math]::Round($fileSize, 2)) MB"
    
    # 删除7天前的备份
    Get-ChildItem $backupDir -Filter "operation_management_*.sql" | 
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | 
        Remove-Item -Force
    
    Write-Host "✓ 已清理7天前的旧备份"
} else {
    Write-Host "✗ 备份失败"
}
```

### 设置定时任务（Windows）

```powershell
# 创建每天凌晨2点自动备份的任务
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File D:\scripts\backup_database.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
Register-ScheduledTask -TaskName "DatabaseBackup" -Action $action -Trigger $trigger -Description "每天自动备份数据库"
```

---

## 📞 常见问题

### Q: 备份文件太大怎么办？
A: 使用压缩备份：`mysqldump -u root -p operation_management | gzip > backup.sql.gz`

### Q: 如何只备份特定表？
A: `mysqldump -u root -p operation_management copyright_content drama_main > partial_backup.sql`

### Q: 恢复时报错"表已存在"？
A: 先删除数据库再恢复，或使用 `--force` 参数：`mysql -u root -p --force operation_management < backup.sql`

### Q: 如何验证备份文件是否完整？
A: 
```bash
# 检查文件大小
ls -lh backup.sql

# 检查文件内容
head -n 20 backup.sql
tail -n 20 backup.sql

# 尝试恢复到测试数据库
mysql -u root -p test_db < backup.sql
```

---

## 📚 相关文档

- `sql/truncate_all_tables.sql` - 清空所有表脚本
- `sql/create_database.sql` - 数据库创建脚本
- `docs/add_new_customer_guide.md` - 新增客户配置指南
