#!/usr/bin/env python3
"""
IoTDB Connection Validator

Checks connectivity to an IoTDB / TimechoDB node through:
  - the tree model RPC interface (SessionPool),
  - the table model RPC interface (TableSessionPool, server V2.0+),
  - the REST service (only if it is enabled on the server).

By default every check is read-only. --write-test additionally creates a uniquely named
database, writes and reads one row, and drops that database again.

Requires: pip install apache-iotdb==<server version> requests
"""

import argparse
import base64
import json
import sys
import time

import requests

from iotdb.SessionPool import PoolConfig, SessionPool
from iotdb.table_session_pool import TableSessionPool, TableSessionPoolConfig


def _rows(session, sql):
    rows = []
    with session.execute_query_statement(sql) as data_set:
        while data_set.has_next():
            rows.append(str(data_set.next()))
    return rows


def check_tree(args):
    pool = SessionPool(
        PoolConfig(host=args.host, port=str(args.port), user_name=args.username, password=args.password),
        1,
        5000,
    )
    try:
        session = pool.get_session()
        try:
            result = {
                "ok": True,
                "version": _rows(session, "SHOW VERSION"),
                "databases": len(_rows(session, "SHOW DATABASES")),
            }
            if args.write_test:
                database = f"root.validate_{int(time.time() * 1000)}"
                session.execute_non_query_statement(f"CREATE DATABASE {database}")
                try:
                    session.execute_non_query_statement(
                        f"INSERT INTO {database}.d1(timestamp, s1) VALUES (1, 1.0)"
                    )
                    result["write_test_rows"] = len(_rows(session, f"SELECT s1 FROM {database}.d1"))
                finally:
                    session.execute_non_query_statement(f"DELETE DATABASE {database}")
            return result
        finally:
            pool.put_back(session)
    except Exception as e:  # report every failure instead of stopping at the first one
        return {"ok": False, "error": str(e)}
    finally:
        pool.close()


def check_table(args):
    pool = TableSessionPool(
        TableSessionPoolConfig(
            node_urls=[f"{args.host}:{args.port}"],
            username=args.username,
            password=args.password,
            max_pool_size=1,
            wait_timeout_in_ms=5000,
        )
    )
    try:
        session = pool.get_session()
        try:
            result = {"ok": True, "databases": len(_rows(session, "SHOW DATABASES"))}
            if args.write_test:
                database = f"validate_{int(time.time() * 1000)}"
                session.execute_non_query_statement(f"CREATE DATABASE {database}")
                try:
                    session.execute_non_query_statement(
                        f"CREATE TABLE {database}.t1 (device_id STRING TAG, s1 DOUBLE FIELD)"
                    )
                    session.execute_non_query_statement(
                        f"INSERT INTO {database}.t1 (time, device_id, s1) VALUES (1, 'd1', 1.0)"
                    )
                    result["write_test_rows"] = len(_rows(session, f"SELECT * FROM {database}.t1"))
                finally:
                    session.execute_non_query_statement(f"DROP DATABASE {database}")
            return result
        finally:
            session.close()
    except Exception as e:
        return {"ok": False, "error": str(e), "hint": "the table model requires server V2.0+"}
    finally:
        pool.close()


def check_rest(args):
    base_url = f"http://{args.host}:{args.rest_port}"
    token = base64.b64encode(f"{args.username}:{args.password}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
    try:
        ping = requests.get(f"{base_url}/ping", timeout=5)
        response = requests.post(
            f"{base_url}/rest/v2/query", headers=headers, json={"sql": "SHOW VERSION"}, timeout=10
        )
        body = response.json()
        # auth errors use HTTP 600/603; statement errors carry a non-200 "code"
        ok = response.status_code == 200 and body.get("code", 200) == 200
        return {"ok": ok, "ping": ping.status_code, "status": response.status_code, "response": body}
    except requests.exceptions.RequestException as e:
        return {
            "ok": False,
            "error": str(e),
            "hint": "REST is disabled by default (enable_rest_service=true, rest_service_port)",
        }


def main():
    parser = argparse.ArgumentParser(description="Validate IoTDB connections")
    parser.add_argument("--host", default="127.0.0.1", help="IoTDB host")
    parser.add_argument("--port", type=int, default=6667, help="IoTDB RPC port")
    parser.add_argument("--rest-port", type=int, default=18080, help="IoTDB REST port")
    parser.add_argument("--username", default="root", help="Username")
    parser.add_argument("--password", default="root", help="Password")
    parser.add_argument("--skip-table", action="store_true", help="Skip the table model check")
    parser.add_argument("--skip-rest", action="store_true", help="Skip the REST check")
    parser.add_argument(
        "--write-test",
        action="store_true",
        help="Also create, write, read and drop a temporary database",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    results = {"tree": check_tree(args)}
    if not args.skip_table:
        results["table"] = check_table(args)
    if not args.skip_rest:
        results["rest"] = check_rest(args)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        for name, result in results.items():
            status = "OK  " if result.get("ok") else "FAIL"
            detail = {k: v for k, v in result.items() if k != "ok"}
            print(f"[{status}] {name}: {detail}")

    sys.exit(0 if all(r.get("ok") for r in results.values()) else 1)


if __name__ == "__main__":
    main()
