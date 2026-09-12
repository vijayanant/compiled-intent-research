# The Akshara Developer API — Design Principles

**Status:** Draft — Design Proposal  
**Date:** 2026-04-10  
**Supersedes:** `rust-api.md` (partial), `core-concepts.md` (partial)

---

## Why This Document Exists

The current Akshara API was designed as **"an encrypted filesystem with sync."** That was a useful starting point — it got us from zero to a working kernel. But it is not what Akshara *is*.

Akshara is not a filesystem. It is not a database. It is not a key-value store.

**Akshara is a substrate for building encrypted, interoperable, verifiable applications on top of Merkle-DAGs.**

This document captures the fundamental principles that the developer API must embody. These are not implementation details. They are the *ideas* that every API decision must be measured against.

---

## Principle 1: A Document Is a Pattern Over a Graph

In the current API, the developer writes:

```rust
graph.insert("/meeting-001", big_blob_of_bytes).await?;
```

This makes a meeting look like a file. It is one encrypted blob. To read any part of it, the developer must fetch and decrypt the entire thing. To update one field, the entire blob gets a new CID. To sync, the entire blob transfers.

**This is wrong.**

In Akshara, a "document" — a meeting, a patient record, a case file — is a **pattern of blocks** connected by a shared path prefix. Each field is independently encrypted, independently addressable, and independently syncable.

```
meetings/001/
├── meta/
│   ├── title          ← 1 block, 40 bytes
│   ├── objective      ← 1 block, 300 bytes
│   └── schedule       ← 1 block, 8 bytes
├── participants/      ← 1 block, 500 bytes
├── agenda/            ← 1 block, 2 KB
└── attachments/
    ├── spec.pdf       ← 1 block, 2 MB
    └── diagram.png    ← 1 block, 500 KB
```

**What this enables:**

- Fetch the meeting's title and agenda without downloading the 2 MB PDF
- Update the agenda — only the agenda block gets a new CID; title, participants, and attachments keep theirs
- Sync the meeting's metadata on mobile, skip attachments until on WiFi
- Prove the integrity of just the consent subtree without auditing the entire graph

**The API implication:** The developer should be able to define a document as a *structure* whose fields map to individual blocks. The SDK handles the block lifecycle. The developer sees typed fields.

---

## Principle 2: Selective Sync Is Not Optional — It Is the Default

The current API has one sync operation: "sync the entire graph." For a healthcare platform with 10,000 patient records, this is unusable. For a mobile app on a hospital's terrible WiFi, it is impossible.

**Sync must be scoped to a subgraph.**

```rust
// Sync only the active patient's current records
client.sync_scope("patients/john-doe/current").await?;

// Sync the meeting agenda, skip attachments
graph.sync_scope("meetings/001/agenda").await?;

// Or sync everything (explicit choice)
graph.sync().await?;
```

This is not a "feature" — it is a consequence of the graph model. Each subtree has its own root in the Merkle Index. Syncing a subtree means fetching only the blocks reachable from that root. The SDK already knows how to walk the index. The developer just needs to say *where to start walking.*

**The API implication:** `sync()` should accept a scope (path prefix). The default should be conservative — sync only what the app needs right now.

---

## Principle 3: A Field Is Not a Block — The SDK Chooses the Mapping

The current API implicitly treats every write as "one path = one block." The naive redesign would swing to "one field = one block." **Both are wrong.**

A single struct may contain fields that are 14 bytes, 50 KB, and 50 MB. Forcing all three into the same block strategy produces either wasteful overhead (a 14-byte title gets its own encrypted block) or broken limits (a 50 MB PDF exceeds `max_block_size`).

The SDK must offer **four block-mapping modes**, chosen per field by the developer:

### `#[inline]` — Embedded in the Parent Index

For tiny, rarely-changing fields that don't deserve their own block.

```rust
#[derive(AksharaDocument)]
struct Meeting {
    #[path("meta")]
    #[inline]
    title: String,       // 14 bytes — part of the index block itself

    #[inline]
    status: MeetingStatus, // enum, 1 byte
}
```

These fields are serialized into the Merkle Index node (the `BTreeMap` that `IndexBuilder` builds). No separate block. No separate CID. Changing them changes the index block's CID, which cascades to the manifest — acceptable for fields that rarely change.

### `#[block]` (default) — One Block Per Value

For structured data that benefits from independent addressing.

```rust
#[derive(AksharaDocument)]
struct Meeting {
    #[path("agenda")]
    agenda: Vec<AgendaItem>,  // → 1 block, up to max_block_size
}
```

Serialized, encrypted, signed, stored as one block. Gets its own CID. Synced independently. Conflicts isolated to this field.

### `#[collection]` — Each Item Is Its Own Block

For lists that grow over time.

