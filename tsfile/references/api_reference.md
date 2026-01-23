# TsFile API Reference

## Overview

TsFile is a columnar storage file format designed for time series data, offering efficient compression, high throughput read/write operations, and compatibility with various frameworks like Spark and Flink.

## Core Concepts

### Basic Data Structure
- **Device**: A source that generates time series data (e.g., sensors, IoT devices)
- **Measurement**: A specific metric or attribute of a device (e.g., temperature, voltage)
- **Time Series**: A sequence of data points for a specific device-measurement combination
- **Timestamp**: The time when a data point was recorded
- **Value**: The actual measurement value at a given timestamp

### Data Types
- **INT32**: 32-bit integer
- **INT64**: 64-bit integer
- **FLOAT**: 32-bit floating point
- **DOUBLE**: 64-bit floating point
- **BOOLEAN**: Boolean true/false
- **TEXT**: String/text data

### Encoding and Compression
Recommended combinations for optimal performance:
- INT32/INT64: TS_2DIFF encoding with LZ4 compression
- FLOAT/DOUBLE: GORILLA encoding with LZ4 compression
- BOOLEAN: RLE encoding with LZ4 compression
- TEXT: DICTIONARY encoding with LZ4 compression

## Java API

### Maven Dependency
```xml
<dependency>
    <groupId>org.apache.tsfile</groupId>
    <artifactId>tsfile</artifactId>
    <version>2.1.0</version>
</dependency>
```

### Writing Data

#### Basic Write Operations
```java
// 1. Create TsFileWriter
File file = new File("test.tsfile");
TsFileWriter tsFileWriter = new TsFileWriter(file);

// 2. Register time series schema
List<IMeasurementSchema> schema = new ArrayList<>();
schema.add(new MeasurementSchema("temperature", TSDataType.FLOAT));
schema.add(new MeasurementSchema("humidity", TSDataType.FLOAT));
tsFileWriter.registerTimeseries(new Path("device1"), schema);

// 3. Write data using TSRecord
TSRecord tsRecord = new TSRecord(System.currentTimeMillis(), "device1");
tsRecord.addTuple(DataPoint.getDataPoint(TSDataType.FLOAT, "temperature", 25.6f));
tsRecord.addTuple(DataPoint.getDataPoint(TSDataType.FLOAT, "humidity", 60.0f));
tsFileWriter.write(tsRecord);

// 4. Close writer
tsFileWriter.close();
```

#### Writing with Tablet (Batch)
```java
// Create tablet for batch writing
Tablet tablet = new Tablet("device1", Arrays.asList(
    new MeasurementSchema("temperature", TSDataType.FLOAT),
    new MeasurementSchema("humidity", TSDataType.FLOAT)
));

// Add batch data
for (int i = 0; i < 100; i++) {
    tablet.addTimestamp(i, System.currentTimeMillis() + i * 1000);
    tablet.addValue("temperature", i, 20.0f + i * 0.1f);
    tablet.addValue("humidity", i, 50.0f + i * 0.5f);
}

tsFileWriter.writeTablet(tablet);
```

### Reading Data

#### Basic Read Operations
```java
// 1. Create TsFileReader
TsFileSequenceReader reader = new TsFileSequenceReader(path);
TsFileReader tsFileReader = new TsFileReader(reader);

// 2. Build query expression
ArrayList<Path> paths = new ArrayList<>();
paths.add(new Path("device1", "temperature"));
paths.add(new Path("device1", "humidity"));

// Time range filter
IExpression timeFilter = BinaryExpression.and(
    new GlobalTimeExpression(TimeFilterApi.gtEq(startTime)),
    new GlobalTimeExpression(TimeFilterApi.ltEq(endTime))
);

QueryExpression queryExpression = QueryExpression.create(paths, timeFilter);

// 3. Execute query
QueryDataSet queryDataSet = tsFileReader.query(queryExpression);
while (queryDataSet.hasNext()) {
    RowRecord record = queryDataSet.next();
    // Process record data
}

// 4. Close reader
tsFileReader.close();
```

## Python API

### Installation
Python version requires C++ TsFile to be built first:
```bash
mvn -P with-cpp,with-python clean verify
# or
python setup.py build_ext --inplace
```

### Writing Data
```python
from tsfile import ColumnSchema, TableSchema, Tablet
from tsfile import TsFileTableWriter, TSDataType, ColumnCategory

# Create schema
columns = [
    ColumnSchema("device_id", TSDataType.STRING, ColumnCategory.TAG),
    ColumnSchema("temperature", TSDataType.FLOAT, ColumnCategory.FIELD),
    ColumnSchema("humidity", TSDataType.FLOAT, ColumnCategory.FIELD)
]
table_schema = TableSchema("sensors", columns=columns)

# Write data
with TsFileTableWriter("data.tsfile", table_schema) as writer:
    tablet = Tablet(
        ["device_id", "temperature", "humidity"],
        [TSDataType.STRING, TSDataType.FLOAT, TSDataType.FLOAT],
        100  # batch size
    )

    for i in range(100):
        tablet.add_timestamp(i, i * 10000)  # timestamp in ms
        tablet.add_value_by_name("device_id", i, "device1")
        tablet.add_value_by_name("temperature", i, 20.0 + i * 0.1)
        tablet.add_value_by_name("humidity", i, 50.0 + i * 0.5)

    writer.write_table(tablet)
```

