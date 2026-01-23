# C++ Examples for IoTDB Connection

## Basic C++ Client Setup

### Prerequisites and Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install build-essential cmake
sudo apt-get install libthrift-dev libboost-dev

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install cmake
sudo yum install thrift-devel boost-devel

# macOS (using Homebrew)
brew install cmake thrift boost
```

### Building IoTDB C++ Client

```bash
# Navigate to IoTDB source directory
cd /path/to/iotdb

# Compile C++ client
mvn clean package -P with-cpp -pl iotdb-client/client-cpp -am -DskipTests

# For Windows with Visual Studio 2022
mvn clean package -P with-cpp -pl iotdb-client/client-cpp -am -DskipTests \
    -D"boost.include.dir"="D:\boost_1_75_0" \
    -D"boost.library.dir"="D:\boost_1_75_0\stage\lib"
```

## Complete C++ Client Example

### basic_iotdb_client.cpp

```cpp
#include "include/Session.h"
#include <iostream>
#include <vector>
#include <memory>
#include <string>
#include <chrono>
#include <thread>
#include <random>

class IoTDBCppClient {
private:
    std::shared_ptr<Session> session;
    std::string host;
    int port;
    std::string username;
    std::string password;

public:
    IoTDBCppClient(const std::string& host = "127.0.0.1",
                   int port = 6667,
                   const std::string& username = "root",
                   const std::string& password = "root")
        : host(host), port(port), username(username), password(password) {}

    void connect() {
        try {
            session = std::make_shared<Session>(host, port, username, password);
            session->open(false);
            std::cout << "Connected to IoTDB at " << host << ":" << port << std::endl;
        } catch (const std::exception& e) {
            std::cerr << "Connection failed: " << e.what() << std::endl;
            throw;
        }
    }

    void disconnect() {
        if (session) {
            try {
                session->close();
                std::cout << "Disconnected from IoTDB" << std::endl;
            } catch (const std::exception& e) {
                std::cerr << "Error during disconnect: " << e.what() << std::endl;
            }
        }
    }

