#!/bin/bash

# Force strict error handling
set -euo pipefail

echo "================================================="
echo "  STARTING FULL 4x3 BENCHMARK SUITE (12 TESTS)   "
echo "================================================="

# Move to the ArchEval root directory so paths work reliably
cd "$(dirname "$0")/.."

# 1. Environment & Runner Detection
if [ -z "${VIRTUAL_ENV:-}" ]; then
  if command -v uv &>/dev/null; then
    exec uv run "$0" "$@"
  elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
  else
    echo "Error: No Python environment detected." >&2
    echo "Please either:" >&2
    echo "  1. Install uv (recommended): https://docs.astral.sh/uv/" >&2
    echo "  2. Or run: ./setup.sh" >&2
    exit 1
  fi
fi

# 2. Check inspect CLI
if ! command -v inspect &>/dev/null; then
  echo "Error: 'inspect' CLI not found. Please activate your environment or run ./setup.sh." >&2
  exit 1
fi

# 3. Check intent CLI & Version
if ! command -v intent &>/dev/null; then
  echo "Error: 'intent' binary not found on PATH." >&2
  echo "Please install it via 'cargo install --git https://github.com/vijayanant/compiled-intent.git --tag v0.1.0'" >&2
  echo "or download a prebuilt binary from: https://github.com/vijayanant/compiled-intent/releases" >&2
  exit 1
fi

INTENT_VER=$(intent --version 2>/dev/null || echo "unknown")
echo "Using intent coprocessor: $(which intent) ($INTENT_VER)"

# 4. Ollama Service & Models Pre-Flight Verification
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Error: Ollama server is not reachable at http://localhost:11434." >&2
  echo "Please launch Ollama with 'ollama serve' before running benchmarks." >&2
  exit 1
fi

MODEL="${1:-ollama/qwen2.5-coder:14b}"
if [[ "$MODEL" != *"/"* ]]; then
  MODEL="ollama/$MODEL"
fi
echo "Target Model: $MODEL"

OLLAMA_MODELS=$(curl -s http://localhost:11434/api/tags)
CLEAN_MODEL_NAME="${MODEL#ollama/}"
if ! echo "$OLLAMA_MODELS" | grep -q "$CLEAN_MODEL_NAME"; then
  echo "Notice: Model '$CLEAN_MODEL_NAME' not found in Ollama. Pulling..."
  ollama pull "$CLEAN_MODEL_NAME"
fi

if ! echo "$OLLAMA_MODELS" | grep -q "nomic-embed-text"; then
  echo "Notice: Embedding model 'nomic-embed-text' not found in Ollama. Pulling..."
  ollama pull nomic-embed-text
fi

# 5. Database Pre-Flight (Auto-Index if missing or requested)
if [ ! -d ".intent_akshara_db" ] || [ "${2:-}" == "--reindex" ] || [ "${1:-}" == "--reindex" ]; then
  echo "Initializing and indexing Akshara specifications into LanceDB..."
  intent --config config/akshara_config.toml index datasets/akshara_specs
fi

# 6. Teardown: Clean up old run logs to ensure clean matrix evaluation
echo "Cleaning up stale eval logs for $MODEL..."
# Note: we keep logs directory ready
mkdir -p logs

echo "-------------------------------------------------"
echo "1/4: ZERO CONTEXT (The Blind LLM)"
echo "-------------------------------------------------"
inspect eval tasks/eval_zero_context.py@zero_context_pr_audit --model "$MODEL" -T 0 --max-connections 10 --log-dir logs
inspect eval tasks/eval_zero_context.py@zero_context_adversarial --model "$MODEL" -T 0 --max-connections 10 --log-dir logs
inspect eval tasks/eval_zero_context.py@zero_context_trivia --model "$MODEL" -T 0 --max-connections 10 --log-dir logs

echo "-------------------------------------------------"
echo "2/4: PROMPT STUFFING (The Kitchen Sink)"
echo "-------------------------------------------------"
inspect eval tasks/eval_prompt_stuffing.py@stuffing_pr_audit --model "$MODEL" -T 0 --max-connections 10 --log-dir logs
inspect eval tasks/eval_prompt_stuffing.py@stuffing_adversarial --model "$MODEL" -T 0 --max-connections 10 --log-dir logs
inspect eval tasks/eval_prompt_stuffing.py@stuffing_trivia --model "$MODEL" -T 0 --max-connections 10 --log-dir logs

echo "-------------------------------------------------"
echo "3/4: RAG INTERCEPTOR (The Surgical Search)"
echo "-------------------------------------------------"
inspect eval tasks/eval_rag_interceptor.py@rag_pr_audit --model "$MODEL" -T 0 --max-connections 10 --log-dir logs
inspect eval tasks/eval_rag_interceptor.py@rag_adversarial --model "$MODEL" -T 0 --max-connections 10 --log-dir logs
inspect eval tasks/eval_rag_interceptor.py@rag_trivia --model "$MODEL" -T 0 --max-connections 10 --log-dir logs

echo "-------------------------------------------------"
echo "4/4: ORACLE RAG (The Theoretical Maximum)"
echo "-------------------------------------------------"
inspect eval tasks/eval_oracle_rag.py@oracle_pr_audit --model "$MODEL" -T 0 --max-connections 10 --log-dir logs
inspect eval tasks/eval_oracle_rag.py@oracle_adversarial --model "$MODEL" -T 0 --max-connections 10 --log-dir logs
inspect eval tasks/eval_oracle_rag.py@oracle_trivia --model "$MODEL" -T 0 --max-connections 10 --log-dir logs

echo "================================================="
echo "Benchmarks complete. Generating final 4x3 matrix:"
echo "================================================="
python3 scripts/parse_results.py "$MODEL"
