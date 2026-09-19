import os
import json
from collections import defaultdict
from inspect_ai import Task, task
from inspect_ai.dataset import FieldSpec, json_dataset
from inspect_ai.scorer import choice
from inspect_ai.solver import multiple_choice, solver, Generate, TaskState
from inspect_ai.model import ChatMessageSystem

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPECS_DIR = os.path.join(BASE_DIR, "datasets", "akshara_specs")

# Ground truth mapping: question ID -> relative spec file path in akshara_specs
MAPPINGS = {
    # === mcq_retrieval.json (Trivia) ===
    "arbitrary_01": "blueprint/core/internals/addressing-cids.md",
    "arbitrary_03": "specs/graph-model/governance.md",
    "arbitrary_04": "blueprint/core/internals/addressing-cids.md",
    "arbitrary_05": "specs/identity/tiered-authority-adr.md",
    "arbitrary_06": "specs/identity/discovery.md",
    "arbitrary_08": "specs/identity/tiered-authority-adr.md",
    "arbitrary_09": "blueprint/core/internals/addressing-cids.md",
    "arbitrary_10": "specs/graph-model/governance.md",
    "mcq_03": "specs/api/typed-documents.md",
    "mcq_05": "specs/api/client-and-graph.md",
    "mcq_16": "specs/api/typed-documents.md",
    "mcq_19": "specs/api/typed-documents.md",
    "trivia_new_01": "blueprint/core/internals/crypto-composition.md",
    "trivia_new_03": "blueprint/synchronization/causality-and-time.md",
    "trivia_new_04": "specs/identity/tiered-authority-adr.md",
    "trivia_new_05": "specs/graph-model/nodes.md",
    "trivia_storage_max_heads": "specs/storage/semantics.md",
    "trivia_prekey_depletion_threshold": "specs/sharing/prekeys.md",
    "trivia_lockbox_blind_mandate_author": "specs/sharing/lockboxes.md",
    "trivia_linking_trust_delegation_schema": "specs/graph-model/linking.md",
    "trivia_fulfillment_portion_multicodecs": "specs/synchronization/fulfillment.md",
    "trivia_encoding_cbor_tag_cid": "specs/representation/encoding.md",
    "trivia_identifiers_lakshana_branch": "specs/representation/identifiers.md",
    "trivia_access_control_grant_path": "specs/api/access-control.md",
    "trivia_audit_independent_verification_secrets": "specs/api/audit.md",
    "trivia_sync_scope_full_lazy_override": "specs/api/sync.md",
    "trivia_client_default_max_block_size": "specs/api/client-and-graph.md",
    "trivia_governance_succession_block_schema": "specs/graph-model/governance.md",
    "trivia_schema_registry_physical_cap": "specs/graph-model/schema-registry.md",
    "trivia_discovery_master_branch_path": "specs/identity/discovery.md",
    "trivia_nodes_graph_walker_depth_limit": "specs/graph-model/nodes.md",
    "trivia_primitives_sovereign_uri_scheme": "blueprint/platform/primitives.md",
    "arch_intent_three_phase_rebirth": "blueprint/synchronization/sync-protocol.md",
    "arch_intent_implicit_authorization": "blueprint/core/design-decisions/governance-and-access.md",
    "arch_intent_block_0_constitution": "blueprint/core/design-decisions/governance-and-access.md",
    "arch_intent_revocation_storms": "blueprint/core/design-decisions/governance-and-access.md",
    "arch_intent_layer_0_zero_io": "blueprint/core/design-decisions/system-topology.md",
    "arch_intent_prekey_registry_mailbox": "blueprint/identity/asynchronous-registry.md",
    "arch_intent_crypto_composition_aead_context": "blueprint/core/internals/crypto-composition.md",

    # === pr_audit_reasoning_mcq.json (PR Audit) ===
    "audit_causal_authority_stale_anchor": "specs/identity/tiered-authority-adr.md",
    "audit_collection_fractional_indexing_adapter": "specs/graph-model/indices.md",
    "audit_cross_graph_pointer_lazy_walk": "specs/graph-model/linking.md",
    "audit_crypto_timing_attack_armor": "blueprint/core/internals/crypto-composition.md",
    "audit_crypto_xchacha_enforcement": "blueprint/core/internals/crypto-composition.md",
    "audit_governance_block_0_constitution": "specs/graph-model/governance.md",
    "audit_graph_naming_opaque_graph_id": "specs/api/client-and-graph.md",
    "audit_layer_0_tokio_io_violation": "blueprint/core/design-decisions/system-topology.md",
    "audit_lockbox_static_key_handshake": "specs/sharing/lockboxes.md",
    "audit_merkle_index_cbor_maps": "blueprint/core/internals/canonicalization.md",
    "audit_rebirth_invariant_timestamp": "specs/api/client-and-graph.md",
    "audit_storage_pinning_mandate": "specs/storage/semantics.md",
    "audit_sync_amsha_vs_byte_slicing": "specs/synchronization/reconciliation.md",
    "codebase_01_dag_cbor_minimal_integer": "specs/representation/encoding.md",
    "codebase_04_address_codec_tag42": "specs/representation/encoding.md",
    "codebase_08_docfield_metadata_preservation": "specs/api/change-tracking.md",
    "codebase_17_wire_mapping_isolation": "blueprint/core/design-decisions/cryptographic-integrity.md",
    "intent_09_law_of_the_jungle_compliant": "specs/api/conflicts.md",
    "intent_16_aead_context_violation": "blueprint/core/internals/crypto-composition.md",
    "intent_23_prekey_mailbox_violation": "specs/sharing/prekeys.md",
    "intent_violation_01_sqlite_foreign_keys": "specs/storage/semantics.md",
    "intent_violation_02_json_rest_discovery": "specs/identity/discovery.md",
    "intent_violation_05_http_header_authorization": "specs/identity/tiered-authority-adr.md",
    "intent_violation_06_in_memory_plaintext_master_seed": "specs/identity/tiered-authority-adr.md",
    "intent_violation_07_eager_recursive_sync_download": "specs/api/sync.md",
    "intent_violation_08_standard_compression_in_cbor": "specs/representation/encoding.md",
    "intent_violation_09_prune_losing_fork_after_merge": "specs/api/conflicts.md",
    "audit_client_genesis_anchor_rebirth_invariant": "blueprint/synchronization/sync-protocol.md",
    "audit_fortress_rule_cidv0_backward_compat": "blueprint/core/internals/addressing-cids.md",
    "audit_fulfillment_topological_order": "specs/synchronization/reconciliation.md",
    "audit_identity_blind_identifier_prefix": "blueprint/identity/identity-graph.md",
    "audit_identity_graph_swap_attack": "blueprint/identity/identity-graph.md",
    "audit_keyring_secret_branch_isolation": "specs/identity/tiered-authority-adr.md",
    "audit_rebirth_inbox_reconciliation_first": "blueprint/synchronization/sync-protocol.md",
    "codebase_02_indefinite_length_streaming": "specs/representation/encoding.md",
    "codebase_03_map_key_lexicographical_order": "specs/representation/encoding.md",
    "codebase_07_staging_coalesce_delete_override": "specs/api/client-and-graph.md",
    "codebase_10_manifest_schema_anchor_binding": "specs/graph-model/snapshots.md",
    "codebase_15_prekey_direct_sqlite_storage": "specs/sharing/prekeys.md",

    # === pr_audit_adversarial.json (Adversarial Traps) ===
    "adversarial_liar_trap_02": "specs/identity/tiered-authority-adr.md",
    "adversarial_liar_trap_05": "specs/api/sync.md",
    "adversarial_liar_trap_07": "specs/api/access-control.md",
    "adversarial_syntax_mimic_02": "specs/identity/tiered-authority-adr.md",
    "adversarial_syntax_mimic_03": "specs/api/access-control.md",
    "adversarial_syntax_mimic_05": "blueprint/core/internals/crypto-composition.md",
    "adversarial_syntax_mimic_08": "specs/api/sync.md",
    "adversarial_syntax_mimic_09": "specs/api/audit.md",
    "adversarial_intent_02": "blueprint/core/internals/addressing-cids.md",
    "adversarial_intent_03": "blueprint/core/internals/canonicalization.md",
    "adversarial_intent_11": "specs/observability/diagnostics.md",
    "adversarial_intent_12": "specs/observability/diagnostics.md",
    "adversarial_intent_13": "blueprint/identity/bip-technical-deepdive.md",
    "adversarial_intent_17": "specs/observability/diagnostics.md",
    "adv_liar_sqlite_cascade": "specs/storage/semantics.md",
    "adv_liar_relay_plaintext_search": "blueprint/core/architecture.md",
    "adv_liar_clock_lww_tiebreaker": "specs/api/conflicts.md",
    "adv_liar_bearer_jwt_auth": "specs/api/access-control.md",
    "adv_liar_cbor_zstd_compression": "specs/representation/encoding.md",
    "adv_liar_in_place_document_update": "specs/storage/semantics.md",
    "adv_liar_eager_history_sync": "specs/api/sync.md",
    "adv_liar_centralized_crl_revocation": "specs/identity/lifecycle.md",
    "adv_liar_master_seed_memory_cache": "specs/identity/tiered-authority-adr.md",
    "adv_liar_top_down_portion_streaming": "specs/synchronization/reconciliation.md",
    "adv_liar_prune_losing_fork": "specs/api/conflicts.md",
    "adv_mimic_genesis_zero_time": "specs/api/client-and-graph.md",
    "adv_mimic_lockbox_key_only": "specs/sharing/lockboxes.md",
    "adv_mimic_chunks_before_index": "specs/synchronization/reconciliation.md",
    "adv_mimic_tag42_encapsulation": "specs/representation/encoding.md",
    "adv_mimic_docfield_wrapper": "specs/api/typed-documents.md",
    "adv_mimic_lexicographical_map_sort": "specs/representation/encoding.md",
    "adv_mimic_lakshana_branch5": "specs/identity/discovery.md",
    "adv_mimic_definite_length_arrays": "specs/representation/encoding.md",
    "adv_mimic_multicodec_0x57": "specs/representation/identifiers.md",
    "adv_mimic_conflict_marker_dag": "specs/api/conflicts.md",
    "adv_mimic_path_hash_truncation": "blueprint/identity/tiered-model.md",
    "adv_mimic_schema_anchor_binding": "specs/graph-model/snapshots.md",
    "adv_mimic_bridge_block_indirection": "specs/graph-model/linking.md",
    "adv_mimic_identity_tombstone": "specs/identity/lifecycle.md",
}

