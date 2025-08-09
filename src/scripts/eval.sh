#!/bin/bash
set -euo pipefail

# === Configuration ===
: "${OPENAI_API_KEY:?OPENAI_API_KEY is not set}"
: "${OPENAI_API_BASE:?OPENAI_API_BASE is not set}"

EVAL_DIR="evaluate"
OUTPUT_DIR="../outputs/evaluation"
DATA_DIR="../data"

MODEL_NAME="gpt-4"
DOCTOR_NAME="GPT-4"

REFERENCE_FILE="$DATA_DIR/patients.json"
OUTPUT_FILE="$OUTPUT_DIR/evaluation_iiyi_${MODEL_NAME}_5part.jsonl"
RESULT_PATH="$OUTPUT_DIR/evaluation_iiyi_${MODEL_NAME}_onestep.jsonl"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# === Functions ===
run_evaluation() {
  echo "Running evaluation for model: $MODEL_NAME"
  pushd "$EVAL_DIR" > /dev/null
  python eval.py \
    --model_name "$MODEL_NAME" \
    --openai_api_key "$OPENAI_API_KEY" \
    --openai_api_base "$OPENAI_API_BASE" \
    --evaluation_platform dialog \
    --eval_save_filepath "$OUTPUT_FILE" \
    --reference_diagnosis_filepath "$REFERENCE_FILE" \
    --doctor_names "$DOCTOR_NAME"
  popd > /dev/null
}

show_evaluation_results() {
  echo "Showing evaluation results..."
  python eval_show.py \
    --interactive_evaluation_result_path "$OUTPUT_FILE" \
    --onestep_evaluation_result_path "$RESULT_PATH"
}

# === Main Execution ===
run_evaluation
show_evaluation_results
