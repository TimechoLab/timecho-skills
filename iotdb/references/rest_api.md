# REST API Reference for IoTDB

## Enable the Service

The REST service is **disabled by default**. On every DataNode that should serve REST, set in
`conf/iotdb-system.properties` and restart the DataNode:

```properties
enable_rest_service=true
# default 18080
rest_service_port=18080
```

| Model | Base path | Notes |
|-------|-----------|-------|
| Tree | `/rest/v2/` | Use v2 for new code (`/rest/v1/` still exists, with a different JSON format). |
| Table (V2.0+) | `/rest/table/v1/` | Every request names its `database`. |

## Authentication

All endpoints except `/ping` use HTTP Basic authentication:

```bash
echo -n "root:root" | base64      # cm9vdDpyb290
```

```
Authorization: Basic cm9vdDpyb290
Content-Type: application/json
```

Use the real password (TimechoDB V2.0.6.1+ defaults to `TimechoDB@2021`), and HTTPS or a trusted network:
Basic credentials are only base64-encoded.

## Health Check

```bash
curl http://127.0.0.1:18080/ping
```

## Tree Model (REST v2)

### Query

```bash
curl -H "Content-Type: application/json" -H "Authorization: Basic cm9vdDpyb290" \
     -X POST --data '{"sql": "SELECT temperature, humidity FROM root.factory.line1.device7 LIMIT 2"}' \
     http://127.0.0.1:18080/rest/v2/query
```

The response is column-oriented: `expressions` lists the selected timeseries, `timestamps` the row times, and
`values` holds one array per expression:

```json
{
  "expressions": ["root.factory.line1.device7.temperature", "root.factory.line1.device7.humidity"],
  "column_names": null,
  "timestamps": [1700000000000, 1700000001000],
  "values": [[25.5, 25.8], [60.0, 59.2]]
}
```

Metadata statements (`SHOW DATABASES`, `SHOW TIMESERIES`, ...) are also sent to `/rest/v2/query`; their results
use `column_names` instead of `expressions`.

### Non-Query (DDL / DML)

```bash
curl -H "Content-Type: application/json" -H "Authorization: Basic cm9vdDpyb290" \
     -X POST --data '{"sql": "CREATE DATABASE root.factory"}' \
     http://127.0.0.1:18080/rest/v2/nonQuery
```

### Insert Tablet

`values` is **column-oriented**: one array per measurement, aligned with `timestamps`.

```bash
curl -H "Content-Type: application/json" -H "Authorization: Basic cm9vdDpyb290" \
     -X POST --data '{
       "device": "root.factory.line1.device7",
       "is_aligned": false,
       "timestamps": [1700000000000, 1700000001000],
       "measurements": ["temperature", "humidity"],
       "data_types": ["FLOAT", "FLOAT"],
       "values": [[25.5, 25.8], [60.0, 59.2]]
     }' \
     http://127.0.0.1:18080/rest/v2/insertTablet
```

Use `null` for missing values.

## Table Model (REST `/rest/table/v1`)

### Query

```bash
curl -H "Content-Type: application/json" -H "Authorization: Basic cm9vdDpyb290" \
     -X POST --data '{"database": "factory", "sql": "SELECT time, device_id, temperature FROM sensors LIMIT 10"}' \
     http://127.0.0.1:18080/rest/table/v1/query
```

### Non-Query

```bash
curl -H "Content-Type: application/json" -H "Authorization: Basic cm9vdDpyb290" \
     -X POST --data '{"database": "", "sql": "CREATE DATABASE IF NOT EXISTS factory"}' \
     http://127.0.0.1:18080/rest/table/v1/nonQuery

curl -H "Content-Type: application/json" -H "Authorization: Basic cm9vdDpyb290" \
     -X POST --data '{"database": "factory", "sql": "CREATE TABLE IF NOT EXISTS sensors (device_id STRING TAG, model STRING ATTRIBUTE, temperature FLOAT FIELD)"}' \
     http://127.0.0.1:18080/rest/table/v1/nonQuery
```

### Insert Tablet

Here `values` is **row-oriented**: one array per row, in the order of `column_names`.
`column_categories` gives `TAG` / `ATTRIBUTE` / `FIELD` for each column; the time column is not listed.

```bash
curl -H "Content-Type: application/json" -H "Authorization: Basic cm9vdDpyb290" \
     -X POST --data '{
       "database": "factory",
       "table": "sensors",
       "column_names": ["device_id", "model", "temperature"],
       "column_categories": ["TAG", "ATTRIBUTE", "FIELD"],
       "data_types": ["STRING", "STRING", "FLOAT"],
       "timestamps": [1700000000000, 1700000001000],
       "values": [["d7", "A", 25.5], ["d7", "A", 25.8]]
     }' \
     http://127.0.0.1:18080/rest/table/v1/insertTablet
```

## Errors

Non-query requests and failures return a JSON body with `code` (an IoTDB status code) and `message`;
success is `{"code": 200, "message": "SUCCESS_STATUS"}`. Some errors use non-standard HTTP status codes:

| Response | Cause |
|----------|-------|
| HTTP `600`, `{"code":600,"message":"WRONG_LOGIN_PASSWORD_ERROR"}` | Wrong username or password |
| HTTP `603`, `{"code":603,"message":"UNINITIALIZED_AUTH_ERROR"}` | Missing `Authorization` header |
| Body `code` other than 200 (for example `407`) | Statement rejected by IoTDB; read `message` |
| Connection refused | REST not enabled on this DataNode, or wrong port |

Check the HTTP status **and** the body `code`; HTTP-library helpers such as `raise_for_status()` ignore 6xx.

## Python Client Sketch

```python
import base64

import requests


class IoTDBRest:
    def __init__(self, host="127.0.0.1", port=18080, username="root", password="root"):
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.base = f"http://{host}:{port}"
        self.http = requests.Session()
        self.http.headers.update(
            {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
        )

    def _post(self, path, body):
        response = self.http.post(self.base + path, json=body, timeout=30)
        result = response.json()
        # auth errors come back as HTTP 600/603; statement errors carry a non-200 "code"
        if response.status_code != 200 or result.get("code", 200) != 200:
            raise RuntimeError(f"IoTDB REST error {response.status_code}: {result}")
        return result

    # tree model
    def tree_query(self, sql):
        return self._post("/rest/v2/query", {"sql": sql})

    def tree_non_query(self, sql):
        return self._post("/rest/v2/nonQuery", {"sql": sql})

    # table model
    def table_query(self, database, sql):
        return self._post("/rest/table/v1/query", {"database": database, "sql": sql})

    def table_non_query(self, database, sql):
        return self._post("/rest/table/v1/nonQuery", {"database": database, "sql": sql})


client = IoTDBRest()
print(client.tree_query("SHOW DATABASES"))
```

## Performance Notes

- REST adds HTTP/JSON overhead; for high-throughput ingestion use the native pools
  (`SessionPool` / `TableSessionPool`).
- Batch rows into `insertTablet` requests instead of one request per row.
- Reuse HTTP connections (`requests.Session`, keep-alive).
