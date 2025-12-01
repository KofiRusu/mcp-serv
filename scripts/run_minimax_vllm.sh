#!/usr/bin/env bash
# Helper to launch a MiniMax model with vLLM's OpenAI-compatible server.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <model_path> [port] [served_model_name]" >&2
  echo "Example: $0 /models/MiniMaxAI/MiniMax-M1-40k 8010 MiniMax-M1" >&2
  exit 1
fi

MODEL_PATH="$1"
PORT="${2:-8000}"
SERVED_NAME="${3:-MiniMax-Local}"

: "${TP_SIZE:=8}"
: "${DTYPE:=bfloat16}"
: "${QUANTIZATION:=experts_int8}"
: "${MAX_MODEL_LEN:=4096}"

export SAFETENSORS_FAST_GPU=1
export VLLM_USE_V1=0

python3 -m vllm.entrypoints.openai.api_server \
  --model "${MODEL_PATH}" \
  --served-model-name "${SERVED_NAME}" \
  --port "${PORT}" \
  --host 0.0.0.0 \
  --tensor-parallel-size "${TP_SIZE}" \
  --dtype "${DTYPE}" \
  --quantization "${QUANTIZATION}" \
  --max-model-len "${MAX_MODEL_LEN}" \
  --trust-remote-code