    void basicOperationsExample() {
        try {
            std::cout << "=== Basic Operations Example ===" << std::endl;

            // Create storage group (database)
            session->setStorageGroup("root.factory");
            std::cout << "Created storage group: root.factory" << std::endl;

            // Create timeseries
            if (!session->checkTimeseriesExists("root.factory.workshop1.temperature")) {
                session->createTimeseries(
                    "root.factory.workshop1.temperature",
                    TSDataType::FLOAT,
                    TSEncoding::RLE,
                    CompressionType::SNAPPY
                );
                std::cout << "Created timeseries: root.factory.workshop1.temperature" << std::endl;
            }

            if (!session->checkTimeseriesExists("root.factory.workshop1.humidity")) {
                session->createTimeseries(
                    "root.factory.workshop1.humidity",
                    TSDataType::FLOAT,
                    TSEncoding::RLE,
                    CompressionType::SNAPPY
                );
                std::cout << "Created timeseries: root.factory.workshop1.humidity" << std::endl;
            }

            // Insert single record
            std::vector<std::string> measurements = {"temperature", "humidity"};
            std::vector<TSDataType::TSDataType> dataTypes = {TSDataType::FLOAT, TSDataType::FLOAT};
            std::vector<char*> values;

            std::string tempValue = "25.5";
            std::string humidValue = "60.0";
            values.push_back(const_cast<char*>(tempValue.c_str()));
            values.push_back(const_cast<char*>(humidValue.c_str()));

            long long timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()
            ).count();

            session->insertRecord(
                "root.factory.workshop1",
                timestamp,
                measurements,
                dataTypes,
                values
            );

            std::cout << "Inserted single record at timestamp: " << timestamp << std::endl;

        } catch (const std::exception& e) {
            std::cerr << "Error in basic operations: " << e.what() << std::endl;
        }
    }

    void bulkInsertExample() {
        try {
            std::cout << "=== Bulk Insert Example ===" << std::endl;

            std::string deviceId = "root.factory.workshop1";
            std::vector<std::string> measurements = {"temperature", "humidity", "pressure"};
            std::vector<TSDataType::TSDataType> dataTypes = {
                TSDataType::FLOAT,
                TSDataType::FLOAT,
                TSDataType::FLOAT
            };

            // Prepare bulk data
            std::vector<std::string> deviceIds;
            std::vector<long long> timestamps;
            std::vector<std::vector<std::string>> measurementsList;
            std::vector<std::vector<TSDataType::TSDataType>> dataTypesList;
            std::vector<std::vector<char*>> valuesList;

            // Generate random data
            std::random_device rd;
            std::mt19937 gen(rd());
            std::uniform_real_distribution<> tempDist(20.0, 30.0);
            std::uniform_real_distribution<> humidDist(40.0, 80.0);
            std::uniform_real_distribution<> pressureDist(990.0, 1050.0);

            long long baseTime = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()
            ).count();

            for (int i = 0; i < 100; ++i) {
                deviceIds.push_back(deviceId);
                timestamps.push_back(baseTime + i * 1000);
                measurementsList.push_back(measurements);
                dataTypesList.push_back(dataTypes);

                std::vector<char*> values;
                std::vector<std::string> valueStrings(3);

                valueStrings[0] = std::to_string(tempDist(gen));
                valueStrings[1] = std::to_string(humidDist(gen));
                valueStrings[2] = std::to_string(pressureDist(gen));

                for (auto& str : valueStrings) {
                    values.push_back(const_cast<char*>(str.c_str()));
                }

                valuesList.push_back(values);
            }

            // Insert bulk data
            session->insertRecords(
                deviceIds,
                timestamps,
                measurementsList,
                dataTypesList,
                valuesList
            );

            std::cout << "Inserted 100 records using bulk insert" << std::endl;

        } catch (const std::exception& e) {
            std::cerr << "Error in bulk insert: " << e.what() << std::endl;
        }
    }

    void tabletInsertExample() {
        try {
            std::cout << "=== Tablet Insert Example ===" << std::endl;

            std::string deviceId = "root.factory.workshop2";
            std::vector<std::pair<std::string, TSDataType::TSDataType>> schemaList = {
                {"temperature", TSDataType::FLOAT},
                {"humidity", TSDataType::FLOAT},
                {"pressure", TSDataType::FLOAT}
            };

            int maxRowNumber = 1024;
            int rowSize = 0;

            // Create tablet
            Tablet tablet(deviceId, schemaList, maxRowNumber);

            // Fill tablet with data
            std::random_device rd;
            std::mt19937 gen(rd());
            std::uniform_real_distribution<> tempDist(20.0, 30.0);
            std::uniform_real_distribution<> humidDist(40.0, 80.0);
            std::uniform_real_distribution<> pressureDist(990.0, 1050.0);

            long long baseTime = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()
            ).count();

            for (int i = 0; i < 500; ++i) {
                tablet.timestamps.push_back(baseTime + i * 1000);
                tablet.values[0].push_back(std::to_string(tempDist(gen)));
                tablet.values[1].push_back(std::to_string(humidDist(gen)));
                tablet.values[2].push_back(std::to_string(pressureDist(gen)));
                rowSize++;

                if (rowSize == maxRowNumber) {
                    tablet.rowSize = rowSize;
                    session->insertTablet(tablet);

                    // Reset tablet
                    tablet.timestamps.clear();
                    for (auto& valueVector : tablet.values) {
                        valueVector.clear();
                    }
                    rowSize = 0;
                }
            }

            // Insert remaining data
            if (rowSize > 0) {
                tablet.rowSize = rowSize;
                session->insertTablet(tablet);
            }

            std::cout << "Inserted 500 records using tablet" << std::endl;

        } catch (const std::exception& e) {
            std::cerr << "Error in tablet insert: " << e.what() << std::endl;
        }
    }

    void queryExample() {
        try {
            std::cout << "=== Query Example ===" << std::endl;

            // Execute query
            std::unique_ptr<SessionDataSet> dataSet = session->executeQueryStatement(
                "SELECT temperature, humidity FROM root.factory.workshop1 LIMIT 10"
            );

            std::cout << "Query results:" << std::endl;
            std::cout << "Column names: ";
            for (const auto& name : dataSet->getColumnNames()) {
                std::cout << name << " ";
            }
            std::cout << std::endl;

            // Print results
            int count = 0;
            while (dataSet->hasNext() && count < 10) {
                RowRecord* record = dataSet->next();
                std::cout << "Timestamp: " << record->getTimestamp();

                const std::vector<Field*>& fields = record->getFields();
                for (size_t i = 0; i < fields.size(); ++i) {
                    if (fields[i]->getDataType() == TSDataType::FLOAT) {
                        std::cout << ", " << dataSet->getColumnNames()[i + 1]
                                  << ": " << fields[i]->getFloatV();
                    }
                }
                std::cout << std::endl;
                count++;
            }

            dataSet->closeOperationHandle();

        } catch (const std::exception& e) {
            std::cerr << "Error in query: " << e.what() << std::endl;
        }
    }

    void aggregationQueryExample() {
        try {
            std::cout << "=== Aggregation Query Example ===" << std::endl;

            std::unique_ptr<SessionDataSet> dataSet = session->executeQueryStatement(
                "SELECT AVG(temperature), MAX(temperature), MIN(temperature) "
                "FROM root.factory.workshop1 "
                "WHERE time >= now() - 1h"
            );

            std::cout << "Aggregation results:" << std::endl;
            while (dataSet->hasNext()) {
                RowRecord* record = dataSet->next();
                std::cout << "Timestamp: " << record->getTimestamp();

                const std::vector<Field*>& fields = record->getFields();
                for (size_t i = 0; i < fields.size(); ++i) {
                    if (fields[i]->getDataType() == TSDataType::DOUBLE) {
                        std::cout << ", Column " << i << ": " << fields[i]->getDoubleV();
                    }
                }
                std::cout << std::endl;
            }

            dataSet->closeOperationHandle();

        } catch (const std::exception& e) {
            std::cerr << "Error in aggregation query: " << e.what() << std::endl;
        }
    }

    void timeseriesManagementExample() {
        try {
            std::cout << "=== Timeseries Management Example ===" << std::endl;

            // Check if timeseries exists
            bool exists = session->checkTimeseriesExists("root.factory.workshop1.temperature");
            std::cout << "Temperature timeseries exists: " << (exists ? "Yes" : "No") << std::endl;

            // Create timeseries with tags and attributes
            std::map<std::string, std::string> tags;
            tags["location"] = "workshop1";
            tags["type"] = "sensor";

            std::map<std::string, std::string> attributes;
            attributes["manufacturer"] = "ACME";
            attributes["model"] = "T1000";

            if (!session->checkTimeseriesExists("root.factory.workshop1.tagged_sensor")) {
                session->createTimeseries(
                    "root.factory.workshop1.tagged_sensor",
                    TSDataType::FLOAT,
                    TSEncoding::RLE,
                    CompressionType::SNAPPY,
                    nullptr,  // props
                    &tags,
                    &attributes,
                    "temperature_sensor"  // alias
                );
                std::cout << "Created tagged timeseries" << std::endl;
            }

            // Delete timeseries (uncomment to test)
            // std::vector<std::string> paths = {"root.factory.workshop1.tagged_sensor"};
            // session->deleteTimeseries(paths);
            // std::cout << "Deleted tagged timeseries" << std::endl;

        } catch (const std::exception& e) {
            std::cerr << "Error in timeseries management: " << e.what() << std::endl;
        }
    }

    void dataManagementExample() {
        try {
            std::cout << "=== Data Management Example ===" << std::endl;

            // Delete data before a certain timestamp
            long long cutoffTime = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()
            ).count() - 3600000;  // 1 hour ago

            std::vector<std::string> paths = {"root.factory.workshop1.temperature"};
            session->deleteData(paths, cutoffTime);

            std::cout << "Deleted old temperature data" << std::endl;

        } catch (const std::exception& e) {
            std::cerr << "Error in data management: " << e.what() << std::endl;
        }
    }
};

