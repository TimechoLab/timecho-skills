# C++ Examples for IoTDB Connection

- **V2.0.11+**: use `SessionPool` (tree and table model). One pool per process, shared across threads.
- **Before V2.0.11**: there is no C++ pool. Create one `Session` (tree) or `TableSession` (table) per worker
  thread, open it once and reuse it; a `Session` must not be used by two threads at the same time.

## Getting the Client

Follow the `iotdb-client/client-cpp` README of the server version you connect to:

- V2.0.11+: unpack the prebuilt SDK `iotdb-session-cpp-<version>-<classifier>.zip` (`include/` and `lib/`),
  or build it with CMake as described in that README.
- Earlier versions are built with Maven, for example
  `mvn package -P with-cpp -pl iotdb-client/client-cpp -am -DskipTests`.

Compile against the SDK (paths depend on where it is unpacked):

```bash
g++ -std=c++11 -O2 app.cpp -I/path/to/sdk/include -L/path/to/sdk/lib -liotdb_session \
    -Wl,-rpath,/path/to/sdk/lib -o app
```

## V2.0.11+: SessionPool

### Tree Model

```cpp
#include "SessionPool.h"

#include <iostream>
#include <utility>
#include <vector>

int main() {
    // host, port, user, password, max pool size
    SessionPool pool("127.0.0.1", 6667, "root", "root", 10);

    try {
        pool.executeNonQueryStatement("CREATE DATABASE root.factory");
    } catch (IoTDBException& e) {
        std::cout << e.what() << std::endl;  // already exists
    }

    // Batch write one device with a Tablet
    std::vector<std::pair<std::string, TSDataType::TSDataType>> schemas = {
        {"temperature", TSDataType::FLOAT},
        {"humidity", TSDataType::FLOAT},
    };
    Tablet tablet("root.factory.line1.device7", schemas, 1000);
    for (int64_t i = 0; i < 5000; i++) {
        size_t row = tablet.rowSize++;
        tablet.timestamps[row] = 1700000000000 + i * 1000;
        tablet.addValue(0, row, 20.0f + (i % 100) / 10.0f);
        tablet.addValue(1, row, 60.0f);
        if (tablet.rowSize == tablet.maxRowNumber) {
            pool.insertTablet(tablet);
            tablet.reset();
        }
    }
    if (tablet.rowSize != 0) {
        pool.insertTablet(tablet);
        tablet.reset();
    }

    // Query: the returned wrapper keeps its session leased until it is destroyed
    {
        auto dataSet = pool.executeQueryStatement(
            "SELECT temperature FROM root.factory.line1.device7 LIMIT 10");
        while (dataSet->hasNext()) {
            auto row = dataSet->next();  // keep the shared_ptr in a local variable
            std::cout << row->toString();
        }
    }

    pool.close();
    return 0;
}
```

### Table Model

```cpp
#include "SessionPool.h"

#include <iostream>
#include <utility>
#include <vector>

int main() {
    auto pool = SessionPoolBuilder()
                    .host("127.0.0.1")
                    ->rpcPort(6667)
                    ->username("root")
                    ->password("root")
                    ->sqlDialect("table")
                    ->database("factory")
                    ->maxSize(10)
                    ->build();

    std::vector<std::pair<std::string, TSDataType::TSDataType>> schema = {
        {"region", TSDataType::STRING},   {"plant_id", TSDataType::STRING},
        {"device_id", TSDataType::STRING}, {"model", TSDataType::STRING},
        {"temperature", TSDataType::FLOAT}, {"humidity", TSDataType::DOUBLE},
    };
    std::vector<ColumnCategory> categories = {
        ColumnCategory::TAG, ColumnCategory::TAG, ColumnCategory::TAG,
        ColumnCategory::ATTRIBUTE, ColumnCategory::FIELD, ColumnCategory::FIELD,
    };
    Tablet tablet("sensors", schema, categories, 1000);
    size_t row = tablet.rowSize++;
    tablet.timestamps[row] = 1700000000000;
    tablet.addValue(0, row, std::string("north"));
    tablet.addValue(1, row, std::string("p1"));
    tablet.addValue(2, row, std::string("d7"));
    tablet.addValue(3, row, std::string("A"));
    tablet.addValue(4, row, 25.5f);
    tablet.addValue(5, row, 60.0);

    // Table-model tablets are written with insertRelationalTablet on a borrowed session
    pool->execute([&](Session& s) { s.insertRelationalTablet(tablet); });

    {
        auto dataSet = pool->executeQueryStatement(
            "SELECT time, device_id, temperature FROM sensors WHERE device_id = 'd7'");
        while (dataSet->hasNext()) {
            auto r = dataSet->next();
            std::cout << r->toString();
        }
    }

    pool->close();
    return 0;
}
```

Create the database and table beforehand (see [Data Models Guide](data_models.md)).

## Before V2.0.11: One Session per Thread

### Tree Model

```cpp
#include "Session.h"

#include <memory>

// Create once per worker thread and reuse it
std::shared_ptr<Session> openTreeSession() {
    auto session = std::make_shared<Session>("127.0.0.1", 6667, "root", "root");
    session->open(false);
    return session;
}

void writeDevice(Session& session) {
    std::vector<std::pair<std::string, TSDataType::TSDataType>> schemas = {
        {"temperature", TSDataType::FLOAT},
        {"humidity", TSDataType::FLOAT},
    };
    Tablet tablet("root.factory.line1.device7", schemas, 1000);
    for (int64_t i = 0; i < 1000; i++) {
        size_t row = tablet.rowSize++;
        tablet.timestamps[row] = 1700000000000 + i * 1000;
        tablet.addValue(0, row, 20.0f);
        tablet.addValue(1, row, 60.0f);
    }
    session.insertTablet(tablet);
    tablet.reset();
}
```

### Table Model

```cpp
#include "TableSession.h"
#include "TableSessionBuilder.h"

std::shared_ptr<TableSession> openTableSession() {
    // build() returns an opened session
    return std::shared_ptr<TableSession>((new TableSessionBuilder())
                                             ->host("127.0.0.1")
                                             ->rpcPort(6667)
                                             ->username("root")
                                             ->password("root")
                                             ->database("factory")
                                             ->build());
}
```

Write table-model tablets with `session->insert(tablet)` and read with
`session->executeQueryStatement(sql)`, as in the table example above.

## Notes

- Tablets are much faster than `insertRecord`; batch hundreds to thousands of rows.
- Store `dataSet->next()` in a local variable before using it; the row is released with its `shared_ptr`.
- Close sessions and pools on shutdown.
