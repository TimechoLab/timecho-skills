---
name: tsfile
description: Comprehensive toolkit for working with Apache TsFile - a columnar storage format for time series data. Use when working with TsFile files (.tsfile extension), time series data storage, IoT data processing, or when users ask about reading, writing, querying, or analyzing time series data in Java, Python, C++, or C. Supports data conversion, schema design, performance optimization, and cross-language integration.
license: Complete terms in LICENSE.txt
---

# TsFile

Apache TsFile is a columnar storage file format designed specifically for time series data, offering efficient compression, high throughput read/write operations, and compatibility with various big data frameworks.

## Quick Start Guide

Choose your programming language to get started:

### Java

```java
// Add Maven dependency (version 2.1.0)
// See assets/pom.xml for complete setup

// Write data
TsFileWriter writer = new TsFileWriter(new File("data.tsfile"));
writer.registerTimeseries(new Path("device1"), schema);
writer.write(tsRecord);
writer.close();

// Read data
TsFileReader reader = new TsFileReader(new TsFileSequenceReader(path));
QueryDataSet result = reader.query(queryExpression);
```

### Python

```python
# Requires C++ build: mvn -P with-cpp,with-python clean verify

from tsfile import TsFileTableWriter, TsFileReader, TableSchema

# Write data
with TsFileTableWriter("data.tsfile", schema) as writer:
    writer.write_table(tablet)

# Read data
with TsFileReader("data.tsfile") as reader:
    df = reader.read_table(table_name)
```

### C++

```cpp
// Build: bash build.sh or mvn -P with-cpp clean verify

#include <writer/tsfile_table_writer.h>

storage::TsFileTableWriter writer(&file, schema);
writer.write_tablet(tablet);

storage::TsFileReader reader;
auto result = reader.read_table(table_name);
```

## Core Workflows

### 1. Data Writing Workflow

**Single Record Writing** (Java, lower throughput)

1. Create `TsFileWriter` with file path
2. Register time series schema with `registerTimeseries()`
3. Create `TSRecord` objects with timestamps and values
4. Write records using `writer.write(tsRecord)`
5. Close writer to finalize file

**Batch Writing** (All languages, recommended)

1. Define table schema with columns and data types
2. Create writer instance
3. Create tablets/batches with multiple records
4. Write complete tablets for better performance
5. Close writer and handle resources

### 2. Data Reading Workflow

**Basic Reading**

1. Open TsFile with appropriate reader
2. Get available tables/time series
3. Build query expressions (optional filters)
4. Execute query and iterate through results
5. Process data and close reader

**Advanced Querying**

1. Define time range filters (`gtEq`, `ltEq`)
2. Combine multiple conditions with `BinaryExpression`
3. Select specific measurements/columns
4. Apply aggregation or analysis logic

### 3. Schema Design Workflow

**Column Categories**

- **TAG**: Device identifier columns (e.g. region, device_id); together their values form the device ID (a joint primary key). Do not put descriptive metadata such as model or firmware here; in IoTDB that belongs in ATTRIBUTE columns
- **FIELD**: Actual measurements (temperature, pressure, etc.)

**Data Type Selection**

- INT32/INT64: Counters, IDs, discrete values
- FLOAT/DOUBLE: Sensor readings, calculations
- BOOLEAN: Status flags, binary states
- TEXT: Device names, error messages

**Encoding Optimization**

- Use TS_2DIFF for integer time series
- Use GORILLA for floating-point measurements
- Use RLE for boolean or low-cardinality data
- Use DICTIONARY for repetitive text

## Language-Specific Operations

### Java Development

- **Setup**: Use Maven with `org.apache.tsfile:tsfile:2.1.0` dependency
- **Writing**: Prefer `Tablet` API for batch operations over `TSRecord`
- **Reading**: Use `QueryExpression` for complex filtering
- **Error Handling**: Catch `WriteProcessException` and `IOException`
- **Template**: Use `assets/TsFileExample.java` and `assets/pom.xml`

