#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=pdf-fast-reprocess
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME

PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
    --local-input-path example-docs/english-and-korean.png \
    --structured-output-dir "$OUTPUT_DIR" \
    --partition-ocr-languages eng+kor \
    --verbose \
    --reprocess

set +e

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
