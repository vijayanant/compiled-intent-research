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
        shuffle_choices=True,
    )


sys_prompt = "You are a software architect. Answer the multiple choice question based purely on your general knowledge. Output ONLY the letter of the correct answer in the format 'ANSWER: A'."


@task
def zero_context_trivia():
    return Task(
        dataset=load_dataset("mcq_retrieval.json"),
        plan=[system_message(sys_prompt), multiple_choice()],
        scorer=choice(),
    )


@task
def zero_context_pr_audit():
    return Task(
        dataset=load_dataset("pr_audit_reasoning_mcq.json"),
        plan=[system_message(sys_prompt), multiple_choice()],
        scorer=choice(),
    )


@task
def zero_context_adversarial():
    return Task(
        dataset=load_dataset("pr_audit_adversarial.json"),
        plan=[system_message(sys_prompt), multiple_choice()],
        scorer=choice(),
    )
