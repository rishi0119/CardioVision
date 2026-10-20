# CardioVision: cross-dataset cardiovascular risk modeling

**Major project report — Phases 1–5**  
**Evaluation artifact:** [final dashboard](../result/final_evaluation_dashboard.png)  
**Generated from:** `notebook/05_evaluation.ipynb`

## Abstract & Problem Statement

This project evaluates tabular cardiovascular risk classifiers across three public datasets: Cardio Train, Framingham, and the Cleveland heart-disease cohort. It combines source-specific cleaning with a six-feature shared representation, compares five binary classifiers using stratified held-out tests, assesses probability quality with Brier scores and calibration error, and probes transportability using zero-shot cross-dataset evaluation. The best held-out ROC-AUC was **0.7876** for Cardio Train (Gradient Boosting) , **0.6908** for Framingham (Logistic Regression), and **0.7603** for Cleveland (KNN (k=5)). Transfer from Cardio Train to both external datasets reduced ROC-AUC for every model. These findings demonstrate why in-dataset discrimination alone is insufficient evidence for a portable clinical prediction model.

The central problem is whether predictive performance measured within one cohort generalizes to populations with different feature distributions, measurement conventions, and outcome definitions. The study treats the cross-dataset experiment as an exploratory stress test, not as external clinical validation.

## Literature Gap Analysis

This project operationalizes three recurring evaluation risks in applied clinical machine learning; it is a project-level gap analysis, not a systematic literature review.

1. **In-distribution overfitting and optimistic validation.** Random train/test partitions from the same source population can preserve cohort-specific patterns and do not establish transportability. A held-out split is necessary for benchmarking but should be supplemented by external validation.
2. **Target mismatch across datasets.** Cardio disease status, Framingham ten-year coronary heart disease risk, and Cleveland disease presence represent related but non-identical endpoints. AUC differences across these datasets therefore reflect endpoint and cohort shifts together, not population shift alone.
3. **Miscalibration hidden by discrimination metrics.** Ranking metrics such as ROC-AUC do not indicate whether predicted probabilities correspond to observed event frequencies. Brier scores and calibration curves add probability-quality evidence relevant to threshold-based decision support.

## Methodology & Novelty Features

- **Data preparation:** Cardio Train blood pressure was filtered using the prior physiological bounds; age in days was converted to integer years. Cleveland `?` markers in `ca`/`thal` were median-imputed, and disease severity was mapped to binary (`target > 0`). Framingham clinical predictors were median-imputed. Imputers and `StandardScaler` instances were fitted only on each training fold.
- **Harmonized MAP feature engineering:** MAP was calculated as `DBP + (SBP - DBP) / 3` for Cardio Train and Framingham, enabling a shared pressure summary. Cleveland has only resting systolic pressure, so systolic pressure served as a clearly documented MAP proxy; it is not physiologically equivalent to true MAP.
- **Shared input representation:** `age_years`, `sex`, `chol`, `glucose/fbs`, `MAP`, and `smoke`. Cardio sex codes were normalized to male=1/female=0. Cardio cholesterol/glucose are ordinal codes, Framingham uses measured concentrations, and Cleveland uses measured cholesterol plus fasting-glucose status. Cleveland lacks smoking; this field was imputed using the Cardio Train training-fold median for strict zero-shot application.
- **Zero-shot OOD testing:** Cardio Train models and its fitted imputer/scaler were applied directly to held-out Framingham and Cleveland data without destination retraining or preprocessing refitting. This intentionally stringent transfer test captures both dataset and endpoint incompatibility.
- **Calibration assessment:** Brier score and ten-quantile-bin calibration error (ECE) accompany ROC curves and classification metrics. The dashboard reports held-out predictions and a Gradient Boosting feature-importance ranking.

## Experimental Setup & 5-Model Benchmark

Each cohort used a reproducible stratified 80/20 train/test split (random state 42). Logistic Regression, 5-nearest neighbors, RBF-kernel SVM with probability estimates, a 100-tree Random Forest, and Gradient Boosting were compared. Framingham Logistic Regression used balanced class weights. The RBF SVM used a reproducible stratified 10,000-row training subset when fitting on the large Cardio cohort; all models were evaluated on the full held-out test set. Precision, recall, and F1 use a 0.5 probability threshold.

