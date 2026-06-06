# Data Directory

`data/` now holds lightweight documentation and metadata only. Runtime question sources live in `questionlist/`, generated run outputs live under ignored local folders, and Final UI runtime data lives in ignored `final_UI/data/`.

## Current Layout

| Path | Role |
| --- | --- |
| `data/QUESTION_SETS.md` | Current question-set contract and dataset catalog notes |
| `questionlist/benchmark/` | Curated benchmark source CSV files |
| `questionlist/regression/` | Curated regression source CSV files |
| `final_UI/data/` | Local UI CSV/JSON runtime data, ignored by Git |

## Moved Out

Development/raw assets were moved out of the runtime package:

| Previous path | Current local archive |
| --- | --- |
| `data/raw/` | `_unused_files/runtime_cleanup_20260606/data/raw/` |
| `sources/bc_cs_notice/` | `_unused_files/runtime_cleanup_20260606/sources/bc_cs_notice/` |
| model notebooks and Modelfiles | `_unused_files/runtime_cleanup_20260606/model/` |

See `data/QUESTION_SETS.md` for the active benchmark/regression dataset contract.
