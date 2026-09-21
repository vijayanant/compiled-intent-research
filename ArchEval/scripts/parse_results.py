import os
import traceback
from inspect_ai.log import read_eval_log

LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
)

results = {"PR Audit": {}, "Adversarial Traps": {}, "Architectural Trivia": {}}

# Mapping task names to their display grids
task_mapping = {
    "zero_context_pr_audit": ("Zero Context", "PR Audit"),
    "zero_context_adversarial": ("Zero Context", "Adversarial Traps"),
    "zero_context_trivia": ("Zero Context", "Architectural Trivia"),
    "stuffing_pr_audit": ("Prompt Stuffing", "PR Audit"),
    "stuffing_adversarial": ("Prompt Stuffing", "Adversarial Traps"),
    "stuffing_trivia": ("Prompt Stuffing", "Architectural Trivia"),
    "rag_pr_audit": ("Compiled Intent", "PR Audit"),
    "rag_adversarial": ("Compiled Intent", "Adversarial Traps"),
    "rag_trivia": ("Compiled Intent", "Architectural Trivia"),
    "oracle_pr_audit": ("Oracle", "PR Audit"),
    "oracle_adversarial": ("Oracle", "Adversarial Traps"),
    "oracle_trivia": ("Oracle", "Architectural Trivia"),
}

architectures = ["Zero Context", "Oracle", "Prompt Stuffing", "Compiled Intent"]

import sys

target_model = sys.argv[1].replace("ollama/", "") if len(sys.argv) > 1 else None

latest_logs = {}
for filename in os.listdir(LOG_DIR):
    if filename.endswith(".eval"):
        filepath = os.path.join(LOG_DIR, filename)
        try:
            log = read_eval_log(filepath)
            task_name = log.eval.task
            model_name = log.eval.model
            if target_model and target_model not in model_name:
                continue
            if task_name in task_mapping:
                # Keep only the newest run for each task
                if task_name not in latest_logs or os.path.getmtime(
                    filepath
                ) > os.path.getmtime(latest_logs[task_name]):
                    latest_logs[task_name] = filepath
        except Exception:
            pass

for task_name, filepath in latest_logs.items():
    try:
        log = read_eval_log(filepath)
        arch, dataset = task_mapping[task_name]

        metrics = log.results.scores[0].metrics
        # FIXED: Extract .value from EvalMetric object
        acc_metric = metrics.get("accuracy")
        acc = acc_metric.value * 100 if acc_metric else 0.0

        results[dataset][arch] = {"acc": acc}
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")

print("\n=== LATEST BENCHMARK MATRIX (4x3) ===")
print(f"{'Architecture':<18} | {'PR Audit':<15} | {'Adversarial':<15} | {'Trivia':<15}")
print("-" * 72)

for arch in architectures:
    pr_val = results["PR Audit"].get(arch, {}).get("acc", "N/A")
    pr_str = f"{pr_val:.1f}%" if isinstance(pr_val, float) else "N/A"

    adv_val = results["Adversarial Traps"].get(arch, {}).get("acc", "N/A")
    adv_str = f"{adv_val:.1f}%" if isinstance(adv_val, float) else "N/A"

    triv_val = results["Architectural Trivia"].get(arch, {}).get("acc", "N/A")
    triv_str = f"{triv_val:.1f}%" if isinstance(triv_val, float) else "N/A"

    print(f"{arch:<18} | {pr_str:<15} | {adv_str:<15} | {triv_str:<15}")
