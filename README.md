# Compiled Intent: Research & Publications

Welcome to the official research repository for the **Compiled Intent** semantic governance engine. This repository houses the source manuscripts, LaTeX formatting files, and the benchmarking harness used to evaluate the engine.

## Research Paper

### Compiled Intent: Architectural Constraint Enforcement for LLM Coding Agents
*Deterministic Semantic Interception and Context Window Efficiency on Edge Hardware*

* **Read the Paper (PDF):** [compiled-intent.pdf](compiled-intent.pdf)
* **Manuscript Source:** [compiled-intent.md](compiled-intent.md)
* **Focus:** This paper explores the physical hardware limits of "Prompt Stuffing" large architectural codebases into local LLMs. It introduces the Episodic Memory Coprocessor as a deterministic semantic firewall, demonstrating how surgical AST-chunked retrieval slashes context payloads to ~491 tokens while achieving 95.2% accuracy on local 14B edge models.

## Repository Structure

* `compiled-intent.pdf`: Research paper preprint (PDF).
* `compiled-intent.md`: Manuscript source (Markdown).
* `ArchEval/`: The `inspect_ai` benchmarking harness used to generate empirical evaluation data. It contains datasets, vector database configurations, tasks, and automated runners.

## Reproducing the Benchmarks

To reproduce the data found in the Results section of the paper, navigate to the `ArchEval` directory:

```bash
cd ArchEval
./setup.sh
./scripts/run_benchmarks.sh
```

*(For detailed benchmark instructions and environment requirements, see `ArchEval/README.md`)*
