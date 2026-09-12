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

@task
def oracle_pr_audit():
    prompt = "You are a software architect. Answer the PASS/FAIL code evaluation question based on the provided architectural rules. Output ONLY the letter of the correct answer in the format 'ANSWER: A' or 'ANSWER: B'."
    return Task(
        dataset=load_dataset("pr_audit_oracle.json"), 
        plan=[system_message(prompt), multiple_choice()], 
        scorer=choice()
    )

@task
def oracle_adversarial():
    prompt = "You are a software architect. Answer the PASS/FAIL code evaluation question based on the provided architectural rules. Output ONLY the letter of the correct answer in the format 'ANSWER: A' or 'ANSWER: B'."
    return Task(
        dataset=load_dataset("adversarial_oracle.json"), 
        plan=[system_message(prompt), multiple_choice()], 
        scorer=choice()
    )

@task
def oracle_trivia():
    prompt = "You are a software architect. Answer the code evaluation question based on the provided architectural rules. Output ONLY the letter of the correct answer in the format 'ANSWER: A' or 'ANSWER: B'."
    return Task(
        dataset=load_dataset("trivia_oracle.json"), 
        plan=[system_message(prompt), multiple_choice()], 
        scorer=choice()
    )