// Error handling and retry mechanism
class RobustIoTDBClient : public IoTDBCppClient {
private:
    int maxRetries;
    int retryDelayMs;

public:
    RobustIoTDBClient(const std::string& host = "127.0.0.1",
                      int port = 6667,
                      const std::string& username = "root",
                      const std::string& password = "root",
                      int maxRetries = 3,
                      int retryDelayMs = 1000)
        : IoTDBCppClient(host, port, username, password),
          maxRetries(maxRetries), retryDelayMs(retryDelayMs) {}

    template<typename Func>
    void executeWithRetry(Func&& func, const std::string& operationName) {
        int attempts = 0;
        while (attempts < maxRetries) {
            try {
                func();
                return;  // Success
            } catch (const std::exception& e) {
                attempts++;
                if (attempts >= maxRetries) {
                    std::cerr << "Operation " << operationName
                              << " failed after " << maxRetries
                              << " attempts: " << e.what() << std::endl;
                    throw;
                }

                std::cout << "Retry " << attempts << "/" << maxRetries
                          << " for " << operationName
                          << " in " << retryDelayMs << "ms: " << e.what() << std::endl;
                std::this_thread::sleep_for(std::chrono::milliseconds(retryDelayMs));
            }
        }
    }

    void connectWithRetry() {
        executeWithRetry([this]() { this->connect(); }, "connect");
    }
};

