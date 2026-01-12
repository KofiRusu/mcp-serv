# Phase 2 Implementation Notes

## Issues Identified During Phase 1 Validation

### Issue 1: Relative Paths in Unsloth Config (CRITICAL)

**Location**: `/home/kr/unsloth/local_kali_pipelines/configs/chatos_qlora.yaml` lines 43-44

**Current State**:
```yaml
dataset:
  train_path: "datasets/chatos_train.jsonl"
  eval_path: "datasets/chatos_eval.jsonl"
```

**Problem**: Paths are relative to working directory, not absolute.

**Impact**: When ChatOS spawns training from `/home/kr/ChatOS-0.1`, the paths will resolve incorrectly.

**Fix for Phase 2**:
In `unsloth_runner.py`, when generating the temp config:
1. Use absolute paths when writing the config
2. OR ensure the subprocess runs with `cwd=/home/kr/unsloth/local_kali_pipelines`

**Recommended approach**:
```python
# In write_temp_config():
config["dataset"]["train_path"] = str(settings.unsloth_datasets_dir / "chatos_train.jsonl")
config["dataset"]["eval_path"] = str(settings.unsloth_datasets_dir / "chatos_eval.jsonl")
config["training"]["output_dir"] = str(settings.unsloth_outputs_dir / job_id)
config["metrics"]["output_path"] = str(settings.unsloth_outputs_dir / job_id / "metrics.jsonl")
```

---

### Issue 2: Missing Unit Tests

**Location**: `ChatOS/training/`

**Impact**: Regression risk when modifying data_pipeline.py

**Fix for Phase 2**: Create `tests/test_data_pipeline.py` with:
- Test `load_raw_conversations()` with mock data
- Test `filter_for_training()` with various min_score values
- Test `to_unsloth_jsonl()` output format

---

### Issue 3: No Validation of Message Content

**Location**: `data_pipeline.py` lines 251-257

**Current State**: Empty messages are not filtered

**Fix for Phase 2**: Add validation in `filter_for_training()`:
```python
# Skip messages with empty content
if not msg.content or not msg.content.strip():
    continue
```

---

### Issue 4: Hardcoded Chat Template

**Location**: `train_qlora.py` line 95

**Current State**:
```python
tokenizer = get_chat_template(
    tokenizer,
    chat_template="qwen-2.5",  # Hardcoded
)
```

**Impact**: Won't work with non-Qwen models (e.g., Mistral, Llama)

**Fix for Phase 2**: Make configurable in YAML:
```yaml
model:
  name: "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
  chat_template: "qwen-2.5"  # New field
```

Then in train_qlora.py:
```python
template = config["model"].get("chat_template", "chatml")
tokenizer = get_chat_template(tokenizer, chat_template=template)
```

---

### Issue 5: No Export Script Yet

**Location**: Missing `export_lora_to_ollama_or_gguf.py`

**Impact**: Phase 5 blocker - cannot export trained adapters

**Fix**: Create in Phase 5 with:
- Merge LoRA adapter with base model (optional)
- Export to GGUF format
- Generate Ollama Modelfile

---

## Phase 2 Checklist

Before starting Phase 2, ensure:

- [x] All Phase 1 validation tests pass
- [x] Issue 1 (relative paths) documented
- [x] Issue 4 (chat template) documented
- [ ] Phase 2 implementation should handle Issue 1 in `unsloth_runner.py`
- [ ] Phase 2 should consider Issue 3 (empty messages) as optional improvement

## Validation Results Summary

| Test | Status |
|------|--------|
| 1.1 Settings Import | PASS |
| 1.3 Unsloth Path Resolution | PASS |
| 1.4 Environment Override | PASS |
| 2.1 Data Pipeline Import | PASS |
| 2.2 CLI Help | PASS |
| 2.3 Conversation Loading | PASS (35 conversations) |
| 2.4 Filtering | PASS (35 examples) |
| 2.5 Output Format | PASS |
| 2.6 Regeneration Idempotency | PASS (31 train, 4 eval) |
| 3.2 YAML Config Validity | PASS |
| 4.1 End-to-End Pipeline | PASS |
| 4.2 Feedback Score Filtering | PASS |

**All validation tests passed. Ready for Phase 2.**

