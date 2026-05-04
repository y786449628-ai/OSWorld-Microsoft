# Microsoft_26 Snapshot Transition Report

## 1. 20260109_113403 -> 20260109_113658
- Summary: Material/Detail.xlsx changed: spreadsheet content changed from 14 to 99 non-empty cells; worksheet names changed; new visible headers or values include: Attribute, Value.1, Value.2, Grape, William: 400; Tom: 250, Detail - Copy.2.
- Likely stage: enter or edit spreadsheet data + rename worksheet
- Confidence: 0.86
- Evidence:
  - file: `"Material/Detail.xlsx"`
  - office_delta: `{"sheet_names": {"from": ["Sheet1"], "to": ["Table1 (2)", "Sheet1"]}, "worksheet_count": {"from": 1, "to": 2}, "nonempty_cells": {"from": 14, "to": 99}, "headers": {"from": ["Product", "Detail"], "to": ["Product", "Detail", "Attribute", "Value.1", "Value.2", "Grape", "William: 400; Tom: 250", "Detail - Copy.2", " Tom", "250", "Product", "Detail"]}}`
  - headers_added: `["Attribute", "Value.1", "Value.2", "Grape", "William: 400; Tom: 250", "Detail - Copy.2", " Tom", "250"]`

## 2. 20260109_113658 -> 20260109_113855
- Summary: Material/Detail.xlsx changed: spreadsheet content changed from 99 to 81 non-empty cells; new visible headers or values include: Customer, Sales Revenue, Row Labels, Sum of Sales Revenue.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Material/Detail.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 99, "to": 81}, "headers": {"from": ["Product", "Detail", "Attribute", "Value.1", "Value.2", "Grape", "William: 400; Tom: 250", "Detail - Copy.2", " Tom", "250", "Product", "Detail"], "to": ["Product", "Customer", "Sales Revenue", "Row Labels", "Sum of Sales Revenue", "Grape", " Tom", "250", "Product", "Detail"]}}`
  - headers_added: `["Customer", "Sales Revenue", "Row Labels", "Sum of Sales Revenue"]`

## 3. 20260109_113855 -> 20260109_114320
- Summary: Material/Detail.xlsx changed: spreadsheet content changed from 81 to 2650 non-empty cells; new visible headers or values include: Banana, Apple, Orange, Coconut, Pear, 3.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Material/Detail.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 81, "to": 2650}, "headers": {"from": ["Product", "Customer", "Sales Revenue", "Row Labels", "Sum of Sales Revenue", "Grape", " Tom", "250", "Product", "Detail"], "to": ["Product", "Customer", "Sales Revenue", "Row Labels", "Sum of Sales Revenue", "Product", "Banana", "Apple", "Orange", "Grape", "Coconut", "Pear", "Grape", " Tom", "250", "3", "100", "0", "0", "0"]}}`
  - headers_added: `["Banana", "Apple", "Orange", "Coconut", "Pear", "3", "100", "0", "0", "0"]`

## 4. 20260109_114320 -> 20260109_114653
- Summary: New files appeared: final result.xlsx.
- Likely stage: create or save file
- Confidence: 0.78
- Evidence:
  - files_added: `["final result.xlsx"]`

## 5. 20260109_114653 -> 20260109_114655
- Summary: No observable file or directory change was detected between these snapshots.
- Likely stage: no observable benchmark state change
- Confidence: 0.2
