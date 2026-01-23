# Python Examples for IoTDB Connection

## Complete Python Session Example

```python
from iotdb.Session import Session
from iotdb.utils.IoTDBConstants import TSDataType
from iotdb.utils.Tablet import Tablet, NumpyTablet
from iotdb.utils.BitMap import BitMap
import numpy as np
import pandas as pd
from datetime import datetime
import time

class IoTDBPythonClient:
    def __init__(self, host="127.0.0.1", port="6667", username="root", password="root"):
        self.session = Session(host, port, username, password)

    def connect(self):
        """Establish connection to IoTDB"""
        self.session.open(False)
        print(f"Connected to IoTDB at {self.session.host}:{self.session.port}")

    def disconnect(self):
        """Close connection to IoTDB"""
        self.session.close()
        print("Disconnected from IoTDB")

    def basic_operations_example(self):
        """Demonstrates basic CRUD operations"""
        try:
            # Create database (storage group)
            self.session.set_storage_group("root.factory")
            print("Created database: root.factory")

            # Create timeseries
            self.session.create_time_series(
                "root.factory.workshop1.temperature",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                Compressor.SNAPPY
            )

            self.session.create_time_series(
                "root.factory.workshop1.humidity",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                Compressor.SNAPPY
            )

            print("Created timeseries for temperature and humidity")

            # Insert single record
            timestamp = int(time.time() * 1000)  # Current timestamp in milliseconds
            self.session.insert_record(
                "root.factory.workshop1",
                timestamp,
                ["temperature", "humidity"],
                [TSDataType.FLOAT, TSDataType.FLOAT],
                [25.5, 60.0]
            )

            print("Inserted single record")

            # Insert multiple records
            device_ids = ["root.factory.workshop1", "root.factory.workshop2"]
            timestamps = [timestamp + 1000, timestamp + 2000]
            measurements_list = [["temperature", "humidity"], ["temperature", "humidity"]]
            data_types_list = [
                [TSDataType.FLOAT, TSDataType.FLOAT],
                [TSDataType.FLOAT, TSDataType.FLOAT]
            ]
            values_list = [
                [26.0, 61.0],
                [24.5, 58.5]
            ]

            self.session.insert_records(
                device_ids,
                timestamps,
                measurements_list,
                data_types_list,
                values_list
            )

            print("Inserted multiple records")

            # Query data
            result = self.session.execute_query_statement(
                "SELECT temperature, humidity FROM root.factory.workshop1"
            )

            print("Query results:")
            while result.has_next():
                print(result.next())

        except Exception as e:
            print(f"Error in basic operations: {e}")

    def tablet_insertion_example(self):
        """Demonstrates efficient bulk insertion using tablets"""
        try:
            device_id = "root.factory.workshop1"
            measurements = ["temperature", "humidity", "pressure"]
            data_types = [TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT]

            # Generate sample data
            num_points = 1000
            timestamps = []
            values = [[] for _ in range(len(measurements))]

            base_time = int(time.time() * 1000)
            for i in range(num_points):
                timestamps.append(base_time + i * 1000)
                values[0].append(20.0 + (i % 10))  # temperature
                values[1].append(50.0 + (i % 20))  # humidity
                values[2].append(1000.0 + (i % 50))  # pressure

            # Create and insert tablet
            tablet = Tablet(device_id, measurements, data_types, values, timestamps)
            self.session.insert_tablet(tablet)

            print(f"Inserted {num_points} points using tablet")

        except Exception as e:
            print(f"Error in tablet insertion: {e}")

    def numpy_tablet_example(self):
        """Demonstrates numpy tablet for better performance"""
        try:
            device_id = "root.factory.workshop2"
            measurements = ["temperature", "humidity", "pressure"]
            data_types = [TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT]

            # Generate numpy arrays
            num_points = 1000
            np_timestamps = np.array(
                [int(time.time() * 1000) + i * 1000 for i in range(num_points)],
                dtype=TSDataType.INT64.np_dtype()
            )

            np_values = [
                np.random.uniform(20, 30, num_points).astype(TSDataType.FLOAT.np_dtype()),
                np.random.uniform(40, 80, num_points).astype(TSDataType.FLOAT.np_dtype()),
                np.random.uniform(990, 1050, num_points).astype(TSDataType.FLOAT.np_dtype())
            ]

            # Create numpy tablet
            np_tablet = NumpyTablet(device_id, measurements, data_types, np_values, np_timestamps)
            self.session.insert_tablet(np_tablet)

            print(f"Inserted {num_points} points using numpy tablet")

        except Exception as e:
            print(f"Error in numpy tablet insertion: {e}")

    def pandas_integration_example(self):
        """Demonstrates pandas DataFrame integration"""
        try:
            # Query data and convert to DataFrame
            result = self.session.execute_query_statement(
                "SELECT * FROM root.factory.** WHERE time >= now() - 1h"
            )

            df = result.todf()
            print("Data as pandas DataFrame:")
            print(df.head())
            print(f"DataFrame shape: {df.shape}")

            # Basic analytics
            if len(df) > 0:
                print("\nBasic statistics:")
                print(df.describe())

                # Time-based resampling (if timestamp column exists)
                if 'Time' in df.columns:
                    df['Time'] = pd.to_datetime(df['Time'])
                    df.set_index('Time', inplace=True)

                    # Resample to 5-minute intervals
                    resampled = df.resample('5T').mean()
                    print("\nResampled data (5-minute intervals):")
                    print(resampled.head())

        except Exception as e:
            print(f"Error in pandas integration: {e}")

    def aligned_timeseries_example(self):
        """Demonstrates aligned timeseries operations"""
        try:
            device_id = "root.factory.aligned_device"
            measurements = ["sensor1", "sensor2", "sensor3"]
            data_types = [TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT]

            # Create aligned timeseries
            self.session.create_aligned_time_series(
                device_id,
                measurements,
                data_types,
                [TSEncoding.RLE] * 3,
                [Compressor.SNAPPY] * 3
            )

            print("Created aligned timeseries")

            # Insert aligned record
            timestamp = int(time.time() * 1000)
            self.session.insert_aligned_record(
                device_id,
                timestamp,
                measurements,
                data_types,
                [25.0, 30.0, 35.0]
            )

            print("Inserted aligned record")

            # Insert aligned tablet
            timestamps = [timestamp + i * 1000 for i in range(100)]
            values = [
                [25.0 + i * 0.1 for i in range(100)],
                [30.0 + i * 0.2 for i in range(100)],
                [35.0 + i * 0.3 for i in range(100)]
            ]

            aligned_tablet = Tablet(device_id, measurements, data_types, values, timestamps)
            self.session.insert_aligned_tablet(aligned_tablet)

            print("Inserted 100 aligned records using tablet")

        except Exception as e:
            print(f"Error in aligned timeseries operations: {e}")

    def advanced_query_examples(self):
        """Demonstrates advanced querying capabilities"""
        try:
            # Time range query
            result = self.session.execute_query_statement(
                "SELECT temperature, humidity FROM root.factory.workshop1 "
                "WHERE time >= now() - 1h AND temperature > 25"
            )

            print("Time range query results:")
            count = 0
            while result.has_next() and count < 5:
                print(result.next())
                count += 1

            # Aggregation query
            result = self.session.execute_query_statement(
                "SELECT AVG(temperature), MAX(temperature), MIN(temperature) "
                "FROM root.factory.workshop1 "
                "WHERE time >= now() - 24h "
                "GROUP BY ([now() - 24h, now()), 1h)"
            )

            print("\nAggregation query results:")
            count = 0
            while result.has_next() and count < 5:
                print(result.next())
                count += 1

            # Last value query
            result = self.session.execute_query_statement(
                "SELECT LAST temperature, humidity FROM root.factory.**"
            )

            print("\nLast value query results:")
            while result.has_next():
                print(result.next())

        except Exception as e:
            print(f"Error in advanced queries: {e}")

    def session_configuration_example(self):
        """Demonstrates session configuration options"""
        try:
            # Configure session parameters
            self.session.set_fetch_size(5000)
            self.session.set_time_zone("Asia/Shanghai")

            # Check configuration
            print(f"Current timezone: {self.session.get_time_zone()}")

            # Test connection
            result = self.session.execute_query_statement("SHOW TIMESERIES")
            print("Available timeseries:")
            count = 0
            while result.has_next() and count < 10:
                print(result.next())
                count += 1

        except Exception as e:
            print(f"Error in session configuration: {e}")


def connection_pool_example():
    """Demonstrates connection management for concurrent access"""
    import threading
    import queue

    class IoTDBConnectionPool:
        def __init__(self, host, port, username, password, pool_size=5):
            self.pool = queue.Queue(maxsize=pool_size)
            for _ in range(pool_size):
                session = Session(host, port, username, password)
                session.open(False)
                self.pool.put(session)

        def get_connection(self):
            return self.pool.get()

        def return_connection(self, session):
            self.pool.put(session)

        def close_all(self):
            while not self.pool.empty():
                session = self.pool.get()
                session.close()

    # Usage example
    pool = IoTDBConnectionPool("127.0.0.1", "6667", "root", "root", pool_size=3)

    def worker_thread(thread_id):
        session = pool.get_connection()
        try:
            # Simulate work
            session.insert_record(
                f"root.factory.thread_{thread_id}",
                int(time.time() * 1000),
                ["value"],
                [TSDataType.FLOAT],
                [float(thread_id)]
            )
            print(f"Thread {thread_id} completed work")
        finally:
            pool.return_connection(session)

    # Start multiple threads
    threads = []
    for i in range(10):
        thread = threading.Thread(target=worker_thread, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    pool.close_all()
    print("Connection pool example completed")


def main():
    """Main example function"""
    client = IoTDBPythonClient()

    try:
        client.connect()

        print("=== Basic Operations Example ===")
        client.basic_operations_example()

        print("\n=== Tablet Insertion Example ===")
        client.tablet_insertion_example()

        print("\n=== Numpy Tablet Example ===")
        client.numpy_tablet_example()

        print("\n=== Pandas Integration Example ===")
        client.pandas_integration_example()

        print("\n=== Aligned Timeseries Example ===")
        client.aligned_timeseries_example()

        print("\n=== Advanced Query Examples ===")
        client.advanced_query_examples()

        print("\n=== Session Configuration Example ===")
        client.session_configuration_example()

    except Exception as e:
        print(f"Error in main execution: {e}")
    finally:
        client.disconnect()

    print("\n=== Connection Pool Example ===")
    connection_pool_example()


if __name__ == "__main__":
    main()
```

