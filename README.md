# Compiled Intent: Enforcing Architectural Invariants for LLM Coding Agents

[![Release](https://img.shields.io/badge/Release-v1.0.0-blue.svg)](https://github.com/vijayanant/compiled-intent-research/releases/tag/v1.0.0)
[![Technical Report (PDF)](https://img.shields.io/badge/Report-Download%20PDF-blue.svg)](https://github.com/vijayanant/compiled-intent-research/releases/latest/download/compiled-intent.pdf)
[![Engine Implementation](https://img.shields.io/badge/Engine-intent%20v0.1.0-orange.svg)](https://github.com/vijayanant/compiled-intent)
[![Research Lab](https://img.shields.io/badge/Lab-LambdaMatters-black.svg)](https://lambdamatters.com)
[![Benchmark Suite](https://img.shields.io/badge/Benchmark-ArchEval%20(117%20tasks)-green.svg)](ArchEval/)

Official research repository for the **Compiled Intent** architectural coprocessor and the **ArchEval** benchmark suite.

---

## Abstract

When teams attempt to enforce architectural constraints with AI, they usually rely on prompt stuffing: injecting large design specifications and Architecture Decision Records (ADRs) into the LLM context. At scale, this breaks down. On local developer workstations, large prompts rapidly exhaust memory bandwidth, degrade Key-Value cache efficiency, and cause inference latency to spike. On hosted APIs, repetitive context injection incurs continuous token expenditure on every review.

Indexing source code syntax fails to resolve this. Code reflects existing implementation, but it does not capture architectural rationale, trade-offs, or structural invariants.

To enforce boundaries reliably, systems must index design intent. We present the **Compitent Engine** (Compiled Intent), an architectural coprocessor that compiles architectural intent (recorded in specifications, RFCs, and Architecture Decision Records) into an offline vector and full-text database. By retrieving compact, AST-bounded constraint chunks (~750 tokens) during code generation and pull request review, the engine matches or exceeds prompt stuffing across evaluated models (`qwen2.5-coder:14b` and `gemma3:12b`). It cuts context payload by **64.3% against single-file oracle retrieval** and by **94.6% against multi-specification stuffing**. On adversarial test cases, isolating normative constraints **raises enforcement accuracy by 12.8 to 17.9 percentage points** over whole-document stuffing by eliminating non-normative rationalization loopholes (**The Ammunition Effect**).

---

## Key Empirical Findings

Empirical evaluation across all 117 benchmark items ($N=117$, temperature $T=0$) comparing **Zero Context**, **Oracle**, **Prompt Stuffing**, and **Compiled Intent**:

### Table 1: Benchmark Accuracy on Qwen 2.5 Coder (14B) & Gemma 3 (12B)

| Strategy | Overall Accuracy | PR Audit Track ($N=39$) | Adversarial Traps ($N=39$) | Architectural Trivia ($N=39$) |
| :--- | :---: | :---: | :---: | :---: |
| **Qwen 2.5 Coder (14B)** | | | | |
| Zero Context | 41.9% | 41.0% | 38.5% | 46.2% |
| Oracle | 75.2% | 71.8% | 59.0% | 94.9% |
| Prompt Stuffing | 75.2% | 64.1% | 69.2% | 92.3% |
| **Compiled Intent** | **74.4%** | **61.5%** | **71.8%** | **89.7%** |
| | | | | |
| **Gemma 3 (12B)** | | | | |
| Zero Context | 46.2% | 35.9% | 51.3% | 51.3% |
| Oracle | 75.2% | 66.7% | 66.7% | 92.3% |
| Prompt Stuffing | 80.3% | 74.4% | 69.2% | 97.4% |
| **Compiled Intent** | **84.6%** | **82.1%** | **82.1%** | **89.7%** |

### Table 2: Context Footprint & Token Accounting

| Strategy | Avg. Input Context | Total Injected Tokens | vs. Oracle (Whole-File) | vs. Prompt Stuffing |
| :--- | :---: | :---: | :---: | :---: |
| **Zero Context** | ~250 tokens | ~33,000 tokens | -88.1% | -98.4% |
| **Oracle** | ~2,100 tokens | ~245,000 tokens | *Baseline* | -86.4% |
| **Prompt Stuffing** | ~15,400 tokens | ~1,880,000 tokens | +633% | *Baseline* |
| **Compiled Intent** | **~750 tokens** | **~102,000 tokens** | **-64.3%** | **-94.6%** |

The token reduction measured against prompt stuffing naturally depends on how much text was stuffed in the first place. The more rigorous metric is the comparison against Oracle: even when a human pre-selects the exact governing file, feeding the whole document injects ~2,100 tokens. Compiled Intent cuts that payload by 64.3% (~750 tokens) by stripping out intra-file narratives, preambles, and mock interfaces.

---

## The Ammunition Effect

Real-world architectural specifications are comprehensive documents containing mock testing interfaces, legacy compatibility notes, and protocol abstractions. 

When an adversarial pull request pairs non-compliant code with a persuasive rationale (such as skipping CID verification on internal links to reduce CPU load), a whole-document prompt provides peripheral context that the model uses as **ammunition** to rationalize an exception. For example, reading about testing mock transports in a 3,500-word sync specification leads the model to infer that internal cluster links might also be exempt.

By extracting only the specific AST block defining the invariant, **Compiled Intent strips away peripheral prose**. With no extraneous exceptions in context, the model evaluates the developer's motivation directly against the governing rule, boosting adversarial accuracy from 59.0% $\rightarrow$ **71.8%** on Qwen and 66.7% $\rightarrow$ **84.6%** on Gemma.

---

## Reproducing the Benchmarks

All benchmark datasets, tasks, and evaluation runners are self-contained in the `ArchEval/` directory.

### 1. Install the `intent` CLI
The benchmark harness queries the `intent` coprocessor engine for AST-bounded hybrid search. Install the engine directly from the [compiled-intent](https://github.com/vijayanant/compiled-intent) repository:

```bash
cargo install --git https://github.com/vijayanant/compiled-intent.git --tag v0.1.0
```

### 2. Pull Ollama Embedding & Models
ArchEval uses local vector embeddings via LanceDB:

```bash
# 1. Required: 768-dimension local embedding model
ollama pull nomic-embed-text

# 2. Pull evaluation models (or evaluate any model you already have)
ollama pull qwen2.5-coder:14b
ollama pull gemma3:12b
```

### 3. Setup Environment
Setup requires Python 3.10+. You can sync dependencies using [`uv`](https://github.com/astral-sh/uv), or run `./setup.sh`:

```bash
cd ArchEval

# Recommended (uv):
uv sync

# Automated / standard Python fallback:
# ./setup.sh
```

### 4. Running Benchmarks

**Execute the full 12-test benchmark matrix:**
```bash
# Run with default model (Qwen 2.5 Coder 14B):
./scripts/run_benchmarks.sh

# Or evaluate Gemma 3 (12B):
./scripts/run_benchmarks.sh ollama/gemma3:12b

# Or evaluate ANY local model you have:
./scripts/run_benchmarks.sh ollama/<your-model>
```

**Run individual tasks (without re-running the entire suite):**
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

### 5. Parse Results
Extract and display the 4x3 summary matrix from the evaluation logs:

```bash
uv run python scripts/parse_results.py [model_name]
# or: python3 scripts/parse_results.py [model_name]
```

---

## Repository Structure

```text
compiled-intent-research/
├── compiled-intent.md       # Manuscript source (pure Markdown)
├── template.tex             # Custom LaTeX pandoc template
├── figures/                 # Standalone TikZ / pgfplots figure sources
│   ├── fig1_lifecycle.tex
│   ├── fig2_architecture.tex
│   ├── fig3_efficiency.tex
│   └── fig4_attention_bleed.tex
├── ArchEval/                # Inspect AI empirical benchmark suite
│   ├── datasets/            # 117 benchmark items & frozen Akshara specs
│   ├── tasks/               # 4 canonical Inspect AI task runners
│   ├── scripts/             # run_benchmarks.sh and parse_results.py
│   └── setup.sh             # Fast environment bootstrapper
└── build/                   # Compiled figures & manuscript build artifacts
```
