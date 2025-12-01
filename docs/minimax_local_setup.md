# MiniMax Local Deployment (M1 & M2)

This guide explains how to host the open-weight **MiniMax-M1** and **MiniMax-M2** models locally and expose them to ChatOS via the built-in MiniMax provider.

> ⚠️ **Hardware & Storage**  
> - MiniMax-M1-40k: ~456 GB of BF16 weights (8× H800 or better recommended).  
> - MiniMax-M2: ~230 GB of FP8/BF16 weights (≥4 high-memory GPUs).  
> Ensure you have enough disk, GPU VRAM, and network bandwidth before pulling the models.

## 1. Prerequisites

```bash
conda create -n minimax python=3.10 -y
conda activate minimax
pip install --upgrade pip
pip install vllm>=0.9.2 huggingface_hub git-lfs
git lfs install
```

Log into Hugging Face so you can download the gated repositories if needed:

```bash
huggingface-cli login
```

## 2. Download the Model Weights

```bash
# M1 (choose 40k or 80k)
huggingface-cli download MiniMaxAI/MiniMax-M1-40k --local-dir /models/MiniMaxAI/MiniMax-M1-40k

# M2
huggingface-cli download MiniMaxAI/MiniMax-M2 --local-dir /models/MiniMaxAI/MiniMax-M2
```

If you are behind a mirror:

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 3. Launch vLLM Servers

Use the helper script we added under `scripts/run_minimax_vllm.sh`:

```bash
# Terminal 1 – MiniMax-M1 on port 8010
TP_SIZE=8 MAX_MODEL_LEN=65536 \
scripts/run_minimax_vllm.sh /models/MiniMaxAI/MiniMax-M1-40k 8010 MiniMax-M1

# Terminal 2 – MiniMax-M2 on port 8011
TP_SIZE=4 MAX_MODEL_LEN=32768 \
scripts/run_minimax_vllm.sh /models/MiniMaxAI/MiniMax-M2 8011 MiniMax-M2
```

The script wraps:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model <path> \
  --served-model-name <MiniMax-M1|MiniMax-M2> \
  --port <8010|8011> \
  --tensor-parallel-size <TP_SIZE> \
  --trust-remote-code \
  --quantization experts_int8 \
  --dtype bfloat16
```

Adjust tensor parallelism, dtype, or quantization to match your hardware. Keep the `--served-model-name` flag aligned with the ChatOS `model_id` (`MiniMax-M1` or `MiniMax-M2`), otherwise ChatOS will not match the running endpoint.

## 4. Verify the Servers

```bash
curl http://localhost:8010/v1/models
curl http://localhost:8011/v1/models

curl http://localhost:8010/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
        "model": "MiniMax-M1",
        "messages": [{"role": "user", "content": "Say hello"}],
        "temperature": 1.0,
        "max_tokens": 512
      }'
```

You should see responses from each server. If you encounter `ModuleNotFoundError: vllm._C`, reinstall vLLM from source (`pip install -e .`) as described in the official guides.

## 5. ChatOS Integration

We registered two MiniMax entries inside `ChatOS-Sandbox/.config/models.json`:

| Name         | Provider | Base URL              | Model ID   |
|--------------|----------|-----------------------|------------|
| MiniMax M1   | minimax  | `http://localhost:8010` | `MiniMax-M1` |
| MiniMax M2   | minimax  | `http://localhost:8011` | `MiniMax-M2` |

Once the vLLM servers are up, ChatOS will:

1. Hit the MiniMax provider.  
2. Attempt Ollama (`minimaxm1` / `minimaxm2`) – this will fail harmlessly.  
3. Fall back to the OpenAI-compatible endpoint at the `base_url` you configured.

Use `/api/minimax/status` or the settings UI to confirm the provider becomes available.

## 6. Troubleshooting

- **Download interruptions**: re-run `huggingface-cli download ... --resume-download`.
- **Port conflicts**: change the port numbers and update `base_url` in `models.json`.
- **Slow throughput**: lower `MAX_MODEL_LEN` or use heavier quantization (e.g., `fp8` for MiniMax-M2).
- **ChatOS errors**: ensure the vLLM server reports the exact `served-model-name` that matches the `model_id`.

With the servers running and ChatOS configured, you can select “MiniMax M1” or “MiniMax M2” in the UI and interact with the models entirely locally.