```rust
#[derive(AksharaDocument)]
struct Meeting {
    #[path("agenda")]
    #[collection]
    agenda: Vec<AgendaItem>,  // each item → its own block
}
```

Each `AgendaItem` gets its own path and block, indexed via fractional indexing:

```
agenda/
├── "a"    ← AgendaItem block
├── "am"   ← AgendaItem block (inserted between "a" and "c")
├── "c"    ← AgendaItem block
└── ...
```

Adding a new item creates one new block + an index update. Existing items keep their CIDs. Two people appending concurrently don't conflict — each gets an independent block.

### `#[chunked]` — Auto-Split Into a Subtree

For large payloads that exceed `max_block_size`.

```rust
#[derive(AksharaDocument)]
struct Meeting {
    #[path("attachments/spec.pdf")]
    #[lazy]
    #[chunked]
    spec_pdf: File,  // 50 MB → ~50 blocks + index
}
```

The SDK splits the payload into chunks (default 1 MB), builds an index tree:

```
attachments/spec.pdf/          ← index block
├── chunk/000                  ← 1 MB block
├── chunk/001                  ← 1 MB block
├── chunk/002                  ← 1 MB block
└── ...
```

The developer sees a single `File` handle. The SDK handles chunking, streaming, and partial fetches. The developer can sync `chunk/000` through `chunk/005` to start viewing the PDF while the rest downloads in the background.

### The Full Picture

```rust
#[derive(AksharaDocument)]
struct Meeting {
    // Tiny, rarely changes → inline
    #[path("meta")]
    #[inline]
    title: String,

    // Structured, medium size → one block
    #[path("meta/objective")]
    objective: String,

    // Collection, grows over time → each item = one block
    #[path("agenda")]
    #[collection]
    agenda: Vec<AgendaItem>,

    // Large, rarely accessed → chunked subtree, lazy-loaded
    #[path("attachments/spec.pdf")]
    #[lazy]
    #[chunked]
    spec_pdf: File,
}
```

**Block count for one meeting:**
- 2 inline fields → 0 blocks (part of index)
- 1 collection (agenda, 5 items) → 5 blocks
- 1 chunked file (50 MB PDF) → ~50 blocks + 1 index
- 1 structured field (objective) → 1 block
- **Total: ~57 blocks, each independently syncable**

### The Developer Escape Hatch

A developer can still choose the wrong mode:

```rust
#[derive(AksharaDocument)]
struct Meeting {
    #[path("everything")]
    data: Vec<u8>,  // dumps 50 MB as one block
}
```

The SDK does not prevent this. But if the block exceeds `max_block_size`, the error is descriptive:

```
Error::BlockSizeExceeded {
    path: "everything",
    size: 52_428_800,
    max: 1_048_576,
    hint: "Consider #[chunked] or #[collection] for large payloads",
}
```

**The API implication:** The derive macro supports four modes — `#[inline]`, `#[block]` (default), `#[collection]`, and `#[chunked]`. The developer picks the annotation that matches their data shape. The SDK handles the block mechanics. `Vec<u8>` remains available for raw access, but the happy path is typed and annotated.

---

## Principle 4: Lazy Fields Are First-Class

Some parts of a document are essential to its identity (a meeting's title, a patient's name). Other parts are optional payload (attachments, images, large datasets).

The developer should be able to mark fields as **lazy** — they exist in the graph, they are part of the document's structure, but they are not fetched on `load()` and not synced by default.

```rust
#[derive(AksharaDocument)]
struct Meeting {
    #[path("meta/title")]
    title: String,

    #[path("agenda")]
    agenda: Vec<AgendaItem>,

    #[path("attachments")]
    #[lazy]
    attachments: LazyField<Vec<AttachmentRef>>,
}

let meeting: Meeting = graph.load("meetings/001").await?;
// attachments NOT fetched yet

// User clicks "view attachments"
let files = meeting.attachments.fetch(&graph).await?;
```

**The API implication:** Lazy is an annotation, not a runtime decision. The SDK knows which fields are lazy and defers their loading. `LazyField<T>` is a handle that can be resolved on demand.

---

## Principle 5: Auto-Commit, Explicit Flush

The current API requires the developer to call `seal()` manually. This has three problems:

1. **`seal()` is O(N)** — it loads the entire graph state, rebuilds the Merkle Index, and signs a manifest. The developer calling `seal()` after every `insert()` creates a performance disaster.

2. **`seal()` is not atomic** — if it crashes halfway, staging still contains the operations. The next seal creates duplicate blocks.

3. **`seal()` is a concept leak** — the developer doesn't care about manifests. They care that their write is "saved."

**The fix:** Writes auto-commit on idle timeout (configurable, default 5 seconds). The developer calls `flush()` when they need determinism (tests, CLI tools, explicit checkpoints).

