# Akshara Architecture — As-Built Narrative

> **Purpose:** A structured description of the architectural decisions that define
> Akshara. Each section covers what the architecture is, why it was chosen,
> and the trade-offs inherent in the choice.
>
> This complements the [System Overview](system-overview.md) — which provides
> the high-level elevator pitch — with a deep dive into every architectural
> dimension as it exists in the codebase today.
>
> **Audience:** Developers joining the project, architects evaluating the system,
> and anyone who needs to understand how the pieces fit together before reading
> the specifications or source code.

---

## 1. Layer Architecture

### The Structure

Akshara is partitioned into three strict layers:

| Layer | Crate | Responsibility | Side Effects |
|---|---|---|---|
| **L0: The Math** | `aadhaara` | Crypto, Merkle-DAGs, identity, sync reconciliation | None |
| **L1: The Brain** | `akshara` | Vault, staging, sealing, sync orchestration | All of them |
| **L2: The Pipe** | `relay` | Blind storage and routing (not yet implemented) | Network, disk |

L0 depends on nothing. L1 depends on L0. L2 (when built) will depend on L0 for content verification but never on L1.

### Why This Structure

The "Blind Foundation" mandate requires that the relay can never inspect user data. By making L0 purely mathematical — no I/O, no clock, no filesystem — it becomes independently verifiable, compilable to WASM, and portable across any platform. L1 is where the real world enters: keychains, databases, network sockets, clocks.

### Trade-offs

**Pros:**
- L0 can be independently audited for cryptographic correctness without distraction
- L0 compiles to any target (browser, mobile, embedded) without modification
- Dependency direction is enforced by Cargo — no accidental layer leaks
- Testing L0 requires no mocks (no side effects to simulate)

**Cons:**
- L1 must write `From`/`Into` mappings between L0 types and L1/wire types (boilerplate)
- L0 cannot use convenient utilities that require any form of I/O
- The strict boundary means some natural operations (like "load this block from disk") require a trip through L1

---

## 2. Data Model Architecture

### The Structure

All data flows through a five-level hierarchy:

```
Graph (GraphId = UUIDv4)
  │
  ├── Manifest chain (ManifestId = CIDv1, codec 0x58)
  │     Header: { graph_id, content_root, parents, identity_anchor, signer_path_hash, created_at=0 }
  │     └── Forms its own DAG with parent links (fork/merge history)
  │
  └── Block DAG (BlockId = CIDv1, codec 0x57)
        Block: { author, signature, encrypted content, block_type, parents }
        └── Content blocks form a DAG via parent references
        └── Index blocks (akshara.index.v1) form a hierarchical tree

Merkle Index: BTreeMap<String, Address>
  │  Each entry maps a path segment → child BlockId or leaf Address
  │  Materialized bottom-up as akshara.index.v1 blocks
  └── Root index BlockId → Manifest.content_root
```

**Key design choice:** Manifests and blocks form *separate* DAG chains. A Manifest points to a Block (the content root), but a Block does not point back to a Manifest. This means:
- Manifests can fork and merge independently of block content
- The manifest chain is the "version history"; the block DAG is the "content history"
- They are linked only through `identity_anchor` (manifest → identity graph) and `content_root` (manifest → block DAG)

### Why This Structure

Content-addressed blocks (CIDv1) make every piece of data immutable and deduplicable. The manifest acts as a signed checkpoint — it says "at this point in time, the graph looked like this, signed by this authority." Separating the two chains means you can have multiple concurrent heads (forks) without duplicating the underlying block content.

The `BTreeMap<String, Address>` index tree implements a content-addressed filesystem metaphor. Paths like `/notes/meeting.txt` resolve by walking from the root index block down through child indices to the leaf data block.

### Trade-offs

**Pros:**
- Immutable blocks → simple storage model (content-addressed, no updates)
- Deterministic deduplication → identical content produces identical CIDs
- Separate manifest chain → version history is independent of content structure
- Hierarchical index → path-based navigation, partial resolution

**Cons:**
- `BTreeMap` index is a filesystem metaphor — does not map naturally to relational data, arrays, or ordered sequences
- Fractional indexing (separate module) is needed as a workaround for ordered lists
- Loading current state on every `seal()` requires a full index tree walk (O(N))
- Block DAG parents track edit lineage per-block, not per-path — reconstructing the history of a single path requires walking all blocks and filtering

