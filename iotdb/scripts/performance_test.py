#!/usr/bin/env python3
"""
IoTDB Connection Smoke Test

Measures client-side write and query timing through one shared SessionPool (tree model):
  1. single-thread Tablet writes to one device,
  2. concurrent Tablet writes from several threads sharing the pool,
  3. a count query over the written data.

All data goes to a uniquely named database (root.perf_smoke_<timestamp>) that is dropped at
the end, even on failure. The numbers reflect this client and network, not server capacity:
for capacity benchmarks use the timechodb-benchmark skill (iot-benchmark).

Requires: pip install apache-iotdb==<server version>
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor

from iotdb.SessionPool import PoolConfig, SessionPool
from iotdb.utils.IoTDBConstants import TSDataType
from iotdb.utils.Tablet import Tablet

MEASUREMENTS = ["s1", "s2"]
DATA_TYPES = [TSDataType.DOUBLE, TSDataType.INT64]


def write_device(pool, device_id, records, batch_size, start_time):
    session = pool.get_session()
    try:
        for offset in range(0, records, batch_size):
            count = min(batch_size, records - offset)
            timestamps = [start_time + offset + i for i in range(count)]
            values = [[(offset + i) * 0.1, offset + i] for i in range(count)]
            session.insert_tablet(Tablet(device_id, MEASUREMENTS, DATA_TYPES, values, timestamps))
    finally:
        pool.put_back(session)


def count_rows(pool, path_pattern):
    session = pool.get_session()
    try:
        with session.execute_query_statement(f"SELECT count(s1) FROM {path_pattern}") as data_set:
            total = 0
            while data_set.has_next():
                total += sum(int(field.get_long_value()) for field in data_set.next().get_fields())
            return total
    finally:
        pool.put_back(session)


def run(args):
    pool = SessionPool(
        PoolConfig(host=args.host, port=str(args.port), user_name=args.username, password=args.password),
        max(args.threads, 1),
        10000,
    )
    database = f"root.perf_smoke_{int(time.time() * 1000)}"
    start_time = 1_700_000_000_000
    results = {"database": database, "records": args.records, "batch_size": args.batch_size}

    setup = pool.get_session()
    try:
        setup.execute_non_query_statement(f"CREATE DATABASE {database}")
    finally:
        pool.put_back(setup)

    try:
        begin = time.perf_counter()
        write_device(pool, f"{database}.single", args.records, args.batch_size, start_time)
        elapsed = time.perf_counter() - begin
        results["single_thread"] = {
            "seconds": round(elapsed, 3),
            "points_per_second": round(args.records * len(MEASUREMENTS) / elapsed),
        }

        per_thread = max(args.records // args.threads, 1)
        begin = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = [
                executor.submit(
                    write_device, pool, f"{database}.t{t}", per_thread, args.batch_size, start_time
                )
                for t in range(args.threads)
            ]
            for future in futures:
                future.result()
        elapsed = time.perf_counter() - begin
        results["concurrent"] = {
            "threads": args.threads,
            "seconds": round(elapsed, 3),
            "points_per_second": round(per_thread * args.threads * len(MEASUREMENTS) / elapsed),
        }

        begin = time.perf_counter()
        total = count_rows(pool, f"{database}.**")
        results["count_query"] = {
            "seconds": round(time.perf_counter() - begin, 3),
            "rows_counted": total,
            "rows_expected": args.records + per_thread * args.threads,
        }
    finally:
        cleanup = pool.get_session()
        try:
            cleanup.execute_non_query_statement(f"DELETE DATABASE {database}")
        finally:
            pool.put_back(cleanup)
            pool.close()
    return results


def main():
    parser = argparse.ArgumentParser(description="IoTDB client-side write/query smoke test")
    parser.add_argument("--host", default="127.0.0.1", help="IoTDB host")
    parser.add_argument("--port", type=int, default=6667, help="IoTDB RPC port")
    parser.add_argument("--username", default="root", help="Username")
    parser.add_argument("--password", default="root", help="Password")
    parser.add_argument("--records", type=int, default=10000, help="Rows per test")
    parser.add_argument("--batch-size", type=int, default=1000, help="Rows per Tablet")
    parser.add_argument("--threads", type=int, default=4, help="Threads for the concurrent test")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    results = run(args)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for key, value in results.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
