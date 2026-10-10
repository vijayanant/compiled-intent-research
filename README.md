# Compiled Intent: Enforcing Architectural Invariants for LLM Coding Agents

[![Release](https://img.shields.io/badge/Release-v1.0.0-blue.svg)](https://github.com/vijayanant/compiled-intent-research/releases/tag/v1.0.0)
[![Technical Report (PDF)](https://img.shields.io/badge/Report-Download%20PDF-blue.svg)](https://github.com/vijayanant/compiled-intent-research/releases/latest/download/compiled-intent.pdf)
[![Engine Implementation](https://img.shields.io/badge/Engine-intent%20v0.1.0-orange.svg)](https://github.com/vijayanant/compiled-intent)
[![Research Lab](https://img.shields.io/badge/Lab-LambdaMatters-black.svg)](https://lambdamatters.com)
[![Benchmark Suite](https://img.shields.io/badge/Benchmark-ArchEval%20(117%20tasks)-green.svg)](ArchEval/)

Official research repository for the **Compiled Intent** architectural coprocessor and the **ArchEval** benchmark suite.

Read the full technical paper: [**Compiled Intent: Enforcing Architectural Invariants for LLM Coding Agents (PDF)**](https://github.com/vijayanant/compiled-intent-research/releases/latest/download/compiled-intent.pdf).

---

## Overview

When engineering teams attempt to enforce architectural constraints with LLMs, they typically resort to **prompt stuffing**: injecting whole Architecture Decision Records (ADRs) and design specifications into the prompt context. On local developer workstations, this rapidly exhausts memory bandwidth and degrades KV cache performance. On hosted APIs, it incurs heavy token costs on every review. Furthermore, whole-document context provides peripheral prose that models use to rationalize architectural violations (the **Ammunition Effect**).

**Compiled Intent** (powered by the **Compitent Engine**) solves this by compiling architectural intent into an offline, AST-bounded vector and full-text index. By retrieving compact constraint chunks (~750 tokens) during code review and code generation, the system matches or exceeds whole-document prompt stuffing while slashing token footprints.

**ArchEval** is our empirical benchmark harness built on [Inspect AI](https://inspect.ai-safety-institute.org.uk/). It rigorously evaluates 117 architectural tasks across three tracks (PR Audits, Adversarial Traps, Architectural Trivia) under four context strategies: **Zero Context**, **Oracle (Single-File)**, **Prompt Stuffing**, and **Compiled Intent**.

---

## Key Results

- **64.3% Token Reduction vs. Oracle:** Cuts injected payload from ~2,100 tokens (single-file oracle) down to ~750 tokens by isolating normative constraints from narratives and mock definitions.
- **94.6% Token Reduction vs. Stuffing:** Drops total injected evaluation tokens from 1.88M tokens down to 102k tokens across the 117-task benchmark suite.
- **+12.8% to +17.9% Higher Adversarial Resistance:** Stripping extraneous prose prevents the model from rationalizing exceptions, boosting adversarial pull-request enforcement from 59.0% to **71.8%** on Qwen 2.5 Coder (14B) and 66.7% to **84.6%** on Gemma 3 (12B).

### Summary Benchmark Matrix ($N=117$, $T=0$)

| Strategy | Avg. Context | Overall (Qwen 14B) | Adversarial (Qwen 14B) | Overall (Gemma 12B) | Adversarial (Gemma 12B) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Zero Context** | ~250 tokens | 41.9% | 38.5% | 46.2% | 51.3% |
| **Oracle (Single-File)** | ~2,100 tokens | 75.2% | 59.0% | 75.2% | 66.7% |
| **Prompt Stuffing** | ~15,400 tokens | 75.2% | 69.2% | 80.3% | 69.2% |
| **Compiled Intent** | **~750 tokens** | **74.4%** | **71.8%** | **84.6%** | **82.1%** |

*(For complete per-track metrics, token accounting, and statistical breakdowns, refer to the [technical report](https://github.com/vijayanant/compiled-intent-research/releases/latest/download/compiled-intent.pdf)).*

---

## Quick Start (Reproducing the Benchmarks)

### 1. Install the `intent` CLI
```bash
cargo install --git https://github.com/vijayanant/compiled-intent.git --tag v0.1.0
intent --version
```

### 2. Pull Ollama Embedding & Models
```bash
# Required 768-dimension local embedding model:
ollama pull nomic-embed-text

# Evaluation models evaluated in the paper:
ollama pull qwen2.5-coder:14b
ollama pull gemma3:12b
```

### 3. Setup & Run
```bash
cd ArchEval

# Recommended setup (using uv):
uv sync

# Or automated fallback for standard Python 3:
# ./setup.sh

# 1. Run a quick smoke test first:
# We recommend running an individual test to estimate inference speed on your hardware
# before committing to the full benchmark matrix.
uv run inspect eval tasks/eval_rag_interceptor.py@rag_adversarial --model ollama/qwen2.5-coder:14b -T 0

# 2. Run the full 4x3 benchmark matrix (12 runs):
# Note: Execution time depends heavily on your local hardware (often upwards of an hour).
./scripts/run_benchmarks.sh

# Or evaluate Gemma 3 (12B):
./scripts/run_benchmarks.sh ollama/gemma3:12b
```

### 4. Parse Results
```bash
uv run python scripts/parse_results.py [model_name]
```

To run individual tasks or launch the Inspect AI visual dashboard, see [`ArchEval/README.md`](ArchEval/).

---

## Repository Structure

```text
compiled-intent-research/
├── CITATION.cff             # Citation metadata (GitHub native citation support)
├── compiled-intent.md       # Manuscript source (pure Markdown)
├── template.tex             # Custom LaTeX pandoc template
├── figures/                 # TikZ / pgfplots figure sources
├── ArchEval/                # Inspect AI benchmark suite
│   ├── datasets/            # 117 benchmark items & frozen Akshara specs
│   ├── tasks/               # Canonical Inspect AI task runners
│   ├── scripts/             # run_benchmarks.sh and parse_results.py
│   ├── pyproject.toml       # Python dependencies and locked environment
│   └── setup.sh             # Fast environment bootstrapper
└── build/                   # Compiled figures & manuscript build artifacts
```

---

## Citation

If you use Compiled Intent or ArchEval in your research, please cite our technical report using GitHub's native **"Cite this repository"** button or refer to [`CITATION.cff`](CITATION.cff).
