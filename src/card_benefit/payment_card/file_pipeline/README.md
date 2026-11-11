# file_pipeline

This candidate adds the core file processing path alongside the existing main-owned `graphrag-chatbot` prototype. The processing path is `doc_index` → `chunking` → `extraction` → `graph/export`. Graph export produces validated CSV files; database loading and chat integration are outside this candidate.

## Runtime inputs

Operators must provide issuer manifests, index inputs, and source PDFs under their configured data directories. This change does not add manifests, PDFs, backups, credentials, or generated results. Tests use synthetic fixtures.

## Modules

- `doc_index/`: normalize issuer manifests and build document indexes. Both Hana and Woori adapters are imported by the CLI.
- `chunking/`: create traceable chunks from indexed PDF inputs.
- `extraction/`: validate schemas, run extraction, resume batches, and inspect results. The CLI imports `eval.variance` and exposes `result_a`, so those modules are included.
- `graph/export.py`: validate chunk/result correspondence and publish graph CSV outputs.

See the module READMEs for their inputs and commands.
