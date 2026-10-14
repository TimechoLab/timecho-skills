# Timecho Skills

专为 Apache IoTDB 和 Apache TsFile 设计的 AI 助手技能集合。这些技能为开发人员提供详细的指南、代码示例和最佳实践，帮助他们更好地使用时序数据存储和物联网应用。

[English Version](README.md)

## 📚 概述

本仓库包含多个专业技能，旨在增强 AI 助手在以下领域帮助开发人员的能力:

1. **IoTDB** - 低成本、高性能的物联网原生时序数据库
2. **TsFile** - 工业时序数据集的开源文件格式
3. **TimechoDB** - TimechoDB 运维类技能：性能测试、日志分析、Pipe 同步、多级存储、树/表模型选型

## 🎯 包含的技能

### IoTDB 技能

**目的**: 提供跨多种编程语言和数据模型连接和使用 Apache IoTDB 的综合指南。

**特性**:

- 多语言支持(Java、Python、C++、REST API)
- 双数据模型支持(树模型 & 表模型)
- 连接方式:
  - Java / Python SessionPool（树模型）与 TableSessionPool（表模型）
  - C++ SessionPool（V2.0.11+）
  - JDBC 接口
  - REST API
- 生产部署最佳实践
- 内存高效的数据读取模式
- 集成示例(Spring Boot、MyBatis)

**使用场景**:

- 建立 IoTDB 数据库连接
- 实现数据插入和查询
- 配置数据库会话
- 构建物联网监控应用
- 时序数据分析

**路径**: `iotdb/`

### TsFile 技能

**目的**: 用于处理 Apache TsFile 格式时序数据存储和处理的工具包。

**特性**:

- 多语言支持(Java、Python、C++、C)
- TsFile 格式的读写操作
- 模式设计和优化
- 高性能批处理
- 跨语言数据交换
- 与大数据框架集成

**使用场景**:

- 读写 TsFile 文件
- 时序数据存储优化
- 物联网数据处理管道
- 数据格式转换
- 大数据集性能调优

**路径**: `tsfile/`

### TimechoDB 技能

| 技能 | 用途 | 路径 |
| --- | --- | --- |
| 性能测试 | 按服务端资源确定 iot-benchmark 压测规模并执行，输出吞吐、延迟与失败数 | `timechodb-benchmark/` |
| 日志分析 | 从 DataNode/ConfigNode 日志定位 OOM、WAL/磁盘、Compaction、慢查询、线程与句柄问题 | `timechodb-log-analyze/` |
| Pipe 同步 | 场站→中心汇聚、级联、双活、SSL、压缩、网闸穿透与积压监控 | `timechodb-pipe-sync/` |
| 多级存储 | 热/温/冷分层、对象存储冷层、分层 TTL 与空间阈值 | `timechodb-tier-storage/` |
| 树/表模型选型 | 树模型与表模型的选择、TAG/ATTRIBUTE/FIELD 映射与模型专属 SQL | `timechodb-tree-table-guide/` |

## 🚀 快速开始

### 对于 AI 助手

这些技能设计用于加载到 AI 助手系统中(如 Claude with MCP 或类似框架),以提供关于 IoTDB 和 TsFile 的专业知识。

每个技能包含:

- `SKILL.md` - 主技能定义和文档
- `references/` - 详细的技术参考和示例
- `assets/` - 代码模板和配置文件
- `scripts/` - 测试和验证实用程序脚本

### 对于开发人员

将这些资源用作综合参考文档:

1. **IoTDB 开发**:
   - 浏览 [iotdb/SKILL.md](iotdb/SKILL.md) 获取连接指南
   - 查看 [iotdb/references/](iotdb/references/) 获取特定语言示例
   - 使用 [iotdb/assets/connection_templates/](iotdb/assets/connection_templates/) 中的模板

2. **TsFile 开发**:
   - 浏览 [tsfile/SKILL.md](tsfile/SKILL.md) 了解文件格式操作
   - 查看 [tsfile/references/](tsfile/references/) 获取 API 文档
   - 使用 [tsfile/assets/](tsfile/assets/) 中的示例

## 📖 文档结构

