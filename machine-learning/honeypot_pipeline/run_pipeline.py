import subprocess
import time
scripts= [
    "data_loader.py",
    "feature_engineering.py",
    "behavioral_analysis.py",
    "heuristic_labeling.py",
    "decision_rules.py",
]

pipeline_start= time.time()
for script in scripts:
    print("\n")
    print("---------------------------")
    print(f"Running {script}...")
    print("---------------------------")
    print("\n")
    step_start= time.time()
    subprocess.run(["python", script], check=True)
    step_elapsed = time.time() - step_start
    print(f"  {script} finished in {step_elapsed:.2f}s")

total_elapsed= time.time()-pipeline_start
print(f"\nPipeline complete. Total runtime: {total_elapsed:.2f}s")