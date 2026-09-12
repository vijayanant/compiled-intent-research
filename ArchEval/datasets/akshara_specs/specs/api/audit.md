# Spec 8: Audit

**Status:** Draft — For Review  
**Date:** 2026-04-10  
**Derived from:** [API Design Principles §8](../blueprint/sdk/api-design-principles.md), [Developer Walkthrough](../blueprint/sdk/developer-walkthrough.md)  
**Cross-references:** [Client & Graph](./client-and-graph.md), [Errors](./errors.md), [Sync](./sync.md)

---

## Scope

This spec defines:
- `prove()` — cryptographic provenance for a single document
- `DocumentProof` — the structured proof artifact
- `audit()` — full graph audit report
- `GraphAuditReport` — compliance-grade audit artifact
- Authority chain verification, revocation status, and transfer chain

---

## 1. Document Provenance

### 1.1 `Graph::prove`

```rust
impl Graph {
    /// Generate a cryptographic provenance report for a document at the given path.
    ///
    /// The proof contains the full chain from the document block back to
    /// the identity graph, enabling independent verification by a third party
    /// (auditor, judge, compliance tool).
    pub async fn prove(&self, path: &str) -> Result<DocumentProof, Error>;
}
```

### 1.2 `DocumentProof`

```rust
pub struct DocumentProof {
    /// The path this proof covers.
    pub path: String,

    /// The block ID (CID) of the document at this path.
    pub block_cid: String,

    /// The manifest ID that anchors this block.
    pub manifest_cid: String,

    /// The public signing key of the author (not obfuscated — needed for verification).
    pub author_public_key: Vec<u8>,

    /// The author's BIP-32 derivation path (for auditing, not for key reconstruction).
    pub author_derivation_path: String,

    /// Full chain of manifests from genesis to current, with authority check for each.
    pub manifest_chain: Vec<ManifestProofEntry>,

    /// The identity anchor manifest that establishes the root of authority.
    pub identity_anchor: ManifestId,

    /// Result of the revocation check for the author.
    pub revocation_status: RevocationStatus,

    /// Raw bytes that can be serialized and sent to a third party for
    /// independent verification.
    pub raw_proof_bytes: Vec<u8>,
}
```

### 1.3 `ManifestProofEntry`

```rust
pub struct ManifestProofEntry {
    /// The manifest ID.
    pub manifest_id: ManifestId,

    /// The signer's public key for this manifest.
    pub signer_public_key: Vec<u8>,

    /// Whether the signer was authorized at the time of signing
    /// (present in identity graph and not revoked).
    pub authority_check: AuthorityCheck,

    /// The manifest's parent IDs (DAG edges).
    pub parent_ids: Vec<ManifestId>,

    /// The content root CID (points to the Merkle Index).
    pub content_root: BlockId,

    /// The identity anchor at the time of this manifest.
    pub identity_anchor: ManifestId,

    /// Timestamp from the manifest header (0 for rebirth manifests).
    pub created_at: i64,
}

pub enum AuthorityCheck {
    Passed,
    Failed { reason: String },
}
```

### 1.4 `RevocationStatus`

```rust
pub enum RevocationStatus {
    /// The author is currently authorized (present and unrevoked in the identity graph).
    Authorized,

    /// The author was revoked at some point after signing this block.
    Revoked {
        /// The manifest ID that contains the revocation.
        revoked_at: ManifestId,
    },

    /// Revocation status could not be determined (identity graph incomplete).
    Unknown {
        reason: String,
    },
}
```

### 1.5 Proof Generation Flow

```
graph.prove("record/consultations/consult-001")
    │
    ├─ 1. Resolve path in current manifest → get BlockId
    │
    ├─ 2. Get the manifest that anchors this block
    │     (walk manifest chain until content_root covers the path)
    │
    ├─ 3. For each manifest in the chain (current → genesis):
    │     a. Record manifest metadata (ID, content_root, parents, anchor)
    │     b. Extract signer's public key
    │     c. Run Auditor::verify_manifest_authority() for this manifest
    │     d. Record AuthorityCheck::Passed or AuthorityCheck::Failed
    │
    ├─ 4. Walk the identity graph from the current anchor back to genesis
    │     IdentityGraph::verify_authority() for each signer
    │
    ├─ 5. Check revocation status of the block's author
    │     Walk identity graph for revocation entries matching the author
    │
    ├─ 6. Serialize the complete proof to raw_proof_bytes (DAG-CBOR)
    │
    └─ 7. Return DocumentProof
```

---

## 2. Graph Audit Report

### 2.1 `Graph::audit`

```rust
impl Graph {
    /// Generate a full audit report for this graph.
    ///
    /// This is a compliance-grade artifact suitable for presentation to
    /// an external auditor (HIPAA, SOC2, legal discovery).
    ///
    /// WARNING: This is O(M × D) where M is the number of manifests
    /// and D is the average index depth. For large graphs, this may
    /// take significant time.
    pub async fn audit(&self) -> Result<GraphAuditReport, Error>;
}
```

### 2.2 `GraphAuditReport`

