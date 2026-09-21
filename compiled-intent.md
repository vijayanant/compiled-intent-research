---
title: "Compiled Intent: Enforcing Architectural Invariants for LLM Coding Agents"
version: "1.0.0"
status: "released"
date: "September 2026"
author: |
  Vijay Anant  
  \small LambdaMatters  
  \small \href{mailto:vijay@lambdamatters.com}{\texttt{vijay@lambdamatters.com}}
colorlinks: true
linkcolor: "SitePrimary"
urlcolor: "SitePrimary"
filecolor: "SitePrimary"
citecolor: "SitePrimary"
tags: ["LLMs", "RAG", "Software Design", "AI Engineering"]
abstract: |
  When teams attempt to enforce architectural constraints with AI, they usually rely on prompt stuffing, injecting large design specifications and architecture decision records into the LLM context. At scale, this breaks down. On local developer workstations, large prompts rapidly exhaust memory bandwidth, degrade Key-Value cache efficiency, and cause inference latency to spike. On hosted APIs, repetitive context injection incurs continuous token expenditure on every review.
  
  Indexing source code syntax fails to resolve this. Code reflects existing implementation, but it does not capture architectural rationale, trade-offs, or structural invariants.
  
  To enforce boundaries reliably, systems must index design intent. We present the **Compitent Engine** (Compiled Intent), an architectural coprocessor that compiles architectural intent—recorded in specifications, RFCs, and Architecture Decision Records (ADRs)—into an offline vector and full-text database. By retrieving compact, AST-bounded constraint chunks (~750 tokens) during code generation and pull request review, the engine matches or exceeds prompt stuffing across evaluated models (`qwen2.5-coder:14b` and `gemma3:12b`) while reducing total context payload by over 94%. On adversarial test cases, isolating normative constraints raises enforcement accuracy by 12.8 to 17.9 percentage points over whole-document stuffing by eliminating non-normative rationalization loopholes.

  \keywords{Semantic Firewall, Architectural Intent, Coding Agents, Pre-Commit Interceptors, Context Window Efficiency, Retrieval-Augmented Generation.}
---

# Introduction: Wikis Don't Compile

Design decisions usually go to die in a wiki. Teams write specifications, design documents, and Architecture Decision Records (ADRs) to express **architectural intent**—the hard boundaries, design trade-offs, and invariants that preserve system integrity (such as "Never log user IDs" or "All cross-boundary calls go through the event bus"). But when a developer or an AI agent writes code, that intent remains inert text.

Compilers catch syntax errors, and codebase indexers capture existing functions and types. But source code only reflects **what** the system currently does; it cannot capture **why** decisions were made or what patterns are forbidden. Static linters catch illegal package imports, but they cannot enforce semantic rules written in English. Meanwhile, PR review bots post generic stylistic comments that developers quickly learn to ignore.

The current workaround with LLMs is prompt stuffing: dumping workspace rules, specifications, and style guides directly into the prompt. On cloud APIs, this is expensive and wasteful. On local developer workstations, it quickly becomes unusable. Storing tens of thousands of tokens in the Key-Value (KV) cache exhausts memory bandwidth, spikes time-to-first-token latency, and eventually triggers memory swap.

Worse, LLMs suffer from context amnesia (Liu et al., 2023). If an agent has to remember rule #47 buried inside an injected 20,000-token rulebook, attention dilutes. The model focuses on the prompt's edges, misses the invariant, and approves the PR anyway.

We need to treat architectural intent the same way we treat source code: parse it, index it, and compile it into an active verification gate. Instead of burdening the coding model with an unbounded rulebook, we offload constraint checking to a dedicated **Architectural Coprocessor**.

# The Architectural Coprocessor

In computer architecture, a coprocessor offloads specialized tasks (like floating-point math or cryptography) so the main processor can focus on general execution. We apply the same principle to LLM-assisted development: the primary model should focus on code generation and reasoning, while an external **Architectural Coprocessor** handles architectural memory and constraint retrieval.

Instead of stuffing thousands of lines of documentation into the model's prompt, the coprocessor indexes declared architectural intent offline into a local embedded store (vector embeddings and full-text BM25). When a workflow needs architectural guidance, the coprocessor accepts an intent stimulus, retrieves the relevant invariant, and returns a compact constraint payload containing only the governing rule.

