#!/usr/bin/env python3
"""
TsFile utility script for common operations

This script provides utilities for working with TsFile format:
- Converting CSV to TsFile
- Reading TsFile metadata
- Basic validation operations
"""

import sys
import pandas as pd
import time
from pathlib import Path

def csv_to_tsfile(csv_path, tsfile_path, device_column="device", timestamp_column="timestamp"):
    """
    Convert CSV data to TsFile format

    Args:
        csv_path: Path to input CSV file
        tsfile_path: Path to output TsFile
        device_column: Name of device identifier column
        timestamp_column: Name of timestamp column
    """
    try:
        # Import TsFile after ensuring it's available
        from tsfile import ColumnSchema, TableSchema, Tablet
        from tsfile import TsFileTableWriter, TSDataType, ColumnCategory

        # Read CSV
        df = pd.read_csv(csv_path)

        if device_column not in df.columns:
            raise ValueError(f"Device column '{device_column}' not found in CSV")

        if timestamp_column not in df.columns:
            raise ValueError(f"Timestamp column '{timestamp_column}' not found in CSV")

        # Infer column types and create schema
        columns = []
        columns.append(ColumnSchema(device_column, TSDataType.STRING, ColumnCategory.TAG))

        for col in df.columns:
            if col in [device_column, timestamp_column]:
                continue

            dtype = df[col].dtype
            if pd.api.types.is_integer_dtype(dtype):
                tsfile_type = TSDataType.INT64
            elif pd.api.types.is_float_dtype(dtype):
                tsfile_type = TSDataType.DOUBLE
            elif pd.api.types.is_bool_dtype(dtype):
                tsfile_type = TSDataType.BOOLEAN
            else:
                tsfile_type = TSDataType.STRING

            columns.append(ColumnSchema(col, tsfile_type, ColumnCategory.FIELD))

        table_schema = TableSchema("data", columns=columns)

        # Write to TsFile
        with TsFileTableWriter(tsfile_path, table_schema) as writer:
            batch_size = 1000
            total_rows = len(df)

            for start_idx in range(0, total_rows, batch_size):
                end_idx = min(start_idx + batch_size, total_rows)
                batch_df = df.iloc[start_idx:end_idx]

                tablet = Tablet(
                    [col.name for col in columns],
                    [col.data_type for col in columns],
                    len(batch_df)
                )

                for i, (_, row) in enumerate(batch_df.iterrows()):
                    # Convert timestamp to milliseconds
                    if pd.api.types.is_datetime64_any_dtype(df[timestamp_column]):
                        timestamp_ms = int(pd.to_datetime(row[timestamp_column]).timestamp() * 1000)
                    else:
                        timestamp_ms = int(row[timestamp_column])

                    tablet.add_timestamp(i, timestamp_ms)

                    for col in columns:
                        if col.name == device_column:
                            tablet.add_value_by_name(col.name, i, str(row[col.name]))
                        elif col.name != timestamp_column:
                            value = row[col.name]
                            if pd.isna(value):
                                continue  # Skip null values
                            tablet.add_value_by_name(col.name, i, value)

                writer.write_table(tablet)

        print(f"Successfully converted {csv_path} to {tsfile_path}")
        print(f"Processed {total_rows} rows")

    except ImportError:
        print("Error: TsFile Python library not found. Please build with: mvn -P with-cpp,with-python clean verify")
        sys.exit(1)
    except Exception as e:
        print(f"Error converting CSV to TsFile: {e}")
        sys.exit(1)

def inspect_tsfile(tsfile_path):
    """
    Inspect TsFile and display metadata information

    Args:
        tsfile_path: Path to TsFile
    """
    try:
        from tsfile import TsFileReader

        with TsFileReader(tsfile_path) as reader:
            tables = reader.get_table_names()
            print(f"TsFile: {tsfile_path}")
            print(f"Number of tables: {len(tables)}")

            for table_name in tables:
                print(f"\nTable: {table_name}")
                df = reader.read_table(table_name)
                print(f"  Rows: {len(df)}")
                print(f"  Columns: {list(df.columns)}")

                if len(df) > 0:
                    print(f"  Time range: {df.index.min()} to {df.index.max()}")
                    print("  Sample data:")
                    print(df.head(3).to_string(max_cols=5))

    except ImportError:
        print("Error: TsFile Python library not found. Please build with: mvn -P with-cpp,with-python clean verify")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading TsFile: {e}")
        sys.exit(1)

def validate_tsfile(tsfile_path):
    """
    Validate TsFile format and check for common issues

    Args:
        tsfile_path: Path to TsFile
    """
    try:
        from tsfile import TsFileReader

        print(f"Validating TsFile: {tsfile_path}")

        # Check if file exists
        if not Path(tsfile_path).exists():
            print("❌ File does not exist")
            return False

        # Try to read the file
        start_time = time.time()
        with TsFileReader(tsfile_path) as reader:
            tables = reader.get_table_names()

            if not tables:
                print("❌ No tables found in TsFile")
                return False

            total_rows = 0
            for table_name in tables:
                df = reader.read_table(table_name)
                total_rows += len(df)

                # Check for timestamp ordering
                if len(df) > 1:
                    timestamps = df.index
                    if not timestamps.is_monotonic_increasing:
                        print(f"⚠️  Table {table_name}: Timestamps are not in ascending order")

        read_time = time.time() - start_time

        print(f"✅ TsFile validation successful")
        print(f"   Tables: {len(tables)}")
        print(f"   Total rows: {total_rows}")
        print(f"   Read time: {read_time:.2f}s")

        return True

    except ImportError:
        print("Error: TsFile Python library not found. Please build with: mvn -P with-cpp,with-python clean verify")
        return False
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("TsFile Utility Script")
        print("\nUsage:")
        print("  python example.py csv2tsfile <csv_file> <tsfile_output> [device_col] [timestamp_col]")
        print("  python example.py inspect <tsfile>")
        print("  python example.py validate <tsfile>")
        return

    command = sys.argv[1]

    if command == "csv2tsfile":
        if len(sys.argv) < 4:
            print("Usage: python example.py csv2tsfile <csv_file> <tsfile_output> [device_col] [timestamp_col]")
            return

        csv_path = sys.argv[2]
        tsfile_path = sys.argv[3]
        device_col = sys.argv[4] if len(sys.argv) > 4 else "device"
        timestamp_col = sys.argv[5] if len(sys.argv) > 5 else "timestamp"

        csv_to_tsfile(csv_path, tsfile_path, device_col, timestamp_col)

    elif command == "inspect":
        if len(sys.argv) < 3:
            print("Usage: python example.py inspect <tsfile>")
            return
        inspect_tsfile(sys.argv[2])

    elif command == "validate":
        if len(sys.argv) < 3:
            print("Usage: python example.py validate <tsfile>")
            return
        validate_tsfile(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        print("Available commands: csv2tsfile, inspect, validate")

if __name__ == "__main__":
    main()
