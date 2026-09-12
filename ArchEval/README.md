# Compiled Intent: Evaluation Harness (ArchEval)

This repository contains the `inspect_ai` evaluation harness used to benchmark the **Compiled Intent (CI)** semantic governance engine. 

It tests the capability of LLMs to adhere to large-scale enterprise architectural specifications, measuring context bloat, inference latency, and the effectiveness of autonomous Vector RAG.

## Project Structure

- `setup.sh`: Bootstraps the Python virtual environment and installs dependencies.
- `config/`: Contains the LanceDB configuration files for the semantic search engine.
- `datasets/`: Contains the evaluation question suites and the frozen specification corpus.
- `tasks/`: Contains the 4 canonical `inspect_ai` task definitions for the 4x3 benchmark matrix.
- `scripts/`: Contains the benchmark runner (`run_benchmarks.sh`) and results parser (`parse_results.py`).

## Dataset & Specification Attribution
The architectural specifications under `datasets/akshara_specs/` represent a frozen snapshot of the **Akshara** system design documents used for all empirical evaluations in the paper. This snapshot is bundled directly to guarantee exact scientific reproducibility of the benchmark and oracle retrieval baselines without upstream drift. Akshara is an independent sovereign system design project.

## Prerequisites

### 1. The `intent` CLI
This harness relies on the `intent` semantic search engine. You must have the `intent` CLI tool installed and available in your system's PATH. (See the main `compiled-intent` repository for installation instructions).

### 2. Ollama Models (LLM & Embeddings)
By default, the benchmark uses a local LLM and a local embedding model. You must have [Ollama](https://ollama.com/) installed and pull both the inference model and the embedding model defined in the configuration (`config/akshara_config.toml`):

```bash
ollama pull qwen2.5-coder:14b
ollama pull nomic-embed-text
```
*Note: Make sure the Ollama server is actively running before executing the benchmarks.*

## Installation

We provide a turnkey setup script that automatically builds the virtual environment and installs the required Python dependencies (`inspect_ai`, `lancedb`, `openai`).

```bash
./setup.sh
```

## Running Benchmarks

### Executing the 4x3 Benchmark Matrix
This suite executes the 12 evaluation runs across the four architectures (Zero Context, Bounded Stuffing, Compiled Intent Static RAG, and Oracle RAG) across all three datasets (PR Audit, Adversarial, Trivia):

```bash
./scripts/run_benchmarks.sh
```

### Parsing Results
To extract the summary matrix directly from the latest evaluation logs:
```bash
python3 scripts/parse_results.py
```

### Viewing Results
All benchmark logs are written to the `logs/` directory in JSON-lines `.eval` format. You can view the raw token consumption and accuracy scores using the native inspect CLI:
```bash
source .venv/bin/activate
inspect view
```
