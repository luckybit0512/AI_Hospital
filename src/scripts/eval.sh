#!/bin/bash

# === Configuration ===
export OPENAI_API_KEY=""
export OPENAI_API_BASE=""

EVAL_DIR="evaluate"
OUTPUT_DIR="../outputs/evaluation"
DATA_DIR="../data"

MODEL_NAME="gpt-4"
DOCTOR_NAME="GPT-4"

REFERENCE_FILE="$DATA_DIR/patients.json"
OUTPUT_FILE="$OUTPUT_DIR/evaluation_iiyi_${MODEL_NAME}_5part.jsonl"
RESULT_PATH="$OUTPUT_DIR/evaluation_iiyi_${MODEL_NAME}_onestep.jsonl"


# === Run Evaluation ===
run_evaluation() {
  echo "Running evaluation for model: $MODEL_NAME"
  (
    cd "$EVAL_DIR" || exit
    python eval.py \
      --model_name "$MODEL_NAME" \
      --openai_api_key "$OPENAI_API_KEY" \
      --openai_api_base "$OPENAI_API_BASE" \
      --evaluation_platform dialog \
      --eval_save_filepath "$OUTPUT_FILE" \
      --reference_diagnosis_filepath "$REFERENCE_FILE" \
      --doctor_names "$DOCTOR_NAME"
  )
}


# === Show Evaluation Results ===
show_evaluation_results() {
  echo "Showing evaluation results..."
  python eval_show.py \
    --interactive_evaluation_result_path "$OUTPUT_FILE" \
    --onestep_evaluation_result_path "$RESULT_PATH"
}


# === Execute Steps ===
run_evaluation
show_evaluation_results
