---
name: iotdb
description: Comprehensive guide for connecting to Apache IoTDB using Java SessionPool/Session/JDBC, Python, C++, and REST APIs. PRIORITIZES SessionPool for production applications and iterator-based data reading for optimal memory efficiency. Provides detailed syntax guides for both tree model (timeseries) and table model (relational) data structures. Use when users need to establish IoTDB connections, implement data insertion/querying, configure database sessions, or work with IoTDB clients across different programming languages and data models.
license: Complete terms in LICENSE.txt
---

# IoTDB Connection Guide

## License

This skill is licensed under the **Apache License 2.0**.

IoTDB itself is an Apache Software Foundation project licensed under Apache 2.0. All code examples and templates in this skill follow the same license for compatibility and consistency with the IoTDB ecosystem.

## Overview

Provides comprehensive guidance for establishing connections to Apache IoTDB across multiple programming languages (Java, Python, C++, REST) and data models (Tree Model for timeseries, Table Model for relational-style data).

## Connection Decision Tree

Choose your connection method based on your requirements:

1. **Java Applications (RECOMMENDED)** → Use IoTDB SessionPool (Primary) or JDBC (Secondary)
   - **SessionPool**: **BEST CHOICE** for production applications with connection pooling and thread safety
   - **JDBC**: Standard SQL interface for existing applications and frameworks
   - Native performance and full feature support
   - Supports both tree and table models
   - **Always use iterator-based reading** for memory efficiency

2. **Python Applications** → Use IoTDB Python Client
   - Full-featured Python API with pandas support
   - Great for data science and analytics workflows
   - Supports both tree and table models
   - **Iterator support available** for large datasets

3. **C++ Applications** → Use IoTDB C++ Client
   - High-performance native C++ integration
   - Ideal for embedded systems or high-performance applications
   - Currently supports tree model

4. **Language-agnostic/HTTP** → Use REST API
   - Cross-platform HTTP-based access
   - Simple integration for any language with HTTP support
   - Supports basic query and insert operations

## Data Model Selection

**Tree Model (Timeseries) - Traditional IoTDB**

- Hierarchical path-based data organization (e.g., `root.factory.workshop.temperature`)
- Optimized for IoT timeseries data with high ingestion rates
- Path structure: `root.{database}.{device}.{sensor}`
- **Best for**: Real-time monitoring, IoT sensors, time-series analytics
- **Syntax**: See [Data Models Guide](references/data_models.md) for complete syntax reference

**Table Model (Relational) - SQL-Like**

- SQL-like table structure with tags, attributes, and fields
- More familiar for users coming from relational databases
- Better for complex queries, joins, and business analytics
- Structure: Tables with columns categorized as TAG, ATTRIBUTE, or FIELD
- **Best for**: Business intelligence, complex analytics, multi-dimensional queries
- **Syntax**: See [Data Models Guide](references/data_models.md) for complete syntax reference

## Java Connection (SessionPool & JDBC)

### 🚀 RECOMMENDED: SessionPool Connection

**SessionPool is the PREFERRED method** for ALL production Java applications. It provides connection pooling, thread safety, and optimal resource management.

```java
// PRIMARY RECOMMENDATION: SessionPool for production
SessionPool sessionPool = new SessionPool.Builder()
    .host("127.0.0.1")
    .port(6667)
    .user("root")
    .password("root")
    .maxSize(10)  // Connection pool size
    .build();

// Always use try-with-resources for proper cleanup
try (SessionDataSet dataSet = sessionPool.executeQueryStatement("SELECT * FROM root.factory.**")) {
    // ALWAYS use iterator for memory efficiency
    DataIterator iterator = dataSet.iterator();
    while (iterator.next()) {
        // Process data efficiently
        System.out.println("Time: " + iterator.getLong(1) + ", Value: " + iterator.getFloat(2));
    }
}
```

### Alternative: Basic Session Connection

**⚠️ Use SessionPool instead** - Single Session is only for simple testing or single-threaded applications.

```java
// ALTERNATIVE: Single session (SessionPool is preferred)
Session session = new Session.Builder()
    .host("127.0.0.1")
    .port(6667)
    .username("root")
    .password("root")
    .build();
session.open(false);

// Remember to close when done
session.close();
```