---

## 3. Identity Architecture

### The Structure

```
24-word BIP-39 mnemonic (Tier 1: Master Root)
  │
  └─→ SLIP-0010 hardened derivation (m/44'/999'/0'/)
        │
        └─→ 6 Functional Branches (Tier 2):
              ├── Branch 0: Legislator — authorize/revoke devices
              ├── Branch 1: Executive — sign manifests daily
              ├── Branch 2: Secret — encrypt graph content
              ├── Branch 3: Handshake — pre-keys for async sharing
              ├── Branch 4: Keyring — cross-device key sync
              └── Branch 5: Discovery — anonymous graph discovery
        │
        └─→ Identity Graph (append-only timeline of credentials)
              ├── /credentials/<pubkey> — authorized device keys
              ├── /revocations/<pubkey> — revoked device keys
              └─→ Serves as the authority chain for all operations

Per-graph Shadow Identities:
  HMAC-SHA256(master_signing_key, "akshara.v1.shadow_identity" ‖ graph_id)
  → Graph-specific signing key, preventing cross-graph signature linkage
```

### Why This Structure

A single-key identity forces the impossible choice between security (key on one device only) and usability (recover from backup). The tiered model separates **Being** (the 24-word master seed, used only for recovery) from **Doing** (branch keys, used for daily operations). Compromise of Branch 1 (Executive) cannot derive Branch 0 (Legislator) — hardened derivation guarantees this.

The Identity Graph is an append-only timeline: you can add credentials and revoke credentials, but never remove history. This means authority is always verifiable by walking the chain from any point back to the genesis.

Shadow identities isolate signing per graph. A signature on graph A's blocks uses a different public key than graph B's blocks. The relay cannot link a user's activity across graphs by observing signing keys.

### Trade-offs

**Pros:**
- 24-word recovery restores entire digital life — no central account recovery needed
- Granular revocation — lose one device, revoke that branch only; others remain valid
- Branch isolation — compromise of one functional key doesn't compromise others
- Cross-graph privacy — shadow identities prevent signature-based activity correlation
- Identity Graph is portable — no server-side registry required

**Cons:**
- Every manifest verification requires an Identity Graph walk — O(N) in the number of credentials
- "Ghost authority" problem: if a signer is revoked, all their past signatures remain mathematically valid. The Frontier Rule (checking revocation at the latest identity, not just the anchor) mitigates this, but requires the latest identity to be explicitly provided
- 24-word mnemonic is the single point of failure — lost means identity permanently unrecoverable
- Executive Provisioning (operating a device with only an Executive key, without the master seed) exists but is not yet fully ergonomic

---

## 4. Cryptographic Architecture

### The Structure

```
┌───────────────────────────────────────────────────────────┐
│  Content Encryption: XChaCha20-Poly1305 (AEAD)            │
│  - GraphKey: 256-bit symmetric key, per-graph             │
│  - Nonce: 192-bit, HMAC-SHA256(key, plaintext) [deterministic]
│  - Associated Data: SHA256(domain ‖ graph_id ‖ author ‖ type ‖ parents)
├───────────────────────────────────────────────────────────┤
│  Signing: Ed25519 (deterministic, strict verification)    │
│  - Per-block signature over BlockId                       │
│  - Per-manifest signature over ManifestId                 │
│  - Shadow identity per graph for isolated signatures      │
├───────────────────────────────────────────────────────────┤
│  Key Sharing: X25519 DH + XChaCha20 (Lockbox)             │
│  - Ephemeral X25519 key per lockbox (forward secrecy)    │
│  - Shared secret → XChaCha20 encryption of GraphKey       │
│  - AD = recipient's public key (prevents replay)          │
├───────────────────────────────────────────────────────────┤
│  Async Handshake: Pre-Key Bundles (Branch 3)              │
│  - Pre-keys derived from Handshake branch                 │
│  - One-time consumption (atomic removal from store)       │
└───────────────────────────────────────────────────────────┘
```

**Algorithm selection:**
- XChaCha20-Poly1305 over AES-GCM: performs well on all CPUs (mobile/edge) without hardware acceleration; 192-bit nonces eliminate nonce management complexity
- Ed25519 over ECDSA: deterministic signatures (no RNG dependence), smaller signatures, faster verification
- X25519 for DH: same curve family as Ed25519, well-vetted, constant-time implementations available
- SHA-256 for content hashing: ubiquity, hardware acceleration on most platforms, sufficient security margin for the foreseeable future

