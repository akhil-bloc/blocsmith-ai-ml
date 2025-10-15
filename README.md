# Golden Set Dataset Generation Pipeline

This repository contains a deterministic pipeline for generating the Golden Set dataset, consisting of 70 application specifications across 14 strata (7 archetypes × 2 complexities × 1 locale), with R=5 per stratum.

## Quickstart

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the entire pipeline:
   ```bash
   make all
   ```

4. Find outputs in the `dist/` directory:
   - Reports: `dedup_report.json`, `diversity_report.json`, `top_up_trace.json`, `band_report.json`
   - Splits: `splits.json` (+ digest)
   - Artifacts: `train.jsonl`, `val.jsonl`, `test.jsonl`, `golden.jsonl`
   - Lockfile: `golden.lock.json`

## Pipeline Stages

The pipeline consists of the following stages, each implemented as a separate script:

1. **intake**: Generate the initial set of strata (7 archetypes × 2 complexities × 1 locale)
2. **expand**: Assign rep and seq numbers to slots
3. **write**: Generate spec variants for each slot with oversubscription
4. **validate**: Validate specs against schema and additional checks
5. **dedup**: Remove near-duplicate specs using MinHash
6. **top_up**: Restore R=5 per stratum after deduplication
7. **diversity**: Ensure cluster diversity in the dataset
8. **bands**: Verify length band distribution
9. **split**: Split dataset into train/val/test
10. **package**: Create final dataset files
11. **lockcheck**: Verify dataset integrity and generate lockfile

Each stage can be run individually using the corresponding make target:

```bash
make intake
make expand
make write
make validate
make dedup
make top_up
make diversity
make bands
make split
make package
make lockcheck
```

## Dataset Specifications

- **Inventory & identity**:
  - Archetypes: blog, guestbook, chat, notes, dashboard, store, gallery
  - Complexities: MVP, Pro
  - Locale: en
  - R=5 per stratum, total N=70
  - slot_id format: `golden_{archetype}{complexity}{locale}_{platform}_rep{rep:02d}_seq{seq:03d}`

- **Length bands**:
  - SHORT: 250-400 tokens
  - STANDARD: 600-900 tokens
  - EXTENDED: 1100-1500 tokens
  - Global target mix: 14 SHORT / 42 STANDARD / 14 EXTENDED (±7 tolerance each)

- **Splits**:
  - train: 42 items
  - val: 14 items
  - test: 14 items

## Error Codes

The pipeline will fail with specific error codes in the following cases:

- `SCHEMA_ERR`: Schema validation failure
- `PLATFORM_ERR`: Platform rules violation
- `LANG_ERR`: Language confidence below threshold
- `PII_ERR`: Potential PII detected
- `STYLE_ERR`: Code style violations
- `DEDUP_DROP`: Near-duplicate items dropped
- `TOPUP_ERR`: Failed to top up strata to R=5
- `DIV_C_ERR`: Failed to achieve cluster diversity
- `DIV_H_ERR`: Failed to achieve Shannon diversity
- `BAND_MIX_ERR`: Band distribution does not meet global targets
- `SPLIT_ERR`: Split error
- `PKG_ERR`: Package error
- `LOCK_ERR`: Lockfile verification failure

## Determinism

The pipeline is designed to be fully deterministic when run with the default seed (2025). All randomized operations use this seed or a deterministic derivative to ensure reproducible results.

## Repository Structure

```
.
├─ README.md
├─ Makefile
├─ requirements.txt
├─ schemas/
│  ├─ golden.pre_split.schema.json
│  └─ golden.final.schema.json
├─ scripts/
│  ├─ intake.py
│  ├─ expand.py
│  ├─ write.py
│  ├─ validate.py
│  ├─ dedup.py
│  ├─ top_up.py
│  ├─ diversity.py
│  ├─ bands.py
│  ├─ split.py
│  ├─ package.py
│  └─ lockcheck.py
├─ golden/
│  ├─ templates/
│  │  ├─ h2_sections.md
│  │  ├─ acl_snippet.txt
│  │  ├─ archetype_kits.yaml
│  │  └─ wording_banks.yaml
│  └─ lib/
│     ├─ io_utils.py
│     ├─ text_norm.py
│     ├─ lang_pii_style.py
│     ├─ bands.py
│     ├─ minhash.py
│     ├─ tfidf_diversity.py
│     ├─ shannon.py
│     ├─ splits.py
│     └─ digest.py
└─ dist/  # generated outputs & reports
