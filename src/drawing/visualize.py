import matplotlib
matplotlib.use('Agg')  # Force non-GUI backend before importing pyplot

import matplotlib.pyplot as plt
from src.constants import LANES_BY_POOL, TIME_SLOTS
import io


def generate_visualization(availability, pool_name, date_str):
    """Generate and save the swim lane availability visualization with a clean reset."""
    lanes = LANES_BY_POOL[pool_name]
    num_lanes = len(lanes)
    num_times = len(TIME_SLOTS)

    fig, ax = plt.subplots(figsize=(14, 8))

    # Draw the table cells
    for i, lane in enumerate(reversed(lanes)):  # Reverse for top-down display
        for j, time in enumerate(TIME_SLOTS):
            is_available = lane in availability.get(time, [])
            color = "green" if is_available else "red"
            rect = plt.Rectangle((j, i), 1, 1, facecolor=color, edgecolor="black")
            ax.add_patch(rect)
            ax.text(j + 0.5, i + 0.5, lane.split()[-1], ha="center", va="center", fontsize=9, color="white")

    # ✅ Keep Grid Aligned (Prevent Shifting)
    ax.set_xlim(0, num_times)
    ax.set_ylim(0, num_lanes)

    # ✅ Standard Tick Labels
    ax.set_xticks(range(num_times))
    ax.set_xticklabels(TIME_SLOTS, fontsize=8, rotation=45, ha="center")

    ax.set_yticks(range(num_lanes))
    ax.set_yticklabels(reversed(lanes), fontsize=10, va="center")

    # Adjust subplot parameters to center the axes
    plt.subplots_adjust(left=0.15, right=0.85, top=0.85, bottom=0.15)

    # ✅ Standard Axis Labels (No Offset Adjustments)
    ax.set_xlabel("Time Slots", fontsize=14, fontweight="bold")
    ax.set_ylabel("Lanes", fontsize=14, fontweight="bold")

    # ✅ Standard Title Placement
    ax.set_title(f"{pool_name} Availability for {date_str}", fontsize=16, fontweight="bold")

    # ✅ Default Spines and Gridlines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    # Save to a temporary in-memory file
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png', bbox_inches="tight")
    img_io.seek(0)

    plt.close(fig)  # Close the figure to free memory

    return img_io
