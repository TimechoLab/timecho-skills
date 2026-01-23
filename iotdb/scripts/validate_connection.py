#!/usr/bin/env python3
"""
IoTDB Connection Validator

This script validates connectivity to an IoTDB instance across different interfaces.
It tests Java Session, Python Session, and REST API connections.
"""

import sys
import time
import requests
import base64
import json
import subprocess
import tempfile
import os
from typing import Dict, List, Optional, Tuple


class IoTDBConnectionValidator:
    def __init__(self, host="127.0.0.1", port=6667, rest_port=18080,
                 username="root", password="root"):
        self.host = host
        self.port = port
        self.rest_port = rest_port
        self.username = username
        self.password = password
        self.results = {}

    def validate_python_connection(self) -> Dict:
        """Validate Python client connection"""
        print("Testing Python connection...")

        try:
            from iotdb.Session import Session
            from iotdb.utils.IoTDBConstants import TSDataType, TSEncoding
            from iotdb.utils.Tablet import Tablet

            session = Session(self.host, str(self.port), self.username, self.password)

            # Test connection
            start_time = time.time()
            session.open(False)
            connect_time = time.time() - start_time

            # Test basic operations
            test_db = "root.test_python_" + str(int(time.time()))

            # Create database
            session.set_storage_group(test_db)

            # Create timeseries
            session.create_time_series(
                f"{test_db}.device.temperature",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                None  # compressor
            )

            # Insert test data
            timestamp = int(time.time() * 1000)
            session.insert_record(
                f"{test_db}.device",
                timestamp,
                ["temperature"],
                [TSDataType.FLOAT],
                [25.5]
            )

            # Query test data
            result = session.execute_query_statement(f"SELECT * FROM {test_db}.device")
            has_data = result.has_next()
            if has_data:
                result.next()

            # Cleanup
            session.delete_storage_group(test_db)
            session.close()

            return {
                "status": "SUCCESS",
                "connect_time": round(connect_time, 3),
                "operations": {
                    "create_database": True,
                    "create_timeseries": True,
                    "insert_data": True,
                    "query_data": has_data
                }
            }

        except ImportError:
            return {
                "status": "FAILED",
                "error": "IoTDB Python client not installed (pip install apache-iotdb)"
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }

    def validate_rest_connection(self) -> Dict:
        """Validate REST API connection"""
        print("Testing REST API connection...")

        try:
            base_url = f"http://{self.host}:{self.rest_port}"

            # Test ping endpoint
            start_time = time.time()
            ping_response = requests.get(f"{base_url}/ping", timeout=5)
            ping_time = time.time() - start_time

            if ping_response.status_code != 200:
                return {
                    "status": "FAILED",
                    "error": f"Ping failed with status {ping_response.status_code}"
                }

            # Create auth header
            credentials = f"{self.username}:{self.password}"
            encoded_creds = base64.b64encode(credentials.encode()).decode()
            auth_header = f"Basic {encoded_creds}"

            headers = {
                "Content-Type": "application/json",
                "Authorization": auth_header
            }

            # Test database operations
            test_db = "root.test_rest_" + str(int(time.time()))

            # Create database
            create_db_response = requests.post(
                f"{base_url}/rest/v1/nonQuery",
                headers=headers,
                json={"sql": f"CREATE DATABASE {test_db}"},
                timeout=10
            )

            if create_db_response.status_code != 200:
                return {
                    "status": "FAILED",
                    "error": f"Create database failed: {create_db_response.text}"
                }

            # Create timeseries
            create_ts_response = requests.post(
                f"{base_url}/rest/v1/nonQuery",
                headers=headers,
                json={
                    "sql": f"CREATE TIMESERIES {test_db}.device.temperature WITH DATATYPE=FLOAT, ENCODING=RLE"
                },
                timeout=10
            )

            # Insert data using tablet
            timestamp = int(time.time() * 1000)
            insert_response = requests.post(
                f"{base_url}/rest/v1/insertTablet",
                headers=headers,
                json={
                    "deviceId": f"{test_db}.device",
                    "measurements": ["temperature"],
                    "dataTypes": ["FLOAT"],
                    "values": [[25.5]],
                    "timestamps": [timestamp],
                    "isAligned": False
                },
                timeout=10
            )

            # Query data
            query_response = requests.post(
                f"{base_url}/rest/v1/query",
                headers=headers,
                json={"sql": f"SELECT * FROM {test_db}.device"},
                timeout=10
            )

            has_data = False
            if query_response.status_code == 200:
                query_data = query_response.json()
                has_data = len(query_data.get("data", {}).get("values", [])) > 0

            # Cleanup
            requests.post(
                f"{base_url}/rest/v1/nonQuery",
                headers=headers,
                json={"sql": f"DELETE DATABASE {test_db}"},
                timeout=10
            )

            return {
                "status": "SUCCESS",
                "ping_time": round(ping_time, 3),
                "operations": {
                    "ping": ping_response.status_code == 200,
                    "create_database": create_db_response.status_code == 200,
                    "create_timeseries": create_ts_response.status_code == 200,
                    "insert_data": insert_response.status_code == 200,
                    "query_data": has_data
                }
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "FAILED",
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }

    def validate_java_connection(self) -> Dict:
        """Validate Java client connection (requires Java and IoTDB client JAR)"""
        print("Testing Java connection...")

        try:
            # Create temporary Java test file
            java_code = f"""
import org.apache.iotdb.session.Session;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;
import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.file.metadata.enums.TSEncoding;
import org.apache.tsfile.file.metadata.enums.CompressionType;
import java.util.Arrays;

public class ConnectionTest {{
    public static void main(String[] args) {{
        Session session = new Session.Builder()
            .host("{self.host}")
            .port({self.port})
            .username("{self.username}")
            .password("{self.password}")
            .build();

        try {{
            long startTime = System.currentTimeMillis();
            session.open(false);
            long connectTime = System.currentTimeMillis() - startTime;

            String testDb = "root.test_java_" + System.currentTimeMillis();

            // Create database
            session.createDatabase(testDb);

            // Create timeseries
            session.createTimeseries(
                testDb + ".device.temperature",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                CompressionType.SNAPPY
            );

            // Insert data
            session.insertRecord(
                testDb + ".device",
                System.currentTimeMillis(),
                Arrays.asList("temperature"),
                Arrays.asList(TSDataType.FLOAT),
                Arrays.asList(25.5f)
            );

            // Query data
            var dataSet = session.executeQueryStatement("SELECT * FROM " + testDb + ".device");
            boolean hasData = dataSet.hasNext();
            dataSet.close();

            // Cleanup
            session.deleteDatabase(testDb);
            session.close();

            System.out.println("SUCCESS:" + connectTime + ":" + hasData);

        }} catch (Exception e) {{
            System.err.println("FAILED:" + e.getMessage());
        }}
    }}
}}
"""

            with tempfile.TemporaryDirectory() as temp_dir:
                java_file = os.path.join(temp_dir, "ConnectionTest.java")
                with open(java_file, 'w') as f:
                    f.write(java_code)

                # Try to compile and run (requires IoTDB JAR in classpath)
                compile_cmd = ["javac", "-cp", ".:$IOTDB_CLIENT_JAR", java_file]
                run_cmd = ["java", "-cp", f".:$IOTDB_CLIENT_JAR:{temp_dir}", "ConnectionTest"]

                try:
                    subprocess.run(compile_cmd, check=True, capture_output=True, timeout=30)
                    result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=30)

                    if result.returncode == 0 and "SUCCESS" in result.stdout:
                        parts = result.stdout.strip().split(":")
                        return {
                            "status": "SUCCESS",
                            "connect_time": float(parts[1]) / 1000,  # Convert to seconds
                            "operations": {
                                "create_database": True,
                                "create_timeseries": True,
                                "insert_data": True,
                                "query_data": parts[2] == "true"
                            }
                        }
                    else:
                        return {
                            "status": "FAILED",
                            "error": result.stderr if result.stderr else "Unknown Java error"
                        }

                except subprocess.TimeoutExpired:
                    return {
                        "status": "FAILED",
                        "error": "Java test timed out"
                    }
                except subprocess.CalledProcessError as e:
                    return {
                        "status": "FAILED",
                        "error": f"Java compilation failed: {e.stderr.decode() if e.stderr else 'Unknown error'}"
                    }

        except Exception as e:
            return {
                "status": "FAILED",
                "error": f"Java test setup failed: {str(e)}"
            }

    def check_server_status(self) -> Dict:
        """Check if IoTDB server is running"""
        print("Checking server status...")

        # Try to connect to RPC port
        import socket

        rpc_status = False
        rest_status = False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.host, self.port))
            rpc_status = result == 0
            sock.close()
        except:
            pass

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.host, self.rest_port))
            rest_status = result == 0
            sock.close()
        except:
            pass

        return {
            "rpc_port_open": rpc_status,
            "rest_port_open": rest_status
        }

    def validate_all(self) -> Dict:
        """Validate all connection types"""
        print(f"Validating IoTDB connections to {self.host}:{self.port}")
        print("=" * 50)

        results = {
            "server": self.check_server_status(),
            "python": self.validate_python_connection(),
            "rest": self.validate_rest_connection(),
            "java": self.validate_java_connection()
        }

        return results

    def print_results(self, results: Dict):
        """Print validation results in a formatted way"""
        print("\n" + "=" * 50)
        print("VALIDATION RESULTS")
        print("=" * 50)

        # Server status
        server = results["server"]
        print(f"Server Status:")
        print(f"  RPC Port ({self.port}): {'✓ OPEN' if server['rpc_port_open'] else '✗ CLOSED'}")
        print(f"  REST Port ({self.rest_port}): {'✓ OPEN' if server['rest_port_open'] else '✗ CLOSED'}")
        print()

        # Connection tests
        for client_type, result in results.items():
            if client_type == "server":
                continue

            print(f"{client_type.upper()} Client:")
            if result["status"] == "SUCCESS":
                print("  Status: ✓ SUCCESS")
                if "connect_time" in result:
                    print(f"  Connection Time: {result['connect_time']}s")
                if "ping_time" in result:
                    print(f"  Ping Time: {result['ping_time']}s")

                if "operations" in result:
                    print("  Operations:")
                    for op, success in result["operations"].items():
                        status = "✓" if success else "✗"
                        print(f"    {op}: {status}")
            else:
                print("  Status: ✗ FAILED")
                print(f"  Error: {result['error']}")
            print()

        # Summary
        success_count = sum(1 for r in results.values()
                          if isinstance(r, dict) and r.get("status") == "SUCCESS")
        total_tests = len([k for k in results.keys() if k != "server"])

        print(f"Summary: {success_count}/{total_tests} connection types successful")

        if success_count == total_tests:
            print("✓ All connections working properly!")
        else:
            print("⚠ Some connections failed - check configuration and dependencies")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Validate IoTDB connections")
    parser.add_argument("--host", default="127.0.0.1", help="IoTDB host")
    parser.add_argument("--port", type=int, default=6667, help="IoTDB RPC port")
    parser.add_argument("--rest-port", type=int, default=18080, help="IoTDB REST port")
    parser.add_argument("--username", default="root", help="Username")
    parser.add_argument("--password", default="root", help="Password")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    validator = IoTDBConnectionValidator(
        host=args.host,
        port=args.port,
        rest_port=args.rest_port,
        username=args.username,
        password=args.password
    )

    try:
        results = validator.validate_all()

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            validator.print_results(results)

        # Exit with error code if any tests failed
        failed_tests = [k for k, v in results.items()
                       if k != "server" and isinstance(v, dict) and v.get("status") == "FAILED"]

        if failed_tests:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Validation error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()