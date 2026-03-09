import matplotlib.pyplot as plt
import numpy as np
import os

# Set seed for reproducibility
np.random.seed(42)

# Metrics
labels = ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'AUC-ROC']
edge_model_scores = [0.95, 0.92, 0.89, 0.90, 0.96]
batch_model_scores = [0.98, 0.96, 0.97, 0.96, 0.99]

x = np.arange(len(labels))  # the label locations
width = 0.35  # the width of the bars

fig, ax = plt.subplots(figsize=(10, 6))
rects1 = ax.bar(x - width/2, edge_model_scores, width, label='Edge Model (Real-Time)', color='#1f77b4')
rects2 = ax.bar(x + width/2, batch_model_scores, width, label='Batch Analytics (Retrained)', color='#ff7f0e')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_ylabel('Scores', fontsize=12)
ax.set_title('Machine Learning Model Performance Comparison', fontsize=14)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=11)
ax.set_ylim(0.8, 1.05)
ax.legend(loc='upper left', fontsize=11)

# Function to auto-label the bars
def autolabel(rects):
    """Attach a text label above each bar in *rects*, displaying its height."""
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10)

autolabel(rects1)
autolabel(rects2)

fig.tight_layout()

# Save the plot
output_path = r"C:\Users\anshu\.gemini\antigravity\brain\ddc374aa-749a-42e2-92ab-f85a9aad2285\performance_evaluation.png"
plt.savefig(output_path, dpi=300)
print(f"Plot saved successfully to {output_path}")
