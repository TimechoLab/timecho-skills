# Timecho Skills

A comprehensive collection of AI assistant skills for working with Apache IoTDB and Apache TsFile. These skills provide detailed guidance, code examples, and best practices for developers working with time-series data storage and IoT applications.

[中文版](README_zh.md)

## 📚 Overview

This repository contains specialized skills designed to enhance AI assistant capabilities when helping developers work with:

1. **IoTDB** - A low-cost, high-performance IoT-native time-series database
2. **TsFile** - Open-source File Format for Industrial Time-Series Datasets
3. **TimechoDB** - Operations skills for TimechoDB: benchmarking, log analysis, Pipe sync, tiered storage, and Tree/Table model selection

## 🎯 Skills Included

### IoTDB Skill

**Purpose**: Comprehensive guide for connecting to and working with Apache IoTDB across multiple programming languages and data models.

**Features**:

- Multi-language support (Java, Python, C++, REST API)
- Dual data model support (Tree Model & Table Model)
- Connection methods:
  - Java SessionPool (production-recommended)
  - JDBC interface
  - Python client
  - C++ client
  - REST API
- Best practices for production deployments
- Memory-efficient data reading patterns
- Integration examples (Spring Boot, MyBatis)

**Use Cases**:

- Establishing IoTDB database connections
- Implementing data insertion and querying
- Configuring database sessions
- Building IoT monitoring applications
- Time-series data analytics

**Path**: `iotdb/`

### TsFile Skill

**Purpose**: Toolkit for working with Apache TsFile format for time-series data storage and processing.

**Features**:

- Multi-language support (Java, Python, C++, C)
- Read/write operations for TsFile format
- Schema design and optimization
- Batch processing for high performance
- Cross-language data exchange
- Integration with big data frameworks

**Use Cases**:

- Reading and writing TsFile files
- Time-series data storage optimization
- IoT data processing pipelines
- Data format conversion
- Performance tuning for large datasets

**Path**: `tsfile/`

### TimechoDB Skills

| Skill | Purpose | Path |
| --- | --- | --- |
| Benchmark | Size and run iot-benchmark load tests; report throughput, latency and failures | `timechodb-benchmark/` |
| Log Analyzer | Locate OOM, WAL/disk, compaction, slow-query and thread/file-handle problems in DataNode/ConfigNode logs | `timechodb-log-analyze/` |
| Pipe Sync | Station-to-center sync, cascading, dual-active, SSL, compression, air-gap transfer and backlog monitoring | `timechodb-pipe-sync/` |
| Tiered Storage | Hot/warm/cold tiers, object-storage cold tier, tier TTL and space thresholds | `timechodb-tier-storage/` |
| Tree/Table Guide | Choose between Tree and Table models; TAG/ATTRIBUTE/FIELD mapping and model-specific SQL | `timechodb-tree-table-guide/` |

## 🚀 Getting Started

### For AI Assistants

These skills are designed to be loaded into AI assistant systems (like Claude with MCP or similar frameworks) to provide specialized knowledge about IoTDB and TsFile.

Each skill contains:

- `SKILL.md` - Main skill definition and documentation
- `references/` - Detailed technical references and examples
- `assets/` - Code templates and configuration files
- `scripts/` - Utility scripts for testing and validation

### For Developers

Use these resources as comprehensive reference documentation:

1. **IoTDB Development**:
   - Browse [iotdb/SKILL.md](iotdb/SKILL.md) for connection guides
   - Check [iotdb/references/](iotdb/references/) for language-specific examples
   - Use templates in [iotdb/assets/connection_templates/](iotdb/assets/connection_templates/)

2. **TsFile Development**:
   - Browse [tsfile/SKILL.md](tsfile/SKILL.md) for file format operations
   - Check [tsfile/references/](tsfile/references/) for API documentation
   - Use examples in [tsfile/assets/](tsfile/assets/)

## 📖 Documentation Structure

