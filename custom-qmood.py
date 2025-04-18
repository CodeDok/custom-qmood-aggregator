#!/usr/bin/env python3
"""
CSV Merger with Value Overrides and QMOOD Metrics Recalculation

This program merges two CSV files. The first CSV is used as a base,
and values from the second CSV will override corresponding values in the first CSV
where column names match. The rows are matched based on class names using loose matching
for file paths.

The program also recalculates QMOOD metrics (Reusability, Flexibility, Understandability,
Functionality, Extendibility, Effectiveness) using hardcoded formulas.
"""

import argparse
import pandas as pd
import os
import re
import sys

# QMOOD metrics
QMOOD_METRICS = [
    'Reusability',
    'Flexibility',
    'Understandability',
    'Functionality',
    'Extendibility',
    'Effectiveness'
]

# Hardcoded formulas for QMOOD metrics calculation
# These are placeholder formulas - modify them according to your needs
# The formula strings reference column names from the merged dataset
QMOOD_FORMULAS = {
    'Reusability': "-0.25 * DCC + 0.25 * lcc + 0.5 * CIS + 0.5 * DSC",
    'Flexibility': "0.25 * DAM - 0.25 * DCC + 0.5 * MOA + 0.5 * NOP",
    'Understandability': "-0.33 * ANA + 0.33 * DAM - 0.33 * DCC + 0.33 * lcc - 0.33 * NOP - 0.33 * WMC + - 0.33 * DSC",
    'Functionality': "0.12 * lcc + 0.22 * NOP + 0.22 * CIS + 0.22 * DSC + 0.22 * NOH",
    'Extendibility': "0.5 * ANA - 0.5 * DCC + 0.5 * MFA + 0.5 * NOP",
    'Effectiveness': "0.2 * ANA + 0.2 * DAM + 0.2 * MOA + 0.2 * MFA + 0.2 * NOP"
}


def parse_arguments():
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description='Merge two CSV files with value overrides')
    parser.add_argument('base_csv', help='Path to the base CSV file')
    parser.add_argument('override_csv', help='Path to the CSV file with override values')
    parser.add_argument('--output', default='merged-output.csv', 
                        help='Path to the output CSV file (default: merged-output.csv)')
    parser.add_argument('--add-columns', 
                        help='Comma-separated list of column names from the override CSV to add to the base CSV')
    return parser.parse_args()


def extract_class_name(filepath):
    """Extract the class name from a file path."""
    # Get the base filename without extension
    base_name = os.path.basename(filepath)
    # Remove the .java extension if present
    if base_name.endswith('.java'):
        base_name = base_name[:-5]
    return base_name


def match_files(row1, row2):
    """
    Determine if two rows match based on class name or file path.
    
    Args:
        row1: Row from the base CSV
        row2: Row from the override CSV
        
    Returns:
        bool: True if the rows match, False otherwise
    """
    # If we have class names in both CSVs, use them for matching
    if 'ClassNames' in row1 and 'class' in row2:
        # Direct match of class names
        if row1['ClassNames'] == row2['class']:
            return True
        
    # Extract file names for looser matching
    if 'Name' in row1 and 'file' in row2:
        base_file = extract_class_name(row1['Name'])
        override_file = extract_class_name(row2['file'])
        
        # Check if the file names match (case insensitive)
        if base_file.lower() == override_file.lower():
            return True
            
    return False


