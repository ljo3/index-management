# TODO

## scikit-learn enhancements

### Covariance estimation
- [ ] **`sklearn.covariance.OAS`** — swap in alongside LedoitWolf in `MaxSharpeRatioPortfolio` to compare Oracle Approximating Shrinkage vs. LedoitWolf bias-variance tradeoff
- [ ] **`sklearn.covariance.GraphicalLassoCV`** — sparse inverse covariance (precision matrix); maps to a conditional independence graph of stock returns, useful for concentrated portfolios

### Dimensionality reduction
- [ ] **`sklearn.decomposition.PCA` on returns** — reconstruct a full-rank covariance from k principal components (statistical factor model) before passing to the MSR optimizer; addresses rank-deficiency with 40 stocks and limited history

### Backtesting / validation
- [ ] **`sklearn.model_selection.TimeSeriesSplit`** — wrap the quarter-by-quarter strategy in a proper walk-forward CV loop; enforces temporal ordering and lets you evaluate whether MSR generalizes out-of-sample

### New strategy
- [ ] **Hierarchical Risk Parity (HRP)** — use `sklearn.cluster.AgglomerativeClustering` on the return correlation matrix as the first step; add as a third strategy class `HierarchicalRiskParity` alongside `CapWeight` and `MaxSharpeRatioPortfolio`; more robust to estimation error than MSR

### Data quality
- [ ] **`sklearn.ensemble.IsolationForest`** or **`sklearn.neighbors.LocalOutlierFactor`** — detect outlier prices/returns before they propagate into the covariance matrix

---

# DONE

## Move data/ to S3

*Prerequisites before Claude can wire up the CI and code changes:*

- [x] Install AWS CLI — `brew install awscli`
- [x] Create an IAM user in AWS console with S3 read/write permissions
- [x] Run `aws configure` with your access key + secret
- [x] Create an S3 bucket (`index-management-data`, eu-west-3)
- [x] Add 3 GitHub Secrets to the repo: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- [x] CI workflows updated, `data/` removed from git, synced to S3
