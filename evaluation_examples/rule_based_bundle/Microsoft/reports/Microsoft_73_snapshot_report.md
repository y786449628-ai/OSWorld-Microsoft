# Microsoft_73 Snapshot Transition Report

## 1. 20260114_203921 -> 20260114_204040
- Summary: New files appeared: Freelancer_Income_Analysis_PPT.pptx.
- Likely stage: create or save file
- Confidence: 0.78
- Evidence:
  - files_added: `["Freelancer_Income_Analysis_PPT.pptx"]`

## 2. 20260114_204040 -> 20260114_204217
- Summary: Freelancer_Dta_Analysis.xlsx changed: spreadsheet content changed from 5511 to 7515 non-empty cells.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Freelancer_Dta_Analysis.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 5511, "to": 7515}, "headers": {"from": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior", "North America", "US", "Bachelor", "267.33999999999997"], "to": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior"]}}`

## 3. 20260114_204217 -> 20260114_204319
- Summary: Freelancer_Dta_Analysis.xlsx changed: spreadsheet content changed from 7515 to 7525 non-empty cells; worksheet names changed.
- Likely stage: enter or edit spreadsheet data + rename worksheet
- Confidence: 0.86
- Evidence:
  - file: `"Freelancer_Dta_Analysis.xlsx"`
  - office_delta: `{"sheet_names": {"from": ["data", "Sheet1"], "to": ["Sheet2", "data", "Sheet1"]}, "worksheet_count": {"from": 2, "to": 3}, "nonempty_cells": {"from": 7515, "to": 7525}, "headers": {"from": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior"], "to": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior"]}}`

## 4. 20260114_204319 -> 20260114_204345
- Summary: Freelancer_Dta_Analysis.xlsx changed: spreadsheet content changed from 7525 to 7533 non-empty cells; new visible headers or values include: junior, 42994.508043478258.
- Likely stage: enter or edit spreadsheet data
- Confidence: 0.86
- Evidence:
  - file: `"Freelancer_Dta_Analysis.xlsx"`
  - office_delta: `{"nonempty_cells": {"from": 7525, "to": 7533}, "headers": {"from": ["freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision", "6.2", "senior"], "to": ["junior", "42994.508043478258", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision"]}}`
  - headers_added: `["junior", "42994.508043478258"]`

## 5. 20260114_204345 -> 20260114_205157
- Summary: Freelancer_Dta_Analysis.xlsx changed: chart/drawing count changed from 0 to 1.
- Likely stage: create or modify chart
- Confidence: 0.9
- Evidence:
  - file: `"Freelancer_Dta_Analysis.xlsx"`
  - office_delta: `{"chart_count": {"from": 0, "to": 1}, "headers": {"from": ["junior", "42994.508043478258", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision"], "to": ["junior", "42994.508043478258", "freelancer_id", "category", "primary_skills", "years_experience", "experience_level", "region", "country", "education", "hourly_rate_usd", "annual_income_usd", "primary_platform", "experience_level", "category", "annual_income_usd", "hourly_rate_usd", "FL0010", "AI/ML Engineering", "PyTorch, NLP, Computer Vision"]}}`

## 6. 20260114_205157 -> 20260114_205521
- Summary: One or more files changed size, but no detailed Office feature delta was detected.
- Likely stage: formatting, metadata, save, or subtle document edit
- Confidence: 0.45
- Evidence:
  - files_changed: `[{"path": "Freelancer_Income_Analysis_PPT.pptx", "size": {"from": 32137, "to": 40787}}]`
