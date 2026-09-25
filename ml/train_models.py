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
        "Logistic Regression": LogisticRegression(class_weight='balanced'),
        "Random Forest": RandomForestClassifier(random_state=42, class_weight='balanced')
    }
    if XGBClassifier is not None:
        models["XGBoost"] = XGBClassifier(eval_metric='logloss', random_state=42, scale_pos_weight=10) # rough proxy for balanced
        
    print("=== Model Evaluation ===")
    print("WARNING: This data is trivially separable and meant for pipeline plumbing validation only.")
    print("Do not quote these accuracy numbers as predictive performance metrics.\n")
    
    for name, model in models.items():
        print(f"--- {name} ---")
        # Compute cross-validation score
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='accuracy')
        print(f"CV Accuracy (5-fold): {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
        
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
            
        print(f"Test Accuracy:  {acc:.4f}")
        print(f"Test Precision: {prec:.4f}")
        print(f"Test Recall:    {rec:.4f}  <-- Most important")
        print(f"Test F1-Score:  {f1:.4f}")
        print(f"Test ROC-AUC:   {roc_auc:.4f}\n")

if __name__ == "__main__":
    train_and_evaluate()
