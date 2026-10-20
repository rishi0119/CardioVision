# Data inspection summary

Generated from the source files by `notebook/01_data_inspection.ipynb`.

- The processed Cleveland source contains **6** literal `?` missing-value flags; these were parsed as nulls for inspection.

## Cardio Train

- **Shape:** 70,000 rows × 13 columns.
- **Target:** `cardio`; class distribution (count and percent):
| Class | Count | Percent |
|---|---:|---:|
| 0 | 35021 | 50.03% |
| 1 | 34979 | 49.97% |
- **Missing values:** none detected (total 0).
- **Column dtypes:** `id`: `int64`, `age`: `int64`, `gender`: `int64`, `height`: `int64`, `weight`: `float64`, `ap_hi`: `int64`, `ap_lo`: `int64`, `cholesterol`: `int64`, `gluc`: `int64`, `smoke`: `int64`, `alco`: `int64`, `active`: `int64`, `cardio`: `int64`.

## Framingham

- **Shape:** 4,240 rows × 16 columns.
- **Target:** `TenYearCHD`; class distribution (count and percent):
| Class | Count | Percent |
|---|---:|---:|
| 0 | 3596 | 84.81% |
| 1 | 644 | 15.19% |
- **Missing values:** `education`: 105; `cigsPerDay`: 29; `BPMeds`: 53; `totChol`: 50; `BMI`: 19; `heartRate`: 1; `glucose`: 388 (total 645).
- **Column dtypes:** `male`: `int64`, `age`: `int64`, `education`: `float64`, `currentSmoker`: `int64`, `cigsPerDay`: `float64`, `BPMeds`: `float64`, `prevalentStroke`: `int64`, `prevalentHyp`: `int64`, `diabetes`: `int64`, `totChol`: `float64`, `sysBP`: `float64`, `diaBP`: `float64`, `BMI`: `float64`, `heartRate`: `float64`, `glucose`: `float64`, `TenYearCHD`: `int64`.

## Cleveland

- **Shape:** 303 rows × 14 columns.
- **Target:** `target`; class distribution (count and percent):
| Class | Count | Percent |
|---|---:|---:|
| 0 | 164 | 54.13% |
| 1 | 55 | 18.15% |
| 2 | 36 | 11.88% |
| 3 | 35 | 11.55% |
| 4 | 13 | 4.29% |
- **Missing values:** `ca`: 4; `thal`: 2 (total 6).
- **Column dtypes:** `age`: `float64`, `sex`: `float64`, `cp`: `float64`, `trestbps`: `float64`, `chol`: `float64`, `fbs`: `float64`, `restecg`: `float64`, `thalach`: `float64`, `exang`: `float64`, `oldpeak`: `float64`, `slope`: `float64`, `ca`: `float64`, `thal`: `float64`, `target`: `int64`.

## Cross-dataset data-type discrepancies

- The datasets use different field names and units for related attributes: cardio `age` is recorded in days, while Framingham and Cleveland `age` are in years; blood pressure and cholesterol fields also have dataset-specific names.
- Cardio Train is predominantly integer-valued with floating-point `weight`; Framingham has a mix of integer and floating-point columns.
- Cleveland's headerless file is parsed mostly as `float64` because its numeric fields contain decimal-formatted values and `?` placeholders; `target` is integer-valued. Encoded clinical categories are numeric codes, not continuous measurements.
- Missingness is explicitly represented by `?` in Cleveland (`ca` and `thal`) and by blank values in Framingham. Cardio Train has no nulls in its source columns.
