# REST API Reference for IoTDB

## Overview

IoTDB provides a RESTful HTTP API for cross-platform database access. The REST API uses JSON for data exchange and Basic Authentication for security.

## Base Configuration

- **Default Port**: 18080
- **Base URL**: `http://localhost:18080`
- **Authentication**: Basic Auth (username:password encoded in base64)
- **Content-Type**: `application/json`

## Authentication

### Generate Basic Auth Token

```bash
# Command line (Unix/Linux/macOS)
echo -n "username:password" | base64

# Example with default credentials
echo -n "root:root" | base64
# Output: cm9vdDpyb290
```

### Include in Request Headers

```bash
curl -H "Authorization: Basic cm9vdDpyb290" \
     -H "Content-Type: application/json" \
     http://127.0.0.1:18080/rest/v1/query
```

## API Endpoints

### 1. Health Check

Check if the IoTDB server is running.

**Endpoint**: `GET /ping`
**Authentication**: Not required

```bash
curl http://127.0.0.1:18080/ping
```

**Response**:
```json
{
  "status": "OK"
}
```

### 2. Execute Query

Execute SQL queries that return data (SELECT statements).

**Endpoint**: `POST /rest/v1/query`
**Authentication**: Required

**Request Body**:
```json
{
  "sql": "SELECT statement"
}
```

#### Examples

**Basic Query**:
```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{"sql": "SELECT * FROM root.factory.workshop1 LIMIT 10"}' \
     http://127.0.0.1:18080/rest/v1/query
```

**Time Range Query**:
```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{"sql": "SELECT temperature, humidity FROM root.factory.workshop1 WHERE time >= now() - 1h"}' \
     http://127.0.0.1:18080/rest/v1/query
```

**Aggregation Query**:
```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{"sql": "SELECT AVG(temperature), MAX(temperature) FROM root.factory.workshop1 GROUP BY ([now() - 1d, now()), 1h)"}' \
     http://127.0.0.1:18080/rest/v1/query
```

**Response**:
```json
{
  "code": 200,
  "message": "SUCCESS",
  "data": {
    "columnNames": ["Time", "root.factory.workshop1.temperature", "root.factory.workshop1.humidity"],
    "columnTypes": ["TIMESTAMP", "FLOAT", "FLOAT"],
    "values": [
      [1635232143960, 25.5, 60.0],
      [1635232153960, 26.0, 61.5],
      [1635232163960, 24.8, 58.2]
    ]
  }
}
```

### 3. Execute Non-Query

Execute DDL/DML statements that don't return data (CREATE, INSERT, UPDATE, DELETE).

**Endpoint**: `POST /rest/v1/nonQuery`
**Authentication**: Required

**Request Body**:
```json
{
  "sql": "DDL/DML statement"
}
```

#### Examples

**Create Database**:
```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{"sql": "CREATE DATABASE root.factory"}' \
     http://127.0.0.1:18080/rest/v1/nonQuery
```

**Create Timeseries**:
```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{"sql": "CREATE TIMESERIES root.factory.workshop1.temperature WITH DATATYPE=FLOAT, ENCODING=RLE"}' \
     http://127.0.0.1:18080/rest/v1/nonQuery
```

**Insert Data**:
```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{"sql": "INSERT INTO root.factory.workshop1(timestamp, temperature, humidity) VALUES(1635232143960, 25.5, 60.0)"}' \
     http://127.0.0.1:18080/rest/v1/nonQuery
```

**Response**:
```json
{
  "code": 200,
  "message": "SUCCESS"
}
```

### 4. Insert Tablet

Efficiently insert bulk data using tablet format.

**Endpoint**: `POST /rest/v1/insertTablet`
**Authentication**: Required

**Request Body**:
```json
{
  "deviceId": "device_path",
  "measurements": ["measurement1", "measurement2"],
  "dataTypes": ["FLOAT", "DOUBLE"],
  "values": [
    [value1_1, value1_2],
    [value2_1, value2_2]
  ],
  "timestamps": [timestamp1, timestamp2],
  "isAligned": false
}
```

#### Examples

**Single Device Tablet**:
```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{
       "deviceId": "root.factory.workshop1",
       "measurements": ["temperature", "humidity", "pressure"],
       "dataTypes": ["FLOAT", "FLOAT", "FLOAT"],
       "values": [
         [25.5, 60.0, 1013.25],
         [26.0, 61.5, 1012.80],
         [24.8, 58.2, 1014.10]
       ],
       "timestamps": [1635232143960, 1635232153960, 1635232163960],
       "isAligned": false
     }' \
     http://127.0.0.1:18080/rest/v1/insertTablet
```

**Aligned Timeseries Tablet**:
```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{
       "deviceId": "root.factory.aligned_device",
       "measurements": ["sensor1", "sensor2", "sensor3"],
       "dataTypes": ["FLOAT", "FLOAT", "FLOAT"],
       "values": [
         [25.0, 30.0, 35.0],
         [26.0, 31.0, 36.0]
       ],
       "timestamps": [1635232143960, 1635232153960],
       "isAligned": true
     }' \
     http://127.0.0.1:18080/rest/v1/insertTablet
```

