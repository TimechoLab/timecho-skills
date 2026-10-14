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

import org.apache.iotdb.isession.ITableSession;
import org.apache.iotdb.isession.SessionDataSet;
import org.apache.iotdb.isession.pool.ITableSessionPool;
import org.apache.iotdb.isession.pool.SessionDataSetWrapper;
import org.apache.iotdb.rpc.IoTDBConnectionException;
import org.apache.iotdb.rpc.StatementExecutionException;
import org.apache.iotdb.session.pool.SessionPool;
import org.apache.iotdb.session.pool.TableSessionPoolBuilder;

import org.apache.tsfile.enums.ColumnCategory;
import org.apache.tsfile.enums.TSDataType;
import org.apache.tsfile.write.record.Tablet;
import org.apache.tsfile.write.schema.IMeasurementSchema;
import org.apache.tsfile.write.schema.MeasurementSchema;

import java.util.Arrays;
import java.util.List;

/**
 * IoTDB connection template (IoTDB/TimechoDB V2.0.x, dependency org.apache.iotdb:iotdb-session).
 *
 * <ul>
 *   <li>Tree model: one {@link SessionPool} per application.
 *   <li>Table model: one {@link ITableSessionPool} per application; borrow an {@link ITableSession}
 *       per unit of work and close it to return it to the pool.
 *   <li>Close every result set; close the pools on shutdown.
 * </ul>
 *
 * <p>Connection settings come from the environment: IOTDB_NODE_URLS (comma separated, default
 * 127.0.0.1:6667), IOTDB_USER (default root), IOTDB_PASSWORD (default root; TimechoDB V2.0.6.1+ uses
 * TimechoDB@2021).
 */
public final class JavaConnectionTemplate implements AutoCloseable {

    private final SessionPool treePool;
    private final ITableSessionPool tablePool;

    public JavaConnectionTemplate(List<String> nodeUrls, String user, String password, int maxSize) {
        this.treePool = new SessionPool.Builder()
            .nodeUrls(nodeUrls)
            .user(user)
            .password(password)
            .maxSize(maxSize)
            .waitToGetSessionTimeoutInMs(30_000)
            .build();
        // No default database here, so this pool can also run CREATE DATABASE.
        this.tablePool = new TableSessionPoolBuilder()
            .nodeUrls(nodeUrls)
            .user(user)
            .password(password)
            .maxSize(maxSize)
            .waitToGetSessionTimeoutInMs(30_000)
            .build();
    }

    public static JavaConnectionTemplate fromEnvironment() {
        String urls = System.getenv().getOrDefault("IOTDB_NODE_URLS", "127.0.0.1:6667");
        return new JavaConnectionTemplate(
            Arrays.asList(urls.split(",")),
            System.getenv().getOrDefault("IOTDB_USER", "root"),
            System.getenv().getOrDefault("IOTDB_PASSWORD", "root"),
            10);
    }

    // ---------------------------------------------------------------- tree model

    /** Writes rows of one device; timeseries are auto-created if they do not exist. */
    public void writeTree(String deviceId, long startTime, int rows)
            throws IoTDBConnectionException, StatementExecutionException {
        List<IMeasurementSchema> schemas = Arrays.asList(
            new MeasurementSchema("temperature", TSDataType.FLOAT),
            new MeasurementSchema("humidity", TSDataType.FLOAT));
        Tablet tablet = new Tablet(deviceId, schemas, 1000);
        for (int i = 0; i < rows; i++) {
            int row = tablet.getRowSize();
            tablet.addTimestamp(row, startTime + i * 1000L);
            tablet.addValue("temperature", row, 20.0f + (i % 100) / 10.0f);
            tablet.addValue("humidity", row, 60.0f);
            if (tablet.getRowSize() == tablet.getMaxRowNumber()) {
                treePool.insertTablet(tablet);
                tablet.reset();
            }
        }
        if (tablet.getRowSize() != 0) {
            treePool.insertTablet(tablet);
            tablet.reset();
        }
    }