### Python Integration

- **Prerequisites**: Must build C++ version first
- **API Style**: Pandas-like interface with DataFrames
- **Context Managers**: Use `with` statements for automatic resource cleanup
- **Data Types**: Automatic conversion between pandas and TsFile types
- **Tools**: Use `scripts/example.py` for CSV conversion and validation

### C++ Implementation

- **Build Requirements**: cmake, make, g++, libuuid-dev
- **Memory Management**: Manual cleanup of schemas and tablets
- **Performance**: Fastest implementation, suitable for embedded systems
- **API**: Lower-level control over encoding and compression
- **Template**: Use `assets/tsfile_example.cpp`

### C Wrapper

- **Use Case**: Integration with C projects or other language bindings
- **API**: Function-based interface around C++ implementation
- **Memory**: Explicit create/free patterns for all objects
- **Portability**: Cross-platform compatibility layer

## Development Tools

### Build Script

Use `scripts/build_tsfile.sh` for streamlined building:

```bash
# Check prerequisites
./scripts/build_tsfile.sh check

# Build specific language
./scripts/build_tsfile.sh build java
./scripts/build_tsfile.sh build cpp
./scripts/build_tsfile.sh build python
./scripts/build_tsfile.sh build all

# Run tests
./scripts/build_tsfile.sh test all
```

### Python Utilities

Use `scripts/example.py` for common tasks:

```bash
# Convert CSV to TsFile
python scripts/example.py csv2tsfile data.csv output.tsfile

# Inspect TsFile structure
python scripts/example.py inspect data.tsfile

# Validate TsFile format
python scripts/example.py validate data.tsfile
```

## Performance Optimization

### Writing Performance

- Use tablet/batch writing instead of individual records
- Set appropriate tablet sizes (100-1000 records typically optimal)
- Group related measurements in same device for locality
- Choose efficient encoding for your data patterns

### Reading Performance

- Use time range filters to limit data scanned
- Select only needed columns in queries
- Leverage indexes on device and time dimensions
- Consider memory constraints for large result sets

### Storage Efficiency

- Apply recommended encoding/compression combinations
- Use appropriate data types (don't over-specify precision)
- Design schema with proper tag vs field categorization
- Monitor compression ratios and adjust settings

## Common Patterns

### IoT Sensor Data

```java
// Tag columns: device_id, location, sensor_type
// Field columns: temperature, humidity, battery_level
// Time series per device with multiple measurements
```

### Industrial Monitoring

```cpp
// Batch writing for high-frequency data
// Time-based partitioning for historical analysis
// Real-time queries with time range filters
```

### Data Pipeline Integration

```python
# Pandas DataFrame to TsFile conversion
# Apache Spark/Flink compatibility
# ETL workflow integration
```

## Troubleshooting

**Build Issues**

- Java: Verify JDK 1.8+ and Maven 3.6.3+
- C++: Install required system packages (cmake, make, g++, libuuid-dev)
- Python: Ensure C++ version builds successfully first

**Runtime Errors**

- File corruption: Use validation tools to check file integrity
- Memory issues: Reduce tablet batch sizes or use streaming reads
- Performance: Profile encoding choices and query patterns

**Integration Problems**

- Classpath: Ensure TsFile JAR is in application classpath
- Native libraries: Verify shared libraries (.so/.dll) are accessible
- Version compatibility: Match TsFile versions across language bindings

## Resources

### Reference Documentation

- **API Reference**: Complete documentation for all supported languages in `references/api_reference.md`

### Code Templates

- **Java**: `assets/TsFileExample.java` and `assets/pom.xml`
- **C++**: `assets/tsfile_example.cpp`
- **Python**: `assets/tsfile_example.py`

### Utility Scripts

- **Build Automation**: `scripts/build_tsfile.sh` for cross-platform builds
- **Python Tools**: `scripts/example.py` for data conversion and validation
