# Microsoft_70 Snapshot Transition Report

## 1. 20260114_190504 -> 20260114_190522
- Summary: material/Sales_Raw_Data.xlsx changed: Office document content changed.
- Likely stage: edit Office document
- Confidence: 0.75
- Evidence:
  - file: `"material/Sales_Raw_Data.xlsx"`
  - office_delta: `{"headers": {"from": ["Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488", "1888"], "to": ["Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488", "1888"]}}`

## 2. 20260114_190522 -> 20260114_190607
- Summary: material/Sales_Raw_Data.xlsx changed: Office document content changed.
- Likely stage: edit Office document
- Confidence: 0.75
- Evidence:
  - file: `"material/Sales_Raw_Data.xlsx"`
  - office_delta: `{"headers": {"from": ["Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488", "1888"], "to": ["Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488", "1888"]}}`

## 3. 20260114_190607 -> 20260114_190702
- Summary: material/Sales_Raw_Data.xlsx changed: Office document content changed.
- Likely stage: edit Office document
- Confidence: 0.75
- Evidence:
  - file: `"material/Sales_Raw_Data.xlsx"`
  - office_delta: `{"headers": {"from": ["Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488", "1888"], "to": ["Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488", "1888"]}}`

## 4. 20260114_190702 -> 20260114_190737
- Summary: material/Sales_Raw_Data.xlsx changed: chart/drawing count changed from 0 to 1.
- Likely stage: create or modify chart
- Confidence: 0.9
- Evidence:
  - file: `"material/Sales_Raw_Data.xlsx"`
  - office_delta: `{"chart_count": {"from": 0, "to": 1}, "headers": {"from": ["Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488", "1888"], "to": ["Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488", "1888"]}}`

## 5. 20260114_190737 -> 20260114_190811
- Summary: material/Sales_Raw_Data.xlsx changed: Office document content changed.
- Likely stage: edit Office document
- Confidence: 0.75
- Evidence:
  - file: `"material/Sales_Raw_Data.xlsx"`
  - office_delta: `{"headers": {"from": ["Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488", "1888"], "to": ["Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488", "1888"]}}`

## 6. 20260114_190811 -> 20260114_190921
- Summary: material/Sales_Raw_Data.xlsx changed: spreadsheet content changed from 104 to 120 non-empty cells; worksheet names changed; chart/drawing count changed from 1 to 2; new visible headers or values include: Forecast(Revenue Difference), Lower Confidence Bound(Revenue Difference), Upper Confidence Bound(Revenue Difference).
- Likely stage: enter or edit spreadsheet data + rename worksheet + create or modify chart
- Confidence: 0.9
- Evidence:
  - file: `"material/Sales_Raw_Data.xlsx"`
  - office_delta: `{"sheet_names": {"from": ["Sheet1"], "to": ["Sheet2", "Sheet1"]}, "worksheet_count": {"from": 1, "to": 2}, "nonempty_cells": {"from": 104, "to": 120}, "chart_count": {"from": 1, "to": 2}, "headers": {"from": ["Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488", "1888"], "to": ["Month", "Revenue Difference", "Forecast(Revenue Difference)", "Lower Confidence Bound(Revenue Difference)", "Upper Confidence Bound(Revenue Difference)", "Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488"]}}`
  - headers_added: `["Forecast(Revenue Difference)", "Lower Confidence Bound(Revenue Difference)", "Upper Confidence Bound(Revenue Difference)"]`

## 7. 20260114_190921 -> 20260114_191005
- Summary: material/Sales_Raw_Data.xlsx changed: worksheet names changed.
- Likely stage: rename worksheet
- Confidence: 0.86
- Evidence:
  - file: `"material/Sales_Raw_Data.xlsx"`
  - office_delta: `{"sheet_names": {"from": ["Sheet2", "Sheet1"], "to": ["Revenue Forecast", "Sheet1"]}, "headers": {"from": ["Month", "Revenue Difference", "Forecast(Revenue Difference)", "Lower Confidence Bound(Revenue Difference)", "Upper Confidence Bound(Revenue Difference)", "Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488"], "to": ["Month", "Revenue Difference", "Forecast(Revenue Difference)", "Lower Confidence Bound(Revenue Difference)", "Upper Confidence Bound(Revenue Difference)", "Region", "Product", "Sales Rep", "Month", "Units Sold", "Actual Revenue (USD)", "Forecasted Revenue", "Revenue Difference", "North", "Alpha", "Michael Chen", "45689", "118", "23600", "25488"]}}`

## 8. 20260114_191005 -> 20260114_191048
- Summary: New files appeared: Sales_Analysis_Model.xlsx.
- Likely stage: create or save file
- Confidence: 0.78
- Evidence:
  - files_added: `["Sales_Analysis_Model.xlsx"]`

## 9. 20260114_191048 -> 20260114_191050
- Summary: No observable file or directory change was detected between these snapshots.
- Likely stage: no observable benchmark state change
- Confidence: 0.2

## 10. 20260114_191050 -> 20260114_191118
- Summary: No observable file or directory change was detected between these snapshots.
- Likely stage: no observable benchmark state change
- Confidence: 0.2

## 11. 20260114_191118 -> 20260114_191214
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "material/Sales_Performance_Presentation.pptx", "size": {"from": 38176, "to": 41632}}]`

## 12. 20260114_191214 -> 20260114_191255
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "material/Sales_Performance_Presentation.pptx", "size": {"from": 41632, "to": 41649}}]`

## 13. 20260114_191255 -> 20260114_191319
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "material/Sales_Performance_Presentation.pptx", "size": {"from": 41649, "to": 464263}}]`

## 14. 20260114_191319 -> 20260114_191342
- Summary: New files appeared: Sales_Performance_Presentation.pptx.
- Likely stage: create or save file
- Confidence: 0.78
- Evidence:
  - files_added: `["Sales_Performance_Presentation.pptx"]`

## 15. 20260114_191342 -> 20260114_191344
- Summary: No observable file or directory change was detected between these snapshots.
- Likely stage: no observable benchmark state change
- Confidence: 0.2
