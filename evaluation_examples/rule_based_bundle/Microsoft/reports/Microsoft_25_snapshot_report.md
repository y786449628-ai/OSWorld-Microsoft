# Microsoft_25 Snapshot Transition Report

## 1. 20260108_220031 -> 20260108_220114
- Summary: Material/Detail.xlsx changed: spreadsheet content changed from 68 to 75 non-empty cells; worksheet names changed; new visible headers or values include: Quarter, 2024 Year, 2025 Year.
- Likely stage: enter or edit spreadsheet data + rename worksheet
- Confidence: 0.86
- Evidence:
  - file: `"Material/Detail.xlsx"`
  - office_delta: `{"sheet_names": {"from": ["2025", "2024"], "to": ["Summary", "2025", "2024"]}, "worksheet_count": {"from": 2, "to": 3}, "nonempty_cells": {"from": 68, "to": 75}, "headers": {"from": ["Date", "Sales Revenue", "45839", "690", "Date", "Sales Revenue", "45474", "860"], "to": ["Quarter", "2024 Year", "2025 Year", "Date", "Sales Revenue", "45839", "690", "Date", "Sales Revenue", "45474", "860"]}}`
  - headers_added: `["Quarter", "2024 Year", "2025 Year"]`

## 2. 20260108_220114 -> 20260108_220226
- Summary: Material/Detail.xlsx changed: spreadsheet content changed from 75 to 86 non-empty cells.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Material/Detail.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 75, "to": 86}, "headers": {"from": ["Quarter", "2024 Year", "2025 Year", "Date", "Sales Revenue", "45839", "690", "Date", "Sales Revenue", "45474", "860"], "to": ["Quarter", "2024 Year", "2025 Year", "Date", "Sales Revenue", "45839", "690", "Date", "Sales Revenue", "45474", "860"]}}`

## 3. 20260108_220226 -> 20260108_220441
- Summary: Material/Detail.xlsx changed: spreadsheet content changed from 86 to 122 non-empty cells; new visible headers or values include: Growth%, Max, Positive gr%, Negative gr%, Positive line, Negative line.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Material/Detail.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 86, "to": 122}, "headers": {"from": ["Quarter", "2024 Year", "2025 Year", "Date", "Sales Revenue", "45839", "690", "Date", "Sales Revenue", "45474", "860"], "to": ["Quarter", "2024 Year", "2025 Year", "Growth%", "Max", "Positive gr%", "Negative gr%", "Positive line", "Negative line", "Date", "Sales Revenue", "45839", "690", "Date", "Sales Revenue", "45474", "860"]}}`
  - headers_added: `["Growth%", "Max", "Positive gr%", "Negative gr%", "Positive line", "Negative line"]`

## 4. 20260108_220441 -> 20260108_220913
- Summary: Material/Detail.xlsx changed: chart/drawing count changed from 0 to 1.
- Likely stage: create or modify chart
- Confidence: 0.9
- Evidence:
  - file: `"Material/Detail.xlsx"`
  - office_delta: `{"chart_count": {"from": 0, "to": 1}, "headers": {"from": ["Quarter", "2024 Year", "2025 Year", "Growth%", "Max", "Positive gr%", "Negative gr%", "Positive line", "Negative line", "Date", "Sales Revenue", "45839", "690", "Date", "Sales Revenue", "45474", "860"], "to": ["Quarter", "2024 Year", "2025 Year", "Growth%", "Max", "Positive gr%", "Negative gr%", "Positive line", "Negative line", "Date", "Sales Revenue", "45839", "690", "Date", "Sales Revenue", "45474", "860"]}}`

## 5. 20260108_220913 -> 20260108_221320
- Summary: New files appeared: final result.xlsx.
- Likely stage: create or save file
- Confidence: 0.78
- Evidence:
  - files_added: `["final result.xlsx"]`

## 6. 20260108_221320 -> 20260108_221322
- Summary: No observable file or directory change was detected between these snapshots.
- Likely stage: no observable benchmark state change
- Confidence: 0.2