## Error Handling and Retry Logic

```python
import time
import logging
from functools import wraps

def retry_operation(max_retries=3, delay=1.0, backoff=2.0):
    """Decorator for retrying IoTDB operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logging.error(f"Operation {func.__name__} failed after {max_retries} retries: {e}")
                        raise e

                    wait_time = delay * (backoff ** (retries - 1))
                    logging.warning(f"Retry {retries}/{max_retries} for {func.__name__} in {wait_time}s: {e}")
                    time.sleep(wait_time)

        return wrapper
    return decorator


class RobustIoTDBClient:
    def __init__(self, host="127.0.0.1", port="6667", username="root", password="root"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.session = None

    def connect(self):
        """Connect with retry logic"""
        @retry_operation(max_retries=3)
        def _connect():
            self.session = Session(self.host, self.port, self.username, self.password)
            self.session.open(False)

        _connect()

    @retry_operation(max_retries=3)
    def insert_record_safe(self, device_id, timestamp, measurements, data_types, values):
        """Insert record with retry logic"""
        if not self.session:
            raise Exception("Not connected to IoTDB")

        return self.session.insert_record(device_id, timestamp, measurements, data_types, values)

    @retry_operation(max_retries=3)
    def query_safe(self, sql):
        """Execute query with retry logic"""
        if not self.session:
            raise Exception("Not connected to IoTDB")

        return self.session.execute_query_statement(sql)

    def disconnect(self):
        """Safely disconnect"""
        if self.session:
            try:
                self.session.close()
            except Exception as e:
                logging.warning(f"Error during disconnect: {e}")
            finally:
                self.session = None
```

