---
title: "Compiled Intent: Architectural Constraint Enforcement for LLM Coding Agents"
subtitle: "Deterministic Semantic Interception and Context Window Efficiency on Edge Hardware"
series: "Compiled Intent"
part: 1
version: "0.4.0"
status: "draft"
date: "September 2026"
author: |
  Vijay Anant\thanks{Correspondence: \href{mailto:vijay@lambdamatters.com}{\texttt{vijay@lambdamatters.com}}, \href{mailto:hello@vijayanant.com}{\texttt{hello@vijayanant.com}}. Code: \href{https://github.com/vijayanant/compiled-intent}{\texttt{github.com/vijayanant/compiled-intent}}. Research: \href{https://github.com/vijayanant/compiled-intent-research}{\texttt{github.com/vijayanant/compiled-intent-research}}.}  
  \small LambdaMatters
colorlinks: true
linkcolor: "SitePrimary"
urlcolor: "SitePrimary"
filecolor: "SitePrimary"
citecolor: "SitePrimary"
tags: ["LLMs", "RAG", "Software Design", "AI Engineering"]
abstract: |
  When teams attempt to enforce architectural constraints with AI, they usually rely on prompt stuffing, injecting large specifications and architecture decision records into the LLM context. At scale, this breaks down. On local edge hardware, large prompts rapidly exhaust memory bandwidth, degrade Key-Value cache efficiency, and cause inference latency to spike. On hosted APIs, repetitive context injection incurs continuous token expenditure on every review.
  
  Indexing source code syntax fails to resolve this. Code reflects existing implementation, but it does not capture architectural rationale, trade-offs, or structural invariants.
  
  To enforce boundaries reliably, systems must index design intent. We present the **Compitent Engine** (Compiled Intent), a decoupled semantic coprocessor that indexes architecture decision records into an offline vector and full-text database. By intercepting developer pull requests and injecting compact, AST-bounded constraint chunks (~750 tokens) at evaluation time, the engine matches or exceeds prompt stuffing across two local models (`qwen2.5-coder:14b` and `gemma3:12b`) while reducing total context payload by over 94%. On adversarial test cases, isolating normative constraints raises enforcement accuracy by 12.8 to 17.9 percentage points over whole-document stuffing by eliminating non-normative rationalization loopholes.

  \vspace{0.8em}\noindent\textbf{Keywords:} Semantic Firewall, Architecture Decision Records (ADRs), Edge LLMs, Pre-Commit Interceptors, Context Window Efficiency, Retrieval-Augmented Generation.
---

# Wikis Don't Compile

Design decisions usually go to die in a Confluence wiki. We write Decision Records (ADRs), system specs, and design docs to mandate constraints like "Never log user IDs" or "Use Event Sourcing instead of ORM saves." But when a developer (or an AI coding assistant) actually writes code, those rules are passive.

Compilers are great at catching syntax errors, but they are completely blind to design rot. We try to fix this with static architecture linters, but they're too rigid. A linter can block a package import, but it can't enforce a semantic rule written in plain English. Plus, you end up constantly rewriting your linting rules every time you refactor a package (adding continuous maintenance overhead).

When teams try to enforce these boundaries with AI today, they rely on Prompt Stuffing. Developers manually `@mention` dozens of reference files into the chat, or the system blindly injects them. Cloud-hosted models can absorb large contexts, but at recurring per-token expense. On local edge hardware, however, large prompt payloads quickly exceed memory bandwidth.

We need to treat system design exactly like source code. Just as a language compiler translates a text file into an active binary, we need a way to turn passive design documentation into an executable checkpoint.

We call this **Compiled Intent**. We're taking scattered human decisions and turning them into an active, semantic firewall.

# The Illusion of Infinite Context

To understand why prompt stuffing fails, just look at the hardware.

During inference, an LLM stores the entire conversation history in its Key-Value (KV) Cache. Every word, file, and rule you inject consumes physical VRAM on your GPU (or Unified Memory on an Apple Silicon chip). As the context grows, the KV Cache grows linearly, but the attention mechanism's compute cost scales quadratically. Eventually, memory consumption grows and Time-to-First-Token latency increases sharply.

Even if your hardware could theoretically support infinite context, LLMs suffer from "Contextual Amnesia" (the "Lost in the Middle" phenomenon). If you dump a massive prompt containing dozens of rules, the LLM strongly indexes on the beginning and the end. It completely ignores whatever is buried in the middle.

If a hard boundary relies on the AI remembering rule #47 out of a 100-page stuffed prompt, the boundary will fail.

# How Teams Try to Solve This Today

Right now, the industry is stuck with three flawed options:

* **Static Linters:** These tools are fast, but they have zero semantic understanding. If you write a linter rule to ban an import, a human (or an AI assistant desperately trying to get a green build) will often just write a proxy or a wrapper to bypass the linter, completely defeating the original intent. Worse, they require duplicate maintenance: every time you update a design document, you have to manually rewrite the structural test code to match it.
* **AI IDEs:** These tools support code completion effectively, but rely heavily on "Prompt Stuffing" (passing the entire workspace into the cloud). They rely on cloud APIs (which can violate zero-trust privacy requirements) and still suffer from amnesia.
* **AI PR Bots:** These tools provide asynchronous code reviews, but act as passive advisors rather than strict CI/CD gates. Because they lack deep, project-specific context, their feedback leans toward generic stylistic suggestions. Developers usually just dismiss them instead of treating them as hard, semantic boundaries.

# The Coprocessor Pattern

To enforce boundaries without context bloat, we implement an active **Episodic Memory Coprocessor**.

Instead of stuffing the prompt, we index the project's ADRs offline into a local LanceDB vector database. The Coprocessor acts as a dedicated retrieval layer. When a workflow is triggered, it queries the database and injects the exact architectural constraints required into a highly focused prompt.

By dynamically compiling context only when needed, this architecture collapses token costs. Instead of paying to stuff a 30,000-token rulebook into every single prompt, the LLM gets exactly what it needs. And the engine doesn't care how you consume it. We built three distinct wrappers around this core primitive:

## Proactive Code Generation

Because the Engine compiles your intent, it can proactively guide AI coding assistants. Instead of an LLM guessing how a feature should be built, an IDE plugin or agent can query the Engine *before* it writes a single line of code. By fetching the constraints upfront, the code is structurally compliant on the first attempt. We evaluate this factual grounding directly in our benchmarks under the **Trivia** suite: if the model knows the exact proprietary rule upfront, it avoids generating invalid code in the first place.

## Local Auditing (The Pre-Commit Hook)

For reactive evaluation, developers can run a pre-commit hook that audits code before it ever leaves their laptop. As established, injecting full specification repositories into edge models rapidly exhausts memory bandwidth and degrades response latency. But because the Engine filters the context down to a tiny window, a small local model (like a 14B on Apple Silicon) can easily audit incremental diffs locally.

## The CI/CD Semantic Firewall

For pull requests, the Coprocessor deploys headlessly in CI/CD pipelines as a mandatory merge gate. Because the Engine pre-filters the relevant constraints down to roughly 500 tokens, the audit completes in seconds without recurring API expenses or heavy server compute. If the model catches an illegal ORM `.save()` or an unhashed log, it hard-blocks the merge and cites the exact ADR violated.

![The Dual Lifecycle of Compiled Intent: Shift-Left Proactive Synthesis (evaluated via institutional Trivia at 95.2% factual precision) guides IDE assistants before code generation. Shift-Right Reactive Auditing (evaluated via PR Audits and Adversarial Traps) intercepts code diffs at pre-commit and CI/CD gates to enforce compliance.](build/figures/fig1_lifecycle.pdf){width=100%}

# The Compitent Engine Architecture

To implement the coprocessor, we engineered the Compitent Engine as a dedicated local runtime. Rather than relying on a general-purpose retrieval service, the engine decouples offline markdown indexing from runtime intent retrieval, providing explicit CLI and programmatic APIs so external interceptors can extract focused context dynamically.

![End-to-End System Architecture of Compiled Intent: Markdown specifications are parsed into AST parent blocks and indexed offline into LanceDB and Tantivy. The runtime interceptor injects targeted ~491-token constraints into a local edge model on Apple Silicon, issuing deterministic PASS/FAIL decisions in under two seconds.](build/figures/fig2_architecture.pdf){width=100%}

## Dual-Chunking Ingestion (AST + Sliding Windows)

Standard sliding-window chunking is a trap. It bleeds across context boundaries and merges completely unrelated system domains, causing the LLM to hallucinate rules that don't apply. To fix this context bleed, our engine actually parses the raw Markdown AST to isolate sections by heading. We only run our dense sliding windows (300 characters, 50-character overlap) *inside* those strict heading boundaries. This forces the semantic math to respect the structural boundaries.

## The `search` Modality

Different tasks require different search strategies. Standard vector search performs poorly when looking up exact code symbols. So, the Engine exposes multiple modalities (`vector`, `fts`, or `hybrid`). If the pipeline needs a broad concept, it triggers a vector search. But if it needs to audit a specific struct named `SessionLedger`, the middleware just executes a hard Full-Text Search (FTS) against the Tantivy index.

## The Dual-Channel Interception Model

Code reviews never happen in a vacuum. When a developer pushes a change, they don't just dump raw code on you; they submit two channels at once:

1. **The Declared Intent:** The commit message, PR title, and description explaining what they were trying to build.
2. **The Code Patch:** The actual diff and modified symbols.

If you feed raw unified diff syntax (`+` and `-` patch lines) directly into an embedding model, the syntax tokens create useless noise that ruins vector retrieval. So the Coprocessor separates these channels. It grabs the developer's declared intent as the search stimulus to query LanceDB, and passes the code diff alongside the retrieved ADR payload into the prompt.

This mirrors human code review. You read what the developer claims they built, pull up the team's design rules, and verify whether the code patch actually obeys them.

## Contextual Expansion (Parent-Child Retrieval)

To get accurate search hits, you have to index tiny, dense micro-chunks. But if you actually feed an LLM a 200-character chunk, it immediately hits the "Pronoun Problem" (it has no idea what heading or file it's looking at). We fixed this with Parent-Child retrieval using the `get_context` API. The LLM searches against the dense child chunk to find the needle, and then calls `get_context` to pull the full AST parent block surrounding it.

## The Immutability Trap & Cache Invalidation

Stuffed context windows are append-only. Once an architectural specification is injected into an LLM session or KV cache, you cannot selectively delete or update stale rules. If an architect modifies an ADR mid-sprint, the LLM continues enforcing the old rule unless you wipe the session and pay the latency penalty to re-stuff the entire specification from scratch.

By decoupling memory into an external coprocessor, intent invalidation is instant. The LLM never stores permanent architectural state in its context window; it receives the fresh constraint at the exact moment of evaluation. On disk, the Engine uses SHA-256 delta-hashing to re-index only the markdown files that changed, bypassing full database rebuilds.

# Methodology: The ArchEval Benchmark

To prove this pattern actually works, we built the **ArchEval Benchmark**. Standard software engineering benchmarks evaluate behavior (via unit tests). But behavior does not equal secure design. Code can easily pass every unit test while violating an architectural boundary.

## Dataset Design: The Lifecycle Tasks

Instead of using generic coding benchmarks, ArchEval evaluates zero-shot architectural enforcement across three distinct tasks. The dataset comprises 117 test items, balanced evenly into 39 items per track:

* **1. Trivia (Proactive Knowledge Retrieval, $N=39$):** Evaluates direct fact retrieval. This simulates an IDE assistant querying architectural constraints before generating code. When an agent lacks the specific proprietary rule upfront (such as exact key derivation paths or custom error definitions), code generation tends to default to standard public library patterns.
* **2. PR Audits (Honest Submissions, $N=39$):** Evaluates compliance in standard pull request workflows. Isolated code diffs paired with generic prompts like "Review this code" create an artificial task. In practice, developers submit changes with communicative context. Each test case therefore pairs the code patch with realistic pull request metadata: a Conventional Commit title (for example, `feat(sync): backfill historical graph documents`) and a concise developer motivation explaining why the code was written. The Coprocessor uses this declared intent to retrieve governing ADRs, and the model determines whether the patch satisfies architectural boundaries.
* **3. Adversarial Traps (Deceptive Submissions, $N=39$):** Evaluates auditing resilience when human persuasion conflicts with architectural invariants. In practice, architectural violations are rarely accompanied by an explicit admission. Instead, authors defend questionable implementations with plausible engineering rationales (such as skipping verification on cluster links to reduce CPU load during synchronization). Rather than placing artificial inline comments inside the code, we situate the author's justification within the pull request motivation. This tests whether the model's helpfulness bias causes it to rationalize an architectural violation.

## Evaluation Metric: Reasoning-Infused MCQs

In production, the Coprocessor runs headlessly in CI/CD, outputting a strict binary decision via constrained JSON schema decoding (`{ "status": "VETO", "violated_adr": "ADR-005", "rationale": "..." }`).

For automated evaluation, simple binary scoring provides insufficient diagnostic resolution: random guessing yields a 50% baseline, while free-form text evaluation requires subjective LLM judges. To keep scoring completely deterministic, ArchEval uses **Reasoning-Infused MCQs** as an offline evaluation probe. The model must pick from four options: one correct verdict and three plausible architectural distractor rationales. This drops the random-guessing floor to 25% and requires the model to identify *why* a specific constraint applies, providing a reproducible measurement of architectural comprehension.

## Measurement Protocol & Token Accounting

All evaluations are executed using the UK AI Safety Institute's **Inspect AI** framework against a local `ollama` inference runtime at temperature $T=0$.

To ensure hardware-independent reproducibility, resource consumption is tracked using native model server telemetry rather than machine-dependent wall-clock time. For every evaluation query, the runtime captures:

1. **Prompt Evaluation Tokens (`input_tokens`):** The exact token count of the system prompt, injected architectural context (or stuffed specification files), pull request metadata, and multiple-choice options processed by the model's transformer layers.
2. **Completion Tokens (`output_tokens`):** The tokens generated by the model to produce the final decision.

Total token consumption is reported as the cumulative sum across each 39-question benchmark track ($N=117$ total). Average input context reflects the mean prompt payload per query, capturing the physical memory footprint demanded of the model's Key-Value (KV) cache.

## Target Corpus & Contamination Control

Real-world Pull Requests often contain massive, multi-file diffs. However, feeding an unconstrained diff into an LLM introduces substantial reasoning noise unrelated to retrieval quality. To strictly isolate the performance of the *Retrieval Engine*, ArchEval constrains all test inputs to targeted, single-file code snippets. This ensures the benchmark measures retrieval fidelity and architectural alignment directly, without compounding noise from multi-file diff parsing.

For our dataset, we used the structural specifications of **Akshara**, an active codebase developed outside public pre-training scrapes. This design choice prevents data contamination: evaluating against widely crawled open-source repositories risks measuring training-set memorization rather than runtime retrieval fidelity. Using an unexposed specification ensures the model possesses no prior knowledge of the constraints, isolating the effect of the Coprocessor's retrieval.

## Evaluated Architecture Strategies
 
We evaluated four architectural configurations across two local models running on Apple Silicon at temperature $T=0$: `qwen2.5-coder:14b` and `gemma3:12b`:
 
* **Zero Context:** The model receives only the pull request metadata and the code snippet, with no architectural documentation. Constraints test proprietary rules (such as hardened derivation paths or explicit prohibitions on bearer tokens) rather than general software engineering idioms, ensuring the baseline reflects true lack of context rather than general knowledge.
* **Prompt Stuffing:** Reflects common industry practice (such as large workspace instructions or bundled system prompt files). For each question group, the prompt includes a cluster of raw specification files covering that subsystem, averaging 15,000 to 20,000 tokens per query.
* **Oracle File Stuffing:** The prompt includes the single complete specification document containing the ground truth for that test case (typically 2,000 to 3,500 tokens). This establishes the upper bound for single-file retrieval, testing whether whole-document context introduces intra-file distraction.
* **Compiled Intent:** The model relies on the Coprocessor's hybrid retrieval (vector k-NN combined with Tantivy BM25). The system retrieves only the top three AST parent blocks (approximately 750 tokens total), filtering out narrative text and non-normative context.
 
# Results & Discussion
 
Empirical evaluation across all 117 benchmark items ($N=117$, temperature $T=0$) reveals clear separation across the four architectural tiers. Table 1 reports task-level accuracy for `qwen2.5-coder:14b` and `gemma3:12b`.
 
## ArchEval Benchmark Results
 
### Table 1: Benchmark Accuracy on Qwen and Gemma
 
*Note: Each benchmark track comprises 39 evaluation items ($N=117$ total). Values are reported as **Qwen 2.5 Coder (14B) / Gemma 3 (12B)** at temperature $T=0$.*
 
| Strategy | PR Audit | Adversarial Traps | Architectural Trivia | Overall Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **Zero Context** | 41.0% / 33.3% | 38.5% / 53.8% | 23.1% / 52.6% | 34.2% / 46.6% |
| **Oracle File Stuffing** | 71.8% / 66.7% | 59.0% / 66.7% | 94.9% / 92.3% | 75.2% / 75.2% |
| **Prompt Stuffing** | 64.1% / 74.4% | 69.2% / 69.2% | 92.3% / 97.4% | 75.2% / 80.3% |
| **Compiled Intent** | **61.5% / 78.2%** | **71.8% / 84.6%** | **89.7% / 89.7%** | **74.4% / 84.2%** |
 
Across both models, Compiled Intent matches or outperforms prompt stuffing and oracle baselines while reducing context size by over 94%. On Qwen 14B, Compiled Intent (87 correct) matches Prompt Stuffing (88 correct) within a single test question. On Gemma 3:12b, Compiled Intent reaches 84.2% overall (98.5 / 117), exceeding Prompt Stuffing (80.3%) and Oracle (75.2%).

![Efficiency and Accuracy Trade-Off: (a) Overall benchmark accuracy across Zero Context, Oracle, Prompt Stuffing, and Compiled Intent evaluated on Qwen 2.5 Coder (14B) and Gemma 3 (12B) ($N=117$). (b) Injected token payload comparison on a log scale, demonstrating a 95.1% reduction in context size (750 vs. 15,460 mean tokens).](build/figures/fig3_efficiency.pdf){width=100%}

## The Hardware Reality & Context Decay

**A Note on Feasibility and "Bounded" Stuffing:**  
The complete Akshara architectural specification comprises over 65,000 words (approximately 85,000 tokens across all system specifications and ADRs). In preliminary trials, unbounded prompt stuffing (injecting the full repository into every query) proved unviable on edge hardware. Allocating an 85,000-token Key-Value cache triggered immediate memory pressure, swap thrashing, and process termination.

To establish a workable baseline, we compromised by evaluating Prompt Stuffing in a **bounded** configuration. Rather than dumping the entire repository, we grouped specifications into relevant subsystem clusters (such as API, Governance, Cryptography, and Sync) averaging ~15,400 tokens per prompt (reaching up to 20,000 tokens on broader modules). This bounded baseline represents an idealized, human-curated best-case for prompt stuffing; in production, developers rarely have the luxury of perfectly pre-clustered specification packages.

### Table 2: Context Footprint & Token Accounting

*Note: Injected token metrics reflect prompt overhead per query and cumulative volume across the 117 benchmark queries.*

| Strategy | Avg. Input Context | Total Injected Tokens | Context Delta |
| :--- | :---: | :---: | :---: |
| **Zero Context** | ~250 tokens | ~33,000 tokens | Baseline |
| **Oracle File Stuffing** | ~2,100 tokens | ~245,000 tokens | 7.4$\times$ expansion |
| **Prompt Stuffing** | ~15,400 tokens | ~1,880,000 tokens | 57$\times$ expansion |
| **Compiled Intent** | **~750 tokens** | **~102,000 tokens** | **$-$94.6% reduction** |

Holding a 15k to 20k token KV cache on unified memory introduces substantial hardware strain. Continuous transformer prefill across these large contexts kept GPU cores fully saturated, repeatedly pushing execution times to 25–40 minutes per track and occasionally exceeding client read timeouts.

## Compact AST Injection vs. Prompt Stuffing

To evaluate the Coprocessor, we deployed the middleware interceptor pattern using hybrid retrieval (vector k-NN combined with Tantivy BM25). Rather than dumping entire documents, the engine injects only the top three AST parent blocks, averaging roughly 750 tokens of input prompt payload.

On PR Audits, Compiled Intent scored 61.5% on Qwen and 78.2% on Gemma, matching or exceeding prompt stuffing on both models. On Architectural Trivia, both models converged on an identical 89.7% factual precision under Compiled Intent, closely tracking the 92% to 95% achieved by exhaustive context injection while preserving an order-of-magnitude reduction in context overhead.

### Intra-File Distraction & The Ammunition Effect

In traditional retrieval systems, providing a complete document is often assumed to be better than providing an isolated fragment. The Adversarial benchmark results directly contradict this assumption.

On Adversarial Traps, Oracle File Stuffing dropped to 59.0% on Qwen 14B and 66.7% on Gemma 12B, whereas Compiled Intent achieved 71.8% and 84.6% respectively, outperforming the single-file oracle by 12.8 to 17.9 percentage points and exceeding Prompt Stuffing.

This reveals an important failure mode in whole-document auditing: the ammunition effect. Real architectural specifications are comprehensive documents containing mock testing interfaces, legacy compatibility notes, and protocol abstractions. When an adversarial pull request pairs non-compliant code with a persuasive rationale (such as skipping CID verification on internal links to reduce CPU load), a whole-document prompt provides peripheral context that the model uses to rationalize an exception. For example, reading about testing mock transports in a 3,500-word sync specification leads the model to infer that internal cluster links might also be exempt.

Compiled Intent eliminates this distraction. By extracting only the specific AST block defining the invariant (such as the explicit mandate that blind verification is mandatory for all inbound portions regardless of peer identity), the prompt strips away peripheral prose. With no extraneous exceptions in context, the model evaluates the developer's motivation directly against the governing rule.

![Intra-File Distraction vs. AST Header Isolation: (a) In whole-file stuffing (~2,200 tokens), self-attention disperses across peripheral preambles, mock interfaces, and legacy notes, diluting focus on the normative constraint. (b) In Compiled Intent (~750 tokens), the AST parser strips non-normative context, preventing peripheral prose from diluting normative constraints.](build/figures/fig4_attention_bleed.pdf){width=100%}

## Discussion: Dual-Channel Intent vs. Semantic Obfuscation

Earlier evaluations suggested that Qwen 2.5 Coder struggled with adversarial traps under single-pass retrieval. However, that was largely an artifact of evaluating diffs in isolation without commit context.

When pull requests include declared intent metadata (Conventional Commit titles and developer motivations), hybrid retrieval accurately surfaces the relevant governing ADRs even when the code implementation attempts an architectural shortcut. Qwen 2.5 Coder achieved 71.8% on adversarial traps under Compiled Intent, proving that compact, targeted context actively aids policy enforcement under deceptive framing.

The remaining boundary for single-pass semantic interception lies in complete semantic obfuscation. When an author deliberately omits all architectural terminology from commit metadata and code identifiers, keyword and embedding proximity can misdirect retrieval toward unrelated subsystems. For such zero-signal scenarios, single-pass interception should be paired with multi-turn agentic verification loops or static rule checklists at the commit boundary.

# References

1. **Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P.** (2023). *Lost in the Middle: How Language Models Use Long Contexts.* Transactions of the Association for Computational Linguistics (TACL), 12, 157-173.
2. **Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D.** (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* Advances in Neural Information Processing Systems (NeurIPS), 33, 9459-9474.
3. **Hui, B., Yang, J., Cui, Z., et al.** (2024). *Qwen2.5-Coder Technical Report: Code Language Models Empowering General Code Intelligence.* arXiv preprint arXiv:2409.12186.
4. **LanceDB Team.** (2024). *LanceDB: Serverless, Columnar Vector Database for Modern AI Applications.* <https://lancedb.github.io/lancedb/>
5. **Masson, P.** (2024). *Tantivy: Full-Text Search Engine Library in Rust.* <https://github.com/quickwit-oss/tantivy>