```
timecho-skills/
├── iotdb/              # IoTDB connection and usage guide
│   ├── SKILL.md        # Main skill documentation
│   ├── references/     # Language-specific guides
│   │   ├── java_examples_priority.md
│   │   ├── python_examples.md
│   │   ├── cpp_examples.md
│   │   ├── rest_api.md
│   │   ├── jdbc_examples.md
│   │   ├── spring_boot_integration.md
│   │   ├── mybatis_integration.md
│   │   └── data_models.md
│   ├── assets/
│   │   └── connection_templates/
│   └── scripts/        # Validation and testing scripts
│
├── tsfile/             # TsFile format toolkit
│   ├── SKILL.md        # Main skill documentation
│   ├── references/     # API references
│   │   └── api_reference.md
│   ├── assets/         # Code examples and config
│   │   ├── TsFileExample.java
│   │   ├── tsfile_example.py
│   │   ├── tsfile_example.cpp
│   │   └── pom.xml
│   └── scripts/        # Build and example scripts
│
├── timechodb-benchmark/         # iot-benchmark load testing
├── timechodb-log-analyze/       # Log analysis and root cause location
├── timechodb-pipe-sync/         # Pipe data sync
├── timechodb-tier-storage/      # Tiered storage
├── timechodb-tree-table-guide/  # Tree/Table model selection
│   ├── SKILL.md
│   └── references/
│
└── LICENSE             # Apache License 2.0
```

## 🔧 Quick Examples

### IoTDB - Java SessionPool Connection

```java
SessionPool sessionPool = new SessionPool.Builder()
    .host("127.0.0.1")
    .port(6667)
    .user("root")
    .password("root")
    .maxSize(10)
    .build();

try (SessionDataSet dataSet = sessionPool.executeQueryStatement("SELECT * FROM root.factory.**")) {
    DataIterator iterator = dataSet.iterator();
    while (iterator.next()) {
        System.out.println("Time: " + iterator.getLong(1) + ", Value: " + iterator.getFloat(2));
    }
}
```

### TsFile - Python Write/Read

```python
from tsfile import TsFileTableWriter, TsFileReader, TableSchema

# Write data
with TsFileTableWriter("data.tsfile", schema) as writer:
    writer.write_table(tablet)

# Read data
with TsFileReader("data.tsfile") as reader:
    df = reader.read_table(table_name)
```

## 📋 Requirements

### IoTDB Skill

- Java: IoTDB Java API (SessionPool/JDBC)
- Python: `apache-iotdb` package
- C++: IoTDB C++ client library
- REST: HTTP client (any language)

### TsFile Skill

- Java: Maven/Gradle with TsFile dependencies
- Python: TsFile Python package (requires C++ build)
- C++: CMake and TsFile C++ library
- C: TsFile C bindings

## 🤝 Contributing

Contributions are welcome! Please ensure:

- Code examples follow best practices
- Documentation is clear and accurate
- Examples are tested and working
- Follow the existing structure and style

## 📄 License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

Both Apache IoTDB and Apache TsFile are Apache Software Foundation projects licensed under Apache 2.0. All code examples and templates in this repository follow the same license for compatibility.

## 🔗 Related Projects

- [Apache IoTDB](https://iotdb.apache.org/) - Official IoTDB website
- [Apache TsFile](https://github.com/apache/tsfile) - TsFile repository
- [IoTDB Documentation](https://iotdb.apache.org/UserGuide/Master/QuickStart/QuickStart.html) - Official documentation

## 💡 Use Cases

### IoT Monitoring

Use IoTDB skill to build real-time monitoring systems for sensors, devices, and industrial equipment with high-throughput data ingestion.

### Data Analytics

Leverage both skills to process and analyze large-scale time-series datasets with efficient storage and query capabilities.

### System Integration

Integrate IoTDB with existing Java applications using Spring Boot and MyBatis integration patterns provided in the IoTDB skill.

### Data Exchange

Use TsFile skill to export, share, and archive time-series data in a portable, efficient columnar format.

## 📞 Support

For issues related to:

- **These skills**: Open an issue in this repository
- **Apache IoTDB**: Visit [IoTDB GitHub](https://github.com/apache/iotdb)
- **Apache TsFile**: Visit [TsFile GitHub](https://github.com/apache/tsfile)

---

**Maintained by Timecho Lab**
