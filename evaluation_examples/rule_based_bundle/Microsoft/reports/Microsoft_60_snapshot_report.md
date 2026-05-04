# Microsoft_60 Snapshot Transition Report

## 1. 20260112_162326 -> 20260112_162433
- Summary: Freelancer_Data_Analysis.xlsx changed: spreadsheet content changed from 5511 to 7014 non-empty cells.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Freelancer_Data_Analysis.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 5511, "to": 7014}, "headers": {"from": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior", "North America", "US", "Bachelor", "267.33999999999997"], "to": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "years_experience", "hourly_rate_usd", "annual_income_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior", "North America"]}}`

## 2. 20260112_162433 -> 20260112_162508
- Summary: No observable file or directory change was detected between these snapshots.
- Likely stage: no observable benchmark state change
- Confidence: 0.2

## 3. 20260112_162508 -> 20260112_162630
- Summary: Freelancer_Data_Analysis.xlsx changed: spreadsheet content changed from 7014 to 7101 non-empty cells; worksheet names changed; new visible headers or values include: Range, 13.5, Range, 264.19000000000005, Range, 258775.71999999997.
- Likely stage: enter or edit spreadsheet data + rename worksheet
- Confidence: 0.86
- Evidence:
  - file: `"Freelancer_Data_Analysis.xlsx"`
  - office_delta: `{"sheet_names": {"from": ["data", "Sheet1"], "to": ["DDS", "data", "Sheet1"]}, "worksheet_count": {"from": 2, "to": 3}, "nonempty_cells": {"from": 7014, "to": 7101}, "headers": {"from": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "years_experience", "hourly_rate_usd", "annual_income_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior", "North America"], "to": ["years_experience", "hourly_rate_usd", "annual_income_usd", "Range", "13.5", "Range", "264.19000000000005", "Range", "258775.71999999997", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform"]}}`
  - headers_added: `["Range", "13.5", "Range", "264.19000000000005", "Range", "258775.71999999997"]`

## 4. 20260112_162630 -> 20260112_162747
- Summary: Freelancer_Data_Analysis.xlsx changed: spreadsheet content changed from 7101 to 7113 non-empty cells; worksheet names changed.
- Likely stage: enter or edit spreadsheet data + rename worksheet
- Confidence: 0.86
- Evidence:
  - file: `"Freelancer_Data_Analysis.xlsx"`
  - office_delta: `{"sheet_names": {"from": ["DDS", "data", "Sheet1"], "to": ["DDS", "CA", "data", "Sheet1"]}, "worksheet_count": {"from": 3, "to": 4}, "nonempty_cells": {"from": 7101, "to": 7113}, "headers": {"from": ["years_experience", "hourly_rate_usd", "annual_income_usd", "Range", "13.5", "Range", "264.19000000000005", "Range", "258775.71999999997", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform"], "to": ["years_experience", "hourly_rate_usd", "annual_income_usd", "Range", "13.5", "Range", "264.19000000000005", "Range", "258775.71999999997", "years_experience", "hourly_rate_usd", "annual_income_usd", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education"]}}`

## 5. 20260112_162747 -> 20260112_162853
- Summary: New files appeared: Freelancer_Income_Analysis_PPT.pptx.
- Likely stage: create or save file
- Confidence: 0.78
- Evidence:
  - files_added: `["Freelancer_Income_Analysis_PPT.pptx"]`

## 6. 20260112_162853 -> 20260112_163229
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Freelancer_Income_Analysis_PPT.pptx", "size": {"from": 32142, "to": 35400}}]`

## 7. 20260112_163229 -> 20260112_163359
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Freelancer_Income_Analysis_PPT.pptx", "size": {"from": 35400, "to": 35816}}]`

## 8. 20260112_163359 -> 20260112_163412
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Freelancer_Income_Analysis_PPT.pptx", "size": {"from": 35816, "to": 36957}}]`

## 9. 20260112_163412 -> 20260112_163545
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Freelancer_Income_Analysis_PPT.pptx", "size": {"from": 36957, "to": 37147}}]`

## 10. 20260112_163545 -> 20260112_164051
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Freelancer_Income_Analysis_PPT.pptx", "size": {"from": 37147, "to": 37504}}]`

## 11. 20260112_164051 -> 20260112_164158
- Summary: Freelancer_Data_Analysis.xlsx changed: spreadsheet content changed from 7113 to 7137 non-empty cells; worksheet names changed; new visible headers or values include: Mobile Development, 36.
- Likely stage: enter or edit spreadsheet data + rename worksheet
- Confidence: 0.86
- Evidence:
  - file: `"Freelancer_Data_Analysis.xlsx"`
  - office_delta: `{"sheet_names": {"from": ["DDS", "CA", "data", "Sheet1"], "to": ["DDS", "CA", "Sheet4", "data", "Sheet1"]}, "worksheet_count": {"from": 4, "to": 5}, "nonempty_cells": {"from": 7113, "to": 7137}, "headers": {"from": ["years_experience", "hourly_rate_usd", "annual_income_usd", "Range", "13.5", "Range", "264.19000000000005", "Range", "258775.71999999997", "years_experience", "hourly_rate_usd", "annual_income_usd", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education"], "to": ["years_experience", "hourly_rate_usd", "annual_income_usd", "Range", "13.5", "Range", "264.19000000000005", "Range", "258775.71999999997", "years_experience", "hourly_rate_usd", "annual_income_usd", "Mobile Development", "36", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region"]}}`
  - headers_added: `["Mobile Development", "36"]`

## 12. 20260112_164158 -> 20260112_164420
- Summary: Freelancer_Data_Analysis.xlsx changed: chart/drawing count changed from 0 to 1.
- Likely stage: create or modify chart
- Confidence: 0.9
- Evidence:
  - file: `"Freelancer_Data_Analysis.xlsx"`
  - office_delta: `{"chart_count": {"from": 0, "to": 1}, "headers": {"from": ["years_experience", "hourly_rate_usd", "annual_income_usd", "Range", "13.5", "Range", "264.19000000000005", "Range", "258775.71999999997", "years_experience", "hourly_rate_usd", "annual_income_usd", "Mobile Development", "36", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region"], "to": ["years_experience", "hourly_rate_usd", "annual_income_usd", "Range", "13.5", "Range", "264.19000000000005", "Range", "258775.71999999997", "years_experience", "hourly_rate_usd", "annual_income_usd", "Mobile Development", "36", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region"]}}`

## 13. 20260112_164420 -> 20260112_164731
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Freelancer_Income_Analysis_PPT.pptx", "size": {"from": 37504, "to": 42094}}]`

## 14. 20260112_164731 -> 20260112_164936
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Freelancer_Income_Analysis_PPT.pptx", "size": {"from": 42094, "to": 42184}}]`
