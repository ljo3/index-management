import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
from index_management.strategy.Manager import MaxSharpeRatioPortfolio

st.title("Portfolio Visualization App")
st.write("This app visualizes portfolio weights and covariance matrices for a given Max Sharpe Ratio Portfolio strategy")

# Date select
target_date = st.selectbox(
    "Select the target date (YYYYMMDD):",
    options=[20231231, 20240331, 20240630, 20240930, 20241231, 20250331],
    index=5  # Default to 20250331
)

# Calculate weights
msr = MaxSharpeRatioPortfolio(target_date)
prior, df_weights = msr.calculate_weights()
df_weights.set_index('Asset', inplace=True)

# Display weights
st.subheader("Portfolio Weights - Comparing Sample Covariance vs Ledoit Wolf Covariance")
st.bar_chart(df_weights)

# Covariance matrices visualization
st.subheader("Covariance Matrices")
fig, axes = plt.subplots(1, 2, figsize=(12, 6))

# Sample covariance matrix
sns.heatmap(msr.df_sample_cov_matrix, annot=False, cmap="coolwarm", cbar=True, ax=axes[0])
axes[0].set_title("Sample Covariance Matrix")

# Ledoit-Wolf shrunk covariance matrix
sns.heatmap(msr.df_LedoitWolf_cov_matrix, annot=False, cmap="coolwarm", cbar=True, ax=axes[1])
axes[1].set_title("Ledoit-Wolf Shrunk Covariance Matrix")

st.pyplot(fig)

# Portfolio weights comparison plot
st.subheader("Portfolio Weights Comparison")

fig, ax = plt.subplots(figsize=(12, 6))
df_weights.plot(kind='bar', ax=ax)
ax.set_title('Portfolio Weights Comparison - Sample vs Ledoit-Wolf Shrunk Covariance', fontsize=16)
ax.set_ylabel('Weight', fontsize=12)
ax.set_xlabel('Asset', fontsize=12)
ax.set_xticklabels(df_weights.index, rotation=45)
ax.legend(['Sample Covariance', 'Ledoit-Wolf Covariance'], fontsize=12)

st.pyplot(fig)