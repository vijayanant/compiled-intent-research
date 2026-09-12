
from inspect_ai.solver import solver
@solver
def print_state():
    async def solve(state, generate):
        print(f"\nSTATE MESSAGES: {len(state.messages)}")
        for m in state.messages:
            print(f"Role: {m.role}, Content Len: {len(m.text)}")
        return state
    return solve
import json
import os
from inspect_ai import Task, task
from inspect_ai.dataset import FieldSpec, json_dataset
from inspect_ai.scorer import choice
from inspect_ai.solver import multiple_choice, system_message

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_dataset(filename):
    return json_dataset(
        os.path.join(BASE_DIR, "datasets", filename),
        FieldSpec(id="id", input="input", choices="choices", target="target"),
        shuffle_choices=True
    )

def generate_system_prompt():
    prompt = "You are a software architect. Answer the PASS/FAIL code evaluation question based on the following architectural rules:\n\n"
    
    # We will stuff a "bounded" context of ~4 major specification files (around 5,000 tokens)
    # This is enough to trigger "Lost in the Middle" without causing OOM crashes.
    target_files = [
        "specs/api/conflicts.md",
        "blueprint/core/internals/crypto-composition.md",
        "blueprint/core/internals/addressing-cids.md",  # Needle 1 
        "specs/graph-model/schemas.md",
        "blueprint/identity/tiered-authority-adr.md",
        "specs/observability/diagnostics.md",          # Needle 2 
        "specs/api/sync.md",
        "blueprint/core/internals/canonicalization.md", # Needle 3 
        "specs/storage/interface.md",
        "specs/identity/derivation.md",                # Needle 4 
        "specs/graph-model/linking.md",                # Needle 5 (MISSING PREVIOUSLY)
        "specs/api/audit.md",
        "blueprint/platform/metadata-spec.md",
        "specs/api/errors.md",                         # Needle 6 
        "specs/api/client-and-graph.md"
    ]
    
    for relative_path in target_files:
        file_path = os.path.join(BASE_DIR, "datasets", "akshara_specs", relative_path)
        try:
            with open(file_path, "r") as f:
                content = f.read()
                # Escape curly braces for inspect_ai templating
                content = content.replace('{', '{{').replace('}', '}}')
                prompt += f"--- START OF {relative_path} ---\n"
                prompt += content + "\n"
                prompt += f"--- END OF {relative_path} ---\n\n"
        except FileNotFoundError:
            pass
            
    prompt += "CRITICAL INSTRUCTION: Output ONLY the letter of the correct answer in the format 'ANSWER: A' or 'ANSWER: B'."
    print(f"\n\nGENERATED PROMPT LEN: {len(prompt)}\n\n")
    return prompt

@task
def stuffing_pr_audit():
    return Task(dataset=load_dataset("pr_audit_reasoning_mcq.json"), plan=[system_message(generate_system_prompt()), print_state(), multiple_choice()], scorer=choice())

@task
def stuffing_adversarial():
    return Task(dataset=load_dataset("pr_audit_adversarial.json"), plan=[system_message(generate_system_prompt()), print_state(), multiple_choice()], scorer=choice())

@task
def stuffing_trivia():
    return Task(dataset=load_dataset("mcq_retrieval.json"), plan=[system_message(generate_system_prompt()), print_state(), multiple_choice()], scorer=choice())