- **Cardio Train:** 68,761 records; stratified train/test sizes 55,008/13,753; positive prevalence 49.5%/49.5%.
- **Framingham:** 4,240 records; stratified train/test sizes 3,392/848; positive prevalence 15.2%/15.2%.
- **Cleveland:** 303 records; stratified train/test sizes 242/61; positive prevalence 45.9%/45.9%.

## Results & Discussion

### In-dataset benchmark

| dataset | model | accuracy | precision | recall | f1 | roc_auc | brier_score | ece_10_quantile_bins |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cardio Train | Logistic Regression | 0.7186 | 0.7387 | 0.6675 | 0.7013 | 0.7755 | 0.1936 | 0.0334 |
| Cardio Train | KNN (k=5) | 0.6875 | 0.6840 | 0.6848 | 0.6844 | 0.7356 | 0.2192 | 0.0925 |
| Cardio Train | SVM (RBF) | 0.7228 | 0.7354 | 0.6868 | 0.7103 | 0.7748 | 0.1922 | 0.0255 |
| Cardio Train | Random Forest | 0.7066 | 0.7222 | 0.6616 | 0.6905 | 0.7595 | 0.2028 | 0.0471 |
| Cardio Train | Gradient Boosting | 0.7249 | 0.7340 | 0.6964 | 0.7147 | 0.7876 | 0.1868 | 0.0071 |
| Framingham | Logistic Regression | 0.6474 | 0.2327 | 0.5736 | 0.3311 | 0.6908 | 0.2148 | 0.2849 |
| Framingham | KNN (k=5) | 0.8349 | 0.3429 | 0.0930 | 0.1463 | 0.5768 | 0.1441 | 0.1198 |
| Framingham | SVM (RBF) | 0.8514 | 0.6154 | 0.0620 | 0.1127 | 0.5434 | 0.1245 | 0.0386 |
| Framingham | Random Forest | 0.8349 | 0.2963 | 0.0620 | 0.1026 | 0.6494 | 0.1297 | 0.0638 |
| Framingham | Gradient Boosting | 0.8361 | 0.2727 | 0.0465 | 0.0795 | 0.6855 | 0.1253 | 0.0404 |
| Cleveland | Logistic Regression | 0.6557 | 0.6400 | 0.5714 | 0.6038 | 0.7013 | 0.2181 | 0.1057 |
| Cleveland | KNN (k=5) | 0.7049 | 0.6562 | 0.7500 | 0.7000 | 0.7603 | 0.2026 | 0.0623 |
| Cleveland | SVM (RBF) | 0.6557 | 0.6522 | 0.5357 | 0.5882 | 0.7143 | 0.2164 | 0.1481 |
| Cleveland | Random Forest | 0.6885 | 0.6800 | 0.6071 | 0.6415 | 0.7376 | 0.2054 | 0.2146 |
| Cleveland | Gradient Boosting | 0.6557 | 0.6296 | 0.6071 | 0.6182 | 0.6380 | 0.2529 | 0.1909 |

The top in-dataset model by ROC-AUC was **Gradient Boosting** on Cardio Train (AUC 0.7876, Brier 0.1868), **Logistic Regression** on Framingham (AUC 0.6908, Brier 0.2148), and **KNN (k=5)** on Cleveland (AUC 0.7603, Brier 0.2026). Framingham has a lower positive prevalence (15.2% in its test set), so accuracy and ROC-AUC should be interpreted alongside recall, precision, and calibration rather than in isolation.

### Zero-shot transfer