**Content Identifiers (CIDs):** CIDv1 with self-describing multicodec prefixes (0x57 for blocks, 0x58 for manifests). The hash algorithm is part of the identifier, enabling future migration (e.g., SHA-256 → BLAKE3) without invalidating historical data.

### Why This Structure

The cipher suite is chosen for the **user's device**, not the server. XChaCha20 is faster than AES-GCM on phones and laptops without AES-NI. Ed25519 eliminates the catastrophic failure mode of ECDSA nonce reuse. The 192-bit nonce space makes random collision statistically impossible, while the deterministic HMAC derivation enables deduplication.

CIDs provide algorithm agility — the system is not locked into SHA-256 forever. The multicodec prefix tells the verifier which hash was used, so old content remains verifiable even after a migration.

### Trade-offs

**Pros:**
- AEAD with context-bound AD prevents cross-graph replay attacks
- Deterministic nonces enable content deduplication without sacrificing security
- Ed25519 strict verification rejects malleable signatures
- CIDv1 enables future hash algorithm migration
- Lockbox forward secrecy — each lockbox uses a fresh ephemeral key
- Pre-key one-time consumption prevents replay attacks

**Cons:**
- GraphKey serves dual purpose: HMAC key for nonce derivation AND XChaCha20 encryption key. Not ideal key separation hygiene
- Lockbox uses raw X25519 shared secret as XChaCha20 key without HKDF extraction. Acceptable for X25519 output quality but not best practice
- Ed25519 strict verification relies on crate default behavior; not explicitly documented or enforced
- SHA-256 for content hashing is not post-quantum secure (true of all current choices)

---

## 5. Sync Architecture

### The Structure

Akshara uses **symmetric convergence** — both peers have data the other lacks, and both share simultaneously:

```
Sync Turn:
  1. Exchange Heads (manifest CIDs with no children)
  2. Reconciliation (Nirūpana):
     - BFS ancestor walk from each peer's heads → known set
     - Set difference → peer_surplus and self_surplus
     - Expand surplus to full address Delta (manifests + block DAG)
  3. Fulfillment (Pradāna):
     - Yield Portions in heads-first order (manifests before blocks)
     - Stream through transport (supports backpressure)
  4. Convergence:
     - Recalculate CID from portion data (blind verification)
     - Audit manifest authority against identity graph
     - Ingest into local store
     - Update identity anchor if identity graph manifest detected
```

**DoS protections:**
- Input heads limited to 1024
- Output delta limited to 100,000 addresses
- MAX_HEADS = 50 in the store

**The Blind Model:** The relay does not have the graph key, so it cannot decrypt index blocks to recursively expand the Delta. `expand_to_delta` walks parent blocks and the content root, but cannot descend into the Merkle Index tree. The SDK must guide deeper sync iteratively.

### Why This Structure

Traditional client-server sync assumes the server is the source of truth. Akshara has no server-side truth — the relay is blind. Symmetric convergence means any two devices can sync directly, with or without a relay. The reconciliation model is based on set operations over content-addressed identifiers: if you know the CIDs, you know what you're missing.

Blind verification — recalculating the CID before ingest — prevents a malicious relay from injecting fabricated content. The authority audit — verifying the signer was authorized at the time of signing — prevents revoked devices from contributing data.

### Trade-offs

**Pros:**
- Works SDK↔Relay or SDK↔SDK (P2P) — topology independent
- Symmetric convergence — no "server decides what's correct"
- Blind verification — relay cannot poison the store with forged CIDs
- Authority audit — revoked signers cannot contribute data
- Functional telemetry — every sync yields a structured report
- Reverse topological ordering — manifests delivered before blocks (verify authority before ingesting data)

**Cons:**
- O(N) BFS ancestor walk for every reconciliation — does not scale to large graphs
- No fingerprint-based skip lists, bloom filters, or range-limited sync
- Blind model means index trees cannot be recursively expanded by the relay — requires client-guided iterative sync for deep structures
- Portion ordering is "manifests first, then blocks" but not true reverse topological order within each category
- Cancellation safety gap: if sync is interrupted mid-stream, some data is stored but the sync is incomplete — no atomic rollback
- No conflict detection or resolution logic — converging on data is implemented; detecting semantic conflicts is not

