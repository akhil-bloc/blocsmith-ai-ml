.PHONY: all intake expand write validate dedup top_up diversity bands split package lockcheck clean

PY = python

intake:
	$(PY) scripts/intake.py --out dist/intake.json

expand:
	$(PY) scripts/expand.py --in dist/intake.json --out dist/expanded.json

write:
	$(PY) scripts/write.py --in dist/expanded.json --out dist/written.jsonl --oversub 1.2 --seed 2025

validate:
	$(PY) scripts/validate.py --in dist/written.jsonl --schema schemas/golden.pre_split.schema.json --out dist/validated.jsonl

dedup:
	$(PY) scripts/dedup.py --in dist/validated.jsonl --out dist/deduped.jsonl --report dist/dedup_report.json --seed 2025

top_up:
	$(PY) scripts/top_up.py --in dist/deduped.jsonl --out dist/topped.jsonl --trace dist/top_up_trace.json --seed 2025

diversity:
	$(PY) scripts/diversity.py --in dist/topped.jsonl --report dist/diversity_report.json --enforce

bands:
	$(PY) scripts/bands.py --in dist/topped.jsonl --report dist/band_report.json --enforce

split:
	$(PY) scripts/split.py --in dist/topped.jsonl --splits dist/splits.json

package:
	$(PY) scripts/package.py --in dist/topped.jsonl --splits dist/splits.json --out-train dist/train.jsonl --out-val dist/val.jsonl --out-test dist/test.jsonl --out-all dist/golden.jsonl

lockcheck:
	$(PY) scripts/lockcheck.py --schemas schemas --reports dist/dedup_report.json,dist/diversity_report.json,dist/top_up_trace.json,dist/band_report.json --splits dist/splits.json --artifacts dist/train.jsonl,dist/val.jsonl,dist/test.jsonl,dist/golden.jsonl --out dist/golden.lock.json

all: intake expand write validate dedup top_up diversity bands split package lockcheck

clean:
	rm -f dist/*.json dist/*.jsonl