```
timecho-skills/
├── iotdb/              # IoTDB 连接和使用指南
│   ├── SKILL.md        # 主技能文档
│   ├── references/     # 特定语言指南
│   │   ├── java_examples.md
│   │   ├── python_examples.md
│   │   ├── cpp_examples.md
│   │   ├── rest_api.md
│   │   ├── jdbc_examples.md
│   │   ├── spring_boot_integration.md
│   │   ├── mybatis_integration.md
│   │   └── data_models.md
│   ├── assets/
│   │   └── connection_templates/
│   └── scripts/        # 验证和测试脚本
│
├── tsfile/             # TsFile 格式工具包
│   ├── SKILL.md        # 主技能文档
│   ├── references/     # API 参考
│   │   └── api_reference.md
│   ├── assets/         # 代码示例和配置
│   │   ├── TsFileExample.java
│   │   ├── tsfile_example.py
│   │   ├── tsfile_example.cpp
│   │   └── pom.xml
│   └── scripts/        # 构建和示例脚本
│
├── timechodb-benchmark/         # iot-benchmark 性能测试
├── timechodb-log-analyze/       # 日志分析与根因定位
├── timechodb-pipe-sync/         # Pipe 数据同步
├── timechodb-tier-storage/      # 多级存储
├── timechodb-tree-table-guide/  # 树/表模型选型
│   ├── SKILL.md
│   └── references/
│
└── LICENSE             # Apache License 2.0
```

## 🔧 快速示例

### IoTDB - Java SessionPool 连接

```java
SessionPool sessionPool = new SessionPool.Builder()
    .host("127.0.0.1")
    .port(6667)
    .user("root")
    .password("root")
    .maxSize(10)
    .build();

// SessionPool 返回 SessionDataSetWrapper，关闭它即把 session 归还给连接池
try (SessionDataSetWrapper wrapper = sessionPool.executeQueryStatement(
        "SELECT temperature FROM root.factory.line1.device7 LIMIT 10")) {
    SessionDataSet.DataIterator iterator = wrapper.iterator();
    while (iterator.next()) {
        System.out.println("Time: " + iterator.getLong(1) + ", Value: " + iterator.getFloat(2));
    }
}
```

### TsFile - Python 读写

```python
from tsfile import TsFileTableWriter, TsFileReader, TableSchema

# 写入数据
with TsFileTableWriter("data.tsfile", schema) as writer:
    writer.write_table(tablet)

# 读取数据
with TsFileReader("data.tsfile") as reader:
    df = reader.read_table(table_name)
```

## 📋 环境要求

### IoTDB 技能

- Java: `iotdb-session`（SessionPool / TableSessionPool）、`iotdb-jdbc`
- Python: `apache-iotdb` 包
- C++: IoTDB C++ 客户端库
- REST: HTTP 客户端(任何语言)

### TsFile 技能

- Java: Maven/Gradle 及 TsFile 依赖
- Python: TsFile Python 包(需要 C++ 构建)
- C++: CMake 和 TsFile C++ 库
- C: TsFile C 绑定

## 🤝 贡献

欢迎贡献! 请确保:

- 代码示例遵循最佳实践
- 文档清晰准确
- 示例经过测试且可运行
- 遵循现有结构和风格

## 📄 许可证

本项目采用 **Apache License 2.0** 许可证 - 详见 [LICENSE](LICENSE) 文件。

Apache IoTDB 和 Apache TsFile 都是 Apache 软件基金会项目,采用 Apache 2.0 许可证。本仓库中的所有代码示例和模板遵循相同的许可证以保持兼容性。

## 🔗 相关项目

- [Apache IoTDB](https://iotdb.apache.org/) - IoTDB 官方网站
- [Apache TsFile](https://github.com/apache/tsfile) - TsFile 仓库
- [IoTDB 文档](https://iotdb.apache.org/zh/UserGuide/Master/QuickStart/QuickStart.html) - 官方文档

## 💡 使用场景

### 物联网监控

使用 IoTDB 技能构建实时监控系统,用于传感器、设备和工业设备的高吞吐量数据采集。

### 数据分析

利用两个技能处理和分析大规模时序数据集,具有高效的存储和查询能力。

### 系统集成

使用 IoTDB 技能中提供的 Spring Boot 和 MyBatis 集成模式,将 IoTDB 集成到现有 Java 应用程序中。

### 数据交换

使用 TsFile 技能以便携、高效的列式格式导出、共享和归档时序数据。

## 📞 支持

如有问题:

- **这些技能相关**: 在本仓库中提交 issue
- **Apache IoTDB**: 访问 [IoTDB GitHub](https://github.com/apache/iotdb)
- **Apache TsFile**: 访问 [TsFile GitHub](https://github.com/apache/tsfile)

---

**由 Timecho Lab 维护**
