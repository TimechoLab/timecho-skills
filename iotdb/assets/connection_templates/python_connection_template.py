# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

#!/usr/bin/env python3
"""
IoTDB Python Connection Template

This template provides ready-to-use connection patterns for IoTDB Python client:
- Iterator-based data reading (CRITICAL for memory efficiency)
- Basic Session connection with proper iterator usage
- Bulk data operations using tablets
- Pandas integration with iterator patterns
- Connection pooling and error handling
"""

import time
import random
import pandas as pd
from typing import List, Optional, Any
from contextlib import contextmanager
import threading
import queue

try:
    from iotdb.Session import Session
    from iotdb.utils.IoTDBConstants import TSDataType, TSEncoding
    from iotdb.utils.Tablet import Tablet, NumpyTablet
    from iotdb.utils.BitMap import BitMap
    import numpy as np
    IOTDB_AVAILABLE = True
except ImportError:
    IOTDB_AVAILABLE = False
    print("Warning: IoTDB Python client not installed. Install with: pip install apache-iotdb")


class IoTDBConnectionTemplate:
    """Main IoTDB connection template class"""

    def __init__(self, host="127.0.0.1", port="6667", username="root", password="root"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    @contextmanager
    def session_context(self):
        """Context manager for session connections"""
        if not IOTDB_AVAILABLE:
            raise ImportError("IoTDB client not available")

        session = Session(self.host, self.port, self.username, self.password)
        try:
            session.open(False)
            yield session
        finally:
            session.close()

    def basic_connection_example(self):
        """Basic connection and operations example with iterator"""
        print("Basic Connection Example (with Iterator)")
        print("-" * 40)

        with self.session_context() as session:
            # Create database
            session.set_storage_group("root.example")
            print("Created database: root.example")

            # Create timeseries
            session.create_time_series(
                "root.example.device1.temperature",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                None  # compressor
            )

            session.create_time_series(
                "root.example.device1.humidity",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                None
            )

            print("Created timeseries for temperature and humidity")

            # Insert single record
            timestamp = int(time.time() * 1000)
            session.insert_record(
                "root.example.device1",
                timestamp,
                ["temperature", "humidity"],
                [TSDataType.FLOAT, TSDataType.FLOAT],
                [25.5, 60.0]
            )

            print(f"Inserted record at timestamp {timestamp}")

            # ⭐ CRITICAL: Always use iterator for reading data
            result = session.execute_query_statement(
                "SELECT temperature, humidity FROM root.example.device1"
            )

            print("Query results (using iterator):")
            print("Time\t\t\tTemperature\tHumidity")
            print("-" * 50)

            # Iterator pattern - RECOMMENDED for all data reading
            while result.has_next():
                record = result.next()
                timestamp = record.get_timestamp()
                fields = record.get_fields()
                temp_value = fields[0].get_value() if len(fields) > 0 else "N/A"
                humid_value = fields[1].get_value() if len(fields) > 1 else "N/A"

                print(f"{timestamp}\t{temp_value}\t\t{humid_value}")

            # Important: close result to free memory
            result.close()
    def tablet_insertion_example(self):
        """Bulk data insertion using tablets with iterator verification"""
        print("Tablet Insertion Example (with Iterator Verification)")
        print("-" * 55)

        with self.session_context() as session:
            device_id = "root.example.bulk_device"
            measurements = ["temperature", "humidity", "pressure"]
            data_types = [TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT]

            # Generate sample data
            num_points = 1000
            base_time = int(time.time() * 1000)

            timestamps = [base_time + i * 1000 for i in range(num_points)]
            values = [
                [20.0 + random.random() * 10 for _ in range(num_points)],  # temperature
                [40.0 + random.random() * 30 for _ in range(num_points)],  # humidity
                [1000.0 + random.random() * 50 for _ in range(num_points)]  # pressure
            ]

            # Create and insert tablet
            tablet = Tablet(device_id, measurements, data_types, values, timestamps)
            session.insert_tablet(tablet)

            print(f"Inserted {num_points} records using tablet")

            # ⭐ CRITICAL: Use iterator to verify insertion
            result = session.execute_query_statement(
                f"SELECT COUNT(*) FROM {device_id}"
            )

            if result.has_next():
                count_record = result.next()
                count_fields = count_record.get_fields()
                count_value = count_fields[0].get_value() if count_fields else 0
                print(f"Verified: {count_value} records in database")

            result.close()

            # Query sample data using iterator
            result = session.execute_query_statement(
                f"SELECT * FROM {device_id} LIMIT 5"
            )

            print("Sample data (first 5 records):")
            print("Time\t\t\tTemp\tHumid\tPress")
            print("-" * 50)

            while result.has_next():
                record = result.next()
                timestamp = record.get_timestamp()
                fields = record.get_fields()

                if len(fields) >= 3:
                    temp = fields[0].get_value()
                    humid = fields[1].get_value()
                    press = fields[2].get_value()
                    print(f"{timestamp}\t{temp:.1f}\t{humid:.1f}\t{press:.1f}")

            result.close()

    def numpy_tablet_example(self):
        """High-performance numpy tablet example"""
        print("Numpy Tablet Example")
        print("-" * 30)

        with self.session_context() as session:
            device_id = "root.example.numpy_device"
            measurements = ["sensor1", "sensor2", "sensor3"]
            data_types = [TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT]

            # Generate numpy arrays
            num_points = 5000
            np_timestamps = np.array(
                [int(time.time() * 1000) + i * 100 for i in range(num_points)],
                dtype=TSDataType.INT64.np_dtype()
            )

            np_values = [
                np.random.uniform(20, 30, num_points).astype(TSDataType.FLOAT.np_dtype()),
                np.random.uniform(40, 80, num_points).astype(TSDataType.FLOAT.np_dtype()),
                np.random.uniform(990, 1050, num_points).astype(TSDataType.FLOAT.np_dtype())
            ]

            # Create numpy tablet
            start_time = time.time()
            np_tablet = NumpyTablet(device_id, measurements, data_types, np_values, np_timestamps)
            session.insert_tablet(np_tablet)
            insert_time = time.time() - start_time

            print(f"Inserted {num_points} records in {insert_time:.2f} seconds")
            print(f"Performance: {num_points / insert_time:.2f} records/second")

    def pandas_integration_example(self):
        """Pandas DataFrame integration with iterator patterns"""
        print("Pandas Integration Example (Iterator-based)")
        print("-" * 45)

        with self.session_context() as session:
            # ⭐ Query data with iterator pattern first
            result = session.execute_query_statement(
                "SELECT * FROM root.example.** LIMIT 100"
            )

            # Option 1: Direct conversion (handles iterator internally - for small datasets)
            df = result.todf()
            print("Query result as DataFrame (todf method):")
            print(df.head())

            if len(df) > 0:
                print(f"DataFrame shape: {df.shape}")
                print("\nBasic statistics:")
                print(df.describe())

                # Time-based analysis (if Time column exists)
                if 'Time' in df.columns:
                    df['Time'] = pd.to_datetime(df['Time'])
                    print("\nTime range:")
                    print(f"From: {df['Time'].min()}")
                    print(f"To: {df['Time'].max()}")

            result.close()

            # Option 2: Manual iterator processing for large datasets (RECOMMENDED for memory control)
            print("\n--- Manual Iterator Processing for Large Datasets ---")
            result = session.execute_query_statement(
                "SELECT * FROM root.example.** LIMIT 50"
            )

            data_rows = []
            column_names = None

            # Process data using iterator for memory efficiency
            while result.has_next():
                record = result.next()

                # Get column names from first record
                if column_names is None:
                    column_names = ['Time'] + [field.get_name() for field in record.get_fields()]

                # Extract data
                row_data = [record.get_timestamp()]
                row_data.extend([field.get_value() for field in record.get_fields()])
                data_rows.append(row_data)

            result.close()

            # Convert to DataFrame manually for better memory control
            if data_rows:
                df_manual = pd.DataFrame(data_rows, columns=column_names)
                print("Manual iterator processing results:")
                print(df_manual.head())
                print(f"Processed {len(df_manual)} rows using iterator")

            # Option 3: Streaming processing for very large datasets
            print("\n--- Streaming Processing Demo ---")
            self._stream_process_large_dataset("SELECT * FROM root.example.**")

    def _stream_process_large_dataset(self, query_sql):
        """Stream processing for very large datasets using iterator"""
        with self.session_context() as session:
            result = session.execute_query_statement(query_sql)

            # Process in chunks to avoid memory issues
            chunk_size = 10  # Small for demo
            chunk_data = []
            total_processed = 0

            print(f"Processing query in chunks of {chunk_size}...")

            while result.has_next():
                record = result.next()

                # Build chunk data
                row_data = [record.get_timestamp()]
                row_data.extend([field.get_value() for field in record.get_fields()])
                chunk_data.append(row_data)

                if len(chunk_data) >= chunk_size:
                    # Process chunk (e.g., save to file, analyze, etc.)
                    total_processed += len(chunk_data)
                    print(f"  Processed chunk: {len(chunk_data)} records (total: {total_processed})")
                    chunk_data = []  # Reset for next chunk

            # Process remaining data
            if chunk_data:
                total_processed += len(chunk_data)
                print(f"  Final chunk: {len(chunk_data)} records (total: {total_processed})")

            result.close()
            print(f"Stream processing completed: {total_processed} total records")

    def aligned_timeseries_example(self):
        """Aligned timeseries operations example"""
        print("Aligned Timeseries Example")
        print("-" * 30)

        with self.session_context() as session:
            device_id = "root.example.aligned_device"
            measurements = ["sensor1", "sensor2", "sensor3"]
            data_types = [TSDataType.FLOAT, TSDataType.FLOAT, TSDataType.FLOAT]

            # Create aligned timeseries
            session.create_aligned_time_series(
                device_id,
                measurements,
                data_types,
                [TSEncoding.RLE] * 3,
                [None] * 3  # compressors
            )

            print("Created aligned timeseries")

            # Insert aligned records
            timestamps = [int(time.time() * 1000) + i * 1000 for i in range(10)]
            values = [
                [25.0 + i * 0.1 for i in range(10)],
                [30.0 + i * 0.2 for i in range(10)],
                [35.0 + i * 0.3 for i in range(10)]
            ]

            aligned_tablet = Tablet(device_id, measurements, data_types, values, timestamps)
            session.insert_aligned_tablet(aligned_tablet)

            print("Inserted 10 aligned records")

            # Query aligned data
            result = session.execute_query_statement(f"SELECT * FROM {device_id}")
            print("Aligned data:")
            count = 0
            while result.has_next() and count < 5:
                print(f"  {result.next()}")
                count += 1


class ConnectionPool:
    """Simple connection pool implementation"""

    def __init__(self, host, port, username, password, pool_size=5):
        self.pool = queue.Queue(maxsize=pool_size)
        self.host = host
        self.port = port
        self.username = username
        self.password = password

        # Initialize pool
        for _ in range(pool_size):
            session = Session(host, port, username, password)
            session.open(False)
            self.pool.put(session)

    def get_session(self):
        """Get a session from the pool"""
        return self.pool.get()

    def return_session(self, session):
        """Return a session to the pool"""
        self.pool.put(session)

    def close_all(self):
        """Close all sessions in the pool"""
        while not self.pool.empty():
            session = self.pool.get()
            session.close()

    @contextmanager
    def session_context(self):
        """Context manager for pooled sessions"""
        session = self.get_session()
        try:
            yield session
        finally:
            self.return_session(session)


class RobustConnection:
    """Connection with retry logic and error handling"""

    def __init__(self, host="127.0.0.1", port="6667", username="root", password="root"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.session = None

    def connect_with_retry(self, max_retries=3, delay=1.0, backoff=2.0):
        """Connect with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                self.session = Session(self.host, self.port, self.username, self.password)
                self.session.open(False)
                print(f"Connected successfully on attempt {attempt + 1}")
                return

            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to connect after {max_retries} attempts: {e}")

                wait_time = delay * (backoff ** attempt)
                print(f"Connection attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {wait_time:.1f} seconds...")
                time.sleep(wait_time)

    def execute_with_retry(self, operation, *args, max_retries=3):
        """Execute operation with retry logic"""
        for attempt in range(max_retries):
            try:
                return operation(*args)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e

                print(f"Operation failed (attempt {attempt + 1}): {e}")
                time.sleep(1.0 * (attempt + 1))

    def close(self):
        """Close connection safely"""
        if self.session:
            try:
                self.session.close()
            except Exception as e:
                print(f"Warning: Error closing session: {e}")


def connection_pool_example():
    """Demonstrate connection pooling"""
    print("Connection Pool Example")
    print("-" * 30)

    if not IOTDB_AVAILABLE:
        print("IoTDB client not available for pool example")
        return

    pool = ConnectionPool("127.0.0.1", "6667", "root", "root", pool_size=3)

    def worker_thread(thread_id):
        """Worker thread function"""
        with pool.session_context() as session:
            # Simulate work
            session.insert_record(
                f"root.example.pool_test.thread_{thread_id}",
                int(time.time() * 1000),
                ["value"],
                [TSDataType.FLOAT],
                [float(thread_id * 10)]
            )
            print(f"Thread {thread_id} completed work")

    # Start multiple threads
    threads = []
    for i in range(10):
        thread = threading.Thread(target=worker_thread, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    pool.close_all()
    print("Connection pool example completed")


def robust_connection_example():
    """Demonstrate robust connection with retry logic"""
    print("Robust Connection Example")
    print("-" * 30)

    if not IOTDB_AVAILABLE:
        print("IoTDB client not available for robust connection example")
        return

    conn = RobustConnection()

    try:
        # Connect with retry
        conn.connect_with_retry(max_retries=3, delay=1.0)

        # Execute operations with retry
        conn.execute_with_retry(
            conn.session.insert_record,
            "root.example.robust_test",
            int(time.time() * 1000),
            ["temperature"],
            [TSDataType.FLOAT],
            [25.0]
        )

        print("Robust operations completed successfully")

    except Exception as e:
        print(f"Robust connection failed: {e}")
    finally:
        conn.close()


def main():
    """Main function demonstrating all examples"""
    if not IOTDB_AVAILABLE:
        print("Error: IoTDB Python client not installed.")
        print("Install with: pip install apache-iotdb")
        return

    template = IoTDBConnectionTemplate()

    print("IoTDB Python Connection Template Examples")
    print("=" * 50)

    try:
        # Basic examples
        template.basic_connection_example()
        print()

        template.tablet_insertion_example()
        print()

        template.numpy_tablet_example()
        print()

        template.pandas_integration_example()
        print()

        template.aligned_timeseries_example()
        print()

        # Advanced examples
        connection_pool_example()
        print()

        robust_connection_example()

    except Exception as e:
        print(f"Example error: {e}")


if __name__ == "__main__":
    main()