### 🔧 JDBC Connection (Alternative for Framework Integration)

JDBC is the **secondary choice** for Java applications, use when integrating with existing JDBC-based frameworks:

```java
// JDBC Connection - for framework integration
String url = "jdbc:iotdb://127.0.0.1:6667/";
String username = "root";
String password = "root";

try (Connection connection = DriverManager.getConnection(url, username, password)) {
    // Use JDBC operations here
} // Auto-close connection
```

**📋 JDBC Examples:** See [JDBC Reference](references/jdbc_examples.md) for comprehensive JDBC integration patterns, Spring Boot examples, and connection pooling configurations.

**🌟 Framework Integration:**

- **Spring Boot**: See [Spring Boot Integration](references/spring_boot_integration.md) for official Spring Boot starter, auto-configuration, and SessionPool management
- **MyBatis**: See [MyBatis Integration](references/mybatis_integration.md) for SQL mapping, generator configuration, and JDBC-based applications

### Tree Model Operations (SessionPool)

```java
// Create database and timeseries using SessionPool
sessionPool.createDatabase("root.factory");
sessionPool.createTimeseries(
    "root.factory.workshop.temperature",
    TSDataType.FLOAT,
    TSEncoding.RLE,
    CompressionType.SNAPPY
);

// Insert single record
sessionPool.insertRecord(
    "root.factory.workshop",
    System.currentTimeMillis(),
    Arrays.asList("temperature", "humidity"),
    Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT),
    Arrays.asList(25.5f, 60.0f)
);

// ⭐ CRITICAL: Always use iterator for reading data (memory efficient)
try (SessionDataSet dataSet = sessionPool.executeQueryStatement(
        "SELECT temperature FROM root.factory.workshop")) {

    // Iterator pattern - RECOMMENDED for all data reading
    DataIterator iterator = dataSet.iterator();
    while (iterator.next()) {
        System.out.println("Time: " + iterator.getLong(1) +
                         ", Temperature: " + iterator.getFloat(2));
    }
} // Auto-close dataset

// Bulk insertion using Tablet (RECOMMENDED for high throughput)
List<String> measurements = Arrays.asList("temperature", "humidity");
List<TSDataType> dataTypes = Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT);
List<TSEncoding> encodings = Arrays.asList(TSEncoding.RLE, TSEncoding.RLE);
List<CompressionType> compressors = Arrays.asList(CompressionType.SNAPPY, CompressionType.SNAPPY);

Tablet tablet = new Tablet("root.factory.workshop", measurements, dataTypes, 1000);
// Add data to tablet rows...
sessionPool.insertTablet(tablet);
```

### JDBC Operations (Alternative Approach)

```java
try (Connection connection = DriverManager.getConnection(
        "jdbc:iotdb://127.0.0.1:6667/", "root", "root")) {

    // Create database and timeseries
    try (Statement stmt = connection.createStatement()) {
        stmt.execute("CREATE DATABASE root.factory");
        stmt.execute("CREATE TIMESERIES root.factory.workshop.temperature " +
                    "WITH DATATYPE=FLOAT, ENCODING=RLE");

        // Insert data
        stmt.execute("INSERT INTO root.factory.workshop(timestamp, temperature) " +
                    "VALUES(" + System.currentTimeMillis() + ", 25.5)");
    }

    // ⭐ CRITICAL: Always use iterator pattern with ResultSet
    try (Statement stmt = connection.createStatement();
         ResultSet rs = stmt.executeQuery("SELECT * FROM root.factory.workshop")) {

        // Iterator-based ResultSet processing for memory efficiency
        while (rs.next()) {
            System.out.println("Time: " + rs.getLong("Time") +
                             ", Temperature: " + rs.getFloat("root.factory.workshop.temperature"));
        }
    }
}
```

**📚 Complete JDBC Guide:** See [JDBC Examples](references/jdbc_examples.md) for:

- Connection pooling with HikariCP
- Spring Boot integration
- Batch operations and performance optimization
- Error handling patterns
- PreparedStatement examples

### Table Model Operations (SessionPool)

