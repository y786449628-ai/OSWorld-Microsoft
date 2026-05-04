# Microsoft_01 Snapshot Transition Report

## 1. 20251209_221844 -> 20251209_222014
- Summary: Book1.xlsx changed: spreadsheet content changed from 4 to 13 non-empty cells.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Book1.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 4, "to": 13}, "headers": {"from": ["Product name", "Q1 sales", "Q2 sales", "Year-over-Tear Growth Rate"], "to": ["Product name", "Q1 sales", "Q2 sales", "Year-over-Tear Growth Rate"]}}`

## 2. 20251209_222014 -> 20251209_222104
- Summary: Book1.xlsx changed: spreadsheet content changed from 13 to 16 non-empty cells.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Book1.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 13, "to": 16}, "headers": {"from": ["Product name", "Q1 sales", "Q2 sales", "Year-over-Tear Growth Rate"], "to": ["Product name", "Q1 sales", "Q2 sales", "Year-over-Tear Growth Rate"]}}`

## 3. 20251209_222104 -> 20251209_222149
- Summary: Book1.xlsx changed: Office document content changed.
- Likely stage: edit Office document
- Confidence: 0.75
- Evidence:
  - file: `"Book1.xlsx"`
  - office_delta: `{"headers": {"from": ["Product name", "Q1 sales", "Q2 sales", "Year-over-Tear Growth Rate"], "to": ["Product name", "Q1 sales", "Q2 sales", "Year-over-Tear Growth Rate"]}}`

## 4. 20251209_222149 -> 20251209_222307
- Summary: Book1.xlsx changed: worksheet names changed.
- Likely stage: rename worksheet
- Confidence: 0.86
- Evidence:
  - file: `"Book1.xlsx"`
  - office_delta: `{"sheet_names": {"from": ["Sheet1"], "to": ["Chart1", "Sheet1"]}, "worksheet_count": {"from": 1, "to": 2}, "headers": {"from": ["Product name", "Q1 sales", "Q2 sales", "Year-over-Tear Growth Rate"], "to": ["Product name", "Q1 sales", "Q2 sales", "Year-over-Tear Growth Rate"]}}`

## 5. 20251209_222307 -> 20251209_222351
- Summary: New files appeared: Doc1.docx.
- Likely stage: create or save file
- Confidence: 0.78
- Evidence:
  - files_added: `["Doc1.docx"]`

## 6. 20251209_222351 -> 20251209_222526
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Doc1.docx", "size": {"from": 13343, "to": 13455}}]`

## 7. 20251209_222526 -> 20251209_222531
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Doc1.docx", "size": {"from": 13455, "to": 13485}}]`

## 8. 20251209_222531 -> 20251209_222601
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Doc1.docx", "size": {"from": 13485, "to": 33791}}]`

## 9. 20251209_222601 -> 20251209_222625
- Summary: New files appeared: Doc1.pdf.
- Likely stage: create or save file
- Confidence: 0.78
- Evidence:
  - files_added: `["Doc1.pdf"]`