**With Null Values**:
```bash
curl -H "Content-Type: application/json" \
     -H "Authorization: Basic cm9vdDpyb290" \
     -X POST \
     --data '{
       "deviceId": "root.factory.workshop2",
       "measurements": ["temperature", "humidity"],
       "dataTypes": ["FLOAT", "FLOAT"],
       "values": [
         [25.5, null],
         [null, 61.5]
       ],
       "timestamps": [1635232143960, 1635232153960],
       "isAligned": false
     }' \
     http://127.0.0.1:18080/rest/v1/insertTablet
```

**Response**:
```json
{
  "code": 200,
  "message": "SUCCESS"
}
```

## Data Types

Supported data types in REST API:

| IoTDB Type | JSON Type | Example |
|------------|-----------|---------|
| BOOLEAN    | boolean   | `true` |
| INT32      | number    | `123` |
| INT64      | number    | `123456789` |
| FLOAT      | number    | `25.5` |
| DOUBLE     | number    | `25.555555` |
| TEXT       | string    | `"hello"` |
| TIMESTAMP  | number    | `1635232143960` |

## Error Handling

### HTTP Status Codes

- **200**: Success
- **400**: Bad Request (invalid SQL or parameters)
- **401**: Unauthorized (invalid credentials)
- **500**: Internal Server Error

### Error Response Format

```json
{
  "code": 400,
  "message": "Error description",
  "data": null
}
```

### Common Errors

**Authentication Failed**:
```json
{
  "code": 401,
  "message": "Authentication failed"
}
```

**Invalid SQL**:
```json
{
  "code": 600,
  "message": "SQL parse error: line 1:8 mismatched input 'SELCT' expecting {'SELECT', 'WITH', 'INSERT', 'CREATE', 'DELETE', 'DROP', 'ALTER', 'FLUSH', 'MERGE', 'FULL', 'CLEAR', 'SET', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN', 'GRANT', 'REVOKE', 'LOAD', 'REMOVE', 'UNLOAD', 'KILL', 'START', 'STOP'}"
}
```

## Complete REST Client Examples

### Python REST Client

```python
import requests
import json
import base64
from datetime import datetime
import time

class IoTDBRestClient:
    def __init__(self, host="127.0.0.1", port=18080, username="root", password="root"):
        self.base_url = f"http://{host}:{port}"
        self.auth_header = self._create_auth_header(username, password)

    def _create_auth_header(self, username, password):
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"

    def _make_request(self, endpoint, data=None):
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.auth_header
        }

        if data:
            response = requests.post(f"{self.base_url}{endpoint}",
                                   headers=headers,
                                   json=data)
        else:
            response = requests.get(f"{self.base_url}{endpoint}",
                                  headers=headers)

        return response.json()

    def ping(self):
        """Health check"""
        response = requests.get(f"{self.base_url}/ping")
        return response.json()

    def query(self, sql):
        """Execute query statement"""
        data = {"sql": sql}
        return self._make_request("/rest/v1/query", data)

    def non_query(self, sql):
        """Execute non-query statement"""
        data = {"sql": sql}
        return self._make_request("/rest/v1/nonQuery", data)

    def insert_tablet(self, device_id, measurements, data_types, values, timestamps, is_aligned=False):
        """Insert tablet data"""
        data = {
            "deviceId": device_id,
            "measurements": measurements,
            "dataTypes": data_types,
            "values": values,
            "timestamps": timestamps,
            "isAligned": is_aligned
        }
        return self._make_request("/rest/v1/insertTablet", data)

# Example usage
def rest_client_example():
    client = IoTDBRestClient()

    # Health check
    print("Health check:", client.ping())

    # Create database and timeseries
    client.non_query("CREATE DATABASE root.factory")
    client.non_query("""
        CREATE TIMESERIES root.factory.workshop1.temperature
        WITH DATATYPE=FLOAT, ENCODING=RLE
    """)

    # Insert data using tablet
    timestamps = [int(time.time() * 1000) + i * 1000 for i in range(5)]
    values = [
        [20.0 + i for i in range(5)],  # temperatures
        [50.0 + i for i in range(5)]   # humidity
    ]

    result = client.insert_tablet(
        device_id="root.factory.workshop1",
        measurements=["temperature", "humidity"],
        data_types=["FLOAT", "FLOAT"],
        values=values,
        timestamps=timestamps
    )
    print("Insert result:", result)

    # Query data
    result = client.query("SELECT * FROM root.factory.workshop1 LIMIT 10")
    print("Query result:", json.dumps(result, indent=2))

if __name__ == "__main__":
    rest_client_example()
```

### JavaScript REST Client

