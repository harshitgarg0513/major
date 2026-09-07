#!/usr/bin/env python3
"""
Phase 1 — Member 3 proof: scikit-learn pipeline on a public dummy dataset.

Uses sklearn.datasets.load_iris (classic public benchmark).
Confirms data -> train -> evaluate runs end-to-end before real telemetry data exists.
"""

from __future__ import annotations

import sys

from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


def main() -> int:
    print("=== Phase 1 / Member 3 — ML toy classifier demo ===")

    X, y = load_iris(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)

    print(f"Dataset: iris ({X.shape[0]} samples, {X.shape[1]} features, 3 classes)")
    print(f"Test accuracy: {acc:.3f}")
    print(classification_report(y_test, preds, target_names=load_iris().target_names))

    try:
        import xgboost  # noqa: F401
        print(f"XGBoost import: OK (v{xgboost.__version__})")
    except ImportError:
        print("XGBoost import: not installed (sklearn-only demo still valid)")

    if acc < 0.90:
        print("FAIL: accuracy below 0.90 on iris — environment issue")
        return 1

    print("PASS: ML pipeline (load -> train -> evaluate) works.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
