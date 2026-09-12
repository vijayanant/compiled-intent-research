# Developer Walkthrough — Building a Patient Records App

**Status:** Draft — Design Exercise  
**Date:** 2026-04-10  
**Purpose:** Exercise the proposed API design against a real use case to find gaps before writing the formal spec.

---

## The App We're Building

**Clinica** — a lightweight patient records app for small medical practices. A doctor needs to:

- Create patient records with notes, diagnoses, and attachments (lab reports, X-rays)
- Add consultation notes over time
- Share specific patients with a specialist (time-limited, read-only)
- View a patient's history across multiple visits
- Generate an audit trail for compliance
- Work offline in hospitals with poor connectivity
- See when a colleague has also updated a shared patient record

We'll build this from zero. Every line of code below uses the *proposed* API (v0.3, not yet implemented). If something feels wrong, we note it.

---

## Step 1: Initialize the Client

```rust
use akshara::{Client, ClientConfig};

#[tokio::main]
async fn main() -> Result<(), akshara::Error> {
    // One-time setup on first launch
    let config = ClientConfig::new()
        .with_keychain_vault()        // macOS Keychain / iOS Secure Enclave
        .with_sqlite_storage("./clinica.db");

    let client = Client::init(config).await?;

    // First launch generates a 24-word mnemonic.
    // The user MUST write this down. There is no "forgot password."
    println!("Setup complete. Your recovery phrase has been generated.");

    Ok(())
}
```

**What the developer doesn't have to think about:** Key derivation, graph keys, encryption algorithms, signing identities, CID computation, nonce generation, manifest creation. All automatic.

**What the developer still needs to handle:** Recovery phrase presentation. The SDK generates it, but the app decides how to display it (QR code, printable card, etc.).

---

## Step 2: Define the Document Types

This is where the developer makes choices about data shape. Each choice maps to a block-mapping mode.

```rust
use akshara::AksharaDocument;
use serde::{Serialize, Deserialize};
use chrono::DateTime;

// --- Core types ---

#[derive(AksharaDocument, Serialize, Deserialize, Clone)]
struct PatientRecord {
    // Tiny, rarely changes -> inline (zero extra blocks)
    #[inline]
    mrn: String,              // Medical Record Number

    #[inline]
    name: String,

    // Structured, changes occasionally -> one block each
    #[path("demographics")]
    demographics: Demographics,

    #[path("allergies")]
    allergies: Vec<Allergy>,

    // Growing list -> each item gets its own block
    #[path("consultations")]
    #[collection]
    consultations: Vec<Consultation>,

    // Large, rarely accessed -> chunked + lazy
    #[path("imaging")]
    #[lazy]
    #[chunked]
    imaging: Vec<AttachmentRef>,

    #[path("lab_reports")]
    #[lazy]
    #[chunked]
    lab_reports: Vec<AttachmentRef>,
}

#[derive(Serialize, Deserialize, Clone)]
struct Demographics {
    dob: chrono::NaiveDate,
    sex: Sex,
    phone: String,
    emergency_contact: String,
}

#[derive(Serialize, Deserialize, Clone)]
struct Allergy {
    substance: String,
    severity: Severity,
    diagnosed: chrono::NaiveDate,
}

// --- Consultations grow over time, each is independent ---

#[derive(Serialize, Deserialize, Clone)]
struct Consultation {
    id: String,
    date: DateTime<Utc>,
    doctor: String,
    chief_complaint: String,
    assessment: String,
    plan: String,
    medications_prescribed: Vec<String>,
}

#[derive(Serialize, Deserialize, Clone)]
struct AttachmentRef {
    name: String,
    mime_type: String,
    uploaded_at: DateTime<Utc>,
    checksum: String,
}
```

**Design decision analysis:**

