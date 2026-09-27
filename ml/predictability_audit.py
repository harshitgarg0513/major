import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("predictability_audit")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "ml" / "labeled_dataset.csv"
OUTPUT_DIR = PROJECT_ROOT / "ml" / "audit_plots"

FEATURES = ["latency_ms", "packet_loss_pct", "throughput_mbps", "utilization_pct", "queue_length", "active_flows"]

def run_audit():
    if not DATA_PATH.exists():
        logger.error(f"Dataset not found at {DATA_PATH}")
        return
        
    df = pd.read_csv(DATA_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Feature Distribution separating Normal (0) and Precursor (1)
    logger.info("Generating feature distribution plots...")
    
    fault_types = df[df['label'] == 1]['fault_type'].unique()
    
    for ftype in fault_types:
        # Compare pure normal (0) vs precursor for this specific fault type (1)
        subset = df[(df['label'] == 0) | ((df['label'] == 1) & (df['fault_type'] == ftype))]
        
        if len(subset[subset['label'] == 1]) == 0:
            continue
            
        plt.figure(figsize=(15, 10))
        for i, feature in enumerate(FEATURES, 1):
            plt.subplot(2, 3, i)
            sns.violinplot(x='label', y=feature, data=subset)
            plt.title(f"{feature}")
            plt.xticks([0, 1], ['Normal', 'Precursor'])
            
        plt.suptitle(f"Predictability Audit: Precursor Signatures for {ftype}")
        plt.tight_layout()
        plot_path = OUTPUT_DIR / f"audit_{ftype}.png"
        plt.savefig(plot_path)
        plt.close()
        logger.info(f"Saved {plot_path}")

    # 2. Statistical Separability Report
    logger.info("\n=============================================")
    logger.info("   STAGE 5B PREDICTABILITY AUDIT REPORT")
    logger.info("=============================================")
    for ftype in fault_types:
        normal_data = df[df['label'] == 0]
        precursor_data = df[(df['label'] == 1) & (df['fault_type'] == ftype)]
        
        if len(precursor_data) == 0:
            continue
            
        logger.info(f"\nFault Type: {ftype}")
        for feature in FEATURES:
            norm_mean = normal_data[feature].mean()
            prec_mean = precursor_data[feature].mean()
            
            # Simple absolute % difference
            if norm_mean > 0:
                diff_pct = abs((prec_mean - norm_mean) / norm_mean) * 100
            else:
                diff_pct = 0 if prec_mean == 0 else 999
                
            detectability = "LOW"
            if diff_pct > 25: detectability = "MODERATE"
            if diff_pct > 75: detectability = "HIGH"
            
            logger.info(f"  {feature:<20} | Normal: {norm_mean:>8.2f} | Precursor: {prec_mean:>8.2f} | Shift: {diff_pct:>6.1f}% | Detectability: {detectability}")
            
if __name__ == "__main__":
    run_audit()
