#!/bin/bash

# Common configuration
DATA_DIR="./data"
OUTPUT_DIR="outputs/dialog_history_iiyi"
MAX_CONVERSATION_TURN=10

run_dialogue_simulation() {
  local name="$1"
  local doctor="$2"
  local doctor_model_flag="$3"
  local doctor_model_value="$4"
  local reporter="Agent.Reporter.GPT"
  local reporter_model="gpt-3.5-turbo"
  local patient="Agent.Patient.GPT"
  local patient_model="gpt-3.5-turbo"
  local save_path="$OUTPUT_DIR/dialog_history_${name}.jsonl"
  local extra_args="$5"

  echo "$name"

  python run.py \
    --patient_database "$DATA_DIR/patients.json" \
    --doctor "$doctor" \
    $doctor_model_flag "$doctor_model_value" \
    --patient "$patient" \
    --patient_openai_model_name "$patient_model" \
    --reporter "$reporter" \
    --reporter_openai_model_name "$reporter_model" \
    --save_path "$save_path" \
    --max_conversation_turn "$MAX_CONVERSATION_TURN" \
    $extra_args
}

# GPT-4
export OPENAI_API_KEY=""
export OPENAI_API_BASE=""
run_dialogue_simulation "gpt4_0222" "Agent.Doctor.GPT" "--doctor_openai_model_name" "gpt-4"

# GPT-3.5-Turbo (uncomment to use)
# export OPENAI_API_KEY=""
# export OPENAI_API_BASE=""
# run_dialogue_simulation "gpt3_0222" "Agent.Doctor.GPT" "--doctor_openai_model_name" "gpt-3.5-turbo"

# WenXin
export WENXIN_API_KEY=""
export WENXIN_SECRET_KEY=""
run_dialogue_simulation "wenxin_0222" "Agent.Doctor.WenXin" "" ""

# Qwen
export DASHSCOPE_API_KEY=""
run_dialogue_simulation "qwen_max" "Agent.Doctor.Qwen" "--doctor_qwen_model_name" "qwen-max"

# BaiChuan
export DASHSCOPE_API_KEY=""
run_dialogue_simulation "baichuan2_13b_chat_v1_0222" "Agent.Doctor.Qwen" "--doctor_qwen_model_name" "baichuan2-13b-chat-v1"

# HuatuoGPT
export HUATUOGPT_MODEL=""
run_dialogue_simulation "huatuogpt2_34b_0222" "Agent.Doctor.HuatuoGPT" "--doctor_huatuogpt_model_name_or_path" "$HUATUOGPT_MODEL" "--ff_print"