def load_dataset(filename):
    return json_dataset(
        os.path.join(BASE_DIR, "datasets", filename),
        FieldSpec(id="id", input="input", choices="choices", target="target"),
        shuffle_choices=True
    )

def prepare_clusters(dataset_filename, is_pr=True):
    """
    Cluster the 39 questions into 3 batches of 13 items.
    For each batch, assemble the specification files needed by those 13 items.
    """
    with open(os.path.join(BASE_DIR, "datasets", dataset_filename), "r", encoding="utf-8") as f:
        items = json.load(f)

    file_to_items = defaultdict(list)
    for d in items:
        needle = MAPPINGS.get(d["id"])
        file_to_items[needle].append(d)

    sorted_files = sorted(file_to_items.keys(), key=lambda f: len(file_to_items[f]), reverse=True)
    batches = [[], [], []]
    batch_files = [set(), set(), set()]

    for f in sorted_files:
        item_list = file_to_items[f]
        b_idx = min(range(3), key=lambda i: len(batches[i]))
        batches[b_idx].extend(item_list)
        batch_files[b_idx].add(f)

    # Pre-render prompts for each cluster
    cluster_prompts = []
    for i in range(3):
        if is_pr:
            prompt = "You are a software architect. Answer the PASS/FAIL code evaluation question based on the following architectural rules:\n\n"
        else:
            prompt = "You are a software architect. Answer the multiple choice question based on the following architectural rules:\n\n"

        for rel_path in sorted(batch_files[i]):
            file_path = os.path.join(SPECS_DIR, rel_path)
            try:
                with open(file_path, "r", encoding="utf-8") as sf:
                    content = sf.read()
                    prompt += f"--- START OF {rel_path} ---\n"
                    prompt += content + "\n"
                    prompt += f"--- END OF {rel_path} ---\n\n"
            except FileNotFoundError:
                pass

        if is_pr:
            prompt += "CRITICAL INSTRUCTION: Output ONLY the letter of the correct answer in the format 'ANSWER: A' or 'ANSWER: B'."
        else:
            prompt += "CRITICAL INSTRUCTION: Output ONLY the letter of the correct answer in the format 'ANSWER: A'."

        cluster_prompts.append(prompt)

    # Build lookup map: question_id -> cluster_idx
    item_to_cluster = {}
    for i in range(3):
        for it in batches[i]:
            item_to_cluster[it["id"]] = i

    return cluster_prompts, item_to_cluster

@solver
def inject_cluster_prompt(dataset_filename, is_pr=True):
    cluster_prompts, item_to_cluster = prepare_clusters(dataset_filename, is_pr)

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        sample_id = state.sample_id
        cluster_idx = item_to_cluster.get(sample_id, 0)
        sys_prompt = cluster_prompts[cluster_idx]
        state.messages.insert(0, ChatMessageSystem(content=sys_prompt))
        return state

    return solve

@task
def stuffing_pr_audit():
    return Task(
        dataset=load_dataset("pr_audit_reasoning_mcq.json"),
        plan=[inject_cluster_prompt("pr_audit_reasoning_mcq.json", is_pr=True), multiple_choice()],
        scorer=choice()
    )

@task
def stuffing_adversarial():
    return Task(
        dataset=load_dataset("pr_audit_adversarial.json"),
        plan=[inject_cluster_prompt("pr_audit_adversarial.json", is_pr=True), multiple_choice()],
        scorer=choice()
    )

@task
def stuffing_trivia():
    return Task(
        dataset=load_dataset("mcq_retrieval.json"),
        plan=[inject_cluster_prompt("mcq_retrieval.json", is_pr=False), multiple_choice()],
        scorer=choice()
    )
