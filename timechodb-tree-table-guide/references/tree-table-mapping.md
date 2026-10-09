# Tree-to-Table Mapping Checklist

Use this checklist to design a mapping. It does not claim that a specific server
version can create a cross-model view or perform the migration automatically.

## Source inventory

Record:

- the Tree database boundary;
- representative device paths;
- measurement names and data types;
- aligned versus non-aligned series;
- timeseries tags and attributes;
- timestamp precision and retention policy;
- path depth variations and optional nodes.

## Target decisions

Define:

- one Table database and table per stable device class;
- TAG columns that form device identity;
- ATTRIBUTE columns for device-level mutable metadata;
- FIELD columns for time-varying measurements;
- the TIME column's type and precision;
- handling for missing measurements, mixed data types, and variable path depth.

## Example conceptual mapping

```text
Tree:  root.factory.beijing.line1.device7.temperature
                 |       |     |       |
Table: region TAG, line TAG, device TAG, temperature FIELD
```

This is a design mapping, not executable DDL. Confirm whether `factory` is the
database boundary and whether every path has the same depth before generating a
schema.

## Metadata caveat

Tree tags and attributes are attached to timeseries metadata. Table TAG and
ATTRIBUTE columns participate in the table's device/row model. Copy them only
through an explicit, reviewed transformation.

## Migration validation

1. Compare source and target series/column counts.
2. Validate representative timestamps and values.
3. Check null behavior for missing measurements.
4. Verify device identity uniqueness.
5. Compare retention and precision semantics.
6. Keep the source unchanged until validation succeeds.