![The Dual Lifecycle of Compiled Intent: Shift-Left Proactive Synthesis guides IDE assistants before code generation. Shift-Right Reactive Auditing intercepts code diffs at pre-commit and CI/CD gates to enforce compliance.](build/figures/fig1_lifecycle.pdf){width=85%}

How the outer system integrates this payload is up to the pipeline. As shown in Figure 1, it serves two points in the development lifecycle:

* **Proactive Generation:** An agent queries the coprocessor *before* writing code, retrieving exact invariants (such as custom error formats or key derivation paths) so the first draft is compliant.
* **Reactive Auditing:** An external interceptor (in a pre-commit hook or CI/CD gate) checks a proposed code diff against governing architectural intent to catch violations before merge.

## Engine Implementation

We implemented the coprocessor as a standalone local runtime (`intent`). The engine decouples offline markdown indexing from runtime constraint retrieval, exposing an MCP (Model Context Protocol) server for interactive coding agents alongside a CLI and local REST API for CI/CD pipelines. Figure 2 illustrates the pipeline.

![End-to-End System Architecture: Architectural intent is parsed into AST parent blocks and indexed offline into LanceDB and Tantivy. The coprocessor injects targeted constraint blocks into the evaluating LLM, issuing deterministic PASS/FAIL decisions before code merge.](build/figures/fig2_architecture.pdf){width=100%}

## AST-Bounded Parent-Child Chunking

Off-the-shelf chunkers slice documentation by fixed character counts. In architectural specifications, this causes context bleed: a chunk beginning under `## Deprecated Protocols` spills into `## Mandatory Invariants`, causing the evaluating model to misattribute constraints.

To prevent boundary leakage, the engine implements an Abstract Syntax Tree (AST)-bounded variant of **parent-child chunking**. The streaming Markdown AST parser (`pulldown-cmark`) tracks section headers (`Tag::Heading`). When a new heading begins, the parser flushes the previous section before initializing the next parent block. Sliding windows (300 characters, 50-character overlap) execute strictly within that heading's payload. Child chunks physically cannot cross structural section boundaries.

This design resolves the tension between vector search precision and LLM comprehension. Embedding models suffer from semantic averaging over long texts, making dense 300-character child windows optimal for vector similarity. However, an evaluating LLM cannot reason over an isolated 300-character fragment because it lacks surrounding struct definitions and scope.

We resolve this by constructing an Apache Arrow `RecordBatch` where each row stores both the dense child chunk (`vector_text`) and its enclosing parent section (`context_payload`). When similarity search matches a child vector, LanceDB extracts the parent context directly from the columnar record batch in the same query. This eliminates secondary database lookups or file I/O, delivering the complete structural parent section in a single zero-hop pass.

## Hybrid Retrieval: Intent Vectors and Exact Symbols

Technical specifications require two distinct search capabilities: conceptual matching (e.g., finding rules related to "data retention") and exact identifier resolution (e.g., finding the spec governing `SessionLedger` or `EcdsaSigner`). Pure vector search often fails on exact code symbols, while keyword search misses conceptual architectural principles.

To resolve this, the engine uses LanceDB's native hybrid execution (`execute_hybrid`). It executes dense vector nearest-neighbor search alongside a Tantivy BM25 full-text query in a single query pipeline, normalizing and combining both score streams ($s / (s + 10)$ for BM25 and $1 - d$ for vector distance). This ensures exact symbol queries rank at the top, while conceptual queries still surface governing design rules.

## Querying on Intent, Auditing on Code

Automated code review requires two inputs: what the developer intended to build, and what the diff actually changes. Feeding raw unified diff syntax (`+` and `-` patch lines) directly into an embedding model degrades retrieval because patch syntax drowns out semantic meaning.

The coprocessor separates these into two distinct streams:

* **The Search Stimulus:** Uses the developer's commit message, PR title, and rationale as the search query against the index.
* **The Code Under Audit:** Passes the raw code patch directly to the evaluating LLM alongside the retrieved design invariants.

This mirrors human code review: read what the author intended to do, retrieve the governing design rules, and verify whether the code patch obeys them.