    /** Reads a time range; the wrapper must be closed to return the session to the pool. */
    public int readTree(String deviceId, long from, long to)
            throws IoTDBConnectionException, StatementExecutionException {
        String sql = String.format(
            "SELECT temperature FROM %s WHERE time >= %d AND time < %d", deviceId, from, to);
        int count = 0;
        try (SessionDataSetWrapper wrapper = treePool.executeQueryStatement(sql)) {
            SessionDataSet.DataIterator it = wrapper.iterator();
            while (it.next()) {
                long time = it.getLong("Time");
                float temperature = it.getFloat(deviceId + ".temperature");
                count++;
            }
        }
        return count;
    }

    // ---------------------------------------------------------------- table model

    public void createTableSchema() throws IoTDBConnectionException, StatementExecutionException {
        try (ITableSession session = tablePool.getSession()) {
            session.executeNonQueryStatement("CREATE DATABASE IF NOT EXISTS factory");
            session.executeNonQueryStatement(
                "CREATE TABLE IF NOT EXISTS factory.sensors ("
                    + "region STRING TAG, device_id STRING TAG, model STRING ATTRIBUTE, "
                    + "temperature FLOAT FIELD, humidity DOUBLE FIELD) WITH (TTL=31536000000)");
        }
    }

    public void writeTable(String region, String deviceId, long startTime, int rows)
            throws IoTDBConnectionException, StatementExecutionException {
        List<String> columns = Arrays.asList("region", "device_id", "model", "temperature", "humidity");
        List<TSDataType> types = Arrays.asList(
            TSDataType.STRING, TSDataType.STRING, TSDataType.STRING, TSDataType.FLOAT, TSDataType.DOUBLE);
        List<ColumnCategory> categories = Arrays.asList(
            ColumnCategory.TAG, ColumnCategory.TAG, ColumnCategory.ATTRIBUTE,
            ColumnCategory.FIELD, ColumnCategory.FIELD);

        try (ITableSession session = tablePool.getSession()) {
            session.executeNonQueryStatement("USE factory");   // lasts until the session is returned
            Tablet tablet = new Tablet("sensors", columns, types, categories, 1000);
            for (int i = 0; i < rows; i++) {
                int row = tablet.getRowSize();
                tablet.addTimestamp(row, startTime + i * 1000L);
                tablet.addValue("region", row, region);
                tablet.addValue("device_id", row, deviceId);
                tablet.addValue("model", row, "A");
                tablet.addValue("temperature", row, 20.0f + (i % 100) / 10.0f);
                tablet.addValue("humidity", row, 60.0);
                if (tablet.getRowSize() == tablet.getMaxRowNumber()) {
                    session.insert(tablet);
                    tablet.reset();
                }
            }
            if (tablet.getRowSize() != 0) {
                session.insert(tablet);
                tablet.reset();
            }
        }
    }

    public int readTable(String region, long from)
            throws IoTDBConnectionException, StatementExecutionException {
        int count = 0;
        try (ITableSession session = tablePool.getSession();
             SessionDataSet dataSet = session.executeQueryStatement(
                 "SELECT time, device_id, temperature FROM factory.sensors "
                     + "WHERE region = '" + region + "' AND time >= " + from)) {
            SessionDataSet.DataIterator it = dataSet.iterator();
            while (it.next()) {
                long time = it.getLong("time");
                String deviceId = it.getString("device_id");
                count++;
            }
        }
        return count;
    }

    @Override
    public void close() {
        treePool.close();
        tablePool.close();
    }

    public static void main(String[] args) throws Exception {
        try (JavaConnectionTemplate iotdb = fromEnvironment()) {
            long now = System.currentTimeMillis();

            iotdb.writeTree("root.template.line1.device1", now, 100);
            System.out.println("tree rows: " + iotdb.readTree("root.template.line1.device1", now, now + 100_000));

            iotdb.createTableSchema();
            iotdb.writeTable("north", "d1", now, 100);
            System.out.println("table rows: " + iotdb.readTable("north", now));
        }
    }
}
