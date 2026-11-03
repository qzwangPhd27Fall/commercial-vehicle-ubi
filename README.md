# Commercial-Vehicle UBI Risk Assessment

A usage-based insurance (UBI) risk-scoring prototype for commercial-vehicle fleets, demonstrating an end-to-end pipeline from driving/ADAS signals to a risk score and premium-adjustment recommendation.

## Method

Risk factors are calibrated through a **three-layer approach** in the absence of full telematics data:

1. **Sample vehicle** — real 4-day operating data (ADAS alerts, distance, speed) to calibrate alert structure and aggregation.
2. **Industry public parameters** — published fleet alert rates and UBI discriminative-power ranges to set magnitudes.
3. **Monte Carlo simulation** — a 400-vehicle fleet generated from (1)+(2) to fit and validate the model.

Scoring combines a **rule-based factor score** with a **GLM (Poisson frequency) model**, averaged 50/50, mapped to a rank-percentile grade (A–E).

## Validation metrics

| Metric | Value | Target |
|---|---|---|
| Model Gini | 0.317 | > 0 (random = 0; strong UBI ≈ 0.3–0.4) |
| ADAS incremental Gini | +8.2 pct | 5–15 pct (literature range) |
| E-grade lift | 1.86 | ≥ 1.5 |
| K–S statistic | 0.262 | ≥ 0.20 |
| Claim-rate monotonicity | strictly increasing | A→E 0.062→0.400 |

## Files

- `demo_pipeline.py` — full reproducible pipeline (simulate → factors → scoring → GLM → validation)
- `build_dashboard.py` — self-contained SVG dashboard generator
- `biz_analysis.py` — business-metric analysis
- `商用车UBI产品演示.html` — standalone dashboard (open in browser)

> **Data note:** ADAS-alert → claim associations are constructed by simulation (accident-pyramid logic); they have not yet been validated against real claims. This is a feasibility demonstration, not a filed rate.

## Run

```bash
python demo_pipeline.py
```

## Related CV entry

This repository is the code for the research experience **"Commercial-Vehicle UBI & ADAS Risk Assessment"** on my CV.