### Reading Data
```python
from tsfile import TsFileReader

with TsFileReader("data.tsfile") as reader:
    # Get table names
    tables = reader.get_table_names()

    # Read specific table
    df = reader.read_table(tables[0])
    print(df.head())

    # Read with time range
    df_filtered = reader.read_table(tables[0], start_time=0, end_time=500000)
```

## C++ API

### Building
```bash
sudo apt-get install cmake make g++ clang-format libuuid-dev
bash build.sh
# or with Maven
mvn package -P with-cpp clean verify
```

### Writing Data
```cpp
#include <writer/tsfile_table_writer.h>

// Initialize library
storage::libtsfile_init();

// Create write file
storage::WriteFile file;
file.create("test.tsfile", O_WRONLY | O_CREAT | O_TRUNC, 0666);

// Create table schema
auto* schema = new storage::TableSchema("table1", {
    common::ColumnSchema("device_id", common::STRING,
                        common::UNCOMPRESSED, common::PLAIN,
                        common::ColumnCategory::TAG),
    common::ColumnSchema("temperature", common::DOUBLE,
                        common::UNCOMPRESSED, common::PLAIN,
                        common::ColumnCategory::FIELD)
});

// Create writer
storage::TsFileTableWriter writer(&file, schema);

// Create tablet for batch writing
auto tablet = new storage::Tablet(schema, 1000);

// Add data
for (int i = 0; i < 1000; i++) {
    tablet->add_timestamp(i, i * 10000);
    tablet->add_value("device_id", i, "sensor_" + std::to_string(i % 10));
    tablet->add_value("temperature", i, 20.0 + (i % 100) * 0.1);
}

// Write and close
writer.write_tablet(tablet);
writer.close();
```

### Reading Data
```cpp
#include <reader/tsfile_reader.h>

// Initialize and open file
storage::libtsfile_init();
storage::ReadFile file;
file.open("test.tsfile");

// Create reader
storage::TsFileReader reader;
reader.open(&file);

// Get tables
std::vector<std::string> table_names = reader.get_table_names();

// Read table data
storage::QueryDataSet result = reader.read_table(table_names[0]);

// Process results
while (result.has_next()) {
    storage::RowRecord record = result.next();
    // Process record data
}

reader.close();
```

## C API

The C API provides a wrapper around the C++ implementation for easier integration with C projects.

### Writing Data (C)
```c
#include "cwrapper/tsfile_writer_wrapper.h"

// Initialize
libtsfile_init();

// Create schema
void* schema = create_table_schema("table1");
add_column_schema(schema, "device_id", STRING_TYPE, TAG_CATEGORY);
add_column_schema(schema, "temperature", DOUBLE_TYPE, FIELD_CATEGORY);

// Create writer
void* writer = create_tsfile_writer("test.tsfile", schema);

// Create and write tablet
void* tablet = create_tablet(schema, 100);
for (int i = 0; i < 100; i++) {
    add_timestamp(tablet, i, i * 10000);
    add_string_value(tablet, "device_id", i, "sensor1");
    add_double_value(tablet, "temperature", i, 20.0 + i * 0.1);
}

write_tablet(writer, tablet);

// Cleanup
close_writer(writer);
free_tablet(tablet);
free_schema(schema);
```

## Common Patterns

### Time Range Queries
Always use appropriate time filters for efficient querying:
- Use `gtEq` (greater than or equal) and `ltEq` (less than or equal) for range queries
- Combine multiple conditions with `BinaryExpression.and()` or `BinaryExpression.or()`

### Batch Writing
Use tablets for batch operations to improve performance:
- Group related data points together
- Use appropriate batch sizes (typically 100-1000 records)
- Write complete tablets rather than individual records when possible

### Schema Design
- Keep related measurements in the same device for better locality
- Use appropriate data types to minimize storage overhead
- Apply recommended encoding/compression combinations for best performance

## Error Handling

### Java
```java
try {
    // TsFile operations
} catch (WriteProcessException e) {
    // Handle write errors
} catch (IOException e) {
    // Handle I/O errors
} finally {
    if (tsFileWriter != null) {
        tsFileWriter.close();
    }
}
```

### Python
```python
try:
    with TsFileTableWriter("data.tsfile", schema) as writer:
        # Write operations
        pass
except Exception as e:
    print(f"Error: {e}")
```

### C++
```cpp
try {
    // TsFile operations
} catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << std::endl;
}
```
