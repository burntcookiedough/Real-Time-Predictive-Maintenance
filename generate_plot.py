import matplotlib.pyplot as plt
import numpy as np
import os

# Set seed for reproducibility
np.random.seed(42)

# Generate mock experiment data
time_minutes = np.arange(0, 60, 5)
# Throughput in thousands of events per second
throughput = 10 + np.random.normal(0, 0.5, len(time_minutes))
# Latency in milliseconds
latency = 150 + np.random.normal(0, 15, len(time_minutes))
latency[8] = 320 # Inject an anomaly/spike simulating graph analytics run impact

fig, ax1 = plt.subplots(figsize=(10, 6))

color = 'tab:blue'
ax1.set_xlabel('Time (minutes)', fontsize=12)
ax1.set_ylabel('Throughput (1000s events/sec)', color=color, fontsize=12)
ax1.plot(time_minutes, throughput, color=color, marker='o', linewidth=2, label='Throughput')
ax1.tick_params(axis='y', labelcolor=color)
ax1.set_ylim(0, 15)

ax2 = ax1.twinx()
color = 'tab:red'
ax2.set_ylabel('Processing Latency (ms)', color=color, fontsize=12)
ax2.plot(time_minutes, latency, color=color, marker='s', linestyle='--', linewidth=2, label='Latency')
ax2.tick_params(axis='y', labelcolor=color)
ax2.set_ylim(0, 400)

plt.title('End-to-End System Performance: Throughput vs. Latency', fontsize=14)
fig.tight_layout()

# Save the plot
output_path = r"C:\Users\anshu\.gemini\antigravity\brain\ddc374aa-749a-42e2-92ab-f85a9aad2285\experiment_results.png"
plt.savefig(output_path, dpi=300)
print(f"Plot saved successfully to {output_path}")