```rust
// Auto-commits after 5 seconds of idle
graph.insert("meetings/001/meta/title", "Sprint Planning").await?;
graph.insert("meetings/001/agenda", agenda_items).await?;
// ... 5 seconds pass ...
// [Automatically sealed by the runtime]

// Or explicit:
graph.flush().await?;  // Like fsync — seal NOW
```

**The API implication:** `seal()` becomes an internal operation. `flush()` is the public API — it communicates intent (force persistence now) without exposing the Merkle-DAG mechanics.

---

## Principle 6: Conflicts Are a Choice, Not a Surprise

The current API claims "conflicts are events" but surfaces them as errors from `sync()` with no resolution mechanism. The developer has no way to *see* the conflicting versions and no way to *resolve* them.

**Conflicts should be opt-in.** Default behavior is last-write-wins (auto-merge). But the developer can choose to be notified:

```rust
graph.set_conflict_policy(ConflictPolicy::Notify);

let branches: Vec<DocumentBranch<PatientNote>> = graph.branches("notes/001").await?;
// branches[0].mine
// branches[0].theirs
// branches[0].merge(resolved_value) — developer decides
```

**The API implication:** Conflicts are not errors. They are a data type — `DocumentBranch<T>` — that the developer can inspect, display to users, and resolve programmatically.

---

## Principle 7: Sharing Is Capability, Not Pubkey Exchange

The current API's `share_with(pubkey)` is fundamentally wrong. It suggests that sharing is about *identifying the recipient*. But Akshara's sharing model is about *granting a capability*:

- Scoped to a path prefix (can read `/patients/john-doe` but not `/patients/jane-doe`)
- Revocable (the grantor creates a signed revocation manifest; the recipient's SDK sees it on next sync and removes the lockbox)
- Portable (the grantee can present the capability token to any Akshara client)

```rust
let grant = graph.grant_access(GrantBuilder::new()
    .to_recipient(bob_lakshana)
    .read_only()
    .scope_prefix("patients/john-doe/")
    .build()
).await?;

let token: String = grant.to_token();
// Bob redeems it:
let shared = client.accept_grant(&token).await?;

// When access should end — application decides when to revoke
graph.revoke_access(&grant.grant_id).await?;
```

**No time-based expiry.** Access persists until explicitly revoked. The application layer decides *when* — after a consultation, on a schedule, manually. The SDK provides the mechanism; the app provides the policy.

**The API implication:** Sharing is not a method on `Graph`. It is a **grant protocol** — a first-class operation with its own lifecycle, revocation, and audit trail.

---

## Principle 8: The Developer Can Prove Everything

Akshara's promise is "you don't trust the host, you trust the math." But the developer must be able to **show that math to someone else** — a compliance auditor, a judge, a patient.

```rust
// Prove a single document's provenance
let proof: DocumentProof = graph.prove("consents/surgery-001").await?;
// proof contains: document CID → block CID → manifest CID → signer identity
//                  → authority chain → revocation status

// Full graph audit report
let audit: GraphAuditReport = graph.audit().await?;
// Every block, every manifest, every authority check, every revocation
```

**The API implication:** Verification is not hidden in the SDK internals. It is a public API. The developer can generate compliance artifacts without understanding the crypto.

---

## Principle 9: Reactive Is Native, Not Bolted-On

Collaboration apps need to respond to changes in real-time. The current API offers no way to watch for changes. The developer must poll.

**The SDK should expose a change stream:**

```rust
let mut stream = graph.watch("meetings/").await?;
while let Some(event) = stream.next().await {
    match event {
        GraphEvent::DocumentUpdated { path, new_version } => { ... }
        GraphEvent::Conflict { path, branches } => { ... }
        GraphEvent::Synced { manifest_id } => { ... }
    }
}
```

This works for local changes (my own seals) and remote changes (synced from peers). It is the foundation for live collaboration, dashboards, and notification systems.

**The API implication:** `watch(path)` returns a `Stream<GraphEvent>`. It is the primitive that reactive apps are built on.

---

## Principle 10: Graphs Interoperate, Not Just Exist

The vision is a **linked graph ecosystem** — a chat graph references a patient graph which references a consent graph. The developer should be able to create these links and traverse them transparently.

```rust
// Create a reference from one graph to another
let consent_ref = medical_graph.link("patients/john-doe/consents/surgery-001");

// Store the reference in another graph
legal_graph.insert("case-001/patient-consent", consent_ref).await?;

// Resolve it transparently
let consent: ConsentForm = consent_ref.resolve::<ConsentForm>().await?;
```

The SDK handles the cross-graph resolution: opening the target graph (via Lakshana or relay resolution), loading the document, verifying authority across graph boundaries.

**The API implication:** `GraphRef` is a type that holds an Akshara URI (`akshara://[GraphID]/path`) and can resolve to a typed document on demand.

---

## Principle 11: Ownership Transfer Is a Two-Party Protocol

The initial owner of a graph is whoever creates it — a hospital intake system, a company HR tool, a lawyer setting up a case file. But ownership must be transferable to the person it truly belongs to: the patient, the employee, the client.

Ownership transfer is **not** a unilateral action. It is a **two-party protocol** initiated by the current owner and accepted by the new owner. This is distinct from granting access:

| Operation | Granter keeps signing rights? | New owner becomes signer? | Revocable? |
|---|---|---|---|
| `grant_access()` | Yes | No (recipient gets a lockbox, not a signing key) | Yes, at any time |
| `transfer_ownership()` | No | Yes (future manifests signed by new owner) | No — it is permanent |

```rust
// Hospital's system creates the patient graph and populates initial data
let patient_graph = hospital_client.create_graph("patient-A-0042").await?;
// ... insert demographics, intake forms, insurance details ...
patient_graph.flush().await?;

// Transfer ownership to the patient
let transfer_token = patient_graph.transfer_ownership(&patient_lakshana).await?;
// Signed by hospital's executive identity
// Shows as QR code at the reception desk

// Patient redeems it on their own device
let owned_graph = patient_client.accept_transfer(&transfer_token).await?;
// Future manifests signed by the patient's shadow identity
// Hospital's signing rights revoked; hospital is now just a grantee
```

**Two modes of transfer, with explicit trade-offs:**

```rust
// Fast: change manifest signer, keep graph key
// Hospital retains ability to decrypt historical blocks (documented limitation)
owned_graph.transfer_fast(&transfer_token).await?;

// Thorough: rotate graph key, re-encrypt all existing blocks
// Clean break — hospital truly loses all access, including historical data
owned_graph.transfer_with_rotation(&transfer_token).await?;
// O(N) — may take minutes for large graphs
```

The SDK does not hide this trade-off. `transfer_fast` is O(1) but leaves the creator with historical read access. `transfer_with_rotation` is O(N) but provides a clean break. The developer (and the patient) chooses.

**The API implication:** Ownership transfer is a two-part operation — `transfer_ownership()` on the grantor side, `accept_transfer()` on the grantee side. It produces a permanent, auditable transfer manifest that any future auditor can trace.

---

## What Stays the Same

These principles change the *surface* of the API, not the foundation:

- **L0/L1 boundary** — aadhaara remains pure, akshara handles side effects
- **Content addressing** — CIDs, Merkle-DAGs, manifests — all unchanged
- **Cryptographic model** — XChaCha20-Poly1305, Ed25519, BIP-39/SLIP-0010 — all unchanged
- **Sync protocol** — Satyātā grammar, blind verification, authority audit — all unchanged
- **Vault model** — keychain, ephemeral, branch isolation — all unchanged

The kernel is solid. The API is what needs to evolve.

---

## Migration Path

| v0.1 (current) | v0.2 (transitional) | v0.3 (this document) |
|---|---|---|
| `insert(path, bytes)` | `insert(path, bytes)` | `insert::<T>(path, T)` |
| `get(path) → Vec<u8>` | `get(path) → Vec<u8>` | `load::<T>(path) → T` |
| `seal()` | `seal()` + `auto_flush` flag | `flush()` (seal is internal) |
| — | `sync_scope(path)` | `sync_scope(path)` |
| — | `conflicts() → Vec<Conflict>` | `branches(path) → Vec<DocumentBranch<T>>` |
| — | `share_with(pubkey)` | `grant_access(GrantBuilder)` |
| — | — | `transfer_ownership() / accept_transfer()` |
| — | — | `watch(path) → Stream<GraphEvent>` |
| — | — | `history(path) → Vec<DocumentVersion<T>>` |
| — | — | `prove(path) → DocumentProof` |

---

## What This Is Not

This document is **not** an implementation specification. It does not define function signatures, error variants, or trait bounds. Those will be defined in a separate spec document derived from these principles.

This document **is** the design intent. Every future API decision should be tested against these eleven principles:

1. Does this treat a document as a graph pattern, not a blob?
2. Can the developer sync a subtree, not just the whole graph?
3. Does the SDK offer the right block-mapping mode for the data shape — inline, block, collection, or chunked?
4. Can the developer mark fields as lazy?
5. Is commit automatic and flush explicit?
6. Are conflicts a choice, not a surprise?
7. Is sharing capability-based, not identity-based?
8. Can the developer prove integrity to a third party?
9. Can the developer build reactive apps natively?
10. Can graphs reference and traverse each other?
11. Is ownership transfer a two-party protocol with explicit trade-offs?

If the answer to any of these is "no," the design is not yet worthy of the name Akshara.

---

**Certified by:**  
*The Akshara Council of One*