int main() {
    try {
        IoTDBCppClient client;

        // Connect to IoTDB
        client.connect();

        // Run examples
        client.basicOperationsExample();
        client.bulkInsertExample();
        client.tabletInsertExample();
        client.queryExample();
        client.aggregationQueryExample();
        client.timeseriesManagementExample();
        client.dataManagementExample();

        // Disconnect
        client.disconnect();

        std::cout << "\n=== Robust Client Example ===" << std::endl;

        // Test robust client
        RobustIoTDBClient robustClient;
        robustClient.connectWithRetry();
        robustClient.disconnect();

    } catch (const std::exception& e) {
        std::cerr << "Application error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
```

## Advanced C++ Features

### session_pool.cpp

```cpp
#include "include/Session.h"
#include <queue>
#include <mutex>
#include <condition_variable>
#include <memory>
#include <thread>
#include <vector>

class SessionPool {
private:
    std::queue<std::shared_ptr<Session>> pool;
    std::mutex poolMutex;
    std::condition_variable condition;
    std::string host;
    int port;
    std::string username;
    std::string password;
    size_t poolSize;
    size_t currentSize;

public:
    SessionPool(const std::string& host, int port,
                const std::string& username, const std::string& password,
                size_t poolSize = 10)
        : host(host), port(port), username(username), password(password),
          poolSize(poolSize), currentSize(0) {

        // Initialize pool
        for (size_t i = 0; i < poolSize; ++i) {
            auto session = std::make_shared<Session>(host, port, username, password);
            session->open(false);
            pool.push(session);
            currentSize++;
        }
    }

    std::shared_ptr<Session> getSession() {
        std::unique_lock<std::mutex> lock(poolMutex);
        condition.wait(lock, [this] { return !pool.empty(); });

        auto session = pool.front();
        pool.pop();
        return session;
    }

    void returnSession(std::shared_ptr<Session> session) {
        std::lock_guard<std::mutex> lock(poolMutex);
        pool.push(session);
        condition.notify_one();
    }

    ~SessionPool() {
        std::lock_guard<std::mutex> lock(poolMutex);
        while (!pool.empty()) {
            auto session = pool.front();
            pool.pop();
            try {
                session->close();
            } catch (const std::exception& e) {
                std::cerr << "Error closing session: " << e.what() << std::endl;
            }
        }
    }
};

void workerThread(SessionPool& pool, int threadId) {
    auto session = pool.getSession();

    try {
        // Simulate work
        std::vector<std::string> measurements = {"value"};
        std::vector<TSDataType::TSDataType> dataTypes = {TSDataType::FLOAT};
        std::vector<char*> values;

        std::string valueStr = std::to_string(static_cast<float>(threadId));
        values.push_back(const_cast<char*>(valueStr.c_str()));

        long long timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()
        ).count();

        session->insertRecord(
            "root.factory.thread_" + std::to_string(threadId),
            timestamp,
            measurements,
            dataTypes,
            values
        );

        std::cout << "Thread " << threadId << " completed work" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "Thread " << threadId << " error: " << e.what() << std::endl;
    }

    pool.returnSession(session);
}

void sessionPoolExample() {
    SessionPool pool("127.0.0.1", 6667, "root", "root", 5);

    std::vector<std::thread> threads;
    for (int i = 0; i < 20; ++i) {
        threads.emplace_back(workerThread, std::ref(pool), i);
    }

    for (auto& thread : threads) {
        thread.join();
    }

    std::cout << "Session pool example completed" << std::endl;
}
```

## Compilation Instructions

### CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.10)
project(IoTDBCppClient)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(PkgConfig REQUIRED)
find_package(Boost REQUIRED COMPONENTS system filesystem thread)
find_package(Thrift REQUIRED)

# Include directories
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
include_directories(${Boost_INCLUDE_DIRS})
include_directories(${THRIFT_INCLUDE_DIR})

# Source files
set(SOURCES
    basic_iotdb_client.cpp
)

# Create executable
add_executable(iotdb_client ${SOURCES})

# Link libraries
target_link_libraries(iotdb_client
    iotdb_session
    ${Boost_LIBRARIES}
    ${THRIFT_LIBRARIES}
    pthread
)

# Add library path
link_directories(/path/to/iotdb-client/lib)
```

### Build Script

```bash
#!/bin/bash
# build_cpp_client.sh

set -e

echo "Building IoTDB C++ Client Example..."

# Set paths (modify according to your setup)
IOTDB_CLIENT_PATH="/path/to/iotdb/iotdb-client/client-cpp/target/client-cpp-*-cpp-*"
BOOST_ROOT="/usr/local"

# Create build directory
mkdir -p build
cd build

# Configure CMake
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DBOOST_ROOT=${BOOST_ROOT} \
    -DIoTDB_CLIENT_PATH=${IOTDB_CLIENT_PATH}

# Build
make -j$(nproc)

echo "Build completed successfully!"
echo "Run with: ./iotdb_client"
```

### Manual Compilation

```bash
# Compile manually (adjust paths as needed)
g++ -std=c++11 -O2 \
    basic_iotdb_client.cpp \
    -I/path/to/iotdb-client/include \
    -L/path/to/iotdb-client/lib \
    -liotdb_session \
    -lboost_system \
    -lboost_filesystem \
    -lboost_thread \
    -lthrift \
    -pthread \
    -Wl,-rpath,/path/to/iotdb-client/lib \
    -o iotdb_client
```

## Cross-Platform Considerations

### Windows (Visual Studio)

```cpp
// For Windows, include Windows-specific headers if needed
#ifdef _WIN32
#include <windows.h>
#define SLEEP_MS(ms) Sleep(ms)
#else
#include <unistd.h>
#define SLEEP_MS(ms) usleep((ms) * 1000)
#endif

// Use appropriate time functions
#ifdef _WIN32
#include <chrono>
using namespace std::chrono;
#else
#include <sys/time.h>
#endif
```

### Linux Deployment

```dockerfile
# Dockerfile for C++ client deployment
FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libthrift-dev \
    libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /app
WORKDIR /app

RUN mkdir build && cd build && \
    cmake .. && \
    make

CMD ["./build/iotdb_client"]
```

## Performance Optimization Tips

1. **Use Tablets for Bulk Operations**: Tablets provide better performance than individual record insertions.

2. **Connection Pooling**: Use session pools for multi-threaded applications.

3. **Batch Operations**: Group multiple operations together to reduce network overhead.

4. **Compression**: Enable compression for large data transfers.

5. **Memory Management**: Properly manage memory allocation and deallocation.

6. **Error Handling**: Implement robust error handling and retry mechanisms.