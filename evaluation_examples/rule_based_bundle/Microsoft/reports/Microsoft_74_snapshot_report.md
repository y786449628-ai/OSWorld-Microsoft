# Microsoft_74 Snapshot Transition Report

## 1. 20260115_101220 -> 20260115_101228
- Summary: Freelancer_Data_Analysis.xlsx changed: Office document content changed.
- Likely stage: edit Office document
- Confidence: 0.75
- Evidence:
  - file: `"Freelancer_Data_Analysis.xlsx"`
  - office_delta: `{"headers": {"from": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior", "North America", "US", "Bachelor", "267.33999999999997"], "to": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior", "North America", "US", "Bachelor", "267.33999999999997"]}}`

## 2. 20260115_101228 -> 20260115_101253
- Summary: No observable file or directory change was detected between these snapshots.
- Likely stage: no observable benchmark state change
- Confidence: 0.2

## 3. 20260115_101253 -> 20260115_101352
- Summary: New files appeared: Freelancer_Income_Analysis_PPT.pptx.
- Likely stage: create or save file
- Confidence: 0.78
- Evidence:
  - files_added: `["Freelancer_Income_Analysis_PPT.pptx"]`

## 4. 20260115_101352 -> 20260115_101354
- Summary: No observable file or directory change was detected between these snapshots.
- Likely stage: no observable benchmark state change
- Confidence: 0.2

## 5. 20260115_101354 -> 20260115_101534
- Summary: Freelancer_Data_Analysis.xlsx changed: spreadsheet content changed from 5511 to 7515 non-empty cells.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Freelancer_Data_Analysis.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 5511, "to": 7515}, "headers": {"from": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior", "North America", "US", "Bachelor", "267.33999999999997"], "to": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior"]}}`

## 6. 20260115_101534 -> 20260115_101739
- Summary: Freelancer_Data_Analysis.xlsx changed: spreadsheet content changed from 7515 to 7539 non-empty cells; worksheet names changed; new visible headers or values include: Mobile Development, 88.255277777777764.
- Likely stage: enter or edit spreadsheet data + rename worksheet
- Confidence: 0.86
- Evidence:
  - file: `"Freelancer_Data_Analysis.xlsx"`
  - office_delta: `{"sheet_names": {"from": ["data", "Sheet1"], "to": ["Sheet2", "data", "Sheet1"]}, "worksheet_count": {"from": 2, "to": 3}, "nonempty_cells": {"from": 7515, "to": 7539}, "headers": {"from": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior"], "to": ["Mobile Development", "88.255277777777764", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision"]}}`
  - headers_added: `["Mobile Development", "88.255277777777764"]`

## 7. 20260115_101739 -> 20260115_101856
- Summary: Freelancer_Data_Analysis.xlsx changed: spreadsheet content changed from 7539 to 7529 non-empty cells; new visible headers or values include: 6.2, senior.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Freelancer_Data_Analysis.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 7539, "to": 7529}, "headers": {"from": ["Mobile Development", "88.255277777777764", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision"], "to": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior"]}}`
  - headers_added: `["6.2", "senior"]`

## 8. 20260115_101856 -> 20260115_101944
- Summary: Freelancer_Data_Analysis.xlsx changed: spreadsheet content changed from 7529 to 7541 non-empty cells; new visible headers or values include: 123.96311111111112.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Freelancer_Data_Analysis.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 7529, "to": 7541}, "headers": {"from": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior"], "to": ["AI/ML Engineering", "123.96311111111112", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision"]}}`
  - headers_added: `["123.96311111111112"]`

## 9. 20260115_101944 -> 20260115_102832
- Summary: Freelancer_Data_Analysis.xlsx changed: chart/drawing count changed from 0 to 1.
- Likely stage: create or modify chart
- Confidence: 0.9
- Evidence:
  - file: `"Freelancer_Data_Analysis.xlsx"`
  - office_delta: `{"chart_count": {"from": 0, "to": 1}, "headers": {"from": ["AI/ML Engineering", "123.96311111111112", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision"], "to": ["AI/ML Engineering", "123.96311111111112", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision"]}}`

## 10. 20260115_102832 -> 20260115_103034
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Freelancer_Income_Analysis_PPT.pptx", "size": {"from": 32122, "to": 33192}}]`

## 11. 20260115_103034 -> 20260115_103153
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Freelancer_Income_Analysis_PPT.pptx", "size": {"from": 33192, "to": 42941}}]`