| Field | Mode | Rationale |
|---|---|---|
| `mrn`, `name` | `#[inline]` | 10-30 bytes, never change after creation. Zero block overhead. |
| `demographics`, `allergies` | `#[block]` (default) | Medium size, updated occasionally. Independent CID means updating allergies doesn't invalidate demographics. |
| `consultations` | `#[collection]` | Grows over time. Each consultation is independent — two doctors adding consults concurrently won't conflict. |
| `imaging`, `lab_reports` | `#[lazy]` + `#[chunked]` | Large files. Doctor doesn't need them to view the patient summary. Fetch on demand. Each file chunked into 1 MB blocks for mobile sync. |

**A question that arose:** Should `consultations` have an `#[ordered]` annotation to preserve chronological order? Fractional indexing handles this automatically, but the developer might not know that. The derive macro should document this clearly.

---


## Step 3: Hospital Creates the Initial Patient Graph

In the real world, the patient doesn't arrive with a pre-existing Akshara graph. The hospital's intake system creates the initial record — demographics, insurance details, intake forms. Ownership transfers to the patient later.

```rust
// The hospital's client creates the patient graph.
// The hospital is the initial signer — all manifests are signed with the
// hospital's shadow identity until ownership is transferred.
let patient_graph = hospital_client.create_graph("patient-A-0042").await?;

let record = PatientRecord {
    mrn: "A-0042".into(),
    name: "Priya Sharma".into(),
    demographics: Demographics {
        dob: chrono::NaiveDate::from_ymd_opt(1985, 3, 15).unwrap(),
        sex: Sex::Female,
        phone: "+91-98765-43210".into(),
        emergency_contact: "Raj Sharma".into(),
    },
    allergies: vec![Allergy {
        substance: "Penicillin".into(),
        severity: Severity::Severe,
        diagnosed: chrono::NaiveDate::from_ymd_opt(2018, 7, 22).unwrap(),
    }],
    consultations: vec![],        // Empty collection
    imaging: vec![],              // Lazy, not fetched
    lab_reports: vec![],          // Lazy, not fetched
};

patient_graph.insert("record", &record).await?;
patient_graph.flush().await?;
```

**What happened under the hood:**

- `mrn` and `name` -> embedded in the root index block (no separate blocks)
- `demographics` -> 1 block, encrypted with the graph key, signed by hospital's shadow identity
- `allergies` -> 1 block, same
- Manifest signed by the hospital. The authority chain starts here.

**The critical question:** The hospital now holds the graph key. It can decrypt everything. **This is expected — the hospital needs to read the data to treat the patient. But the patient should eventually become the owner.** That's Step 3b.

---


## Step 3b: Transfer Ownership to the Patient

After the patient's Akshara identity is set up (24-word mnemonic generated on their phone), the hospital transfers ownership.

```rust
// HOSPITAL initiates the transfer — signs a transfer manifest
let transfer_token = patient_graph.transfer_ownership(&patient_lakshana).await?;
// The token is signed with the hospital's executive identity.
// It is displayed as a QR code at the reception desk.

// PATIENT scans the QR code on their own device
// They use transfer_with_rotation for a clean break:
let owned_graph = patient_client
    .accept_transfer(&transfer_token)
    .with_key_rotation()   // Re-encrypt all existing blocks
    .await?;

// Result:
// - All future manifests signed by the patient's shadow identity
// - Hospital's signing rights permanently revoked
// - Graph key rotated — hospital can no longer decrypt historical data
// - A transfer manifest is recorded in the chain (auditable)
```

**Why `with_key_rotation()` matters here:** Without rotation, the hospital retains the graph key and can decrypt all historical blocks. With rotation, every block is re-encrypted under a new key derived from the patient's identity. The O(N) cost is acceptable here — patient intake graphs are small, and this happens once.

**What the audit trail shows:** The manifest chain now contains a transfer manifest:

```
Manifest #1 — signed by hospital (intake record)
Manifest #2 — signed by hospital (insurance details)
Manifest #3 — ** TRANSFER OF OWNERSHIP ** — from hospital to patient
Manifest #4 — signed by patient (first consultation added by patient's doctor)
Manifest #5 — signed by patient (lab results)
```

