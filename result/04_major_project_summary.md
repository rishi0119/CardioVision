# CardioVision modeling summary

All metrics are computed on stratified held-out test sets. The 15 in-dataset fits use the six requested harmonized feature names; Logistic Regression is class-weighted only for Framingham. Precision, recall, and F1 use a 0.5 probability threshold. For runtime scalability, the RBF SVM uses a reproducible stratified 10,000-row subset of its training fold when that fold is larger; all other models use the full training fold, and every model is scored on the full test fold.

## Dataset and class balance

- **Cardio Train:** 68,761 records; train/test = 55,008/13,753; positive rate = 49.5%/49.5%.
- **Framingham:** 4,240 records; train/test = 3,392/848; positive rate = 15.2%/15.2%.
- **Cleveland:** 303 records; train/test = 242/61; positive rate = 45.9%/45.9%.

## In-dataset model comparison

| dataset | model | accuracy | precision | recall | f1 | roc_auc | brier_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cardio Train | Logistic Regression | 0.7186 | 0.7387 | 0.6675 | 0.7013 | 0.7755 | 0.1936 |
| Cardio Train | KNN (k=5) | 0.6875 | 0.6840 | 0.6848 | 0.6844 | 0.7356 | 0.2192 |
| Cardio Train | SVM (RBF) | 0.7228 | 0.7354 | 0.6868 | 0.7103 | 0.7748 | 0.1922 |
| Cardio Train | Random Forest | 0.7066 | 0.7222 | 0.6616 | 0.6905 | 0.7595 | 0.2028 |
| Cardio Train | Gradient Boosting | 0.7249 | 0.7340 | 0.6964 | 0.7147 | 0.7876 | 0.1868 |
| Framingham | Logistic Regression | 0.6474 | 0.2327 | 0.5736 | 0.3311 | 0.6908 | 0.2148 |
| Framingham | KNN (k=5) | 0.8349 | 0.3429 | 0.0930 | 0.1463 | 0.5768 | 0.1441 |
| Framingham | SVM (RBF) | 0.8514 | 0.6154 | 0.0620 | 0.1127 | 0.5434 | 0.1245 |
| Framingham | Random Forest | 0.8349 | 0.2963 | 0.0620 | 0.1026 | 0.6494 | 0.1297 |
| Framingham | Gradient Boosting | 0.8361 | 0.2727 | 0.0465 | 0.0795 | 0.6855 | 0.1253 |
| Cleveland | Logistic Regression | 0.6557 | 0.6400 | 0.5714 | 0.6038 | 0.7013 | 0.2181 |
| Cleveland | KNN (k=5) | 0.7049 | 0.6562 | 0.7500 | 0.7000 | 0.7603 | 0.2026 |
| Cleveland | SVM (RBF) | 0.6557 | 0.6522 | 0.5357 | 0.5882 | 0.7143 | 0.2164 |
| Cleveland | Random Forest | 0.6885 | 0.6800 | 0.6071 | 0.6415 | 0.7376 | 0.2054 |
| Cleveland | Gradient Boosting | 0.6557 | 0.6296 | 0.6071 | 0.6182 | 0.6380 | 0.2529 |

## Best ROC-AUC model per dataset

| dataset | model | roc_auc | brier_score |
| --- | --- | --- | --- |
| Cardio Train | Gradient Boosting | 0.7876 | 0.1868 |
| Cleveland | KNN (k=5) | 0.7603 | 0.2026 |
| Framingham | Logistic Regression | 0.6908 | 0.2148 |

## Zero-shot Cardio Train → Framingham/Cleveland

`roc_auc_change` = OOD ROC-AUC − held-out Cardio Train ROC-AUC (negative values indicate a drop). All destination records are evaluated without refitting the transferred model or its preprocessing.

| destination | model | cardio_test_roc_auc | ood_roc_auc | roc_auc_change | accuracy | precision | recall | f1 | brier_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Framingham | Logistic Regression | 0.7755 | 0.5045 | -0.2710 | 0.1592 | 0.1532 | 1.0000 | 0.2657 | 0.8391 |
| Cleveland | Logistic Regression | 0.7755 | 0.5000 | -0.2755 | 0.4590 | 0.4590 | 1.0000 | 0.6292 | 0.5410 |
| Framingham | KNN (k=5) | 0.7356 | 0.5824 | -0.1532 | 0.3892 | 0.1742 | 0.8062 | 0.2865 | 0.4205 |
| Cleveland | KNN (k=5) | 0.7356 | 0.5395 | -0.1961 | 0.4426 | 0.4483 | 0.9286 | 0.6047 | 0.3600 |
| Framingham | SVM (RBF) | 0.7748 | 0.5039 | -0.2710 | 0.1568 | 0.1528 | 1.0000 | 0.2652 | 0.3929 |
| Cleveland | SVM (RBF) | 0.7748 | 0.5000 | -0.2748 | 0.4590 | 0.4590 | 1.0000 | 0.6292 | 0.2913 |
| Framingham | Random Forest | 0.7595 | 0.5875 | -0.1720 | 0.4186 | 0.1773 | 0.7752 | 0.2886 | 0.3964 |
| Cleveland | Random Forest | 0.7595 | 0.4394 | -0.3201 | 0.4590 | 0.4545 | 0.8929 | 0.6024 | 0.4143 |
| Framingham | Gradient Boosting | 0.7876 | 0.6331 | -0.1545 | 0.3962 | 0.1814 | 0.8450 | 0.2986 | 0.3601 |
| Cleveland | Gradient Boosting | 0.7876 | 0.5065 | -0.2811 | 0.4590 | 0.4590 | 1.0000 | 0.6292 | 0.4101 |

## Interpretation and limitations

- Calibration curves are in `calibration_curves.png`; Brier scores in the tables measure probability error (lower is better).
- The shared input columns are not measurement-equivalent: Cardio cholesterol/glucose are ordinal codes; Framingham cholesterol/glucose are measured concentrations; Cleveland uses cholesterol concentration and binary fasting blood sugar. Cardio sex codes were normalized to male=1, female=0.
- Cleveland has no smoking field and only systolic resting pressure. Its requested shared `smoke` feature is filled using the Cardio Train training-fold median, and its shared `MAP` field uses systolic pressure as a clearly imperfect proxy. This mapping is fixed without fitting on Cleveland data.
- The outcome definitions differ: Cardio disease status, Framingham ten-year CHD risk, and Cleveland disease presence. Zero-shot results confound population, measurement, and endpoint shifts and should not be interpreted as clinical performance estimates.