def merge_csvs(base_df, override_df, add_columns=None):
    """
    Merge two DataFrames, overriding values in the base DataFrame with values from
    the override DataFrame where column names match and rows correspond to the same class.
    
    Args:
        base_df: DataFrame containing the base CSV data
        override_df: DataFrame containing the override CSV data
        add_columns: List of column names from override_df to add to the result_df
        
    Returns:
        DataFrame: The merged DataFrame
    """
    # Create a copy of the base DataFrame to modify
    result_df = base_df.copy()
    
    # Add columns from override_df to result_df if specified
    if add_columns:
        for col in add_columns:
            if col in override_df.columns and col not in result_df.columns:
                # Add the column to result_df with NaN values
                result_df[col] = pd.NA
                print(f"Added new column '{col}' from override CSV to result")
    
    # Keep track of which override rows were used
    used_override_rows = set()
    
    # For each row in the base DataFrame
    for i, base_row in base_df.iterrows():
        # For each row in the override DataFrame
        for j, override_row in override_df.iterrows():
            if match_files(base_row, override_row):
                print(f"Found match: {base_row.get('Name', '')} - {override_row.get('file', '')}")
                
                # For each column in the override DataFrame
                for col in override_df.columns:
                    # If this is a column we're adding from override_df or
                    # the column exists in both DataFrames (with case-insensitive matching)
                    should_add = False
                    if add_columns is not None and col in add_columns:
                        should_add = True
                        target_col = col
                    else:
                        # For existing columns, find the matching column in base_df
                        matching_cols = [c for c in base_df.columns if c.lower() == col.lower()]
                        if matching_cols:
                            should_add = True
                            target_col = matching_cols[0]
                    
                    if should_add:
                        # Override the value in the result DataFrame
                        result_df.at[i, target_col] = override_row[col]
                        is_new_column = add_columns is not None and col in add_columns and col not in base_df.columns
                        print(f"  {'Adding' if is_new_column else 'Overriding'} {target_col} with value from {col}")
                
                used_override_rows.add(j)
                break  # Move to next base row after finding a match
    
    # Print warning for override rows that weren't used
    unused_rows = set(range(len(override_df))) - used_override_rows
    if unused_rows:
        print(f"\nWarning: {len(unused_rows)} rows in the override CSV were not matched:")
        for j in unused_rows:
            row = override_df.iloc[j]
            class_name = row.get('class', 'Unknown')
            file_name = row.get('file', 'Unknown')
            print(f"  - {class_name} ({file_name})")
    
    return result_df


def recalculate_qmood_metrics(df):
    """
    Recalculate QMOOD metrics using the hardcoded formulas.
    
    Args:
        df: DataFrame containing the merged data
        
    Returns:
        DataFrame: The DataFrame with recalculated QMOOD metrics
    """
    result_df = df.copy()
    
    # Process each QMOOD metric using its formula
    for metric, formula in QMOOD_FORMULAS.items():
        try:
            print(f"Recalculating {metric} using formula: {formula}")
            
            # Replace column names with DataFrame references
            expr = formula
            for col in df.columns:
                if col in expr:
                    # Use word boundaries to avoid replacing substrings of other column names
                    pattern = r'\b' + re.escape(col) + r'\b'
                    expr = re.sub(pattern, f"df['{col}']", expr)
            
            # Evaluate the expression safely
            result_df[metric] = eval(expr)
            print(f"  Successfully recalculated {metric}")
            
        except Exception as e:
            print(f"  Error calculating {metric}: {e}", file=sys.stderr)
            if metric in result_df.columns:
                print(f"  Keeping original values for {metric}")
            else:
                print(f"  Setting {metric} to 0.0")
                result_df[metric] = 0.0
    
    return result_df


def main():
    # Parse command line arguments
    args = parse_arguments()
    
    try:
        # Read the CSV files
        print(f"Reading base CSV: {args.base_csv}")
        base_df = pd.read_csv(args.base_csv)
        
        print(f"Reading override CSV: {args.override_csv}")
        override_df = pd.read_csv(args.override_csv)
        
        # Parse add-columns argument
        add_columns = None
        if args.add_columns:
            add_columns = [col.strip() for col in args.add_columns.split(',')]
        
        # Merge the CSV files
        print("\nMerging CSVs...")
        merged_df = merge_csvs(base_df, override_df, add_columns)
        
        # Recalculate QMOOD metrics
        print("\nRecalculating QMOOD metrics using hardcoded formulas...")
        merged_df = recalculate_qmood_metrics(merged_df)
        
        # Save the merged DataFrame to a CSV file
        print(f"\nSaving merged CSV to: {args.output}")
        merged_df.to_csv(args.output, index=False)
        
        print("Processing completed successfully")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()