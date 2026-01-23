#!/usr/bin/env python3
"""
IoTDB Performance Benchmark Tool

This script benchmarks IoTDB connection and operations performance across
different client interfaces and data insertion methods.
"""

import time
import statistics
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple
import random


class IoTDBPerformanceTester:
    def __init__(self, host="127.0.0.1", port=6667, rest_port=18080,
                 username="root", password="root"):
        self.host = host
        self.port = port
        self.rest_port = rest_port
        self.username = username
        self.password = password
        self.results = {}

    def benchmark_python_session(self, num_records=1000, batch_size=100) -> Dict:
        """Benchmark Python session performance"""
        print(f"Benchmarking Python Session ({num_records} records, batch size {batch_size})...")

        try:
            from iotdb.Session import Session
            from iotdb.utils.IoTDBConstants import TSDataType, TSEncoding
            from iotdb.utils.Tablet import Tablet

            session = Session(self.host, str(self.port), self.username, self.password)

            # Connection timing
            start_time = time.time()
            session.open(False)
            connect_time = time.time() - start_time

            test_db = f"root.perf_test_{int(time.time())}"

            # Setup
            session.set_storage_group(test_db)
            session.create_time_series(
                f"{test_db}.device.temperature",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                None
            )
            session.create_time_series(
                f"{test_db}.device.humidity",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                None
            )

            # Single record insertion benchmark
            single_insert_times = []
            base_time = int(time.time() * 1000)

            for i in range(min(100, num_records)):  # Limit single inserts
                start = time.time()
                session.insert_record(
                    f"{test_db}.device",
                    base_time + i,
                    ["temperature"],
                    [TSDataType.FLOAT],
                    [20.0 + random.random() * 10]
                )
                single_insert_times.append(time.time() - start)

            # Batch insertion benchmark (using tablet)
            batch_times = []
            remaining_records = num_records - len(single_insert_times)

            while remaining_records > 0:
                current_batch = min(batch_size, remaining_records)

                measurements = ["temperature", "humidity"]
                data_types = [TSDataType.FLOAT, TSDataType.FLOAT]
                values = [
                    [20.0 + random.random() * 10 for _ in range(current_batch)],
                    [40.0 + random.random() * 20 for _ in range(current_batch)]
                ]
                timestamps = [base_time + len(single_insert_times) + i for i in range(current_batch)]

                tablet = Tablet(f"{test_db}.device", measurements, data_types, values, timestamps)

                start = time.time()
                session.insert_tablet(tablet)
                batch_times.append(time.time() - start)

                remaining_records -= current_batch
                base_time += current_batch

            # Query benchmark
            query_times = []
            for i in range(5):  # 5 query runs
                start = time.time()
                result = session.execute_query_statement(f"SELECT * FROM {test_db}.device")
                count = 0
                while result.has_next() and count < 1000:  # Limit to avoid memory issues
                    result.next()
                    count += 1
                query_times.append(time.time() - start)

            # Cleanup
            session.delete_storage_group(test_db)
            session.close()

            return {
                "status": "SUCCESS",
                "connect_time": connect_time,
                "single_insert": {
                    "count": len(single_insert_times),
                    "avg_time": statistics.mean(single_insert_times),
                    "min_time": min(single_insert_times),
                    "max_time": max(single_insert_times),
                    "records_per_second": len(single_insert_times) / sum(single_insert_times)
                },
                "batch_insert": {
                    "batch_count": len(batch_times),
                    "avg_batch_time": statistics.mean(batch_times) if batch_times else 0,
                    "total_time": sum(batch_times),
                    "records_per_second": (num_records - len(single_insert_times)) / sum(batch_times) if batch_times else 0
                },
                "query": {
                    "runs": len(query_times),
                    "avg_time": statistics.mean(query_times),
                    "min_time": min(query_times),
                    "max_time": max(query_times)
                }
            }

        except ImportError:
            return {"status": "FAILED", "error": "IoTDB Python client not installed"}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    def benchmark_rest_api(self, num_records=1000, batch_size=100) -> Dict:
        """Benchmark REST API performance"""
        print(f"Benchmarking REST API ({num_records} records, batch size {batch_size})...")

        try:
            import requests
            import base64

            base_url = f"http://{self.host}:{self.rest_port}"
            credentials = f"{self.username}:{self.password}"
            encoded_creds = base64.b64encode(credentials.encode()).decode()
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {encoded_creds}"
            }

            # Connection timing (ping test)
            start_time = time.time()
            ping_response = requests.get(f"{base_url}/ping", timeout=5)
            connect_time = time.time() - start_time

            if ping_response.status_code != 200:
                return {"status": "FAILED", "error": "Ping failed"}

            test_db = f"root.perf_rest_{int(time.time())}"

            # Setup
            requests.post(f"{base_url}/rest/v1/nonQuery",
                         headers=headers,
                         json={"sql": f"CREATE DATABASE {test_db}"},
                         timeout=10)

            requests.post(f"{base_url}/rest/v1/nonQuery",
                         headers=headers,
                         json={"sql": f"CREATE TIMESERIES {test_db}.device.temperature WITH DATATYPE=FLOAT, ENCODING=RLE"},
                         timeout=10)

            requests.post(f"{base_url}/rest/v1/nonQuery",
                         headers=headers,
                         json={"sql": f"CREATE TIMESERIES {test_db}.device.humidity WITH DATATYPE=FLOAT, ENCODING=RLE"},
                         timeout=10)

            # Single record insertion benchmark (using SQL)
            single_insert_times = []
            base_time = int(time.time() * 1000)

            for i in range(min(50, num_records)):  # Limit single inserts for REST
                temp_value = 20.0 + random.random() * 10
                sql = f"INSERT INTO {test_db}.device(timestamp, temperature) VALUES({base_time + i}, {temp_value})"

                start = time.time()
                response = requests.post(f"{base_url}/rest/v1/nonQuery",
                                       headers=headers,
                                       json={"sql": sql},
                                       timeout=10)
                single_insert_times.append(time.time() - start)

                if response.status_code != 200:
                    break

            # Batch insertion benchmark (using tablet)
            batch_times = []
            remaining_records = num_records - len(single_insert_times)

            while remaining_records > 0:
                current_batch = min(batch_size, remaining_records)

                timestamps = [base_time + len(single_insert_times) + i for i in range(current_batch)]
                temp_values = [20.0 + random.random() * 10 for _ in range(current_batch)]
                humidity_values = [40.0 + random.random() * 20 for _ in range(current_batch)]

                tablet_data = {
                    "deviceId": f"{test_db}.device",
                    "measurements": ["temperature", "humidity"],
                    "dataTypes": ["FLOAT", "FLOAT"],
                    "values": [temp_values, humidity_values],
                    "timestamps": timestamps,
                    "isAligned": False
                }

                start = time.time()
                response = requests.post(f"{base_url}/rest/v1/insertTablet",
                                       headers=headers,
                                       json=tablet_data,
                                       timeout=30)
                batch_times.append(time.time() - start)

                if response.status_code != 200:
                    break

                remaining_records -= current_batch
                base_time += current_batch

            # Query benchmark
            query_times = []
            for i in range(3):  # Fewer query runs for REST
                start = time.time()
                response = requests.post(f"{base_url}/rest/v1/query",
                                       headers=headers,
                                       json={"sql": f"SELECT * FROM {test_db}.device LIMIT 100"},
                                       timeout=30)
                query_times.append(time.time() - start)

            # Cleanup
            requests.post(f"{base_url}/rest/v1/nonQuery",
                         headers=headers,
                         json={"sql": f"DELETE DATABASE {test_db}"},
                         timeout=10)

            return {
                "status": "SUCCESS",
                "connect_time": connect_time,
                "single_insert": {
                    "count": len(single_insert_times),
                    "avg_time": statistics.mean(single_insert_times) if single_insert_times else 0,
                    "min_time": min(single_insert_times) if single_insert_times else 0,
                    "max_time": max(single_insert_times) if single_insert_times else 0,
                    "records_per_second": len(single_insert_times) / sum(single_insert_times) if single_insert_times else 0
                },
                "batch_insert": {
                    "batch_count": len(batch_times),
                    "avg_batch_time": statistics.mean(batch_times) if batch_times else 0,
                    "total_time": sum(batch_times),
                    "records_per_second": (num_records - len(single_insert_times)) / sum(batch_times) if batch_times else 0
                },
                "query": {
                    "runs": len(query_times),
                    "avg_time": statistics.mean(query_times) if query_times else 0,
                    "min_time": min(query_times) if query_times else 0,
                    "max_time": max(query_times) if query_times else 0
                }
            }

        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    def benchmark_concurrent_connections(self, num_threads=5, operations_per_thread=100) -> Dict:
        """Benchmark concurrent connection performance"""
        print(f"Benchmarking concurrent connections ({num_threads} threads, {operations_per_thread} ops each)...")

        try:
            from iotdb.Session import Session
            from iotdb.utils.IoTDBConstants import TSDataType

            def worker_thread(thread_id):
                session = Session(self.host, str(self.port), self.username, self.password)
                results = {"connect_time": 0, "operations": 0, "errors": 0}

                try:
                    # Connection timing
                    start = time.time()
                    session.open(False)
                    results["connect_time"] = time.time() - start

                    test_device = f"root.concurrent_test.thread_{thread_id}"

                    # Perform operations
                    for i in range(operations_per_thread):
                        try:
                            session.insert_record(
                                test_device,
                                int(time.time() * 1000) + i,
                                ["value"],
                                [TSDataType.FLOAT],
                                [float(i)]
                            )
                            results["operations"] += 1
                        except Exception:
                            results["errors"] += 1

                    session.close()

                except Exception as e:
                    results["error"] = str(e)

                return results

            # Run concurrent threads
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(worker_thread, i) for i in range(num_threads)]
                thread_results = [future.result() for future in as_completed(futures)]

            total_time = time.time() - start_time

            # Aggregate results
            total_operations = sum(r["operations"] for r in thread_results)
            total_errors = sum(r["errors"] for r in thread_results)
            connect_times = [r["connect_time"] for r in thread_results if "connect_time" in r]

            return {
                "status": "SUCCESS",
                "threads": num_threads,
                "total_time": total_time,
                "operations_per_second": total_operations / total_time,
                "total_operations": total_operations,
                "total_errors": total_errors,
                "avg_connect_time": statistics.mean(connect_times) if connect_times else 0,
                "success_rate": (total_operations / (total_operations + total_errors)) * 100 if (total_operations + total_errors) > 0 else 0
            }

        except ImportError:
            return {"status": "FAILED", "error": "IoTDB Python client not installed"}
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}

    def run_all_benchmarks(self, num_records=1000, batch_size=100, concurrent_threads=5) -> Dict:
        """Run all performance benchmarks"""
        print(f"Starting IoTDB Performance Benchmarks")
        print(f"Target: {self.host}:{self.port}")
        print(f"Records: {num_records}, Batch Size: {batch_size}")
        print("=" * 60)

        results = {
            "config": {
                "host": self.host,
                "port": self.port,
                "num_records": num_records,
                "batch_size": batch_size,
                "concurrent_threads": concurrent_threads,
                "timestamp": int(time.time())
            },
            "python_session": self.benchmark_python_session(num_records, batch_size),
            "rest_api": self.benchmark_rest_api(num_records, batch_size),
            "concurrent": self.benchmark_concurrent_connections(concurrent_threads, 100)
        }

        return results

    def print_results(self, results: Dict):
        """Print benchmark results in a formatted way"""
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)

        config = results["config"]
        print(f"Configuration:")
        print(f"  Host: {config['host']}:{config['port']}")
        print(f"  Records: {config['num_records']}")
        print(f"  Batch Size: {config['batch_size']}")
        print()

        for test_name, result in results.items():
            if test_name == "config":
                continue

            print(f"{test_name.replace('_', ' ').title()}:")
            if result["status"] == "SUCCESS":
                if test_name == "concurrent":
                    print(f"  Threads: {result['threads']}")
                    print(f"  Operations/sec: {result['operations_per_second']:.2f}")
                    print(f"  Success Rate: {result['success_rate']:.1f}%")
                    print(f"  Avg Connect Time: {result['avg_connect_time']:.3f}s")
                else:
                    print(f"  Connect Time: {result['connect_time']:.3f}s")

                    if "single_insert" in result:
                        si = result["single_insert"]
                        print(f"  Single Insert: {si['records_per_second']:.2f} records/sec")
                        print(f"    Avg: {si['avg_time']:.3f}s, Min: {si['min_time']:.3f}s, Max: {si['max_time']:.3f}s")

                    if "batch_insert" in result:
                        bi = result["batch_insert"]
                        print(f"  Batch Insert: {bi['records_per_second']:.2f} records/sec")
                        print(f"    Batches: {bi['batch_count']}, Avg Time: {bi['avg_batch_time']:.3f}s")

                    if "query" in result:
                        q = result["query"]
                        print(f"  Query: {q['avg_time']:.3f}s average")
                        print(f"    Min: {q['min_time']:.3f}s, Max: {q['max_time']:.3f}s")
            else:
                print(f"  Status: FAILED - {result['error']}")
            print()

        # Performance summary
        print("Performance Summary:")
        successful_tests = [k for k, v in results.items()
                          if k != "config" and v.get("status") == "SUCCESS"]

        if "python_session" in successful_tests:
            py_result = results["python_session"]
            batch_perf = py_result["batch_insert"]["records_per_second"]
            print(f"  Python Batch Performance: {batch_perf:.2f} records/sec")

        if "rest_api" in successful_tests:
            rest_result = results["rest_api"]
            batch_perf = rest_result["batch_insert"]["records_per_second"]
            print(f"  REST API Batch Performance: {batch_perf:.2f} records/sec")

        if "concurrent" in successful_tests:
            conc_result = results["concurrent"]
            print(f"  Concurrent Performance: {conc_result['operations_per_second']:.2f} ops/sec")

        print(f"\nTotal Tests: {len(successful_tests)}/{len(results) - 1} successful")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="IoTDB Performance Benchmark")
    parser.add_argument("--host", default="127.0.0.1", help="IoTDB host")
    parser.add_argument("--port", type=int, default=6667, help="IoTDB RPC port")
    parser.add_argument("--rest-port", type=int, default=18080, help="IoTDB REST port")
    parser.add_argument("--username", default="root", help="Username")
    parser.add_argument("--password", default="root", help="Password")
    parser.add_argument("--records", type=int, default=1000, help="Number of records to insert")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for bulk operations")
    parser.add_argument("--threads", type=int, default=5, help="Number of concurrent threads")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    tester = IoTDBPerformanceTester(
        host=args.host,
        port=args.port,
        rest_port=args.rest_port,
        username=args.username,
        password=args.password
    )

    try:
        results = tester.run_all_benchmarks(
            num_records=args.records,
            batch_size=args.batch_size,
            concurrent_threads=args.threads
        )

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            tester.print_results(results)

        # Exit with error code if any tests failed
        failed_tests = [k for k, v in results.items()
                       if k != "config" and v.get("status") == "FAILED"]

        if failed_tests:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Benchmark error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()