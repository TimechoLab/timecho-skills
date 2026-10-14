# Python Examples for IoTDB Connection

Application code uses a pool: `SessionPool` for the tree model and `TableSessionPool` for the table model.
Create each pool once, share it across threads, and close it when the application stops.

## Installation

```bash
# keep the client version equal to the server version
pip install apache-iotdb==<server version>
```

`TableSessionPool` requires V2.0+; `has_next_df()` / `next_df()` require V2.0.8+.

## Tree Model: SessionPool

### Pool and Borrow Helper

```python
import os
from contextlib import contextmanager

from iotdb.SessionPool import PoolConfig, SessionPool

pool_config = PoolConfig(
    node_urls=["127.0.0.1:6667"],
    user_name=os.getenv("IOTDB_USER", "root"),
    password=os.getenv("IOTDB_PASSWORD", "root"),
    fetch_size=1024,
    time_zone="Asia/Shanghai",
    max_retry=3,
)
tree_pool = SessionPool(pool_config, max_pool_size=10, wait_timeout_in_ms=3000)


@contextmanager
def tree_session():
    """Borrow a session and always return it to the pool."""
    session = tree_pool.get_session()
    try:
        yield session
    finally:
        tree_pool.put_back(session)
```

### Schema

```python
def ensure_database(session, database):
    # CREATE DATABASE has no IF NOT EXISTS in the tree model
    with session.execute_query_statement(f"SHOW DATABASES {database}") as data_set:
        if data_set.has_next():
            return
    session.execute_non_query_statement(f"CREATE DATABASE {database}")


with tree_session() as session:
    ensure_database(session, "root.factory")
    # Optional: timeseries are created on first write while enable_auto_create_schema=true (default)
    session.execute_non_query_statement(
        "CREATE ALIGNED TIMESERIES root.factory.line1.device8(temperature FLOAT, humidity FLOAT)"
    )
```

### Batch Write with Tablet

```python
from iotdb.utils.IoTDBConstants import TSDataType
from iotdb.utils.Tablet import Tablet


def write_device(device_id, start_time, rows, aligned=False, batch_size=1000):
    measurements = ["temperature", "humidity"]
    data_types = [TSDataType.FLOAT, TSDataType.FLOAT]
    with tree_session() as session:
        for offset in range(0, rows, batch_size):
            count = min(batch_size, rows - offset)
            timestamps = [start_time + (offset + i) * 1000 for i in range(count)]
            # one list per row, in the order of `measurements`
            values = [[20.0 + (offset + i) % 100 / 10, 55.0] for i in range(count)]
            tablet = Tablet(device_id, measurements, data_types, values, timestamps)
            if aligned:
                session.insert_aligned_tablet(tablet)
            else:
                session.insert_tablet(tablet)


write_device("root.factory.line1.device7", 1700000000000, 10_000)
write_device("root.factory.line1.device8", 1700000000000, 10_000, aligned=True)
```

For large batches, `iotdb.utils.NumpyTablet.NumpyTablet` avoids per-value Python objects.

### Query

```python
with tree_session() as session:
    # Iterate row by row; the data set is closed when the block exits
    with session.execute_query_statement(
        "SELECT temperature FROM root.factory.line1.device7 "
        "WHERE time >= 1700000000000 AND time < 1700000600000"
    ) as data_set:
        print(data_set.get_column_names())  # ['Time', 'root.factory.line1.device7.temperature']
        while data_set.has_next():
            record = data_set.next()
            print(record.get_timestamp(), record.get_fields()[0].get_float_value())

    # Small results only: whole result as one DataFrame
    with session.execute_query_statement(
        "SELECT avg(temperature) FROM root.factory.line1.device7 "
        "GROUP BY ([2023-11-14T00:00:00, 2023-11-15T00:00:00), 1h)"
    ) as data_set:
        df = data_set.todf()
```

## Table Model: TableSessionPool

### Pool