```java
// Table Model Connection - Use ITableSession for table operations
ITableSession tableSession = new TableSessionBuilder()
    .nodeUrls(Collections.singletonList("127.0.0.1:6667"))
    .username("root")
    .password("root")
    .database("factory")  // Optional: set default database
    .build();

// Create database and table with proper schema design
tableSession.executeNonQueryStatement("CREATE DATABASE factory");
tableSession.executeNonQueryStatement("USE factory");

tableSession.executeNonQueryStatement(
    "CREATE TABLE sensors(" +
    "region_id STRING TAG, " +           // TAG: Low cardinality, indexed
    "workshop_id STRING TAG, " +         // TAG: Used for filtering
    "device_type STRING ATTRIBUTE, " +   // ATTRIBUTE: Metadata
    "temperature FLOAT FIELD, " +        // FIELD: Actual measurements
    "humidity DOUBLE FIELD" +            // FIELD: Actual measurements
    ") WITH (TTL=3600000)"               // TTL: Data retention policy
);

// Insert using tablet (RECOMMENDED for bulk data)
List<String> columnNames = Arrays.asList("region_id", "workshop_id", "device_type", "temperature", "humidity");
List<TSDataType> dataTypes = Arrays.asList(TSDataType.STRING, TSDataType.STRING, TSDataType.STRING, TSDataType.FLOAT, TSDataType.DOUBLE);
List<ColumnCategory> columnTypes = Arrays.asList(ColumnCategory.TAG, ColumnCategory.TAG, ColumnCategory.ATTRIBUTE, ColumnCategory.FIELD, ColumnCategory.FIELD);

Tablet tablet = new Tablet("sensors", columnNames, dataTypes, columnTypes, 100);
// Add data to tablet rows...
tableSession.insert(tablet);

// ⭐ CRITICAL: Always use iterator for querying (memory efficient)
try (SessionDataSet dataSet = tableSession.executeQueryStatement(
        "SELECT * FROM sensors WHERE region_id = 'region_1'")) {

    DataIterator iterator = dataSet.iterator();
    while (iterator.next()) {
        System.out.println("Region: " + iterator.getString("region_id") +
                         ", Temperature: " + iterator.getFloat("temperature"));
    }
} // Auto-close dataset
```

**📋 Table Model Syntax:** See [Data Models Guide](references/data_models.md) for complete SQL syntax, column types, and query patterns.

## Python Connection

### Installation and Basic Setup

```bash
pip install apache-iotdb
```

```python
from iotdb.Session import Session

# Tree Model Connection
session = Session("127.0.0.1", "6667", "root", "root")
session.open(False)

# Set timezone (optional)
session.set_time_zone("Asia/Shanghai")
```

### Tree Model Operations (Python with Iterator)

```python
# Create database and timeseries
session.set_storage_group("root.factory")
session.create_time_series(
    "root.factory.workshop.temperature",
    TSDataType.FLOAT,
    TSEncoding.RLE,
    Compressor.SNAPPY
)

# Insert single record
session.insert_record(
    "root.factory.workshop",
    1635232143960,
    ["temperature", "humidity"],
    [TSDataType.FLOAT, TSDataType.FLOAT],
    [25.5, 60.0]
)

# ⭐ CRITICAL: Always use iterator for data reading (memory efficient)
result = session.execute_query_statement("SELECT * FROM root.factory.workshop")

# Iterator pattern - RECOMMENDED for all data reading
while result.has_next():
    record = result.next()
    print(f"Time: {record.get_timestamp()}, Values: {record.get_fields()}")

# Close result to free memory
result.close()

# Bulk insertion using tablet (RECOMMENDED for high throughput)
measurements = ["temperature", "humidity"]
data_types = [TSDataType.FLOAT, TSDataType.FLOAT]
values = [
    [25.5, 26.0, 24.8],  # Temperature values
    [60.0, 61.5, 58.2]   # Humidity values
]
timestamps = [1635232143960, 1635232153960, 1635232163960]

tablet = Tablet("root.factory.workshop", measurements, data_types, values, timestamps)
session.insert_tablet(tablet)
```

### Pandas Integration with Iterator

