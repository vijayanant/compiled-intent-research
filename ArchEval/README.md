# Compiled Intent: Evaluation Harness (ArchEval)

This directory contains the [`inspect_ai`](https://inspect.ai-safety-institute.org.uk/) evaluation harness used to benchmark the **Compiled Intent** semantic coprocessor against enterprise architectural specifications.

It empirically measures architectural constraint adherence, prompt token footprints, and policy enforcement across four context strategies: **Zero Context**, **Prompt Stuffing**, **Oracle**, and **Compiled Intent**.

---

## Prerequisites

### 1. The `intent` Semantic Engine CLI

The harness queries the `intent` coprocessor runtime to evaluate hybrid AST retrieval. You must have the `intent` CLI installed and available in your `PATH`:

```bash
# Install directly from the compiled-intent repository (pinned to v0.1.0):
cargo install --git https://github.com/vijayanant/compiled-intent.git --tag v0.1.0

# Verify installation:
intent --version
```

### 2. Ollama & Embedding Model

ArchEval uses local vector embeddings via LanceDB. You must have [Ollama](https://ollama.com/) running and pull the 768-dimension embedding model specified in `config/akshara_config.toml`:

```bash
ollama pull nomic-embed-text
```

### 3. Evaluating LLMs

You can evaluate **any model** supported by Ollama or Inspect AI. To reproduce the exact results published in the research paper:

```bash
# Qwen 2.5 Coder (14B)
ollama pull qwen2.5-coder:14b

# Gemma 3 (12B)
ollama pull gemma3:12b
```

*Note: Make sure `ollama serve` is running in the background before starting the benchmark.*

---

## Installation

Setup requires Python 3.10+.

**Recommended (`uv`):**
```bash
uv sync
```

**Automated / Standard Python Setup:**
If you prefer an automated setup or do not have `uv`, run `./setup.sh`. It detects `uv` automatically or creates a standard Python 3 virtual environment with `pip`:
```bash
./setup.sh
```

---

## Running Benchmarks

### Executing the Full 4x3 Benchmark Matrix (12 Runs)

To run the complete benchmark suite across all four strategies (Zero Context, Bounded Stuffing, Compiled Intent, and Oracle) across all three tracks (PR Audit, Adversarial Traps, Institutional Trivia):

```bash
# Run with default model (Qwen 2.5 Coder 14B):
./scripts/run_benchmarks.sh

# Or evaluate Gemma 3 (12B):
./scripts/run_benchmarks.sh ollama/gemma3:12b

# Or evaluate ANY local model you have:
./scripts/run_benchmarks.sh ollama/<your-model>
```

*Note: On the first run, the script automatically builds the local LanceDB and Tantivy hybrid index from `datasets/akshara_specs/` into `.intent_akshara_db/`.*

### Running Individual Tasks

Instead of running all 12 tests, you can evaluate individual tracks or strategies directly:

```bash
# Evaluate Adversarial Traps under Compiled Intent:
uv run inspect eval tasks/eval_rag_interceptor.py@rag_adversarial --model ollama/qwen2.5-coder:14b -T 0

# Evaluate PR Audits under Zero Context:
uv run inspect eval tasks/eval_zero_context.py@zero_context_pr_audit --model ollama/qwen2.5-coder:14b -T 0

# Evaluate Architectural Trivia under Prompt Stuffing:
uv run inspect eval tasks/eval_prompt_stuffing.py@stuffing_trivia --model ollama/qwen2.5-coder:14b -T 0

# Evaluate PR Audits under Oracle (Single-File):
uv run inspect eval tasks/eval_oracle_rag.py@oracle_pr_audit --model ollama/qwen2.5-coder:14b -T 0
```

### Parsing Results

To parse and print the summary accuracy and token reduction matrix from the evaluation logs:

```bash
uv run python scripts/parse_results.py [model_name]

# Or, if using standard venv without uv:
# source .venv/bin/activate && python3 scripts/parse_results.py [model_name]
```

### Interactive Log Inspection

All runs write native `.eval` trace logs to `logs/`. You can launch Inspect AI's visual dashboard to inspect individual prompts, retrieved chunks, and model reasoning chains:

```bash
uv run inspect view

# Or, if using standard venv without uv:
# source .venv/bin/activate && inspect view
```

---

## Dataset & Specification Attribution

The specifications under `datasets/akshara_specs/` represent a frozen snapshot of the **Akshara** system architecture (distributed protocols, cryptographic keys, capability ledgers, and governance rules). This snapshot is bundled directly to guarantee exact scientific reproducibility of the benchmark and oracle retrieval baselines without upstream drift. Akshara is an independent sovereign system design project.
