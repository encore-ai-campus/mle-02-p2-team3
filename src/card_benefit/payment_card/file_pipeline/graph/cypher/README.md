# Inspecting payment card data in Neo4j Browser

Use the already running Neo4j shared by your local environment. Do not start another Neo4j instance. Open <http://localhost:7474> and enter the existing account at the Neo4j Browser login screen; this document does not store a password.

Before importing, run this first check:

```cypher
CALL db.labels()
```

Confirm that no returned label starts with `Pf`. This export uses only `Pf` node labels and `PF_` relationship types to keep this project's graph separate from other projects in the shared database.

## 1. Convert CSV files to Cypher

`graph/export.py` creates the CSV files in the selected folder.

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.graph.cypher_export --csv-dir /tmp/pf-graph-out7 --output /tmp/pf-graph-out7/load.cypher
```

Keep the generated `load.cypher` outside the repository because it contains data.

## 2. Import data

Open `/tmp/pf-graph-out7/load.cypher`, paste its contents into Neo4j Browser, and run it. The script uses constraints and `MERGE`, so rerunning the same data does not create duplicate nodes or relationships. APOC is not required.

String, number, boolean, and null node properties are stored as properties. Lists and objects are stored as JSON in `props_json`. Evidence for relationships is represented by `PfEvidence` nodes with an `edge_id` property. Example queries are in [queries.cypher](queries.cypher).

## 3. Reset this project's data

Only use the following reset, which deletes nodes carrying a label that starts with `Pf`. Never delete everything from the shared database.

```cypher
MATCH (n) WHERE any(l IN labels(n) WHERE l STARTS WITH 'Pf') DETACH DELETE n
```
