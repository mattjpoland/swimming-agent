import matplotlib
matplotlib.use('Agg')  # Force non-GUI backend before importing pyplot

import matplotlib.pyplot as plt
import src.contextManager 
import io
import datetime
from io import BytesIO
import matplotlib.image as mpimg
import numpy as np

def generate_visualization(availability, pool_name, date_str, appt, context):
    """Generate and save the swim lane availability visualization with a clean reset."""
    lanes = context["LANES_BY_POOL"][pool_name]
    num_lanes = len(lanes)
    num_times = len(context["TIME_SLOTS"])

    if appt:
        print(f"Appointment found: {appt}")

    fig, ax = plt.subplots(figsize=(14, 8))

    # Set to keep track of slots that should be colored blue
    blue_slots = set()

    # Determine the blue slots based on the appointment
    if appt:
        appt_lane = appt.get("lane")
        appt_time = datetime.datetime.strptime(appt.get("time"), "%I:%M %p").time()
        appt_duration = appt.get("duration")
        for j, time in enumerate(context["TIME_SLOTS"]):
            slot_time = datetime.datetime.strptime(time, "%I:%M %p").time()
            if appt_time == slot_time:
                blue_slots.add((appt_lane, j))
                if appt_duration == 60 and j + 1 < num_times:
                    blue_slots.add((appt_lane, j + 1))

    # Draw the table cells
    for i, lane in enumerate(reversed(lanes)):  # Reverse for top-down display
        for j, time in enumerate(context["TIME_SLOTS"]):
            is_available = lane in availability.get(time, [])
            color = "green" if is_available else "red"

            # Check if this cell should be colored blue
            if (lane, j) in blue_slots:
                color = "blue"

            rect = plt.Rectangle((j, i), 1, 1, facecolor=color, edgecolor="black")
            ax.add_patch(rect)
            ax.text(j + 0.5, i + 0.5, lane.split()[-1], ha="center", va="center", fontsize=9, color="white")

    # ✅ Keep Grid Aligned (Prevent Shifting)
    ax.set_xlim(0, num_times)
    ax.set_ylim(0, num_lanes)

    # ✅ Standard Tick Labels
    ax.set_xticks(range(num_times))
    ax.set_xticklabels(context["TIME_SLOTS"], fontsize=8, rotation=45, ha="center")

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

def combine_visualizations(img1, img2):
    """
    Combine two images vertically and return the combined image as a BytesIO object.

    Args:
        img1 (BytesIO): The first image (top).
        img2 (BytesIO): The second image (bottom).

    Returns:
        BytesIO: The combined image.
    """
    # Read the images from BytesIO
    img1_fig = mpimg.imread(BytesIO(img1.getvalue()))
    img2_fig = mpimg.imread(BytesIO(img2.getvalue()))

    # Determine the height and width of the combined image
    img1_height, img1_width, _ = img1_fig.shape
    img2_height, img2_width, _ = img2_fig.shape

    # Ensure both images have the same width by padding if necessary
    max_width = max(img1_width, img2_width)
    if img1_width < max_width:
        padding = ((0, 0), (0, max_width - img1_width), (0, 0))
        img1_fig = np.pad(img1_fig, padding, mode='constant', constant_values=255)
    if img2_width < max_width:
        padding = ((0, 0), (0, max_width - img2_width), (0, 0))
        img2_fig = np.pad(img2_fig, padding, mode='constant', constant_values=255)

    # Create a new figure to combine the images
    combined_height = img1_height + img2_height
    combined_fig, ax = plt.subplots(figsize=(max_width / 100, combined_height / 100), dpi=100)

    # Display the images in the correct positions
    ax.imshow(np.vstack((img1_fig, img2_fig)))
    ax.axis("off")

    # Save the combined image to a BytesIO object
    combined_img_io = BytesIO()
    plt.savefig(combined_img_io, format="png", bbox_inches="tight", pad_inches=0)
    combined_img_io.seek(0)

    # Close the figure to free memory
    plt.close(combined_fig)

    return combined_img_io
