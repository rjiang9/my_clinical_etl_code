#!/usr/bin/env bash


python src/clinical_etl/generate_schema.py --out tmp_template
diff tmp_template.csv moh_template.csv > tests/moh_diffs.txt
bytes=$(head -5 tests/moh_diffs.txt | wc -c)
dd if=tests/moh_diffs.txt  bs="$bytes" skip=1 conv=notrunc of=tests/moh_diffs1.txt
mv tests/moh_diffs1.txt tests/moh_diffs.txt
rm tmp_template.csv
