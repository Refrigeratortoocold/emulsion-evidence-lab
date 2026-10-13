# Data provenance

`demo_documents.jsonl` contains four invented software fixtures. Their numbers
do not describe actual experiments, the maintainer's earlier research, or the
papers in the seed catalogue. `demo_gold.json` contains manually specified
expected values for those fixtures.

`paper_seed_catalog.csv` lists two real publications whose titles, DOIs and
source pages were checked on 13 October 2026. It contains bibliographic metadata
only. No paper texts have been downloaded, annotated or processed by this project.
The authors of those papers are not members of this project.

For your own inputs, use one JSON object per line:

```json
{"id":"your-paper-001","title":"Actual title","data_kind":"published","source_url":"https://doi.org/ACTUAL-DOI","text":"Text you have permission to process"}
```

Use `synthetic`, `published` or `user_owned` as `data_kind`. A published record
requires a source URL. Record DOI, licence, excerpt location and retrieval date
in your own corpus manifest. Keep restricted text in `private_data/`, which is
excluded from git. Publish a gold dataset only when its content licence permits it.

The seven output fields represent one observation per field, selected from a
supplied excerpt. Null means **not extracted**, rather than proof that a property
is absent or that the complete paper did not report it. Multiple formulations,
conditions, replicates, uncertainty and full-text tables need a future schema.
