# Limitations, risk and responsible interpretation

This prototype is **not** a regulated investment, fraud, credit or compliance
service. It does not place trades or approve/reject loans.

1. **Synthetic data vs. actual ESG truth**: C02 and C06 use generated labels and
   unusually separable features. PR-AUC reflects this test generator only.
   No real-world performance claims are justified without independent labeled
   data, entity/time splits, external evaluation and operating-point review.
2. **Issuer disclosures**: uploaded reports may be incomplete or misleading.
   ChromaDB retrieval establishes citation provenance, not report truth or
   independent sustainability assurance. No evidence -> unverified.
3. **Predictive uncertainty**: historical price return signals, regularized
   covariance and a simple KRBN proxy trend cannot predict a reliable future
   return. The forecast band is heuristic, not calibrated coverage.
4. **Regulatory explainability**: C06 SHAP explains the C02 IsolationForest
   anomaly score for 3 synthetic decisions, NOT the entire final portfolio,
   true causality, or a legal approval/rejection. Separate documented portfolio
   reason codes and citations support the investment memo.
5. **Feedback**: simulated outcomes are held separately and explicitly marked.
   The prototype does not currently match future real returns to live predictions
   automatically. Only verified labels may influence market-mode decisions.
6. **Architecture scope**: a single-process Streamlit/LangGraph system is used,
   not container-orchestrated distributed microservices. Docker and sample CI
   are supplied, but EC2/Jenkins execution and MongoDB Atlas deployment have
   not been independently tested.
7. **API dependency**: Groq/Llama-3 from the original statement was replaced by
   optional Gemini/OpenRouter in the existing repository. In the absence of
   a provider or validated report, real-company ESG assessment is unverified.
8. **Data privacy and licensing**: do not commit confidential reports, account
   numbers, private keys or credentials. Confirm permission to index/share
   ESG documents. `.gitignore` excludes downloaded data and database files.

## Next steps beyond the hackathon

- Obtain documented, licensed, independently labeled ESG disclosure outcomes.
- Extract six C02 features from issuer-linked reports with preprocessing tests.
- Validate issuer/time generalization and drift, confidence calibration, and
  fairness/cost-aware alert policy with regulator-approved thresholds.
- Add robust external market/ESG data contracts, as-of clocks, historical
  reproducibility and automated monitoring.
- Connect real future outcomes via verified timestamped labels and evaluate
  before applying performance feedback.
- Scale services only when performance requirements justify it.
