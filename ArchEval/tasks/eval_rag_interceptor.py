import json
import os
import re
import subprocess
from inspect_ai import Task, task
from inspect_ai.dataset import FieldSpec, json_dataset
from inspect_ai.scorer import choice
from inspect_ai.solver import multiple_choice, solver
from inspect_ai.model import ChatMessageSystem

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_dataset(filename):
    return json_dataset(
        os.path.join(BASE_DIR, "datasets", filename),
        FieldSpec(id="id", input="input", choices="choices", target="target"),
        shuffle_choices=True
    )

@solver
def inject_intent_context():
    async def solve(state, generate_fn):
        question = state.user_prompt.text if state.user_prompt else state.input_text
        search_query = re.sub(r'```.*?```', '', question, flags=re.DOTALL).strip()
        config_path = os.path.join(BASE_DIR, "config", "akshara_config.toml")
        try:
            result = subprocess.run(
                ["intent", "--config", config_path, "search", "--mode", "hybrid", "--limit", "1", search_query],
                capture_output=True, text=True, check=True
            )
            search_data = json.loads(result.stdout)
            retrieved_text = ""
            for i, chunk in enumerate(search_data):
                retrieved_text += f"\n[RETRIEVED CHUNK {i+1}]\nSource: {chunk.get('file_path', 'Unknown')}\n{chunk.get('context', '')}\n"
        except Exception as e:
            retrieved_text = f"Failed to retrieve context: {e}"

        is_pr = "```rust" in question
        if is_pr:
            sys_prompt = f"""You are an automated CI/CD Architectural Enforcer.
Evaluate the developer's pull request against the {len(search_data)} retrieved architectural chunks below.

{retrieved_text}

CRITICAL INSTRUCTION: Output ONLY the letter of the correct answer in the format 'ANSWER: A' or 'ANSWER: B'."""
        else:
            sys_prompt = f"""You are an automated CI/CD Architectural Enforcer.
Answer the architectural question based strictly on the {len(search_data)} retrieved architectural chunks below.

{retrieved_text}

CRITICAL INSTRUCTION: Output ONLY the letter of the correct answer in the format 'ANSWER: A' or 'ANSWER: B'."""

        state.messages.insert(0, ChatMessageSystem(content=sys_prompt))
        return state
    return solve

@task
def rag_pr_audit():
    return Task(dataset=load_dataset("pr_audit_reasoning_mcq.json"), plan=[inject_intent_context(), multiple_choice()], scorer=choice())

@task
def rag_adversarial():
    return Task(dataset=load_dataset("pr_audit_adversarial.json"), plan=[inject_intent_context(), multiple_choice()], scorer=choice())

@task
def rag_trivia():
    return Task(dataset=load_dataset("mcq_retrieval.json"), plan=[inject_intent_context(), multiple_choice()], scorer=choice())