```python
import pandas as pd

# Query and convert to pandas DataFrame (iterator-based)
result = session.execute_query_statement("SELECT * FROM root.factory.workshop")

# Option 1: Direct conversion (handles iterator internally - RECOMMENDED for small datasets)
df = result.todf()
print(df)

# Option 2: Manual iteration for large datasets (RECOMMENDED for memory control)
data_rows = []
while result.has_next():
    record = result.next()
    data_rows.append([record.get_timestamp()] + [field.get_value() for field in record.get_fields()])

# Convert to DataFrame manually for better memory control
df = pd.DataFrame(data_rows, columns=['Time'] + result.get_column_names()[1:])
print(df.head())

# Option 3: Streaming processing for very large datasets
def process_large_dataset(query_sql):
    result = session.execute_query_statement(query_sql)

    # Process in chunks to avoid memory issues
    chunk_size = 1000
    chunk_data = []

    while result.has_next():
        record = result.next()
        chunk_data.append([record.get_timestamp()] + [field.get_value() for field in record.get_fields()])

        if len(chunk_data) >= chunk_size:
            # Process chunk (e.g., save to file, analyze, etc.)
            chunk_df = pd.DataFrame(chunk_data, columns=['Time'] + result.get_column_names()[1:])
            # Do something with chunk_df
            chunk_data = []  # Reset for next chunk

    # Process remaining data
    if chunk_data:
        chunk_df = pd.DataFrame(chunk_data, columns=['Time'] + result.get_column_names()[1:])
        # Process final chunk

    result.close()  # Important: close result

# Example usage
process_large_dataset("SELECT * FROM root.factory.**")
```

### Table Model (Python)

Note: Table model support in Python client may require newer versions. Check the current documentation for availability.

## C++ Connection

### Prerequisites and Build

```bash
# Install dependencies (Ubuntu/Debian)
sudo apt-get install libthrift-dev libboost-dev

# Compile IoTDB C++ client
mvn clean package -P with-cpp -pl iotdb-client/client-cpp -am -DskipTests
```

### Basic Usage

```cpp
#include "include/Session.h"
#include <memory>
#include <iostream>

int main() {
    // Create session
    std::shared_ptr<Session> session(
        new Session("127.0.0.1", 6667, "root", "root")
    );
    session->open(false);

    // Create database
    session->setStorageGroup("root.factory");

    // Create timeseries
    if (!session->checkTimeseriesExists("root.factory.workshop.temperature")) {
        session->createTimeseries(
            "root.factory.workshop.temperature",
            TSDataType::FLOAT,
            TSEncoding::RLE,
            CompressionType::SNAPPY
        );
    }

    // Insert data
    std::vector<std::string> measurements = {"temperature", "humidity"};
    std::vector<TSDataType::TSDataType> dataTypes = {TSDataType::FLOAT, TSDataType::FLOAT};
    std::vector<char*> values = {"25.5", "60.0"};

    session->insertRecord(
        "root.factory.workshop",
        1635232143960,
        measurements,
        dataTypes,
        values
    );

    session->close();
    return 0;
}
```

### Compilation

```bash
clang++ -O2 your-code.cpp -liotdb_session \
    -L/path/to/iotdb-client/lib \
    -Wl,-rpath /path/to/iotdb-client/lib \
    -std=c++11
```

## REST API Connection

### Basic Authentication

All REST endpoints (except `/ping`) require Basic Authentication:

```bash
# Generate base64 encoding for username:password
echo -n "root:root" | base64
# Output: cm9vdDpyb290
```

### REST Endpoints

**Health Check**

```bash
curl http://127.0.0.1:18080/ping
```

**Execute Query**

```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{"sql": "SELECT * FROM root.factory.workshop"}' \
     http://127.0.0.1:18080/rest/v1/query
```

**Execute Non-Query (DDL/DML)**

```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{"sql": "CREATE DATABASE root.factory"}' \
     http://127.0.0.1:18080/rest/v1/nonQuery
```

**Insert Tablet Data**