---

## 6. Trust Architecture

### The Structure

Every piece of data encountered during traversal is audited through three tiers:

```
Tier 1: Mathematical Integrity
  ├─ Verify hash: calculated_id == stored_id
  └─ Verify signature: author.public_key.verify(id, signature)

Tier 2: Path-Aware Purpose Enforcement
  └─ Genesis manifests (identity_anchor == null) MUST be signed by
     a Legislator at derivation path m/44'/999'/0'/0'/0'
     (verified via SHA-256 hash of the path, compared to signer_path_hash)

Tier 3: Social Authority (Causality)
  └─ IdentityGraph.verify_authority(signer_pubkey, anchor_root_key)
       ├─ Walk identity graph from anchor
       ├─ Find credential entry for signer
       ├─ Verify no revocation exists between credential and anchor
       └─ If latest_identity is provided, re-check at frontier (Frontier Rule)
```

The **Frontier Rule** is critical: if a signer was authorized at the identity_anchor point but has since been revoked (a newer credential exists at the latest_identity), the signature is rejected. This closes the "ghost branch" attack where an old signature from a now-revoked device would otherwise be accepted.

### Why This Structure

Most encrypted platforms stop at Tier 1 — "the math checks out." But in a system with revocation, mathematical validity is not enough. A signature from a revoked device is mathematically valid but socially invalid. Tier 3 enforces that authority is a temporal property, not just a cryptographic one.

Tier 2 prevents unauthorized parties from performing administrative actions. Only a Legislator (the master branch) can create a genesis manifest, which is the root of authority for a graph. This prevents an attacker from creating a parallel identity graph with their own credentials.

### Trade-offs

**Pros:**
- Authority is temporal — revocation actually works, not just theoretically
- Frontier Rule prevents old signatures from revoked devices
- Purpose enforcement prevents unauthorized administrative actions
- Existence verification prevents "ghost pointer" resolution

**Cons:**
- Authority check is at the manifest level only — blocks ingested during sync skip independent authority audit
- The `latest_identity` must be explicitly provided to the Auditor — it is not automatically fetched
- Identity Graph walk is O(N) in the number of credentials — no caching or indexing
- Shadow identity verification adds another O(N) loop: for each credential, the shadow key must be recomputed and compared

---

## 7. Storage Architecture

### The Structure

```rust
trait GraphStore: Send + Sync {
    async fn put_block(&self, block: &Block) -> Result<(), AksharaError>;
    async fn get_block(&self, id: &BlockId) -> Result<Option<Block>, AksharaError>;
    async fn put_manifest(&self, manifest: &Manifest) -> Result<(), AksharaError>;
    async fn get_manifest(&self, id: &ManifestId) -> Result<Option<Manifest>, AksharaError>;
    async fn get_heads(&self, graph_id: &GraphId) -> Result<Vec<ManifestId>, AksharaError>;
    async fn put_lockbox(&self, lakshana: Lakshana, lockbox: &Lockbox) -> Result<(), AksharaError>;
    async fn get_lockboxes(&self, lakshana: &Lakshana) -> Result<Vec<Lockbox>, AksharaError>;
    async fn put_prekey_bundle(&self, bundle: &PreKeyBundle) -> Result<(), AksharaError>;
    async fn get_prekey_bundle(&self, device_key: &SigningPublicKey) -> Result<Option<PreKeyBundle>, AksharaError>;
    async fn consume_prekey(&self, device_key: &SigningPublicKey, prekey_index: u32) -> Result<Option<EncryptionPublicKey>, AksharaError>;
}
```

The `InMemoryStore` implementation:
- Thread-safe via `Arc<RwLock<HashMap<...>>>` per data domain
- Auto-manages heads: when a manifest is stored, its parents are removed from the heads list, and the new manifest is added
- Enforces `MAX_HEADS = 50` to prevent branch-flooding attacks
- Atomic `consumeprekey` — removes the pre-key from the bundle's internal map in a single lock acquisition

### Why This Structure

The trait covers three domains: graph data (blocks, manifests), head tracking (the frontier of each graph), and cryptography (lockboxes, pre-keys). This keeps the storage interface self-contained — a single trait covers everything the protocol needs from storage.

Head management inside the store (rather than as a separate concern) means the store always has a consistent view of the frontier. When parents arrive after children, the head list is correctly updated.

### Trade-offs

