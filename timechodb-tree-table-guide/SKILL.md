---
name: timechodb-tree-table-guide
description: Explain and select TimechoDB or Apache IoTDB Tree versus Table models. Use for hierarchical path design, TAG/ATTRIBUTE/FIELD mapping, device and measurement boundaries, model-specific SQL, schema migration planning, and deciding which model fits a workload.
metadata:
  version: "1.0.0"
  description_zh: >-
    树/表模型选型：层级路径设计、TAG/ATTRIBUTE/FIELD 映射、设备与测点边界、模型专属 SQL
compatibility: >
  The Table model and sql_dialect exist only in IoTDB/TimechoDB V2.0+; V1.3.x supports only
  the Tree model. Confirm the connected version before choosing a model.
---

# TimechoDB Tree and Table Models

Keep model choice explicit; do not translate syntax or metadata implicitly.

## Quick choice

- Choose **Tree** for hierarchical paths such as
  `root.<database>.<device>.<measurement>` and path-oriented operations.
- Choose **Table** (V2.0+ only) for relational tables with TAG, ATTRIBUTE,
  FIELD, and TIME columns and SQL-oriented analysis.
- Choose coexistence only after defining which model owns writes, how data is
  exposed to the other model, and which connected versions support that bridge.

## Minimal workflow

1. Confirm the connected version (the Table model requires V2.0+) and current
   SQL dialect.
2. Describe the source hierarchy or table schema without translating it yet.
3. Identify stable device identity, mutable attributes, measurements, and time
   semantics.
4. Select Tree or Table from the workload's write and query requirements.
5. Generate model-specific schema or SQL, using
   [syntax-comparison.md](references/syntax-comparison.md) as the baseline.
6. If migration or a cross-model view is requested, verify the exact feature and
   syntax against the target version before producing DDL.

## Core mapping

| Tree concept | Table concept | Important difference |
|---|---|---|
| `root.<database>` scope | Database | Names and lifecycle are model-specific. |
| Device path | One or more TAG columns | The mapping depends on the chosen path boundary. |
| Measurement leaf | FIELD column | Data type and nullability must be checked. |
| Timeseries tags | No automatic equivalent | Tree tags belong to timeseries metadata. |
| Timeseries attributes | No automatic equivalent | Table ATTRIBUTE columns belong to table rows/devices. |
| Timestamp | TIME column | Literal and precision semantics must be verified. |

## Tree query binding

A Tree timeseries path has this shape:

```text
root.<database>.<device>.<measurement>
```

For ordinary reads and aggregations, bind `FROM` to the device/path pattern and
project the measurement:

```sql
SELECT temperature FROM root.db.device1;
```

Do not assume that a full timeseries path is a ready-to-use `FROM` clause.

## Boundaries

- Do not infer Tree/Table dialect or CSV mapping from column names alone.
- Do not describe a Tree tag as equivalent to a Table TAG column without an
  explicit migration rule.
- Do not promise cross-model visibility, writable views, or automatic schema
  evolution without version-specific evidence.
- Do not mix Tree and Table DDL in one SQL source.

## References

- Read [tree-table-mapping.md](references/tree-table-mapping.md) to design an
  explicit mapping.
- Read [syntax-comparison.md](references/syntax-comparison.md) for conservative
  model-specific schema and query shapes.
