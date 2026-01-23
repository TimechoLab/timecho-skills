#!/usr/bin/env python3
"""
TsFile Python Example

This example demonstrates how to write and read time series data using TsFile Python API.
Customize this template for your specific use case.
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta

try:
    from tsfile import ColumnSchema, TableSchema, Tablet
    from tsfile import TsFileTableWriter, TsFileReader, TSDataType, ColumnCategory
except ImportError:
    print("❌ TsFile Python library not found.")
    print("   Please build with: mvn -P with-cpp,with-python clean verify")
    sys.exit(1)

def generate_sample_data(num_devices=5, records_per_device=100):
    """
    Generate sample IoT sensor data

    TODO: Replace this with your actual data source
    """
    data = []
    base_time = datetime.now()

    for device_id in range(1, num_devices + 1):
        for i in range(records_per_device):
            timestamp = base_time + timedelta(seconds=i * 10)  # 10-second intervals

            # Simulate sensor readings with some variation
            temperature = 20.0 + device_id + (i % 20) * 0.5
            humidity = 50.0 + device_id * 2 + (i % 30) * 0.3
            pressure = 1013.25 + (i % 10) * 0.1
            battery_level = max(0, 100 - (i * 0.2))  # Decreasing battery

            data.append({
                'timestamp': timestamp,
                'device_id': f'sensor_{device_id:02d}',
                'location': f'zone_{device_id % 3 + 1}',
                'temperature': temperature,
                'humidity': humidity,
                'pressure': pressure,
                'battery_level': battery_level,
                'is_online': True if i % 50 != 0 else False  # Occasional offline status
            })

    return pd.DataFrame(data)

def write_tsfile_example(filename="example.tsfile"):
    """
    Write data to TsFile using the Python API

    TODO: Customize schema and data according to your requirements
    """
    print(f"📝 Writing data to {filename}...")

    # Define table schema
    # TODO: Modify these columns based on your data structure
    columns = [
        # Tag columns (identifiers/categories)
        ColumnSchema("device_id", TSDataType.STRING, ColumnCategory.TAG),
        ColumnSchema("location", TSDataType.STRING, ColumnCategory.TAG),

        # Field columns (measurements)
        ColumnSchema("temperature", TSDataType.DOUBLE, ColumnCategory.FIELD),
        ColumnSchema("humidity", TSDataType.DOUBLE, ColumnCategory.FIELD),
        ColumnSchema("pressure", TSDataType.DOUBLE, ColumnCategory.FIELD),
        ColumnSchema("battery_level", TSDataType.DOUBLE, ColumnCategory.FIELD),
        ColumnSchema("is_online", TSDataType.BOOLEAN, ColumnCategory.FIELD)
    ]

    table_schema = TableSchema("sensor_data", columns=columns)

    # Generate sample data
    # TODO: Replace with your actual data source
    df = generate_sample_data()

    # Write to TsFile
    with TsFileTableWriter(filename, table_schema) as writer:
        batch_size = 100  # TODO: Adjust batch size based on your memory constraints
        total_rows = len(df)

        print(f"   Writing {total_rows} records in batches of {batch_size}...")

        for start_idx in range(0, total_rows, batch_size):
            end_idx = min(start_idx + batch_size, total_rows)
            batch_df = df.iloc[start_idx:end_idx]

            # Create tablet for this batch
            tablet = Tablet(
                [col.name for col in columns],
                [col.data_type for col in columns],
                len(batch_df)
            )

            # Add data to tablet
            for i, (_, row) in enumerate(batch_df.iterrows()):
                # Convert timestamp to milliseconds
                timestamp_ms = int(row['timestamp'].timestamp() * 1000)
                tablet.add_timestamp(i, timestamp_ms)

                # Add values by column name
                # TODO: Modify based on your column names and types
                tablet.add_value_by_name("device_id", i, row['device_id'])
                tablet.add_value_by_name("location", i, row['location'])
                tablet.add_value_by_name("temperature", i, float(row['temperature']))
                tablet.add_value_by_name("humidity", i, float(row['humidity']))
                tablet.add_value_by_name("pressure", i, float(row['pressure']))
                tablet.add_value_by_name("battery_level", i, float(row['battery_level']))
                tablet.add_value_by_name("is_online", i, bool(row['is_online']))

            # Write the batch
            writer.write_table(tablet)

            print(f"   Wrote batch {start_idx//batch_size + 1}/{(total_rows-1)//batch_size + 1}")

    print(f"✅ Successfully wrote {total_rows} records to {filename}")

def read_tsfile_example(filename="example.tsfile"):
    """
    Read data from TsFile using the Python API

    TODO: Customize reading logic based on your analysis needs
    """
    print(f"📖 Reading data from {filename}...")

    if not os.path.exists(filename):
        print(f"❌ File {filename} not found. Run write example first.")
        return

    with TsFileReader(filename) as reader:
        # Get available tables
        tables = reader.get_table_names()
        print(f"   Found {len(tables)} table(s): {tables}")

        for table_name in tables:
            print(f"\n📊 Analyzing table: {table_name}")

            # Read entire table
            # TODO: Add time range filters if needed:
            # start_time = int(datetime(2024, 1, 1).timestamp() * 1000)
            # end_time = int(datetime(2024, 12, 31).timestamp() * 1000)
            # df = reader.read_table(table_name, start_time=start_time, end_time=end_time)

            df = reader.read_table(table_name)

            print(f"   Rows: {len(df)}")
            print(f"   Columns: {list(df.columns)}")

            if len(df) > 0:
                print(f"   Time range: {df.index.min()} to {df.index.max()}")

                # TODO: Add your specific analysis here
                print("\n   Sample data:")
                print(df.head(5).to_string())

                # Basic statistics
                print("\n   Numeric column statistics:")
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    print(df[numeric_cols].describe())

                # Device distribution (if applicable)
                if 'device_id' in df.columns:
                    print(f"\n   Records per device:")
                    device_counts = df['device_id'].value_counts()
                    print(device_counts)

def main():
    """
    Main example function

    TODO: Modify the workflow based on your needs
    """
    filename = "example_python.tsfile"

    # Clean up previous file
    if os.path.exists(filename):
        os.remove(filename)
        print(f"🗑️  Removed existing file: {filename}")

    try:
        # Write example data
        write_tsfile_example(filename)

        # Read and analyze the data
        read_tsfile_example(filename)

        print(f"\n🎉 TsFile example completed successfully!")
        print(f"   Generated file: {filename}")

    except Exception as e:
        print(f"❌ Error during TsFile operations: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())