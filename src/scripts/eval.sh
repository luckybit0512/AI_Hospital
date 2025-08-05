# Set API credentials
export OPENAI_API_KEY=""
export OPENAI_API_BASE=""

# Define variables
EVAL_DIR="evaluate"
OUTPUT_FILE="../outputs/evaluation/evaluation_iiyi_gpt4_5part.jsonl"
REFERENCE_FILE="../data/patients.json"
RESULT_PATH="../outputs/evaluation/evaluation_iiyi_gpt4_onestep.jsonl"
MODEL_NAME="gpt-4"
DOCTOR_NAME="GPT-4"

# Run evaluation
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

# Show evaluation results
python eval_show.py \
  --interactive_evaluation_result_path "$OUTPUT_FILE" \
  --onestep_evaluation_result_path "$RESULT_PATH"