## IoTDB DBAPI Example

```python
from iotdb.dbapi import connect

def dbapi_example():
    """Demonstrates IoTDB DB-API 2.0 interface"""

    # Connect using DB-API
    conn = connect(
        host="127.0.0.1",
        port="6667",
        username="root",
        password="root",
        fetch_size=1024,
        zone_id="Asia/Shanghai"
    )

    cursor = conn.cursor()

    try:
        # Simple query execution
        cursor.execute("SHOW TIMESERIES")
        results = cursor.fetchall()
        print("Timeseries:")
        for row in results:
            print(row)

        # Parameterized query
        cursor.execute(
            "SELECT * FROM root.** WHERE time < %(time)s",
            {"time": "2024-01-01T00:00:00.000"}
        )

        results = cursor.fetchmany(5)
        print("Parameterized query results:")
        for row in results:
            print(row)

        # Batch operations
        insert_params = [
            {"timestamp": int(time.time() * 1000) + i, "value": i * 10}
            for i in range(5)
        ]

        cursor.executemany(
            "INSERT INTO root.test(timestamp, value) VALUES(%(timestamp)s, %(value)s)",
            insert_params
        )

        print("Inserted batch data")

    except Exception as e:
        print(f"DB-API error: {e}")
    finally:
        cursor.close()
        conn.close()


# SQLAlchemy Integration Example
def sqlalchemy_example():
    """Demonstrates SQLAlchemy integration (experimental)"""
    try:
        from sqlalchemy import create_engine, Column, Float, BigInteger, MetaData
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import sessionmaker

        # Create engine
        engine = create_engine("iotdb://root:root@127.0.0.1:6667")

        # Define model
        metadata = MetaData(schema='root.factory')
        Base = declarative_base(metadata=metadata)

        class SensorData(Base):
            __tablename__ = "workshop1.device1"
            Time = Column(BigInteger, primary_key=True)
            temperature = Column(Float)
            humidity = Column(Float)

        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()

        # Query using ORM
        results = session.query(SensorData.temperature).filter(
            SensorData.temperature > 25
        ).limit(10).all()

        print("SQLAlchemy ORM results:")
        for result in results:
            print(result)

        session.close()

    except ImportError:
        print("SQLAlchemy not installed, skipping example")
    except Exception as e:
        print(f"SQLAlchemy error: {e}")


if __name__ == "__main__":
    print("=== DB-API Example ===")
    dbapi_example()

    print("\n=== SQLAlchemy Example ===")
    sqlalchemy_example()
```

## Requirements

```txt
# requirements.txt for Python IoTDB client

apache-iotdb>=1.2.0
numpy>=1.19.0
pandas>=1.3.0
thrift>=0.14.1

# Optional dependencies
sqlalchemy>=1.4.0  # For SQLAlchemy dialect
testcontainers>=3.4.0  # For testing
```

## Installation Script

```bash
#!/bin/bash
# install_iotdb_python.sh

echo "Installing IoTDB Python client and dependencies..."

# Install base package
pip install apache-iotdb

# Install optional dependencies
pip install numpy pandas

# Install development dependencies (optional)
pip install sqlalchemy testcontainers

echo "Installation complete!"
echo "Test connection with: python -c 'from iotdb.Session import Session; print(\"IoTDB Python client installed successfully\")'"
```