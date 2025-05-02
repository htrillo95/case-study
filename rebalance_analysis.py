import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data
df = pd.read_csv("Classified_Routes.csv")

# Sort and filter overloaded routes
sorted_df = df.sort_values(by="estimated_stops_per_day", ascending=False)
threshold = 52
overloaded = sorted_df[sorted_df["estimated_stops_per_day"] > threshold]

print("Overloaded Routes:")
print(overloaded)

# Rebalancing function: divide stops evenly across ZIPs
def rebalance_row(row):
    zips = str(row["zip_codes"]).split()
    total_stops = row["estimated_stops_per_day"]
    stops_per_zip = total_stops // len(zips)
    return pd.DataFrame({
        "route_code": [row["route_code"]] * len(zips),
        "zip_code": zips,
        "rebalanced_stops": [stops_per_zip] * len(zips)
    })

# Apply rebalance logic
rebalanced_frames = [rebalance_row(row) for _, row in overloaded.iterrows()]
rebalanced_df = pd.concat(rebalanced_frames, ignore_index=True)

# Display sample
print(rebalanced_df.head(10))

# Standard deviation before and after
original_std = overloaded["estimated_stops_per_day"].std()
rebalance_std = rebalanced_df.groupby("route_code")["rebalanced_stops"].sum().std()
print(f"STD Before: {original_std}, After: {rebalance_std}")

# Top ZIPs by workload
zip_totals = rebalanced_df.groupby("zip_code")["rebalanced_stops"].sum().sort_values(ascending=False)
print("Top ZIPs by Rebalanced Stops:")
print(zip_totals.head(10))

# ---- 📊 Chart: Before vs After ----

routes = overloaded["route_code"].values
original = overloaded["estimated_stops_per_day"].values
rebalance = rebalanced_df.groupby("route_code")["rebalanced_stops"].sum().reindex(routes).values

# Sort by biggest improvement (difference)
improvement = original - rebalance
sorted_indices = np.argsort(improvement)[::-1]
routes = routes[sorted_indices]
original = original[sorted_indices]
rebalance = rebalance[sorted_indices]

x = np.arange(len(routes))
bar_width = 0.4

plt.figure(figsize=(12, 6))
plt.gca().set_facecolor("#f7f7f7")
plt.grid(axis="y", linestyle="--", alpha=0.4)

# Bars
plt.bar(x, original, width=bar_width, label="Original", color="tomato")
plt.bar(x + bar_width, rebalance, width=bar_width, label="Rebalanced", color="skyblue")

# Annotations
for i in range(len(routes)):
    plt.text(x[i], original[i] + 0.5, str(original[i]), ha="center", fontsize=8)
    plt.text(x[i] + bar_width, rebalance[i] + 0.5, str(rebalance[i]), ha="center", fontsize=8)

# Labels
plt.xticks(x + bar_width / 2, routes, rotation=45)
plt.ylabel("Stops per Route")
plt.title("Before vs After Rebalancing (Sorted by Impact)")
plt.legend()
plt.tight_layout()
plt.show()