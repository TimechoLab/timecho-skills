/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package com.example.iotdb;

import org.apache.iotdb.session.Session;
import org.apache.iotdb.session.SessionPool;
import org.apache.iotdb.isession.ITableSession;
import org.apache.iotdb.session.TableSessionBuilder;
import org.apache.iotdb.isession.SessionDataSet;
import org.apache.iotdb.tsfile.read.common.DataIterator;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;

import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.enums.ColumnCategory;
import org.apache.tsfile.file.metadata.enums.TSEncoding;
import org.apache.tsfile.file.metadata.enums.CompressionType;
import org.apache.tsfile.write.record.Tablet;
import org.apache.tsfile.write.schema.IMeasurementSchema;
import org.apache.tsfile.write.schema.MeasurementSchema;

import java.util.*;

/**
 * IoTDB Java Connection Template
 *
 * This template provides ready-to-use connection patterns for IoTDB:
 * - SessionPool connection (RECOMMENDED for production)
 * - Iterator-based data reading (CRITICAL for memory efficiency)
 * - Tree Model and Table Model examples
 * - Bulk insertion using tablets
 * - Error handling and retry patterns
 */
public class IoTDBConnectionTemplate {

    // Configuration
    private static final String HOST = "127.0.0.1";
    private static final int PORT = 6667;
    private static final String USERNAME = "root";
    private static final String PASSWORD = "root";

    /**
     * 🚀 RECOMMENDED: SessionPool connection example with iterator
     */
    public static void sessionPoolExample() {
        SessionPool sessionPool = new SessionPool.Builder()
            .host(HOST)
            .port(PORT)
            .user(USERNAME)
            .password(PASSWORD)
            .maxSize(10)  // Connection pool size
            .build();

        try {
            // Create database and timeseries
            sessionPool.createDatabase("root.example");

            sessionPool.createTimeseries(
                "root.example.device1.temperature",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                CompressionType.SNAPPY
            );

            sessionPool.createTimeseries(
                "root.example.device1.humidity",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                CompressionType.SNAPPY
            );

            // Insert single record
            sessionPool.insertRecord(
                "root.example.device1",
                System.currentTimeMillis(),
                Arrays.asList("temperature", "humidity"),
                Arrays.asList(TSDataType.FLOAT, TSDataType.FLOAT),
                Arrays.asList(25.5f, 60.0f)
            );

            // ⭐ CRITICAL: Always use iterator for reading data (memory efficient)
            try (SessionDataSet dataSet = sessionPool.executeQueryStatement(
                    "SELECT * FROM root.example.device1")) {

                DataIterator iterator = dataSet.iterator();
                System.out.println("Reading data with iterator:");
                System.out.println("Time\t\t\tTemperature\tHumidity");
                System.out.println("-".repeat(50));

                while (iterator.next()) {
                    long timestamp = iterator.getLong(1);
                    float temperature = iterator.getFloat(2);
                    float humidity = iterator.getFloat(3);

                    System.out.printf("%d\t%.2f\t\t%.2f%n",
                        timestamp, temperature, humidity);
                }
            } // Auto-close dataset

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        } finally {
            sessionPool.close();
        }
    }

