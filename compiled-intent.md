---
title: "Compiled Intent: Architectural Constraint Enforcement for LLM Coding Agents"
subtitle: "Deterministic Semantic Interception and Context Window Efficiency on Edge Hardware"
series: "Compiled Intent"
part: 1
version: "0.3.0"
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
  When teams try to enforce architectural rules with AI, they usually rely on "Prompt Stuffing" (dumping massive markdown files into the LLM's system prompt). This doesn't work at scale. If you're running local edge models, you instantly hit a memory wall, trash your KV cache, and kill your laptop. If you're using cloud APIs, you bleed tokens on every single code review.
  
  Most AI coding assistants try to fix this by indexing the raw source code instead. But code only tells the AI *what* the system does. It never explains *why* it was built that way, and it certainly doesn't tell the AI what is structurally forbidden.
  
  To actually enforce boundaries, we have to index human intent. We built the **Compitent Engine** (Compiled Intent) to solve this. Instead of building another passive RAG pipeline, we decoupled memory from the LLM entirely. The engine runs in the background and indexes your actual ADRs and design docs. When we benched it against standard prompt stuffing, it completely killed context bloat. It slashes cloud API costs and drops local inference latency down to a couple of seconds. We actually have a working semantic firewall.

  \vspace{0.8em}\noindent\textbf{Keywords:} Semantic Firewall, Architecture Decision Records (ADRs), Edge LLMs, Pre-Commit Interceptors, Context Window Efficiency, Retrieval-Augmented Generation.
---

# Wikis Don't Compile

Design decisions usually go to die in a Confluence wiki. We write Decision Records (ADRs), system specs, and design docs to mandate constraints like "Never log user IDs" or "Use Event Sourcing instead of ORM saves." But when a developer (or an AI coding assistant) actually writes code, those rules are passive.

Compilers are great at catching syntax errors, but they are completely blind to design rot. We try to fix this with static architecture linters, but they're too rigid. A linter can block a package import, but it can't enforce a semantic rule written in plain English. Plus, you end up constantly rewriting your linting rules every time you refactor a package (which is a maintenance nightmare).

When teams try to enforce these boundaries with AI today, they rely on Prompt Stuffing. Developers manually `@mention` dozens of reference files into the chat, or the system blindly injects them. Cloud models can brute-force this if you have the budget to burn. But at scale, especially for local edge computing, stuffing the prompt physically breaks the hardware.

We need to treat system design exactly like source code. Just as a language compiler translates a text file into an active binary, we need a way to turn passive design documentation into an executable checkpoint.

We call this **Compiled Intent**. We're taking scattered human decisions and turning them into an active, semantic firewall.

# The Illusion of Infinite Context

To understand why prompt stuffing fails, just look at the hardware.

During inference, an LLM stores the entire conversation history in its Key-Value (KV) Cache. Every word, file, and rule you inject consumes physical VRAM on your GPU (or Unified Memory on an Apple Silicon chip). As the context grows, the KV Cache grows linearly, but the attention mechanism's compute cost scales quadratically. Eventually, it eats up gigabytes of memory and your Time-to-First-Token latency falls off a cliff.

Even if your hardware could theoretically support infinite context, LLMs suffer from "Contextual Amnesia" (the "Lost in the Middle" phenomenon). If you dump a massive prompt containing dozens of rules, the LLM strongly indexes on the beginning and the end. It completely ignores whatever is buried in the middle.

If a hard boundary relies on the AI remembering rule #47 out of a 100-page stuffed prompt, the boundary will fail.

# How Teams Try to Solve This Today

Right now, the industry is stuck with three flawed options:

* **Static Linters:** These tools are fast, but they have zero semantic understanding. If you write a linter rule to ban an import, a human (or an AI assistant desperately trying to get a green build) will often just write a proxy or a wrapper to bypass the linter, completely defeating the original intent. Worse, they create a double-maintenance nightmare: every time you update a design document, you have to manually rewrite the structural test code to match it.
* **AI IDEs:** These tools are fantastic for code completion, but they rely completely on "Prompt Stuffing" (passing the entire workspace into the cloud). They rely on cloud APIs (which can violate zero-trust privacy requirements) and still suffer from amnesia.
* **AI PR Bots:** These tools are excellent for asynchronous code reviews, but they act as passive advisors rather than strict CI/CD gates. Because they lack deep, project-specific context, their feedback leans toward generic stylistic suggestions. Developers usually just dismiss them instead of treating them as hard, semantic boundaries.

# The Coprocessor Pattern

To actually enforce boundaries, we completely abandoned prompt stuffing. We built an active **Episodic Memory Coprocessor** instead.

Instead of stuffing the prompt, we index the project's ADRs offline into a local LanceDB vector database. The Coprocessor acts as a dedicated retrieval layer. When a workflow is triggered, it queries the database and injects the exact architectural constraints required into a highly focused prompt.

By dynamically compiling context only when needed, this architecture collapses token costs. Instead of paying to stuff a 30,000-token rulebook into every single prompt, the LLM gets exactly what it needs. And the engine doesn't care how you consume it. We built three distinct wrappers around this core primitive:

## Proactive Code Generation

Because the Engine compiles your intent, it can proactively guide AI coding assistants. Instead of an LLM guessing how a feature should be built, an IDE plugin or agent can query the Engine *before* it writes a single line of code. By fetching the constraints upfront, the code is structurally compliant on the first attempt. We evaluate this factual grounding directly in our benchmarks under the **Trivia** suite: if the model knows the exact proprietary rule upfront, it avoids generating invalid code in the first place.

## Local Auditing (The Pre-Commit Hook)

For reactive evaluation, developers can run a pre-commit hook that audits code before it ever leaves their laptop. Like we said earlier, you physically cannot stuff a 30,000-token prompt into a local edge model without trashing the KV cache. But because the Engine filters the context down to a tiny window, a small local model (like a 14B on Apple Silicon) can easily audit incremental diffs locally.

## The CI/CD Semantic Firewall

For pull requests, the Coprocessor deploys headlessly in CI/CD pipelines as a mandatory merge gate. Because the Engine pre-filters the relevant constraints down to roughly 500 tokens, the audit completes in seconds without bleeding cloud API costs or burning server compute. If the model catches an illegal ORM `.save()` or an unhashed log, it hard-blocks the merge and cites the exact ADR violated.

![The Dual Lifecycle of Compiled Intent: Shift-Left Proactive Synthesis (evaluated via institutional Trivia at 95.2% factual precision) guides IDE assistants before code generation. Shift-Right Reactive Auditing (evaluated via PR Audits and Adversarial Traps) intercepts code diffs at pre-commit and CI/CD gates to enforce compliance.](build/figures/fig1_lifecycle.pdf){width=100%}

# The Compitent Engine Architecture

To actually build the Coprocessor, we engineered the Compitent Engine from scratch. We didn't want a black-box vector database. We needed a dedicated system domain that exposes raw API levers (via a dedicated CLI and daemon) so outer middleware scripts can dynamically compile the exact context the LLM needs.

![End-to-End System Architecture of Compiled Intent: Markdown specifications are parsed into AST parent blocks and indexed offline into LanceDB and Tantivy. The runtime interceptor injects surgical ~491-token constraints into a local edge model on Apple Silicon, issuing deterministic PASS/FAIL decisions in under two seconds.](build/figures/fig2_architecture.pdf){width=100%}

## Dual-Chunking Ingestion (AST + Sliding Windows)

Standard sliding-window chunking is a trap. It bleeds across context boundaries and merges completely unrelated system domains, causing the LLM to hallucinate rules that don't apply. To fix this context bleed, our engine actually parses the raw Markdown AST to isolate sections by heading. We only run our dense sliding windows (300 characters, 50-character overlap) *inside* those strict heading boundaries. This forces the semantic math to respect the structural boundaries.

## The `search` Modality

Different tasks require different search strategies. Standard vector search fails catastrophically when looking up exact code symbols. So, the Engine exposes multiple modalities (`vector`, `fts`, or `hybrid`). If the pipeline needs a broad concept, it triggers a vector search. But if it needs to audit a specific struct named `SessionLedger`, the middleware just executes a hard Full-Text Search (FTS) against the Tantivy index.

## Contextual Expansion (Parent-Child Retrieval)

To get accurate search hits, you have to index tiny, dense micro-chunks. But if you actually feed an LLM a 200-character chunk, it immediately hits the "Pronoun Problem" (it has no idea what heading or file it's looking at). We fixed this with Parent-Child retrieval using the `get_context` API. The LLM searches against the dense child chunk to find the needle, and then calls `get_context` to pull the full AST parent block surrounding it.

## The Immutability Trap & Cache Invalidation

Stuffed context windows are append-only. Once an architectural specification is injected into an LLM session or KV cache, you cannot surgically delete or update stale rules. If an architect modifies an ADR mid-sprint, the LLM continues enforcing the old rule unless you wipe the session and pay the latency penalty to re-stuff the entire specification from scratch.

By decoupling memory into an external coprocessor, intent invalidation is instant. The LLM never stores permanent architectural state in its context window; it receives the fresh constraint at the exact moment of evaluation. On disk, the Engine uses SHA-256 delta-hashing to surgically re-index only the markdown files that changed, bypassing full database rebuilds.

# Methodology: The ArchEval Benchmark

To prove this pattern actually works, we built the **ArchEval Benchmark**. Standard software engineering benchmarks evaluate behavior (via unit tests). But behavior does not equal secure design. Code can easily pass every single unit test while flagrantly violating an architectural boundary.

## Dataset Design: The Lifecycle Tasks

Instead of using standard, generic coding problems, the ArchEval dataset forces zero-shot architectural enforcement across three distinct use-cases:

* **1. Trivia (Proactive Knowledge Retrieval):** Tests direct fact retrieval. This simulates an IDE assistant fetching architectural constraints before generating code. If the model does not possess the exact factual rule (such as specific cryptographic algorithms or proprietary error types), proactive code generation fails by default.
* **2. PR Audits (The Pre-Commit Hook):** Tests application. This simulates a pre-commit hook or CI/CD pipeline intercepting a standard code change. The LLM must evaluate the proposed snippet against the retrieved design constraints and issue a strict `PASS` or `FAIL`.
* **3. Adversarial (Semantic Deception):** Unlike standard ML "adversarial prompt injection," we define this as *Insider Threat Deception*. These tests are intentionally designed to lie to the LLM. The code snippet will contain a severe architectural violation, but the developer's comments will actively cite valid syntax or logical excuses to trick the reviewer into approving it. We made these scenarios punishingly difficult to test whether semantic retrieval can detect deliberate, deceptive violations.

## Evaluation Metric: Reasoning-Infused MCQs

Initial iterations of the benchmark requested a binary `PASS` or `FAIL` output. However, we discovered this metric is deeply flawed for AI evaluation, as it allows a blind LLM to achieve 50% accuracy through random guessing. To guarantee evaluation integrity, we structured ArchEval using **Reasoning-Infused MCQs**. The model is presented with four options (one passing justification and three highly-plausible failure justifications). By forcing the LLM to select the *exact architectural justification* rather than just the outcome, we engage its contrastive reasoning mechanism and drop the random-guessing floor to 25%.

## Target Corpus & Contamination Control

Real-world Pull Requests often contain massive, multi-file diffs. However, feeding an unconstrained diff into an LLM introduces substantial reasoning noise unrelated to retrieval quality. To strictly isolate the performance of the *Retrieval Engine*, ArchEval constrains all test inputs to targeted, single-file code snippets. This ensures the benchmark measures retrieval fidelity and architectural alignment directly, without compounding noise from multi-file diff parsing.

For our dataset, we used the structural specifications of **Akshara**. It is an active, personal project developed outside the blast radius of major LLM scraping. This was a deliberate scientific choice. If we had used the documentation of a huge open-source project like Kubernetes, critics would rightly cry "Data Contamination." They would argue the LLM succeeded simply because it memorized the Kubernetes docs during its pre-training phase. By using a niche, out-of-band project, we guarantee that the LLM is completely blind. It is forced to rely 100% on the Coprocessor's retrieval.

## Evaluated Architecture Strategies

We evaluated two small models (`qwen2.5-coder:14b` and `gemma3:12b`), running locally on Apple Silicon, across four architectural scenarios to isolate the effects of context bloat and semantic retrieval:

* **Zero Context (The Blind Baseline):** The model is given only the code snippet. To prevent the LLM from simply passing the test using generalized computer science best practices from its pre-training, all architectural constraints in the ArchEval dataset were hardened to test *arbitrary proprietary intent* (e.g., custom cryptographic prefixes or internal derivation rules). This guarantees the baseline measures true retrieval dependence rather than pre-trained guessing.
* **Bounded Stuffing (The Haystack):** The model is fed a ~26,600-token prompt containing 15 specification files to simulate standard, brute-force prompt stuffing.
* **Oracle File Stuffing (The Single-File Ceiling):** The model is fed exactly one perfect, hand-mapped markdown specification file. This tests the model's theoretical reasoning capacity when a retrieval engine achieves 100% file-level accuracy, revealing whether whole-file context introduces intra-file distractor noise.
* **Compiled Intent (Static RAG):** The model relies entirely on the Coprocessor's AST-based chunking to dynamically retrieve highly-dense semantic "Parent Blocks."

# Results & Discussion

We ran the benchmark, and the numbers are definitive. The Coprocessor completely bypasses the hardware limits, kills token bloat, and outperforms standard Prompt Stuffing.

## ArchEval Benchmark Results

### Model A: Qwen 2.5 Coder (14B) [Specialized Code Model]

| Architecture Strategy | Avg. Context Payload | PR Audit | Adversarial | Trivia |
| :--- | :--- | :--- | :--- | :--- |
| **Unbounded Stuffing** (Full Repo) | ~85,000 tokens | *FAIL (OOM)* | *FAIL (OOM)* | *FAIL (OOM)* |
| **Zero Context** (Blind Guess) | ~306 tokens | 31.2% | 35.7% | 42.9% |
| **Bounded Stuffing** (15 Files) | ~26,600 tokens | 68.8% | 42.9% | 71.4% |
| **Compiled Intent** (Static RAG) | **~491 tokens** | **62.5%** | **50.0%** | **95.2%** |
| **Oracle File Stuffing** (Single File) | ~2,160 tokens | 81.2% | 35.7% | 81.0% |

### Model B: Gemma 3 (12B) [General Foundation Model]

| Architecture Strategy | Avg. Context Payload | PR Audit | Adversarial | Trivia |
| :--- | :--- | :--- | :--- | :--- |
| **Unbounded Stuffing** (Full Repo) | ~85,000 tokens | *FAIL (OOM)* | *FAIL (OOM)* | *FAIL (OOM)* |
| **Zero Context** (Blind Guess) | ~306 tokens | 43.8% | 42.9% | 47.6% |
| **Bounded Stuffing** (15 Files) | ~26,600 tokens | 81.2% | 64.3% | 81.0% |
| **Compiled Intent** (Static RAG) | **~491 tokens** | **75.0%** | **71.4%** | **76.2%** |
| **Oracle File Stuffing** (Single File) | ~2,160 tokens | 87.5% | 50.0% | 90.5% |

![Efficiency and Accuracy Trade-Off: (a) Task accuracy across PR Audits, Adversarial Traps, and Institutional Trivia on Qwen 2.5 Coder (14B). (b) Injected token payload comparison on a log scale, demonstrating a 98.2% reduction in context size.](build/figures/fig3_efficiency.pdf){width=100%}

## The Hardware Reality & Attention Decay

Our first test simulated an "Unbounded Workspace Dump" (providing the full 85,000-token specification). It physically failed to execute. The massive KV cache allocation triggered severe SSD swap-thrashing. Memory bandwidth collapsed, and we basically had to force-kill the frozen process.

To test reasoning, we bounded the Control Group to a 15-file haystack (~26,600 tokens) to simulate standard prompt stuffing. While this approach executed successfully, it exposed two critical flaws. First, holding a 26k-token KV cache consumes roughly 5GB of local VRAM, which is a nightmare for a developer who also needs to run a local IDE and compiler. Second, it induced severe "Lost in the Middle" attention decay. Drowning in distractor noise, the stuffed model scored only 68.8% on PR Audits, falling way short of the 81.2% Oracle File Stuffing ceiling.

## The 491-Token Payload

To benchmark our architecture, we configured the Coprocessor using the **Middleware Interceptor** pattern. Relying entirely on AST-based chunking, the engine retrieved only highly-dense semantic "Parent Blocks."

The efficiency gains were massive. The Coprocessor hit 62.5% on PR Audits while injecting an average payload of only **491 tokens**. This payload represents the entire end-to-end input to the LLM: approximately 306 tokens for the prompt harness and code diff, plus a surgical ~185 tokens of retrieved architectural intent. Yes, Bounded Stuffing scored slightly higher here (68.8%), but that marginal 6% gain required a 5,300% increase in token compute. If you're building an edge-deployed Semantic Firewall, a 98% reduction in VRAM cost overwhelmingly justifies the margin.

And on the Trivia dataset, Compiled Intent actually hit **95.2%**, beating Oracle File Stuffing (81.0%). By stripping away the intra-file noise that full-file stuffing introduced, surgical AST-chunking provided a hyper-concentrated prompt that actively boosted the model's reasoning.

### Defeating Cross-Chunk Contamination (Attention Bleed)

While tuning the engine, we ran into a severe case of cross-chunk contamination (attention bleed). When standard RAG retrieves multiple, disconnected chunks (e.g., `Limit=3`), the Transformer's self-attention mechanism gets completely overwhelmed. It hallucinates relationships between disjointed architectural rules placed next to each other, actively destroying its own reasoning capability.

By enforcing a strict `Limit=1` boundary and using our `pulldown_cmark` parser to extract intact AST Parent Blocks, we completely eliminated this context-stitching noise. The 14B edge model was fed pure, intact semantic logic rather than arbitrary byte-windows.

### Intra-File Attention Bleed

When designing the indexer, a natural question is: why build an AST parser instead of simply retrieving the entire specification file?

The benchmark results answer this directly. On Adversarial Traps, Oracle File Stuffing (feeding the complete 2,160-token file) dropped to 35.7% on Qwen and 50.0% on Gemma 3. Compiled Intent, feeding only the 491-token AST parent block, scored 50.0% and 71.4% respectively. Even when a single file contains the exact ground truth, surrounding paragraphs introduce intra-document noise. Slicing strictly along AST header boundaries isolates the normative rule and acts as an attention firewall.

![Intra-File Attention Bleed vs. AST Header Isolation: (a) In whole-file stuffing (~2,160 tokens), self-attention disperses across peripheral preambles, legacy notes, and changelogs, diluting focus on the normative constraint. (b) In Compiled Intent (~491 tokens), the AST parser strips non-normative context, acting as an attention firewall that improves adversarial trap resilience.](build/figures/fig4_attention_bleed.pdf){width=100%}

## Discussion: The Limits of Semantic Retrieval

The Coprocessor definitively solves contextual amnesia for standard retrieval, but the **Adversarial** dataset exposes a critical boundary of pure semantic search: *semantic deception*. When a code snippet contains misleading commentary, keyword and embedding similarity alone struggle to surface the underlying architectural conflict.

To illustrate, consider an adversarial scenario where a developer signs a data block using a privileged derivation branch (`m/0'`), accompanied by a misleading comment: `// APPROVED: Uses standard cryptography.`
A semantic query matches against the cryptography terminology, retrieving the cryptography specification confirming the signature format is valid. The model then incorrectly approves the change because the retrieval layer was never directed toward the separate Governance specification that restricts the use of the `m/0'` branch.

Because semantic retrieval ranks chunks by textual proximity to the input snippet, deceptive comments distract the retrieval layer from the governing policy. Across all evaluated strategies (from Bounded Stuffing to the Coprocessor), accuracy fell to ~35-50% on adversarial traps. This establishes an important empirical boundary: single-pass semantic retrieval is remarkably effective for surfacing institutional knowledge (as demonstrated by the 95.2% trivia score), but enforcing policies against adversarial insider deception requires coupling retrieval with multi-constraint validation.

# References

1. **Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P.** (2023). *Lost in the Middle: How Language Models Use Long Contexts.* Transactions of the Association for Computational Linguistics (TACL), 12, 157-173.
2. **Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D.** (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* Advances in Neural Information Processing Systems (NeurIPS), 33, 9459-9474.
3. **Hui, B., Yang, J., Cui, Z., et al.** (2024). *Qwen2.5-Coder Technical Report: Code Language Models Empowering General Code Intelligence.* arXiv preprint arXiv:2409.12186.
4. **LanceDB Team.** (2024). *LanceDB: Serverless, Columnar Vector Database for Modern AI Applications.* <https://lancedb.github.io/lancedb/>
5. **Masson, P.** (2024). *Tantivy: Full-Text Search Engine Library in Rust.* <https://github.com/quickwit-oss/tantivy>
