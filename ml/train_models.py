#!/usr/bin/env python3
"""
Phase 2 — ML Training Pipeline Scaffolding
"""
import os
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

def train_and_evaluate():
    data_path = "ml/synthetic_telemetry.csv"
    if not os.path.exists(data_path):
        print(f"Data not found at {data_path}. Please run generate_synthetic_data.py first.")
        return

    df = pd.read_csv(data_path)
    
    # Feature columns
    features = ["throughput_mbps", "latency_ms", "packet_loss_pct", "utilization_pct", "queue_length", "active_flows"]
    X = df[features]
    y = df["will_fail_in_5s"]
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {
        "Logistic Regression": LogisticRegression(),
        "Random Forest": RandomForestClassifier(random_state=42)
    }
    if XGBClassifier is not None:
        models["XGBoost"] = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
        
    print("=== Model Evaluation ===")
    for name, model in models.items():
        print(f"--- {name} ---")
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)
        
        # Calculate metrics
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        try:
            y_prob = model.predict_proba(X_test_scaled)[:, 1]
            roc_auc = roc_auc_score(y_test, y_prob)
        except AttributeError:
            roc_auc = float('nan')
            
        print(f"Accuracy:  {acc:.4f}")
        print(f"Precision: {prec:.4f}")
        print(f"Recall:    {rec:.4f}  <-- Most important")
        print(f"F1-Score:  {f1:.4f}")
        print(f"ROC-AUC:   {roc_auc:.4f}\n")

if __name__ == "__main__":
    train_and_evaluate()
