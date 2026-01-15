# Implementation Plan: 版权更新优化

## Overview

本实现计划将优化 `web_app1/routers/copyright.py` 中的版权数据更新逻辑，实现增量更新、事务保护和批量操作。

## Tasks

- [x] 1. 实现增量更新核心函数
  - [x] 1.1 创建 `_get_current_episode_count()` 函数获取当前子集数量
    - 查询指定 drama_id 的子集数量
    - 返回整数值
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.2 创建 `_update_episodes_incremental()` 函数实现增量更新逻辑
    - 比较 old_count 和 new_count
    - 集数不变时不操作
    - 集数增加时调用批量追加
    - 集数减少时删除多余子集
    - 返回操作统计信息
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 1.3 编写属性测试：增量更新正确性
    - **Property 1: 增量更新正确性**
    - **Validates: Requirements 1.1, 1.2, 1.3**

- [x] 2. 实现批量插入优化
  - [x] 2.1 创建 `_batch_create_episodes()` 函数
    - 构建所有子集数据列表
    - 使用 executemany 批量插入
    - 支持指定起始和结束集数
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 2.2 重构 `_create_episodes_for_customer()` 使用批量插入
    - 调用 `_batch_create_episodes()` 替代逐条插入
    - _Requirements: 3.1, 3.2_

- [x] 3. 实现介质名称变更处理
  - [x] 3.1 创建 `_update_episode_properties()` 函数
    - 当介质名称变化时更新所有子集的节目名称和媒体地址
    - 使用批量更新语句
    - _Requirements: 1.4_

  - [ ]* 3.2 编写属性测试：介质名称变更传播
    - **Property 3: 介质名称变更传播**
    - **Validates: Requirements 1.4**

- [x] 4. 重构 `_update_drama_for_customer()` 函数
  - [x] 4.1 修改函数签名，增加 old_episode_count 和 old_media_name 参数
    - 接收原集数和原介质名称用于比较
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 4.2 实现增量更新逻辑
    - 调用 `_update_episodes_incremental()` 替代全删全建
    - 检测介质名称变化并调用属性更新
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 4.3 编写属性测试：子集ID保持性
    - **Property 2: 子集ID保持性**
    - **Validates: Requirements 1.1, 1.2**

- [x] 5. 实现事务一致性保证
  - [x] 5.1 重构 `update_copyright()` API 添加事务控制
    - 移除中间 commit 调用（当前有多处 conn.commit()）
    - 添加 try/except/rollback 结构
    - 所有操作在单一事务中完成
    - 传递原集数和原介质名称给 `_update_drama_for_customer()`
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 5.2 编写属性测试：事务原子性
    - **Property 4: 事务原子性**
    - **Validates: Requirements 2.1, 2.2**

- [x] 6. 添加性能监控日志
  - [x] 6.1 添加更新操作耗时记录
    - 记录开始和结束时间
    - 计算并记录总耗时
    - _Requirements: 4.1_

  - [x] 6.2 添加操作统计日志
    - 记录更新的剧头数量
    - 记录子集的增删改数量
    - _Requirements: 4.2_

- [x] 7. Checkpoint - 确保所有测试通过
  - 运行所有单元测试和属性测试
  - 确保无回归问题
  - 如有问题请询问用户

## Notes

- 任务标记 `*` 的为可选测试任务，可跳过以加快 MVP 开发
- 每个任务都引用了具体的需求条款以便追溯
- 属性测试使用 `hypothesis` 库，每个测试至少运行100次迭代
- 所有修改集中在 `web_app1/routers/copyright.py` 文件
- 当前 `_update_drama_for_customer()` 使用全删全建方式，需要重构为增量更新
- 当前 `_create_episodes_for_customer()` 使用逐条插入，需要重构为批量插入
- 当前 `update_copyright()` API 有多处 `conn.commit()` 调用，需要合并为单一事务