Any auditor can trace exactly when and by whom the graph changed hands.

---

## Step 4: Add a Consultation

```rust
let consult = Consultation {
    id: "consult-001".into(),
    date: Utc::now(),
    doctor: "Dr. Mehta".into(),
    chief_complaint: "Persistent headaches for 2 weeks".into(),
    assessment: "Migraine, likely stress-induced".into(),
    plan: "MRI recommended. Prescribed sumatriptan 50mg PRN.".into(),
    medications_prescribed: vec!["sumatriptan 50mg".into()],
};

// Push to the collection
patient_graph.push("record/consultations", &consult).await?;

// Flush the update
patient_graph.flush().await?;
```

**What changed in the graph:**

- The `consultations` collection gets a new entry with a fractional index (e.g., `"a"`)
- Only the new consultation block is created + the collection index is updated
- The `demographics` block, `allergies` block, and root index keep their CIDs
- A new manifest is signed

**The important part:** If someone else updates `allergies` at the same time, they create a new allergies block and update the root index — but their changes don't touch `consultations`. The two operations are on independent subtrees. No conflict.

---

## Step 5: Read a Patient Record

```rust
// Load the record — this fetches inline fields, demographics, allergies,
// and the consultations collection. Does NOT fetch imaging or lab_reports.
let record: PatientRecord = patient_graph.load("record").await?;

println!("Patient: {} ({})", record.name, record.mrn);
println!("Allergies:");
for allergy in &record.allergies {
    println!("  - {} ({:?})", allergy.substance, allergy.severity);
}
println!("Consultations: {}", record.consultations.len());

// The lazy fields are placeholder handles — they know their path
// but haven't fetched data yet.
if !record.imaging.is_empty() {
    println!("{} imaging files available (not loaded)", record.imaging.len());
}
```

**The developer experience:** They see a typed `PatientRecord` struct. The `Vec<Consultation>` is real data. The lazy fields exist but are empty. No `Vec<u8>`, no manual deserialization, no CID handling.

**Now the doctor clicks "View MRI Scan":**

```rust
// Fetch the lazy imaging references
let imaging_refs = record.imaging.fetch(&patient_graph).await?;

for attachment in &imaging_refs {
    println!("Attachment: {} ({})", attachment.name, attachment.mime_type);
}

// The doctor clicks on a specific PDF — fetch just that file
let mri_bytes = patient_graph
    .fetch_blob("record/imaging/0")  // chunked auto-resolved
    .await?;

// Display or save the file
std::fs::write("./mri_report.pdf", &mri_bytes)?;
```

**Selective loading in action:** The MRI PDF is chunked into ~50 blocks. The doctor can start viewing the first page while the rest downloads. The SDK handles chunk reassembly transparently.

---

## Step 6: Selective Sync on Poor WiFi

```rust
// The doctor is at a rural clinic. WiFi is terrible.
// They need the patient summary, not the 200 MB of imaging.

// Sync only the essential fields
client.sync_scope("patient-A-0042/record/demographics").await?;
client.sync_scope("patient-A-0042/record/allergies").await?;
client.sync_scope("patient-A-0042/record/consultations").await?;

// OR — shorthand: sync everything under "record" except lazy paths
// The SDK knows which fields are #[lazy] and excludes them by default
client.sync_scope("patient-A-0042/record").await?;
// Transfer: 3.2 KB in 1.4 seconds

// Later, on good WiFi, sync the imaging
client.sync_scope("patient-A-0042/record/imaging").await?;
// Transfer: 187 MB in 45 seconds
```

**The gap this exposed:** The SDK needs to know the lazy paths of documents it hasn't even loaded yet. This means the schema (or at least the lazy annotations) must be communicated during sync so the SDK knows what to skip. Either:

- (a) Lazy paths are stored in the index block metadata (structural info is always synced)
- (b) The developer explicitly excludes paths: `sync_scope("record").exclude("record/imaging")`

Option (a) is better — it's automatic. The schema metadata should be part of the index.

