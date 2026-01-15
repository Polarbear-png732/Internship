# Requirements Document

## Introduction

优化版权数据更新逻辑，提升更新操作的性能和数据一致性。当前系统在更新版权信息时，会全量删除并重建所有子集数据，即使集数没有变化也会执行这个操作，造成不必要的性能开销。同时缺乏事务一致性保证，可能导致数据不一致。

## Glossary

- **Copyright_Service**: 版权数据管理服务，负责版权信息的增删改查
- **Drama_Main**: 剧头表，存储剧集主信息
- **Drama_Episode**: 子集表，存储每集信息
- **Episode_Count**: 集数，版权数据中的总集数字段
- **Transaction**: 数据库事务，保证一组操作的原子性

## Requirements

### Requirement 1: 子集增量更新

**User Story:** As a 系统管理员, I want 更新版权信息时只在集数变化时重建子集, so that 减少不必要的数据库操作提升性能。

#### Acceptance Criteria

1. WHEN 更新版权数据且集数(episode_count)未变化, THE Copyright_Service SHALL 只更新剧头(drama_main)的动态属性而不重建子集
2. WHEN 更新版权数据且集数(episode_count)增加, THE Copyright_Service SHALL 保留现有子集并追加新增的子集
3. WHEN 更新版权数据且集数(episode_count)减少, THE Copyright_Service SHALL 删除多余的子集并保留剩余子集
4. WHEN 更新版权数据且介质名称(media_name)变化, THE Copyright_Service SHALL 更新所有子集的节目名称和媒体拉取地址

### Requirement 2: 事务一致性保证

**User Story:** As a 系统管理员, I want 版权数据更新操作具有事务一致性, so that 避免部分更新导致的数据不一致问题。

#### Acceptance Criteria

1. THE Copyright_Service SHALL 在单一事务中完成版权数据及所有关联剧头/子集的更新
2. IF 更新过程中发生任何错误, THEN THE Copyright_Service SHALL 回滚所有已执行的更改
3. WHEN 事务提交成功, THE Copyright_Service SHALL 返回更新成功的响应
4. WHEN 事务回滚, THE Copyright_Service SHALL 返回包含错误详情的失败响应

### Requirement 3: 批量插入优化

**User Story:** As a 系统管理员, I want 子集数据使用批量插入, so that 减少数据库交互次数提升创建性能。

#### Acceptance Criteria

1. WHEN 创建多个子集时, THE Copyright_Service SHALL 使用批量插入(executemany)而非逐条插入
2. WHEN 批量插入子集, THE Copyright_Service SHALL 在单次数据库调用中插入所有子集数据
3. THE Copyright_Service SHALL 支持批量插入至少100条子集数据

### Requirement 4: 更新性能监控

**User Story:** As a 开发人员, I want 更新操作记录执行时间, so that 可以监控和优化性能。

#### Acceptance Criteria

1. WHEN 执行版权数据更新, THE Copyright_Service SHALL 在日志中记录操作耗时
2. THE Copyright_Service SHALL 记录更新影响的剧头数量和子集数量
