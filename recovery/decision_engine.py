#!/usr/bin/env python3
"""
Phase 2 — Confidence-Threshold Policy Skeleton
"""

import yaml
import os

def load_thresholds():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'contracts', 'threshold_config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def evaluate_probability(probability: float) -> str:
    """
    Given a predicted failure probability, return the corresponding recovery action.
    Threshold logic based on contracts/threshold_config.yaml.
    """
    config = load_thresholds()
    for bin_cfg in config['bins']:
        if probability < bin_cfg['max_probability']:
            return bin_cfg['action']
    return config['bins'][-1]['action'] # fallback to last

if __name__ == "__main__":
    test_probs = [0.1, 0.49, 0.6, 0.8, 0.85, 0.99]
    for p in test_probs:
        print(f"Probability: {p:.2f} -> Action: {evaluate_probability(p)}")