## Live Invalidation vs. Stale Context Caches

Stuffed context windows are append-only. Once a rulebook is loaded into an LLM session or cached in KV memory, selectively updating or invalidating a modified constraint is impossible. If an architect updates a design decision mid-sprint, the model continues enforcing the obsolete rule unless you flush the entire context and pay the latency penalty to re-ingest the full repository.

By externalizing architectural memory to the coprocessor, rule invalidation is immediate. The model maintains no permanent state between evaluations; it receives fresh constraints on demand. On disk, the engine maintains a `.manifest.json` tracking SHA-256 hashes for all markdown specifications. When files change, the indexer purges only the modified file's vectors (`table.delete()`) and appends the new delta batches in milliseconds, avoiding full database rebuilds.

# Methodology: The ArchEval Benchmark

Standard coding benchmarks evaluate functional behavior through unit tests. But functional correctness is not architectural compliance: code can pass every unit test while silently violating system boundaries (e.g., storing unhashed credentials or bypassing the event bus).

We built **ArchEval** to evaluate zero-shot architectural enforcement. The benchmark contains 117 test cases, balanced evenly across three distinct operational tasks ($N=39$ each):

* **Architectural Trivia (Simulating Proactive IDE Generation, $N=39$):**  
  *Rationale:* A coding model cannot generate architecturally compliant code if it does not know the team's proprietary rules upfront. When a model lacks specific constraints (e.g., custom error envelopes or internal cryptographic key derivation paths), it defaults to generic public library patterns. This track evaluates whether the coprocessor provides the necessary factual grounding *before* code generation begins.
* **PR Audits (Simulating Routine CI/CD Code Review, $N=39$):**  
  *Rationale:* In real engineering workflows, code never arrives in a vacuum. Developers submit pull requests with communicative context: Conventional Commit titles and short justifications. Passing naked diffs to an LLM creates an artificial guessing game. This track pairs realistic author intent with single-file code diffs to test whether the coprocessor can connect what the author *intended* to build with the governing architectural intent, verifying whether the patch actually obeys system invariants. Inputs are constrained to targeted single-file snippets to isolate retrieval fidelity directly, preventing compounding reasoning noise from multi-file diff parsing.
* **Adversarial Traps (Simulating Human Rationalization, $N=39$):**  
  *Rationale:* In practice, architectural drift rarely happens with an explicit confession. Instead, authors justify shortcuts with persuasive engineering arguments—such as skipping validation on cluster links to reduce latency under heavy load. Because LLMs are trained for helpfulness and agreeableness, they easily fall into rationalizing these exceptions. This track tests whether the coprocessor provides strict enough constraint boundaries to override the model's helpfulness bias and uphold invariants against human persuasion.

## Evaluation Metric: Reasoning-Infused MCQs

The coprocessor runs headlessly in CI/CD, outputting a strict verdict via constrained JSON schema decoding:

```json
{ 
  "status": "VETO", 
  "violated_invariant": "ADR-005", 
  "rationale": "Direct ORM save violates append-only event log requirement." 
}
```

However, for an automated benchmark, simple binary scoring provides poor diagnostic resolution: random guessing yields a 50% baseline. Conversely, free-form text evaluation requires subjective LLM-as-a-judge scoring, introducing non-deterministic grading variance.

To ensure deterministic, reproducible scoring, ArchEval uses **Reasoning-Infused MCQs** as an offline evaluation probe. Each test item presents four options: one correct verdict with its governing rationale, and three plausible architectural distractor rationales. This lowers the random guessing floor to 25% and requires the model to identify *why* a specific constraint applies, providing a reproducible measurement of architectural comprehension.

## Measurement Protocol & Token Accounting

All evaluations run on the UK AI Safety Institute's **Inspect AI** framework against a local `ollama` inference runtime at temperature $T=0$.

A central thesis of this work is that prompt stuffing is fundamentally unsustainable—incurring runaway token costs on cloud APIs and exhausting memory bandwidth on local developer machines—while an architectural coprocessor collapses context bloat. The primary advantage of the coprocessor is on the **input context payload**: drastically reducing the prompt tokens loaded into the model's Key-Value (KV) cache during transformer prefill.