---


## Step 7: Cross-Graph Reference — Linking a Consent Form

The practice has a separate "consent" graph per patient. The main record references it.

```rust
// The consent graph exists (maybe created by the front desk)
let consent_graph = client.open_graph("consent-A-0042").await?;

// Store a reference from the patient record to the consent
let consent_ref = consent_graph.link("forms/surgery-consent-001");

// We don't store the consent data itself in the patient graph —
// we store a reference that resolves on demand
record.active_consent = Some(consent_ref);
patient_graph.insert("record", &record).await?;
patient_graph.flush().await?;
```

**Later, when the doctor needs the consent details:**

```rust
if let Some(consent_ref) = record.active_consent {
    let consent: ConsentForm = consent_ref.resolve().await?;
    println!("Consent signed: {}", consent.signed_at);
    println!("Procedure: {}", consent.procedure);
}
```

**What the SDK handles:** Opening the consent graph (via the embedded Lakshana in the `GraphRef`), loading the form at the path, verifying authority across the graph boundary.

**A design question:** What if the doctor doesn't have access to the consent graph? The `resolve()` should return an error that clearly distinguishes "graph not found" from "access denied" from "path doesn't exist within graph." The error hierarchy needs thought.

---

## Step 8: Conflict Handling — Two Doctors Update the Same Patient

Dr. Mehta and Dr. Rao both update the allergies simultaneously. The SDK detects it.

```rust
// The doctor wants to be notified about conflicts (not the default auto-merge)
patient_graph.set_conflict_policy(ConflictPolicy::Notify);
```

Later, after a sync:

```rust
// Check for conflicts
let conflicts: Vec<ConflictEvent> = patient_graph.conflicts().await?;

for conflict in &conflicts {
    println!("Conflict at path: {}", conflict.path);
    println!("  Local version:  {:?}", conflict.mine);
    println!("  Remote version: {:?}", conflict.theirs);
}

// For allergies, the doctor wants to merge — keep both allergy lists
if conflicts.iter().any(|c| c.path == "record/allergies") {
    let local_record: PatientRecord = patient_graph.load("record").await?;
    let remote_record: PatientRecord = patient_graph
        .load_branch("record", Branch::Remote)
        .await?;

    // Merge: union of both allergy lists
    let mut merged = local_record.clone();
    merged.allergies.extend(
        remote_record.allergies.iter()
            .filter(|a| !merged.allergies.iter().any(|b| b.substance == a.substance))
            .cloned()
    );

    // Resolve the conflict
    patient_graph
        .resolve_conflict("record/allergies", &merged.allergies)
        .await?;

    patient_graph.flush().await?;
}
```

**What feels wrong here:** The conflict resolution code is verbose and manual. For a production app, the developer would want a `ConflictPolicy::MergeWith(Box<dyn MergeStrategy>)` where they provide a merge function once and it applies automatically.

**Better API:**

```rust
patient_graph.set_merge_strategy("record/allergies", |local, remote| {
    // Custom merge: union of both lists
    let mut merged = local.clone();
    merged.extend(remote.iter().filter(|a| !merged.iter().any(|b| b.substance == a.substance)));
    merged
});
```

This is more ergonomic than the raw branch-resolution API for common cases.

---

## Step 9: Reactive UI — Watching for Changes

The app has a patient list view that needs to update when records change.

```rust
// Watch for any changes to the patient graph
let mut events = patient_graph.watch("record/").await?;

while let Some(event) = events.next().await {
    match event {
        GraphEvent::DocumentUpdated { path, .. } => {
            // A consultation was added — refresh the timeline
            if path.starts_with("record/consultations") {
                refresh_timeline();
            }
        }
        GraphEvent::Conflict { path, .. } => {
            show_conflict_banner(&path);
        }
        GraphEvent::Synced { manifest_id } => {
            status_bar.set_text(&format!("Synced: {}", manifest_id));
        }
        GraphEvent::Flushed { manifest_id, blocks_created } => {
            status_bar.set_text(&format!("Saved: {} blocks", blocks_created));
        }
    }
}
```

