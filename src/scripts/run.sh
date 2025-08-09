#!/bin/bash

# === Common Configuration ===
DATA_DIR="./data"
OUTPUT_DIR="outputs/dialog_history_iiyi"
MAX_CONVERSATION_TURN=10

# === Helper Function ===
run_dialogue_simulation() {
  local name="$1"
  local doctor="$2"
  local model_flag="$3"
  local model_value="$4"
  local extra_args="$5"

  local reporter="Agent.Reporter.GPT"
  local reporter_model="gpt-3.5-turbo"
  local patient="Agent.Patient.GPT"
  local patient_model="gpt-3.5-turbo"
  local save_path="$OUTPUT_DIR/dialog_history_${name}.jsonl"

  echo "Running simulation: $name"

  python run.py \
    --patient_database "$DATA_DIR/patients.json" \
    --doctor "$doctor" \
    $model_flag "$model_value" \
    --patient "$patient" \
    --patient_openai_model_name "$patient_model" \
    --reporter "$reporter" \
    --reporter_openai_model_name "$reporter_model" \
    --save_path "$save_path" \
    --max_conversation_turn "$MAX_CONVERSATION_TURN" \
    $extra_args
}

# === Model Configurations ===
declare -A MODELS=(
  ["gpt4_0222"]="Agent.Doctor.GPT|--doctor_openai_model_name|gpt-4|OPENAI_API_KEY OPENAI_API_BASE"
  ["wenxin_0222"]="Agent.Doctor.WenXin|||WENXIN_API_KEY WENXIN_SECRET_KEY"
  ["qwen_max"]="Agent.Doctor.Qwen|--doctor_qwen_model_name|qwen-max|DASHSCOPE_API_KEY"
  ["baichuan2_13b_chat_v1_0222"]="Agent.Doctor.Qwen|--doctor_qwen_model_name|baichuan2-13b-chat-v1|DASHSCOPE_API_KEY"
  ["huatuogpt2_34b_0222"]="Agent.Doctor.HuatuoGPT|--doctor_huatuogpt_model_name_or_path|\$HUATUOGPT_MODEL|HUATUOGPT_MODEL|--ff_print"
)

# === API Keys Setup ===
export OPENAI_API_KEY=""
export OPENAI_API_BASE=""
export WENXIN_API_KEY=""
export WENXIN_SECRET_KEY=""
export DASHSCOPE_API_KEY=""
export HUATUOGPT_MODEL=""

# === Run All Simulations ===
for name in "${!MODELS[@]}"; do
  IFS='|' read -r doctor flag value env_vars extra <<< "${MODELS[$name]}"

  # Export required env vars if specified
  for var in $env_vars; do
    export "$var"="${!var}"
  done

  run_dialogue_simulation "$name" "$doctor" "$flag" "$value" "$extra"
done
