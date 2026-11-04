# Inspecting payment card data in Neo4j Browser

## 샘플로 카드 1~2개 확인하기 (기존 Neo4j 사용)

이미 실행 중인 Neo4j(컨테이너 `graphrag-neo4j`, 포트 7474/7687)를 그대로 씁니다. 새 컨테이너는 만들지 않습니다. 이 샘플은 `Fp` 접두사 라벨과 `FP_` 관계만 만들어서 기존 데이터와 섞이지 않습니다.

1. 샘플 만들기 (저장소 밖 `/tmp`에 생성):

```bash
cd /home/lee/workspace/mle-02-p2-team3
export UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit
uv run --locked --no-sync python -m payment_card.file_pipeline.graph.cypher_export --csv-dir /tmp/fp-check-hana --list-cards 20
uv run --locked --no-sync python -m payment_card.file_pipeline.graph.cypher_export --csv-dir /tmp/fp-check-hana --card-id <카드 id> --output /tmp/fp-sample-hana.cypher
```

2. 브라우저에서 <http://localhost:7474>를 열고 기존 계정으로 로그인합니다. 비밀번호는 `.env`의 `NEO4J_*` 값이며 이 문서에 쓰지 않습니다. 사용자가 직접 입력합니다.
3. 붙여 넣기 전에 기존 라벨을 확인합니다. `Fp`로 시작하는 라벨이 없어야 합니다. 다른 프로젝트 라벨이 보이는 것은 정상입니다.

```cypher
CALL db.labels();
```

4. `/tmp/fp-sample-hana.cypher` 파일 내용을 입력창에 붙여 넣고 실행합니다 (제약조건 → 노드 → 관계 → 근거 순서로 만들어집니다). 파일이 커서 붙여 넣기가 안 되면 터미널에서 실행합니다. `<비밀번호>`는 사용자가 직접 넣습니다.

```bash
cat /tmp/fp-sample-hana.cypher | docker exec -i graphrag-neo4j cypher-shell -u <사용자> -p '<비밀번호>'
```

5. `queries.cypher`의 샘플 확인용 질의를 위에서부터 하나씩 실행하고, 카드 노드를 더블클릭해 연결을 펼쳐 봅니다.
6. 확인이 끝나면 **`Fp` 라벨만** 지웁니다. 라벨 없는 전체 삭제는 다른 프로젝트 데이터까지 지우므로 쓰지 않습니다.

```cypher
MATCH (n) WHERE any(l IN labels(n) WHERE l STARTS WITH 'Fp') DETACH DELETE n;
```

Use the already running Neo4j shared by your local environment. Do not start another Neo4j instance. Open <http://localhost:7474> and enter the existing account at the Neo4j Browser login screen; this document does not store a password.

Before importing, run this first check:

```cypher
CALL db.labels()
```

Confirm that no returned label starts with `Fp`. This export uses only `Fp` node labels and `FP_` relationship types to keep this project's graph separate from other projects in the shared database.

## 1. Convert CSV files to Cypher

`graph/export.py` creates the CSV files in the selected folder.

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.graph.cypher_export --csv-dir /tmp/fp-check-hana --output /tmp/fp-check-hana/load.cypher
```

Keep the generated `load.cypher` outside the repository because it contains data.

## 2. Import data

Open `/tmp/fp-check-hana/load.cypher`, paste its contents into Neo4j Browser, and run it. The script uses constraints and `MERGE`, so rerunning the same data does not create duplicate nodes or relationships. APOC is not required.

String, number, boolean, and null node properties are stored as properties. Lists and objects are stored as JSON in `props_json`. Evidence for relationships is represented by `FpEvidence` nodes with an `edge_id` property. Example queries are in [queries.cypher](queries.cypher).

## 3. Reset this project's data

Only use the following reset, which deletes nodes carrying a label that starts with `Fp`. Never delete everything from the shared database.

```cypher
MATCH (n) WHERE any(l IN labels(n) WHERE l STARTS WITH 'Fp') DETACH DELETE n
```

## 주피터 노트북으로 확인

`notebooks/neo4j_sample_check.ipynb`를 열고 셀 0부터 셀 9까지 순서대로 실행합니다. 먼저 셀 3의 기존 `Fp` 라벨을 확인하고 셀 4의 정적 검사 결과가 모두 통과했는지 확인하세요. 실제 적재가 필요할 때만 셀 1에서 `WRITE=True`로 바꾼 뒤 셀 5를 실행합니다. 노트북을 저장하기 전 **Clear All Outputs**를 실행해 출력이 없는 상태로 저장합니다.