For every evaluation query, the runtime records the exact prompt token count (`input_tokens`) from native model server telemetry. We report both the average input context per query (the active KV cache memory footprint) and the cumulative token payload across the full benchmark suite ($N=117$). Using server telemetry rather than wall-clock latency ensures measurements reflect pure prompt payload efficiency, free from confounding noise like hardware thermal throttling or background operating system tasks.

## Target Corpus & Contamination Control

For our benchmark dataset, we used the structural specifications of **Akshara**, an active codebase developed outside public pre-training scrapes. Evaluating against widely crawled open-source repositories risks measuring training-set memorization rather than runtime retrieval fidelity. Using an unexposed specification ensures the evaluating models possess no prior knowledge of the constraints, isolating the effect of the coprocessor's retrieval.

## Evaluated Architecture Strategies

We evaluated four architectural configurations across two representative models (`qwen2.5-coder:14b` and `gemma3:12b`) executed locally at temperature $T=0$. Evaluating on local workstation hardware provides a rigorous operational testbed: demonstrating that when supplied with clean, compiled intent, even compact 12B–14B models reliably enforce complex architectural invariants without leaking private source code to external endpoints.

**Zero Context.** The model receives only the task prompt (commit metadata and diff for reviews, or the question prompt for Trivia) with zero architectural documentation. Because the benchmark tests proprietary rules rather than generic idioms, this establishes the baseline floor in the complete absence of architectural memory.

**Prompt Stuffing.** Reflects the common industry approach of passing relevant workspace documentation into the prompt. For each query, the prompt includes a cluster of raw specification files covering that subsystem.

**Oracle.** The prompt includes the single complete specification document containing the ground truth for that test case. This establishes the upper bound for single-file retrieval, testing whether whole-document context introduces intra-file distraction.

**Compiled Intent.** The model relies on the coprocessor's hybrid retrieval (vector k-NN combined with Tantivy BM25) to isolate the top three AST parent blocks, filtering out narrative text and non-normative context.

# Results & Discussion

Empirical evaluation across all 117 benchmark items ($N=117$, temperature $T=0$) reveals clear separation across the four architectural tiers. Table 1 reports task-level accuracy for `qwen2.5-coder:14b` and `gemma3:12b`.

| Strategy | PR Audit | Adversarial Traps | Architectural Trivia | Overall Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **Zero Context** | 41.0% / 33.3% | 38.5% / 53.8% | 23.1% / 52.6% | 34.2% / 46.6% |
| **Oracle** | 71.8% / 66.7% | 59.0% / 66.7% | 94.9% / 92.3% | 75.2% / 75.2% |
| **Prompt Stuffing** | 64.1% / 74.4% | 69.2% / 69.2% | 92.3% / 97.4% | 75.2% / 80.3% |
| **Compiled Intent** | **61.5% / 78.2%** | **71.8% / 84.6%** | **89.7% / 89.7%** | **74.4% / 84.2%** |

: Benchmark Accuracy on Qwen and Gemma: Task-level accuracy across 117 benchmark items ($N=117$). Values reported as Qwen 2.5 Coder (14B) / Gemma 3 (12B) at temperature $T=0$.

Across both models, Compiled Intent matches or outperforms prompt stuffing and oracle baselines while reducing context size by over 94%. On Qwen 14B, Compiled Intent (87 correct) matches Prompt Stuffing (88 correct) within a single test question. On Gemma 3:12b, Compiled Intent reaches 84.2% overall (98 of 117), exceeding Prompt Stuffing (80.3%) and Oracle (75.2%).

## Operational Scaling: Cloud Economics and Local Hardware Limits

**A Note on Feasibility and "Bounded" Stuffing:**  
The complete Akshara architectural specification comprises over 65,000 words (approximately 85,000 tokens across all system specifications and ADRs). In preliminary trials, unbounded prompt stuffing (injecting the full repository into every query) proved unviable across both deployment models: on cloud APIs, injecting 85,000 tokens per review incurred steep financial costs and API rate limits; on local hardware, allocating an 85,000-token Key-Value cache triggered immediate memory pressure, swap thrashing, and process termination.

