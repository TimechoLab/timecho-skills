---
name: timechodb-test-gen
description: >
  Generate test cases from knowledge base: deployment verification, RN defect,
  performance regression. Output steps + expected results + report.
description_zh: 根据知识库生成测试用例：部署验证/RN缺陷/性能回归，输出步骤化用例与报告
version: 1.0.0
agent_created: true
---

# TimechoDB 测试用例生成 (Test Gen)

## 触发场景

- "根据这个 RN 生成测试用例"
- "帮我写一个回归测试脚本"

## 工作流

### Step 1 — 解析输入

从 Release Note 或需求描述中提取：
- 涉及的操作域（部署/SQL/配置/性能）
- 变更参数或 SQL 语法
- 预期行为

### Step 2 — 生成用例模板

```markdown
## 用例: <title>
- 来源: RN-xxxx
- 类型: 功能验证 / 性能回归 / 兼容性
- 前置条件: <要求>
- 优先级: P0/P1/P2

### 步骤
1. <action 1>
2. <action 2>
3. <验证点>

### 预期结果
- <expected behavior>

### 清理
- <cleanup steps>
```

### Step 3 — 示例

**来源: 表模型建表语法 — `time` 列由系统隐式创建**

```markdown
## 用例: 隐式 TIME 列创建表
- 来源: 表模型建表语法
- 类型: 功能验证
- 优先级: P1

### 步骤
1. CREATE TABLE t1(dev STRING TAG, v FLOAT FIELD)
2. DESC t1; → 确认系统自动生成 `time TIMESTAMP TIME` 列
3. INSERT INTO t1(time, dev, v) VALUES(1000, 'd1', 23.5)
4. SELECT * FROM t1; → 正常返回

### 预期结果
- 表创建成功，隐式 `time` 列正常读写

### 清理
- DROP TABLE t1
```