**This enables:** Live collaboration indicators, sync status badges, conflict notifications, auto-refresh on peer changes. All without polling.

**A gap:** The `watch()` stream needs backpressure. If a large sync pulls in 1000 updates, the app shouldn't get 1000 events. It needs debouncing: `watch("record/").debounce(Duration::from_secs(1))`.

---


## Step 10: Patient Shares with a Specialist

The **patient** (now the owner) wants to share their record with Dr. Iyer, a specialist. They grant access for 48 hours, limited to consultations and imaging only — demographics stays private.

```rust
// Dr. Iyer's Lakshana (obtained from a professional directory or QR code)
let iyer_lakshana = "akshara1q...";

// The PATIENT's device grants scoped, time-limited access
let grant = owned_graph.grant_access(GrantBuilder::new()
    .to_recipient(&iyer_lakshana)
    .read_only()
    .scope_prefix("record/consultations")
    .build()
).await?;

let grant2 = owned_graph.grant_access(GrantBuilder::new()
    .to_recipient(&iyer_lakshana)
    .read_only()
    .scope_prefix("record/imaging")
    .build()
).await?;

// The grants produce portable tokens
let token = grant.to_token();
// Sent to Dr. Iyer via secure channel (email, messaging, etc.)

// Dr. Iyer redeems the token on their own device:
let shared_patient = doctor_client.accept_grant(&token).await?;

// Dr. Iyer can read consultations and imaging, but NOT demographics
let consults: Vec<Consultation> = shared_patient
    .load("record/consultations")
    .await?;

// Demographics is outside the granted scope
let result = shared_patient.load("record/demographics").await;
assert!(matches!(result, Err(akshara::Error::AccessDenied { .. })));
```

**What's happening under the hood:** The SDK creates lockboxes containing the graph key (or subtree key), encrypted with Dr. Iyer's public key. The lockbox is scoped to the path prefix. After 48 hours, the lockbox expires and Dr. Iyer's client can no longer decrypt new data. Old data remains decryptable only if cached locally — the grant controls *access to the graph*, not *possession of data already fetched*.

**A design question:** Should revocation cut access immediately, or only prevent future sync? If Dr. Mehta revokes Dr. Iyer's access, Dr. Iyer may still have cached data locally. The API should make this limitation explicit:

```rust
let result = patient_graph.revoke_access(&iyer_lakshana).await?;
// result: RevocationReport {
//   effective_immediately: false,  // Can't delete cached data from Iyer's device
//   prevents_future_sync: true,    // Iyer won't receive new data
//   prevents_further_decrypt: true, // New data uses rotated keys
// }
```

---

## Step 11: Audit Trail — Compliance Report

The practice needs to prove to an auditor that every access to patient A-0042's records was authorized.

```rust
let audit = patient_graph.audit().await?;

println!("=== Patient A-0042 Audit Report ===");
println!("Manifest chain length: {}", audit.manifest_count);
println!("Total blocks: {}", audit.block_count);
println!();

for manifest in &audit.manifests {
    println!("Manifest {} — signed by {} at {}",
        manifest.id.short(),
        manifest.signer_fingerprint(),  // Obfuscated path hash
        manifest.created_at
    );
    for check in &manifest.authority_checks {
        match check {
            AuthorityCheck::Passed { signer, path_hash } => {
                println!("  OK {} authorized", signer.fingerprint());
            }
            AuthorityCheck::Failed { reason, .. } => {
                println!("  NO FAILED: {}", reason);
            }
        }
    }
}

// Prove a specific consultation's provenance
let proof: DocumentProof = patient_graph
    .prove("record/consultations/consult-001")
    .await?;

println!("\nProvenance for consult-001:");
println!("  Block CID:      {}", proof.block_cid);
println!("  Signed by:      {}", proof.author_fingerprint());
println!("  Manifest CID:   {}", proof.manifest_cid);
println!("  Authority chain: {} hops, all valid", proof.authority_chain.len());
println!("  Revocation check: {}", proof.revocation_status);
```