```javascript
class IoTDBRestClient {
    constructor(host = "127.0.0.1", port = 18080, username = "root", password = "root") {
        this.baseUrl = `http://${host}:${port}`;
        this.authHeader = this.createAuthHeader(username, password);
    }

    createAuthHeader(username, password) {
        const credentials = `${username}:${password}`;
        const encodedCredentials = btoa(credentials);
        return `Basic ${encodedCredentials}`;
    }

    async makeRequest(endpoint, data = null) {
        const options = {
            method: data ? 'POST' : 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': this.authHeader
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, options);
        return await response.json();
    }

    async ping() {
        const response = await fetch(`${this.baseUrl}/ping`);
        return await response.json();
    }

    async query(sql) {
        return await this.makeRequest('/rest/v1/query', { sql });
    }

    async nonQuery(sql) {
        return await this.makeRequest('/rest/v1/nonQuery', { sql });
    }

    async insertTablet(deviceId, measurements, dataTypes, values, timestamps, isAligned = false) {
        const data = {
            deviceId,
            measurements,
            dataTypes,
            values,
            timestamps,
            isAligned
        };
        return await this.makeRequest('/rest/v1/insertTablet', data);
    }
}

// Example usage
async function restClientExample() {
    const client = new IoTDBRestClient();

    try {
        // Health check
        console.log("Health check:", await client.ping());

        // Create database
        await client.nonQuery("CREATE DATABASE root.factory");

        // Create timeseries
        await client.nonQuery(`
            CREATE TIMESERIES root.factory.workshop1.temperature
            WITH DATATYPE=FLOAT, ENCODING=RLE
        `);

        // Insert data
        const timestamps = Array.from({length: 5}, (_, i) => Date.now() + i * 1000);
        const values = [
            Array.from({length: 5}, (_, i) => 20.0 + i),  // temperatures
            Array.from({length: 5}, (_, i) => 50.0 + i)   // humidity
        ];

        const insertResult = await client.insertTablet(
            "root.factory.workshop1",
            ["temperature", "humidity"],
            ["FLOAT", "FLOAT"],
            values,
            timestamps
        );
        console.log("Insert result:", insertResult);

        // Query data
        const queryResult = await client.query("SELECT * FROM root.factory.workshop1 LIMIT 10");
        console.log("Query result:", JSON.stringify(queryResult, null, 2));

    } catch (error) {
        console.error("Error:", error);
    }
}

// Run example
restClientExample();
```

### Java REST Client

```java
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Base64;
import java.util.List;
import java.util.Arrays;
import com.google.gson.Gson;
import com.google.gson.JsonObject;

public class IoTDBRestClient {
    private final String baseUrl;
    private final String authHeader;
    private final HttpClient httpClient;
    private final Gson gson;

    public IoTDBRestClient(String host, int port, String username, String password) {
        this.baseUrl = String.format("http://%s:%d", host, port);
        this.authHeader = createAuthHeader(username, password);
        this.httpClient = HttpClient.newHttpClient();
        this.gson = new Gson();
    }

    private String createAuthHeader(String username, String password) {
        String credentials = username + ":" + password;
        String encodedCredentials = Base64.getEncoder().encodeToString(credentials.getBytes());
        return "Basic " + encodedCredentials;
    }

    public String ping() throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/ping"))
            .GET()
            .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    public String query(String sql) throws IOException, InterruptedException {
        JsonObject data = new JsonObject();
        data.addProperty("sql", sql);

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/rest/v1/query"))
            .header("Content-Type", "application/json")
            .header("Authorization", authHeader)
            .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(data)))
            .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    public String nonQuery(String sql) throws IOException, InterruptedException {
        JsonObject data = new JsonObject();
        data.addProperty("sql", sql);

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/rest/v1/nonQuery"))
            .header("Content-Type", "application/json")
            .header("Authorization", authHeader)
            .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(data)))
            .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    public static void main(String[] args) {
        IoTDBRestClient client = new IoTDBRestClient("127.0.0.1", 18080, "root", "root");

        try {
            // Health check
            System.out.println("Health check: " + client.ping());

            // Create database
            System.out.println(client.nonQuery("CREATE DATABASE root.factory"));

            // Query data
            System.out.println(client.query("SELECT * FROM root.factory.** LIMIT 5"));

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

## Performance Considerations

1. **Batch Operations**: Use tablet insertion for bulk data instead of individual records
2. **Connection Pooling**: Reuse HTTP connections for multiple requests
3. **Compression**: Enable gzip compression for large responses
4. **Pagination**: Use LIMIT and OFFSET for large result sets
5. **Timeout Configuration**: Set appropriate timeouts for long-running queries

## Security Best Practices

1. **Use HTTPS**: Configure SSL/TLS for production environments
2. **Strong Authentication**: Use strong passwords and consider external authentication
3. **Network Security**: Restrict access using firewalls and VPNs
4. **Input Validation**: Always validate and sanitize SQL inputs
5. **Rate Limiting**: Implement rate limiting to prevent abuse