```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{
       "timestamps": [1635232143960, 1635232153960],
       "measurements": ["temperature", "humidity"],
       "dataTypes": ["FLOAT", "FLOAT"],
       "values": [[25.5, 26.0], [60.0, 61.5]],
       "isAligned": false,
       "deviceId": "root.factory.workshop"
     }' \
     http://127.0.0.1:18080/rest/v1/insertTablet
```

## Connection Configuration

### Common Connection Parameters

- **Host**: IoTDB server address (default: 127.0.0.1)
- **Port**: IoTDB RPC port (default: 6667)
- **REST Port**: REST API port (default: 18080)
- **Username**: Authentication username (default: root)
- **Password**: Authentication password (default: root)
- **Fetch Size**: Number of records to fetch per batch (default: 10000)
- **Timeout**: Connection and query timeout settings

### Session Pool (Java)

For high-concurrency applications:

```java
SessionPool sessionPool = new SessionPool.Builder()
    .host("127.0.0.1")
    .port(6667)
    .user("root")
    .password("root")
    .maxSize(10)  // Maximum concurrent sessions
    .build();
```

### SSL/TLS Configuration

For secure connections, configure SSL settings:

```java
// Java SSL configuration
session.setEnableSSL(true);
session.setKeyStore("/path/to/keystore");
session.setKeyStorePassword("password");
```

## Best Practices

1. **Connection Management (CRITICAL)**
   - **🚀 Always prefer SessionPool** over individual sessions for production applications
   - Always close sessions/connections after use (use try-with-resources in Java)
   - Configure appropriate pool sizes based on application concurrency needs
   - Use connection pooling for JDBC applications (HikariCP recommended)

2. **Data Reading (MEMORY EFFICIENCY)**
   - **⭐ ALWAYS use iterators** for reading query results - never load entire datasets into memory
   - Use `DataIterator.next()` pattern for SessionPool operations
   - Use `ResultSet.next()` pattern for JDBC operations
   - Use `result.has_next()` pattern for Python operations
   - Process data in chunks for very large datasets

3. **Data Insertion (PERFORMANCE)**
   - **Use tablets for bulk data insertion** - significantly better performance than individual records
   - Batch multiple records together for better throughput
   - Consider aligned timeseries for related measurements in tree model
   - Use prepared statements for JDBC batch operations

4. **Query Optimization**
   - Use time range filters to limit data scope (`WHERE time >= ? AND time <= ?`)
   - Create appropriate indexes for frequently queried paths/tags
   - Consider using aggregation functions for large datasets
   - Filter by TAG columns first in table model queries

5. **Model Selection**
   - Choose **Tree Model** for traditional IoT timeseries data, high ingestion rates
   - Choose **Table Model** for complex analytical queries, business intelligence
   - Consider data access patterns and query complexity when selecting model
   - Use TAG columns wisely in table model (low cardinality, frequently filtered)

## Resources

### References

- **[Java Examples (SessionPool Priority)](references/java_examples_priority.md) - UPDATED: SessionPool-first approach with iterator patterns**
- [Java Examples (Original)](references/java_examples.md) - SessionPool, Session, and iterator examples
- [Python Examples](references/python_examples.md) - Python with iterator patterns and pandas integration
- [C++ Examples](references/cpp_examples.md) - C++ implementation examples
- [JDBC Reference](references/jdbc_examples.md) - Complete JDBC integration guide with Spring Boot, connection pooling, and performance optimization
- **[Spring Boot Integration](references/spring_boot_integration.md) - Official Spring Boot starter examples with SessionPool and auto-configuration**
- **[MyBatis Integration](references/mybatis_integration.md) - MyBatis generator and configuration examples for JDBC-based applications**
- [REST API Reference](references/rest_api.md) - Complete REST API documentation
- **[Data Models Guide](references/data_models.md) - COMPREHENSIVE syntax guide for both Tree and Table models with examples**

### Scripts

- [Connection Validator](scripts/validate_connection.py) - Test IoTDB connectivity
- [Data Model Converter](scripts/convert_models.py) - Convert between tree and table models
- [Performance Test](scripts/performance_test.py) - Benchmark connection performance

### Assets

- [Connection Templates](assets/connection_templates/) - Ready-to-use connection code templates
- [Configuration Files](assets/configs/) - Sample configuration files for different environments