    /**
     * Table Model connection example with iterator
     */
    public static void tableModelExample() {
        try (ITableSession session = new TableSessionBuilder()
                .nodeUrls(Collections.singletonList(HOST + ":" + PORT))
                .username(USERNAME)
                .password(PASSWORD)
                .build()) {

            // Create database and table
            session.executeNonQueryStatement("CREATE DATABASE example_db");
            session.executeNonQueryStatement("USE example_db");

            session.executeNonQueryStatement("""
                CREATE TABLE sensors(
                    region_id STRING TAG,
                    device_id STRING TAG,
                    device_type STRING ATTRIBUTE,
                    temperature FLOAT FIELD,
                    humidity DOUBLE FIELD
                ) WITH (TTL=7200000)
                """);

            // Insert data using tablet
            List<String> columnNames = Arrays.asList(
                "region_id", "device_id", "device_type", "temperature", "humidity"
            );

            List<TSDataType> dataTypes = Arrays.asList(
                TSDataType.STRING, TSDataType.STRING, TSDataType.STRING,
                TSDataType.FLOAT, TSDataType.DOUBLE
            );

            List<ColumnCategory> columnTypes = Arrays.asList(
                ColumnCategory.TAG, ColumnCategory.TAG, ColumnCategory.ATTRIBUTE,
                ColumnCategory.FIELD, ColumnCategory.FIELD
            );

            Tablet tablet = new Tablet("sensors", columnNames, dataTypes, columnTypes, 10);

            // Add sample data
            int rowIndex = tablet.getRowSize();
            tablet.addTimestamp(rowIndex, System.currentTimeMillis());
            tablet.addValue("region_id", rowIndex, "region_1");
            tablet.addValue("device_id", rowIndex, "device_001");
            tablet.addValue("device_type", rowIndex, "temperature_sensor");
            tablet.addValue("temperature", rowIndex, 25.5f);
            tablet.addValue("humidity", rowIndex, 60.0);

            session.insert(tablet);

            // ⭐ CRITICAL: Always use iterator for reading data
            try (SessionDataSet dataSet = session.executeQueryStatement(
                    "SELECT * FROM sensors WHERE region_id = 'region_1'")) {

                DataIterator iterator = dataSet.iterator();
                System.out.println("Table Model Results:");
                System.out.println("Region\tDevice\tType\t\tTemp\tHumidity");
                System.out.println("-".repeat(60));

                while (iterator.next()) {
                    String regionId = iterator.getString("region_id");
                    String deviceId = iterator.getString("device_id");
                    String deviceType = iterator.getString("device_type");
                    float temperature = iterator.getFloat("temperature");
                    double humidity = iterator.getDouble("humidity");

                    System.out.printf("%s\t%s\t%s\t%.1f\t%.1f%n",
                        regionId, deviceId, deviceType, temperature, humidity);
                }
            } // Auto-close dataset

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        }
    }

    /**
     * Alternative: Basic Session connection (SessionPool preferred)
     */
    public static void basicSessionExample() {
        Session session = new Session.Builder()
            .host(HOST)
            .port(PORT)
            .username(USERNAME)
            .password(PASSWORD)
            .build();

        try {
            // Connect
            session.open(false);
            System.out.println("Connected to IoTDB");

            // Create database
            session.createDatabase("root.basic_example");

            // Create timeseries
            session.createTimeseries(
                "root.basic_example.device1.temperature",
                TSDataType.FLOAT,
                TSEncoding.RLE,
                CompressionType.SNAPPY
            );

            // Insert single record
            session.insertRecord(
                "root.basic_example.device1",
                System.currentTimeMillis(),
                Arrays.asList("temperature"),
                Arrays.asList(TSDataType.FLOAT),
                Arrays.asList(25.5f)
            );

            // ⭐ CRITICAL: Always use iterator for reading data
            try (SessionDataSet dataSet = session.executeQueryStatement(
                    "SELECT * FROM root.basic_example.device1")) {

                DataIterator iterator = dataSet.iterator();
                System.out.println("Basic Session Results:");

                while (iterator.next()) {
                    System.out.printf("Time: %d, Temperature: %.2f%n",
                        iterator.getLong(1), iterator.getFloat(2));
                }
            } // Auto-close dataset

        } catch (IoTDBConnectionException | StatementExecutionException e) {
            System.err.println("Error: " + e.getMessage());
        } finally {
            try {
                session.close();
            } catch (IoTDBConnectionException e) {
                System.err.println("Error closing session: " + e.getMessage());
            }
        }
    }