```rust
pub struct GraphAuditReport {
    /// The graph this report covers.
    pub graph_id: GraphId,

    /// The lakshana for external reference.
    pub lakshana: String,

    /// When the report was generated.
    pub generated_at: DateTime<Utc>,

    /// Total number of blocks in the graph (including tombstones and index blocks).
    pub total_blocks: usize,

    /// Total number of manifests in the manifest chain.
    pub total_manifests: usize,

    /// Every manifest in the chain, with authority verification.
    pub manifests: Vec<ManifestAuditEntry>,

    /// Summary of all unique signers observed.
    pub signers: Vec<SignerSummary>,

    /// Ownership transfer events (if any).
    pub ownership_transfers: Vec<OwnershipTransferEntry>,

    /// Active grants (if any).
    pub active_grants: Vec<GrantSummary>,

    /// Revoked grants (if any).
    pub revoked_grants: Vec<GrantSummary>,

    /// Whether every manifest passed authority verification.
    pub all_manifests_authorized: bool,

    /// Manifests that failed authority verification (empty if all passed).
    pub failed_manifests: Vec<ManifestId>,
}
```

### 2.3 `ManifestAuditEntry`

```rust
pub struct ManifestAuditEntry {
    pub manifest_id: ManifestId,
    pub signer_fingerprint: String,   // Obfuscated for readability
    pub created_at: i64,
    pub parent_ids: Vec<ManifestId>,
    pub content_root: BlockId,
    pub identity_anchor: ManifestId,
    pub authority_check: AuthorityCheck,
    pub block_count_under_this_manifest: usize,
}
```

### 2.4 `SignerSummary`

```rust
pub struct SignerSummary {
    /// The signer's public key fingerprint.
    pub fingerprint: String,

    /// Number of manifests signed by this identity.
    pub manifest_count: usize,

    /// Whether this signer is currently authorized (not revoked).
    pub currently_authorized: bool,

    /// If revoked, the manifest that revoked them.
    pub revoked_at: Option<ManifestId>,
}
```

### 2.5 `OwnershipTransferEntry`

```rust
pub struct OwnershipTransferEntry {
    /// The manifest that records the transfer.
    pub transfer_manifest_id: ManifestId,

    /// The previous owner's fingerprint.
    pub from_fingerprint: String,

    /// The new owner's lakshana.
    pub to_lakshana: String,

    /// Whether key rotation was performed.
    pub key_rotated: bool,
}
```

### 2.6 `GrantSummary`

```rust
pub struct GrantSummary {
    pub grant_id: String,
    pub recipient_lakshana: String,
    pub scope_prefix: String,
    pub permissions: GrantPermissions,
    pub granted_at: DateTime<Utc>,
    pub revoked_at: Option<DateTime<Utc>>,
}
```

---

## 3. Independent Verification

### 3.1 Purpose

A third-party auditor (compliance firm, court expert) should be able to verify a `DocumentProof` or `GraphAuditReport` **without** having access to the Akshara SDK or the graph key. The proof contains all public data needed for verification.

### 3.2 Verification Steps (for an external tool)

1. Parse `raw_proof_bytes` (DAG-CBOR) to reconstruct `DocumentProof`
2. For each `ManifestProofEntry`:
   - Fetch the manifest from the relay or local store using `manifest_id`
   - Verify the Ed25519 signature using `signer_public_key`
   - Verify the `authority_check` by walking the identity graph
3. For the document block:
   - Fetch the block using `block_cid`
   - Verify the block's signature using `author_public_key`
   - Verify the block's content is reachable from `content_root` via path resolution
4. Check `revocation_status` by scanning the identity graph for revocation entries

### 3.3 What the Auditor Needs

- Access to the blocks and manifests referenced in the proof (either from the relay or a local copy)
- The identity graph (public data)
- No access to the graph key or any secret material

---

## 4. Design Decisions

### 4.1 Why `prove` is separate from `load`

`load()` returns the deserialized value. `prove()` returns the cryptographic chain that proves the value's integrity and authority. They serve different purposes — one is for reading data, the other is for proving it to a third party. Combining them would make `load()` expensive (it would need to walk the full manifest chain) and would conflate data access with compliance.

### 4.2 Why `audit` is O(M × D)

The audit must visit every manifest and verify every block under it. There is no shortcut — each manifest's authority must be independently verified. For large graphs, this is expensive but necessary for compliance. Pagination or incremental audit is planned for v0.2.

### 4.3 Why `author_public_key` is not obfuscated in proofs

The proof is designed for external verification. An auditor needs the actual public key to verify the Ed25519 signature. The `fingerprint` fields in summaries are obfuscated for human readability, but the proof's raw data is complete and unredacted.

### 4.4 Why ownership transfers are tracked separately

A transfer manifest (`AksharaSuccessionV1` block type) is a significant event in the graph's lifecycle. It changes the root of trust. An auditor must be able to find all transfer points quickly without walking every manifest.

---

## 5. Cross-Reference Index

| Concept | Defined here | Used in |
|---|---|---|
| `prove()` / `DocumentProof` | §1 | [Client & Graph](./client-and-graph.md), [Reactive](./reactive.md) |
| `audit()` / `GraphAuditReport` | §2 | [Client & Graph](./client-and-graph.md) |
| `AuthorityCheck` | §1.3 | [Errors](./errors.md), [Conflicts](./conflicts.md) |
| Independent verification | §3 | — |
| `RevocationStatus` | §1.4 | [Access Control](./access-control.md), [Errors](./errors.md) |

---

**Certified by:**  
*The Akshara Council of One*
