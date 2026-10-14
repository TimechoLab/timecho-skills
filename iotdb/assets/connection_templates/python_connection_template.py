#!/usr/bin/env python3
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
"""
IoTDB Python connection template (apache-iotdb V2.0.x).

- Tree model: one SessionPool per process; borrow with get_session(), return with put_back().
- Table model: one TableSessionPool per process; borrow with get_session(), return with close().
- Close every result set (use `with`), and close the pools on shutdown.

Connection settings come from the environment: IOTDB_NODE_URLS (comma separated, default
127.0.0.1:6667), IOTDB_USER (default root), IOTDB_PASSWORD (default root; TimechoDB V2.0.6.1+
uses TimechoDB@2021).
"""

import os
import time
from contextlib import contextmanager

from iotdb.SessionPool import PoolConfig, SessionPool
from iotdb.table_session_pool import TableSessionPool, TableSessionPoolConfig
from iotdb.utils.IoTDBConstants import TSDataType
from iotdb.utils.Tablet import ColumnType, Tablet


class IoTDBClient:
    def __init__(self, node_urls, user, password, max_pool_size=10, wait_timeout_in_ms=3000):
        self.tree_pool = SessionPool(
            PoolConfig(node_urls=node_urls, user_name=user, password=password, fetch_size=1024),
            max_pool_size,
            wait_timeout_in_ms,
        )
        # No default database, so this pool can also run CREATE DATABASE.
        self.table_pool = TableSessionPool(
            TableSessionPoolConfig(
                node_urls=node_urls,
                username=user,
                password=password,
                max_pool_size=max_pool_size,
                wait_timeout_in_ms=wait_timeout_in_ms,
            )
        )

    @classmethod
    def from_environment(cls):
        return cls(
            os.getenv("IOTDB_NODE_URLS", "127.0.0.1:6667").split(","),
            os.getenv("IOTDB_USER", "root"),
            os.getenv("IOTDB_PASSWORD", "root"),
        )

    @contextmanager
    def tree_session(self):
        session = self.tree_pool.get_session()
        try:
            yield session
        finally:
            self.tree_pool.put_back(session)

    @contextmanager
    def table_session(self):
        session = self.table_pool.get_session()
        try:
            yield session
        finally:
            session.close()  # returns the session to the pool

    # ------------------------------------------------------------ tree model

    def write_tree(self, device_id, start_time, rows, batch_size=1000):
        """Write rows of one device; timeseries are auto-created if they do not exist."""
        measurements = ["temperature", "humidity"]
        data_types = [TSDataType.FLOAT, TSDataType.FLOAT]
        with self.tree_session() as session:
            for offset in range(0, rows, batch_size):
                count = min(batch_size, rows - offset)
                timestamps = [start_time + (offset + i) * 1000 for i in range(count)]
                values = [[20.0 + (offset + i) % 100 / 10, 60.0] for i in range(count)]
                session.insert_tablet(
                    Tablet(device_id, measurements, data_types, values, timestamps)
                )

    def read_tree(self, device_id, start_time, end_time):
        rows = 0
        with self.tree_session() as session:
            with session.execute_query_statement(
                f"SELECT temperature FROM {device_id} "
                f"WHERE time >= {start_time} AND time < {end_time}"
            ) as data_set:
                while data_set.has_next():
                    data_set.next()
                    rows += 1
        return rows

    # ------------------------------------------------------------ table model

    def create_table_schema(self):
        with self.table_session() as session:
            session.execute_non_query_statement("CREATE DATABASE IF NOT EXISTS factory")
            session.execute_non_query_statement(
                "CREATE TABLE IF NOT EXISTS factory.sensors ("
                "region STRING TAG, device_id STRING TAG, model STRING ATTRIBUTE, "
                "temperature FLOAT FIELD, humidity DOUBLE FIELD) WITH (TTL=31536000000)"
            )

    def write_table(self, region, device_id, start_time, rows, batch_size=1000):
        columns = ["region", "device_id", "model", "temperature", "humidity"]
        data_types = [TSDataType.STRING] * 3 + [TSDataType.FLOAT, TSDataType.DOUBLE]
        categories = [ColumnType.TAG] * 2 + [ColumnType.ATTRIBUTE] + [ColumnType.FIELD] * 2
        with self.table_session() as session:
            session.execute_non_query_statement("USE factory")  # lasts until the session is returned
            for offset in range(0, rows, batch_size):
                count = min(batch_size, rows - offset)
                timestamps = [start_time + (offset + i) * 1000 for i in range(count)]
                values = [
                    [region, device_id, "A", 20.0 + (offset + i) % 100 / 10, 60.0]
                    for i in range(count)
                ]
                session.insert(
                    Tablet("sensors", columns, data_types, values, timestamps, categories)
                )

    def read_table(self, region, start_time):
        rows = 0
        with self.table_session() as session:
            with session.execute_query_statement(
                "SELECT time, device_id, temperature FROM factory.sensors "
                f"WHERE region = '{region}' AND time >= {start_time}"
            ) as data_set:
                while data_set.has_next():
                    data_set.next()
                    rows += 1
        return rows

    def close(self):
        self.tree_pool.close()
        self.table_pool.close()


if __name__ == "__main__":
    client = IoTDBClient.from_environment()
    try:
        now = int(time.time() * 1000)

        client.write_tree("root.template.line1.device1", now, 100)
        print("tree rows:", client.read_tree("root.template.line1.device1", now, now + 100_000))

        client.create_table_schema()
        client.write_table("north", "d1", now, 100)
        print("table rows:", client.read_table("north", now))
    finally:
        client.close()
