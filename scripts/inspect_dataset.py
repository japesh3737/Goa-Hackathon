import sys
import os
from pathlib import Path

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.dataset_inspector import inspect_and_save_report

if __name__ == "__main__":
    print("=== MSMARCO-XI Dataset Inspection Tool ===")
    report = inspect_and_save_report("data/schema_report.json")
    print(f"Dataset Name: {report.get('dataset_name')}")
    print(f"Detected Schema: {report.get('detected_schema')}")
    print("Full report written to data/schema_report.json")