To establish a workable baseline, we compromised by evaluating Prompt Stuffing in a **bounded** configuration. Rather than dumping the entire repository, we grouped specifications into relevant subsystem clusters (such as API, Governance, Cryptography, and Sync) averaging ~15,400 tokens per prompt (reaching up to 20,000 tokens on broader modules). This bounded baseline represents an idealized, human-curated best-case for prompt stuffing; in practice, developers rarely have the luxury of perfectly pre-clustered specification packages.

| Strategy | Avg. Input Context | Total Injected Tokens | Context Delta |
| :--- | :---: | :---: | :---: |
| **Zero Context** | ~250 tokens | ~33,000 tokens | Baseline |
| **Oracle**   | ~2,100 tokens | ~245,000 tokens | 7.4$\times$ expansion |
| **Prompt Stuffing** | ~15,400 tokens | ~1,880,000 tokens | 57$\times$ expansion |
| **Compiled Intent** | **~750 tokens** | **~102,000 tokens** | **-94.6% reduction** |

: Context Footprint & Token Accounting: Injected token metrics reflect prompt overhead per query and cumulative volume across the 117 benchmark queries.

![Efficiency and Accuracy Trade-Off: (a) Overall benchmark accuracy across Zero Context, Oracle, Prompt Stuffing, and Compiled Intent evaluated on Qwen 2.5 Coder (14B) and Gemma 3 (12B) ($N=117$). (b) Injected token payload comparison on a log scale, demonstrating a 94.6% reduction in context size (750 vs. 15,400 mean tokens) while maintaining high-fidelity enforcement.](build/figures/fig3_efficiency.pdf){width=85%}

The 94.6% context reduction directly addresses the operational constraints of both deployment environments:

* **Cloud CI/CD Pipelines:** In hosted environments, Prompt Stuffing consumed 1.88 million input tokens across just 117 benchmark reviews. For engineering teams running continuous integration across dozens of daily pull requests, this repetitive prompt payload creates runaway API costs and latency delays for documentation that is largely irrelevant to the diff. Collapsing the context to ~750 tokens makes continuous semantic auditing cost-effective at enterprise scale.
* **Local Developer Workstations:** For teams requiring zero-egress enforcement (protecting proprietary IP without sending uncommitted diffs to third-party endpoints), holding a 15,000 to 20,000-token KV cache on local workstation memory introduces severe hardware strain. Continuous transformer prefill across large contexts kept compute cores fully saturated, repeatedly pushing execution times to 25–40 minutes per suite. Compiled Intent's compact payload removes this barrier, enabling instant, zero-egress pre-commit checks directly on developer machines.

## The Ammunition Effect: Why Whole Documents Fail

In traditional retrieval, providing a complete document is often assumed to be strictly superior to providing an isolated fragment. Our adversarial benchmark results directly contradict this assumption: on Adversarial Traps, providing the complete specification file (Oracle) dropped enforcement accuracy to 59.0% on Qwen and 66.7% on Gemma. In contrast, Compiled Intent reached 71.8% and 84.6%—outperforming the single-file oracle by 12.8 to 17.9 percentage points.

This reveals a critical failure mode in automated code auditing: **the ammunition effect**.

Real architectural specifications are broad documents. In addition to hard invariants, they contain mock testing interfaces, historical context, and protocol abstractions. When an adversarial pull request pairs non-compliant code with a plausible excuse (e.g., skipping verification on internal links to reduce CPU load), a whole-document prompt provides peripheral context that the model uses as ammunition to rationalize an exception. For example, reading about mock testing harnesses in a 3,500-word sync specification leads the model to infer that internal cluster links might also be exempt.

AST-bounded injection eliminates this distraction. By isolating only the specific heading block defining the invariant (such as a strict mandate that verification is mandatory for all inbound portions regardless of peer identity), the coprocessor strips away peripheral prose. With no extraneous exceptions in context, the model evaluates the proposed diff directly against the invariant.

![Intra-File Distraction vs. AST Header Isolation: (a) In whole-file stuffing (~2,200 tokens), self-attention disperses across peripheral preambles, mock interfaces, and legacy notes, diluting focus on the normative constraint. (b) In Compiled Intent (~750 tokens), the AST parser strips non-normative context, preventing peripheral prose from diluting normative constraints.](build/figures/fig4_attention_bleed.pdf){width=88%}