    /**
     * Bulk data insertion using tablets (high performance)
     */
    public static void bulkInsertWithTablet() {
        SessionPool sessionPool = new SessionPool.Builder()
            .host(HOST)
            .port(PORT)
            .user(USERNAME)
            .password(PASSWORD)
            .maxSize(5)
            .build();

        try {
            // Create schema for tablet
            List<IMeasurementSchema> schemaList = new ArrayList<>();
            schemaList.add(new MeasurementSchema("temperature", TSDataType.FLOAT));
            schemaList.add(new MeasurementSchema("humidity", TSDataType.FLOAT));
            schemaList.add(new MeasurementSchema("pressure", TSDataType.FLOAT));

            int batchSize = 1000;
            Tablet tablet = new Tablet("root.example.bulk_device", schemaList, batchSize);

            // Generate bulk data
            long baseTime = System.currentTimeMillis();
            Random random = new Random();

            for (int i = 0; i < batchSize; i++) {
                int rowIndex = tablet.getRowSize();
                tablet.addTimestamp(rowIndex, baseTime + i * 1000);
                tablet.addValue("temperature", rowIndex, 20.0f + random.nextFloat() * 10);
                tablet.addValue("humidity", rowIndex, 40.0f + random.nextFloat() * 30);
                tablet.addValue("pressure", rowIndex, 1000.0f + random.nextFloat() * 100);
            }

            // Insert tablet (high performance)
            sessionPool.insertTablet(tablet);
            System.out.println("Bulk insert completed: " + batchSize + " records");

            // ⭐ CRITICAL: Query with iterator for memory efficiency
            try (SessionDataSet dataSet = sessionPool.executeQueryStatement(
                    "SELECT temperature, humidity, pressure FROM root.example.bulk_device LIMIT 10")) {

                DataIterator iterator = dataSet.iterator();
                System.out.println("Sample bulk data (first 10 records):");
                System.out.println("Temp\tHumid\tPress");
                System.out.println("-".repeat(30));

                while (iterator.next()) {
                    float temperature = iterator.getFloat(2);
                    float humidity = iterator.getFloat(3);
                    float pressure = iterator.getFloat(4);

                    System.out.printf("%.1f\t%.1f\t%.1f%n", temperature, humidity, pressure);
                }
            }

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        } finally {
            sessionPool.close();
        }
    }

    /**
     * Connection manager with retry logic
     */
    public static class ConnectionManager {
        private Session session;
        private final String host;
        private final int port;
        private final String username;
        private final String password;

        public ConnectionManager(String host, int port, String username, String password) {
            this.host = host;
            this.port = port;
            this.username = username;
            this.password = password;
        }

        public void connect() throws IoTDBConnectionException {
            session = new Session.Builder()
                .host(host)
                .port(port)
                .username(username)
                .password(password)
                .build();

            session.open(false);
        }

        public void connectWithRetry(int maxRetries, long delayMs) throws IoTDBConnectionException {
            Exception lastException = null;

            for (int i = 0; i < maxRetries; i++) {
                try {
                    connect();
                    return;  // Success
                } catch (IoTDBConnectionException e) {
                    lastException = e;
                    if (i < maxRetries - 1) {
                        try {
                            Thread.sleep(delayMs * (i + 1));  // Exponential backoff
                        } catch (InterruptedException ie) {
                            Thread.currentThread().interrupt();
                            throw new IoTDBConnectionException("Connection interrupted", ie);
                        }
                    }
                }
            }

            throw new IoTDBConnectionException("Failed to connect after " + maxRetries + " attempts", lastException);
        }

        public Session getSession() {
            return session;
        }

        public void close() {
            if (session != null) {
                try {
                    session.close();
                } catch (IoTDBConnectionException e) {
                    System.err.println("Error closing session: " + e.getMessage());
                }
            }
        }
    }

    public static void main(String[] args) {
        System.out.println("IoTDB Java Connection Examples");
        System.out.println("==============================");

        try {
            System.out.println("1. 🚀 RECOMMENDED: SessionPool Example:");
            sessionPoolExample();

            System.out.println("\n2. Table Model Example:");
            tableModelExample();

            System.out.println("\n3. Bulk Insert with Tablet:");
            bulkInsertWithTablet();

            System.out.println("\n4. Basic Session Example (Alternative):");
            basicSessionExample();

        } catch (Exception e) {
            System.err.println("Example error: " + e.getMessage());
        }
    }
}