| destination | model | cardio_test_roc_auc | ood_roc_auc | roc_auc_change | accuracy | precision | recall | f1 | brier_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Framingham | Logistic Regression | 0.7755 | 0.5045 | -0.2710 | 0.1592 | 0.1532 | 1.0000 | 0.2657 | 0.8391 |
| Cleveland | Logistic Regression | 0.7755 | 0.5000 | -0.2755 | 0.4590 | 0.4590 | 1.0000 | 0.6292 | 0.5410 |
| Framingham | KNN (k=5) | 0.7356 | 0.5824 | -0.1532 | 0.3892 | 0.1742 | 0.8062 | 0.2865 | 0.4205 |
| Cleveland | KNN (k=5) | 0.7356 | 0.5395 | -0.1961 | 0.4426 | 0.4483 | 0.9286 | 0.6047 | 0.3600 |
| Framingham | SVM (RBF) | 0.7748 | 0.5039 | -0.2710 | 0.1568 | 0.1528 | 1.0000 | 0.2652 | 0.3929 |
| Cleveland | SVM (RBF) | 0.7748 | 0.5000 | -0.2748 | 0.4590 | 0.4590 | 1.0000 | 0.6292 | 0.2913 |
| Framingham | Random Forest | 0.7595 | 0.5875 | -0.1720 | 0.4186 | 0.1773 | 0.7752 | 0.2886 | 0.3964 |
| Cleveland | Random Forest | 0.7595 | 0.4399 | -0.3195 | 0.4590 | 0.4545 | 0.8929 | 0.6024 | 0.4143 |
| Framingham | Gradient Boosting | 0.7876 | 0.6331 | -0.1545 | 0.3962 | 0.1814 | 0.8450 | 0.2986 | 0.3601 |
| Cleveland | Gradient Boosting | 0.7876 | 0.5065 | -0.2811 | 0.4590 | 0.4590 | 1.0000 | 0.6292 | 0.4101 |

All ten zero-shot comparisons had lower ROC-AUC than the corresponding Cardio Train baseline. The least negative transfer changes were -0.1532 to Framingham and -0.1961 to Cleveland. Average ROC-AUC drops across the five Cardio-trained models were 0.2043 and 0.2694, respectively. The Cardio Train Gradient Boosting transfer AUCs were 0.6331 for Framingham and 0.5065 for Cleveland. The dashboard shows all model-by-destination ROC-AUC changes.

These results are consistent with substantial distribution and label shift, but do not isolate their individual causal contributions. In particular, the Cleveland proxy features and distinct disease endpoint limit direct clinical comparability. ROC-AUC drop indicates ranking degradation; destination Brier scores and calibration behavior also shift, so source-cohort probability interpretation should not be carried over to the external cohorts.

### Feature ranking

For the Cardio Train Gradient Boosting model, the three largest impurity-based feature importances were: `MAP` (0.755), `age_years` (0.144), `chol` (0.088). These are model-specific predictive associations, not causal effects or clinical risk factors ranked across cohorts.

## Clinical Decision Support & Future Scope

The current models are research prototypes and must not be used to diagnose, rule out disease, recommend treatment, or replace clinician judgment. Before decision-support use, a model would require prespecified target definitions, clinically equivalent input measurements, representative prospective external cohorts, subgroup and fairness analyses, confidence intervals, calibration assessment and (if justified) recalibration, threshold/utility analysis, human-factors testing, governance, and ongoing drift monitoring. Missingness patterns and dataset provenance must be documented for each deployed source.

Future work should (1) align outcomes and prediction horizons, (2) validate on independent contemporary cohorts with consistent laboratory and blood-pressure protocols, (3) compare recalibration and domain-adaptation approaches only after retaining a strict untouched external test set, (4) estimate uncertainty using repeated or nested validation and bootstrap intervals, (5) evaluate decision-curve/net-benefit measures and subgroup performance, and (6) develop a versioned, auditable pipeline with clinician input and post-deployment safety monitoring.

## Reproducibility and Artifacts

- Evaluation notebook: `../notebook/05_evaluation.ipynb`.
- Four-panel dashboard: `../result/final_evaluation_dashboard.png`.
- In-dataset metrics: `../result/evaluation_metrics.csv`.
- Zero-shot metrics: `../result/evaluation_zero_shot_metrics.csv`.
- Test probabilities and targets: `../result/evaluation_performance_arrays.npz`.
- Cardio Train Gradient Boosting feature ranking: `../result/cardio_gradient_boosting_feature_importance.csv`.