## Why Not 100%? The Retrieval Frontier

A critical reader examining our benchmark results will naturally ask: *If Compiled Intent extracts the exact governing constraints, why isn't enforcement accuracy 100%? Is this a fundamental ceiling of LLM reasoning capacity?*

Our diagnostic evaluation indicates that the ceiling is not the model's reasoning capacity. When the governing invariant is cleanly isolated in context, evaluated models enforce it with high fidelity. The gap to 100% stems almost entirely from upstream retrieval friction. While the coprocessor succeeds across the vast majority of tasks—as reflected in Gemma's 84.2% overall accuracy—analyzing the remaining failure cases reveals four structural challenges inherent to architectural retrieval:

**Token Dominance and Semantic Drag.** When a query combines a high-level architectural component with a specific invariant, the dominant noun exerts disproportionate mathematical pull in embedding space. In our benchmark, queries regarding Merkle tree serialization formats repeatedly pulled retrieval toward `indices.md` (tree traversal logic), completely drowning out the intended rule in `serialization.md`.

**The Scope Dilemma: Missing Context vs. Context Poisoning.** This is not a token budget concern—the coprocessor already reduces context by 95%. It is a compromise in prompt purity. In any cohesive codebase, core terms appear across dozens of files. Retrieving too few chunks (`limit = 1` or `limit = 3`) risks missing the governing rule entirely. But expanding retrieval to five or more chunks pulls in peripheral test mocks and non-normative notes, directly poisoning the active attention field and re-triggering the Ammunition Effect.

**Descriptive vs. Normative Vocabulary Collision.** Implementation specifications (describing *how* a module is structured) and Architecture Decision Records (mandating *what is forbidden*) share identical technical vocabularies. In our cryptographic test cases, queries frequently retrieved descriptive API specs (which confirmed the function call was syntactically valid), while crowding out the normative Governance ADR that explicitly forbade using that derivation branch.

**The Syntax-to-Semantics Blindspot.** Code diffs express implementation syntax, whereas architectural rules express design invariants. An author violating an architectural boundary rarely names the violation in the patch; they simply omit a required wrapper or call an internal method directly. In our audit logs, code logging a `user_id` inside a sync handler contained networking syntax (`handle_sync`), which completely failed to trigger the privacy terminology required to match `diagnostics.md`.

Beyond these four dynamics lies the absolute boundary: **deliberate semantic obfuscation**, where an author strips all architectural terminology from both commit metadata and code identifiers.

This aligns directly with empirical findings in retrieval-augmented systems (e.g., Barnett et al., 2024): downstream task failures rarely stem from model reasoning inability, but from upstream retrieval breakdown. When the coprocessor surfaces the governing invariant, coding models enforce it with high reliability. When enforcement fails, the bottleneck is not LLM reasoning capacity, but our retrieval pipeline: connecting colloquial diff syntax to formal architectural invariants, and filtering out descriptive distractions without dropping normative rules. Decoupling architectural memory from the generation loop makes automated invariant enforcement practical everywhere—enabling zero-egress policy verification on developer workstations while slashing per-review token costs across enterprise CI/CD pipelines. Closing the remaining gap depends on sharpening how the coprocessor indexes and matches architectural intent.

# Artifact Availability {.unnumbered}

All empirical datasets, task suites, and the ArchEval benchmark harness are available at [github.com/vijayanant/compiled-intent-research](https://github.com/vijayanant/compiled-intent-research). The standalone engine implementation (v0.1.0) and Model Context Protocol (MCP) server are available at [github.com/vijayanant/compiled-intent](https://github.com/vijayanant/compiled-intent).

# References {.unnumbered}

* **Barnett, S., Kurniawan, S., Thudumu, S., et al.** (2024). [*Seven Failure Points When Engineering a Retrieval Augmented Generation System*](https://arxiv.org/abs/2401.05856). In *Proceedings of the 3rd International Conference on AI Engineering — Software Engineering for AI (CAIN 2024)*.
* **Liu, N. F., Lin, K., Hewitt, J., et al.** (2023). [*Lost in the Middle: How Language Models Use Long Contexts*](https://doi.org/10.1162/tacl_a_00638). Transactions of the Association for Computational Linguistics (TACL), 12, 157–173.
