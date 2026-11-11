"""Metrics are calculated in train_model.py and persisted as a JSON-backed Markdown report."""
from pathlib import Path
def report_path(): return Path(__file__).resolve().parents[1]/'models'/'MODEL_REPORT_RESULTS.md'
def main():
    p=report_path()
    print(p.read_text(encoding='utf-8') if p.exists() else 'No evaluation result. Train with python -m backend.ml.train_model after downloading UCI data.')
if __name__=='__main__': main()