**What an auditor gets:** Every block's CID, every signature, every authority verification, every revocation status. The auditor doesn't need to understand cryptography — they get a structured report that their tooling can verify independently (the proof includes raw CIDs and public keys).

---


## What This Walkthrough Revealed

### Things the design handles well

| Area | Verdict |
|---|---|
| **Typed documents** | Clean. `#[derive(AksharaDocument)]` maps struct fields to graph blocks naturally. |
| **Four block modes** | `#[inline]`, `#[block]`, `#[collection]`, `#[chunked]` cover the real data shapes. |
| **Lazy loading** | Doctor loads patient summary without downloading 200 MB of imaging. Natural fit. |
| **Selective sync** | `sync_scope("record/consultations")` works. Lazy exclusions are automatic. |
| **Cross-graph refs** | `GraphRef` with `resolve()` enables linking without data duplication. |
| **Audit/prove** | Compliance reports feel natural on the API surface. |

### Gaps that need design decisions

| Gap | Description | Options |
|---|---|---|
| **Schema in index** | SDK needs lazy paths for documents it hasn't loaded. | Store schema metadata in index block (automatic) vs developer excludes manually (error-prone). **Recommendation: automatic.** |
| **Conflict ergonomics** | Raw branch resolution is too verbose for common merges. | Add `set_merge_strategy(path, fn)` for common cases. Keep raw `resolve_conflict()` for complex ones. |
| **Flush observation** | Developer needs to know when auto-flush happens. | `watch()` stream should include `Flushed` events. Add `last_flush_report()` for imperative access. |
| **Grant revocation semantics** | Revocation can't delete cached data from recipient's device. | The `RevocationReport` must make this limitation explicit. No false promises. |
| **Cross-graph error taxonomy** | `resolve()` can fail in multiple ways. | `Error::GraphNotAccessible`, `Error::PathNotFound`, `Error::RevokedGrant` — distinguish clearly. |
| **Watch backpressure** | Large sync -> 1000 events. App needs debouncing. | `watch().debounce(duration)` or `watch().throttle(count, duration)`. |
| **Collection ordering** | `#[collection]` uses fractional indexing but developer might not know. | Add `#[ordered]` (explicit) or document that collection = ordered by default. |
| **Ownership transfer audit** | Transfer manifest must be findable and verifiable by auditors. | Dedicated `TransferManifest` block type vs a standard manifest with a `transfer` flag. **Recommendation: dedicated block type.** |
| **Key rotation performance** | `transfer_with_rotation()` is O(N). For large graphs this takes minutes. | Background re-encryption with progress reporting vs blocking operation. |

### Things this walkthrough didn't exercise

| Not exercised | Why it matters |
|---|---|
| **Offline-first conflict at scale** | What happens when two devices write offline, then come online? The `ConflictPolicy::Notify` handles detection, but the UI for presenting branches to a non-technical user (doctor, not developer) is the app's problem — the API just needs to surface it clearly. |
| **Large-scale sync pagination** | Syncing 10,000 patients is different from syncing 1. The `sync_scope()` model scales, but resumability of large syncs needs thought. |
| **Schema evolution** | What happens when the doctor adds a new field to `PatientRecord`? Old blocks don't have it. The SDK needs a deserialization strategy (default values, migration, tolerant parsing). |
| **Document deletion semantics** | `graph.delete("record/consultations/consult-001")` — what does deletion mean in an append-only DAG? It creates a tombstone block. The developer needs to understand that "deleted" doesn't mean "gone from history." |

---

## Next Steps

This walkthrough validated the core API shape but exposed 7 specific gaps that the formal spec must address. The next document should be the **formal API specification** — function signatures, trait definitions, error variants, and derive macro behavior — with each of these gaps resolved.

**Certified by:**  
*The Akshara Council of One*
