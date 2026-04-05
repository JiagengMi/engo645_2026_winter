#!/usr/bin/env python
"""
Quick View: Final Model Evaluation Results
Shows the final evaluation in a clear, formatted way
"""

from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parent
eval_dir = root / "processed" / "model_outputs" / "evaluation"

print("\n" + "="*90)
print("FINAL MODEL EVALUATION RESULTS")
print("="*90)

# Load results
cv_df = pd.read_csv(eval_dir / "final_cv_summary.csv")
test_df = pd.read_csv(eval_dir / "final_test_summary.csv")

# Display test results (sorted by F1)
test_df_sorted = test_df.sort_values("f1", ascending=False).reset_index(drop=True)

print("\nTEST SET EVALUATION (Hold-out Data)")
print("-" * 90)
print("\nRanking by F1 Score:")
for idx, row in test_df_sorted.iterrows():
    rank_mark = ["[1st]", "[2nd]", "[3rd]"][idx]
    print(f"{rank_mark} {row['model']:40s} F1={row['f1']:.4f}")

print("\n\nDetailed Test Results:")
print("-" * 90)
for idx, row in test_df_sorted.iterrows():
    print(f"\n{row['model']}:")
    print(f"  Accuracy:  {row['accuracy']:.4f}")
    print(f"  Precision: {row['precision']:.4f} (false alarm rate: {100*(1-row['precision']):.1f}%)")
    print(f"  Recall:    {row['recall']:.4f} (detection rate: {100*row['recall']:.1f}%)")
    print(f"  F1 Score:  {row['f1']:.4f}")
    print(f"  ROC-AUC:   {row['roc_auc']:.4f}")
    print(f"  PR-AUC:    {row['pr_auc']:.4f}")

# Cross-validation comparison
print("\n\nCROSS-VALIDATION RESULTS (5-Fold Stratified)")
print("-" * 90)
for idx, row in cv_df.iterrows():
    print(f"\n{row['model']}:")
    print(f"  F1:        {row['f1_mean']:.4f} +/- {row['f1_std']:.4f}")
    print(f"  Precision: {row['precision_mean']:.4f} +/- {row['precision_std']:.4f}")
    print(f"  Recall:    {row['recall_mean']:.4f} +/- {row['recall_std']:.4f}")
    print(f"  ROC-AUC:   {row['roc_auc_mean']:.4f} +/- {row['roc_auc_std']:.4f}")

# Summary table
print("\n\nQUICK SUMMARY TABLE")
print("-" * 90)
summary = []
for row in test_df.values:
    summary.append({
        "Model": row[0],
        "Test_F1": f"{row[4]:.4f}",
        "Test_Prec": f"{row[2]:.4f}",
        "Test_Rec": f"{row[3]:.4f}",
        "ROC_AUC": f"{row[5]:.4f}",
    })

summary_df = pd.DataFrame(summary)
summary_df = summary_df.sort_values("Test_F1", ascending=False)
print(summary_df.to_string(index=False))

print("\n" + "="*90)
print("Results location: processed/model_outputs/evaluation/")
print("  - final_test_summary.csv")
print("  - final_cv_summary.csv")
print("  - final_roc_curves.png")
print("  - final_pr_curves.png")
print("  - final_metrics_comparison.png")
print("="*90 + "\n")