```python
import os

from iotdb.table_session_pool import TableSessionPool, TableSessionPoolConfig

table_config = TableSessionPoolConfig(
    node_urls=["127.0.0.1:6667"],
    username=os.getenv("IOTDB_USER", "root"),
    password=os.getenv("IOTDB_PASSWORD", "root"),
    database="factory",          # default database of every borrowed session
    max_pool_size=10,
    fetch_size=1024,
    wait_timeout_in_ms=3000,
)
table_pool = TableSessionPool(table_config)
```

A borrowed `TableSession` is returned to the pool by `session.close()`; `TableSession` is not a context manager,
so use `try`/`finally`.

### Schema

```python
session = table_pool.get_session()
try:
    session.execute_non_query_statement("CREATE DATABASE IF NOT EXISTS factory")
    session.execute_non_query_statement(
        "CREATE TABLE IF NOT EXISTS factory.sensors ("
        "region STRING TAG, plant_id STRING TAG, device_id STRING TAG, "
        "model STRING ATTRIBUTE, "
        "temperature FLOAT FIELD, humidity DOUBLE FIELD) WITH (TTL=31536000000)"
    )
finally:
    session.close()
```

If the database does not exist yet, create it with a pool configured without `database=...`.

### Batch Write with Tablet

```python
from iotdb.utils.IoTDBConstants import TSDataType
from iotdb.utils.Tablet import ColumnType, Tablet

COLUMNS = ["region", "plant_id", "device_id", "model", "temperature", "humidity"]
TYPES = [TSDataType.STRING] * 4 + [TSDataType.FLOAT, TSDataType.DOUBLE]
CATEGORIES = [ColumnType.TAG] * 3 + [ColumnType.ATTRIBUTE] + [ColumnType.FIELD] * 2


def write_table_rows(device_id, start_time, rows, batch_size=1000):
    session = table_pool.get_session()
    try:
        for offset in range(0, rows, batch_size):
            count = min(batch_size, rows - offset)
            timestamps = [start_time + (offset + i) * 1000 for i in range(count)]
            values = [
                ["north", "p1", device_id, "A", 20.0 + (offset + i) % 100 / 10, 55.0]
                for i in range(count)
            ]
            session.insert(Tablet("sensors", COLUMNS, TYPES, values, timestamps, CATEGORIES))
    finally:
        session.close()


write_table_rows("d7", 1700000000000, 10_000)
```

### Query

```python
session = table_pool.get_session()
try:
    with session.execute_query_statement(
        "SELECT time, device_id, temperature FROM sensors "
        "WHERE region = 'north' AND time >= now() - 1h"
    ) as data_set:
        while data_set.has_next():
            print(data_set.next())

    # Large results as DataFrame batches (V2.0.8+); do not mix with todf()/next()
    with session.execute_query_statement(
        "SELECT * FROM sensors WHERE device_id = 'd7'"
    ) as data_set:
        while data_set.has_next_df():
            chunk = data_set.next_df()
            print(len(chunk))
finally:
    session.close()
```

## Threads

```python
from concurrent.futures import ThreadPoolExecutor

# max_pool_size >= number of worker threads; extra threads wait up to wait_timeout_in_ms
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [
        executor.submit(write_device, f"root.factory.line1.device{d}", 1700000000000, 10_000)
        for d in range(100)
    ]
    for f in futures:
        f.result()
```

## Error Handling

```python
from iotdb.utils.exception import IoTDBConnectionException, StatementExecutionException

try:
    write_device("root.factory.line1.device7", 1700000000000, 1000)
except StatementExecutionException as e:
    # The server rejected the statement; str(e) is "<status code>: <message>". Do not retry blindly.
    raise
except IoTDBConnectionException:
    # Server unreachable after the pool's retries (max_retry)
    raise
```

## Shutdown

```python
tree_pool.close()
table_pool.close()
```

## Other Interfaces

`iotdb.dbapi` (DB-API 2.0) and the `iotdb.sqlalchemy` dialect exist for tree-model tooling such as BI clients.
Application code should use the pools above.