**Pros:**
- Single trait covers all storage needs — no composite interfaces
- Head management is automatic — callers don't need to track frontier state
- MAX_HEADS prevents unbounded fork growth
- Atomic pre-key consumption prevents replay attacks
- Parameterized over `S: GraphStore + ?Sized` — future `SqliteStore` drops in cleanly

**Cons:**
- Head management logic is duplicated inside each storage implementation — every new store must reimplement the same head-pruning algorithm
- `get_block` returns an owned `Block` — clones the entire struct including ciphertext on every read
- No reachability-based garbage collection — all stored data is permanent (in-memory store loses data on restart; a persistent store would accumulate forever)
- No transaction support — `put_block` + `put_manifest` are not atomic, so interrupted writes leave orphan blocks
- No bulk operations — no `put_blocks`, no range queries, no batch reads

---

## 8. Evolution / Codec Agility Architecture

### The Structure

All content identifiers are CIDv1, which self-describe:
- Version: CIDv1 only (CIDv0 rejected)
- Multicodec: 0x57 (Akshara Block) or 0x58 (Akshara Manifest)
- Multihash: SHA-256, 32-byte digest (current default)

The `BlockType` enum uses a reserved namespace registry:
- `akshara.index.v1`, `akshara.data.v1`, `akshara.auth.v1`, `akshara.revocation.v1`, `akshara.trust.v1`, `akshara.succession.v1` — protocol-reserved
- `Custom(String)` — application-defined, must NOT start with `akshara.`

### Why This Structure

Raw hashes are blind — if SHA-256 is broken, the network dies. CIDs embed the algorithm identifier in the content address itself, so the system can support multiple hash algorithms simultaneously. Old content hashed with SHA-256 remains verifiable even after new content uses BLAKE3 or a post-quantum hash.

The reserved namespace prevents application-defined block types from colliding with protocol types. If an app creates a `Custom("akshara.data.v1")` block, it's technically valid but semantically confusing — the validation gap here is noted.

### Trade-offs

**Pros:**
- Hash algorithm migration without data invalidation
- Multi-algorithm coexistence (old and new content can coexist in the same graph)
- Reserved namespace prevents type confusion
- Protocol versioning in domain separators (`"AKSHARA_V1_BLOCK"`, `"AKSHARA_V1_BLOCK_AD"`)

**Cons:**
- No migration tooling — the codebase doesn't yet support re-hashing content from one algorithm to another
- `BlockType::Custom` accepts any string including reserved prefixes — validation gap
- Domain separators are hardcoded strings — changing them requires a protocol version bump with no migration path

---

## 9. Error and Recovery Architecture

### The Structure

The error hierarchy is layered:
- `aadhaara` defines: `AksharaError`, `CryptoError`, `IntegrityError`, `IdentityError`, `StoreError`, `ProtocolError`
- `akshara` defines: `Error`, `VaultError`, `StorageError`
- `akshara::Error` wraps `akshara_aadhaara::AksharaError` via `#[from]`

All errors implement `thiserror::Error` with descriptive messages. Error chains are preserved via `#[source]` and `#[from]` attributes.

### What's Missing

There is no explicit error recovery model:
- If `seal()` is interrupted after `put_block()` but before `clear_committed()`, the store contains blocks and a manifest, but staging still has "pending" operations. The next `seal()` re-applies those operations, creating duplicate blocks.
- If sync is interrupted mid-stream, some manifests/blocks are stored but the sync is incomplete. There is no "resume from checkpoint" mechanism.
- There is no "repair" or "rebuild" operation to detect and clean orphan blocks (blocks not reachable from any manifest head).
- There is no "reconcile store with manifest" operation to detect and fix state corruption.

### Why This Matters

The current architecture assumes writes complete atomically, which they don't in practice. Network failures, process crashes, and disk errors are normal operating conditions. A production system needs explicit recovery paths.

### Trade-offs

**Pros:**
- Rich error types with context preservation
- Proper error chains for debugging
- Idempotent `converge()` — duplicate portions are handled gracefully

**Cons:**
- No atomic commits — interrupted writes leave partial state
- No repair operations — orphan blocks accumulate with no cleanup
- No state reconciliation — no way to detect and fix corruption between store and manifests
- No checkpoint/resume for long-running sync operations

---

*This document describes the architecture as implemented in Akshara v0.1.0-alpha.1, April 2026.*
