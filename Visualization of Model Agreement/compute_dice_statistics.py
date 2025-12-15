#!/usr/bin/env python3
import sys
import numpy as np
import pandas as pd


def load_results(csv_file):

    df_results = pd.read_csv(csv_file, skiprows=1)
    df_results = df_results.rename(columns={df_results.columns[0]: "Structure"})
    df_results = df_results.iloc[1:].reset_index(drop=True)
    return df_results


def compute_statistics(df_results: pd.DataFrame) -> pd.DataFrame:
    df_numeric = df_results.select_dtypes(include=[np.number])

    if df_numeric.empty:
        raise ValueError("No numeric columns found to compute statistics.")

    df_stats = pd.DataFrame({
        "Structure": df_results["Structure"],
        "Mean": df_numeric.mean(axis=1, skipna=True),
        "Median": df_numeric.median(axis=1, skipna=True),
        "Std": df_numeric.std(axis=1, skipna=True),
        "Min": df_numeric.min(axis=1, skipna=True),
        "Max": df_numeric.max(axis=1, skipna=True),
        "IQR": df_numeric.quantile(0.75, axis=1) - df_numeric.quantile(0.25, axis=1),
    })

    return df_stats


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compute_stats.py <input_scores_csv> <output_stats_csv>")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_csv = sys.argv[2]

    df = load_results(input_csv)
    stats = compute_statistics(df)
    stats.to_csv(output_csv, index=False)

    print(f"Saved statistics CSV to: {output_csv}")
