#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import path
import os

# Add the parent directory of the src to sys.path
path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import numpy as np
import matplotlib.pyplot as plt
from fastdtw import fastdtw

from lib.params import DATA
from lib.params import SENSOR_CONFIGS,SENSOR_DEF

data_file = "stub_3s_20250904_145115_raw.json"
file_path = os.path.join(DATA, 'json', 'raw', data_file)

raw_flag = False

# Load data from the JSON file
with open(file_path, 'r') as f:
    data = json.load(f)

# Function to clean phases and fix phase shifts
def clean_phases(phase_list):
    cleaned = []
    for phase in phase_list:
        if phase > 270:
            cleaned.append(abs(phase - 360))
        elif phase > 135:
            cleaned.append(abs(phase - 180))
        else:
            cleaned.append(abs(phase))
    return np.array(cleaned)

# Function to calculate DTW alignment between two sequences
def dynamic_time_warp(signal1, signal2):
    _, path = fastdtw(signal1, signal2)
    aligned_signal1 = [signal1[i] for i, j in path]
    aligned_signal2 = [signal2[j] for i, j in path]
    return np.array(aligned_signal1), np.array(aligned_signal2)

# Extract phases and channels for both RFID tags
tag_1 = data[SENSOR_CONFIGS[SENSOR_DEF]['epc'][0]]
tag_2 = data[SENSOR_CONFIGS[SENSOR_DEF]['epc'][1]]

l1 = len(tag_1["phases"])
l2 = len(tag_2["phases"])

# Set time start and end for truncating experiment graph for better clarity
t_start, t_end = 35,45
# Set the total time of the experiment
t_total = 60

start_1 = int(( t_start / t_total) * l1)
end_1 = int(( t_end / t_total) * l1)

start_2 = int(( t_start / t_total) * l2)
end_2 = int(( t_end / t_total) * l2)

# Truncated tag 1 and tag 2 data
trunc = False
if trunc:
    tag_1_data = {
        "phases": tag_1["phases"][start_1:end_1],
        "channels": tag_1["channels"][start_1:end_1]
    }
    tag_2_data = {
        "phases": tag_2["phases"][start_2:end_2],
        "channels": tag_2["channels"][start_2:end_2]
    }
else:
    tag_1_data = {
        "phases": tag_1["phases"],
        "channels": tag_1["channels"]
    }
    tag_2_data = {
        "phases": tag_2["phases"],
        "channels": tag_2["channels"]
    }

plt.figure(1)
plt.plot(tag_1_data["phases"], color='red', label="RFID 1")
plt.plot(tag_2_data["phases"], color='blue', label="RFID 2")
plt.title("Raw phases")

# Store phases by channel for both tags
tag_1_phases_by_channel = {}
tag_2_phases_by_channel = {}

for i, channel in enumerate(tag_1_data["channels"]):
    if channel not in tag_1_phases_by_channel:
        tag_1_phases_by_channel[channel] = []
    tag_1_phases_by_channel[channel].append(tag_1_data["phases"][i])

for i, channel in enumerate(tag_2_data["channels"]):
    if channel not in tag_2_phases_by_channel:
        tag_2_phases_by_channel[channel] = []
    tag_2_phases_by_channel[channel].append(tag_2_data["phases"][i])

# Find common channels between the two tags
common_channels = set(tag_1_phases_by_channel.keys()) & set(tag_2_phases_by_channel.keys())

# Plotting the phase data and phase differences
phase_diffs = []
colors = ['red', 'blue', 'green', 'magenta', 'cyan', 'black']

for idx, channel in enumerate(common_channels):
    phase_1 = np.array(tag_1_phases_by_channel[channel])
    phase_2 = np.array(tag_2_phases_by_channel[channel])

    if raw_flag:
        # Plot raw cleaned phases if raw_flag is True
        aligned_phase_1 = phase_1
        aligned_phase_2 = phase_2
    else:
        # DTW alignment for processed phases
        aligned_phase_1, aligned_phase_2 = dynamic_time_warp(phase_1, phase_2)

    # Find the minimum length of the two arrays
    min_length = min(len(aligned_phase_1), len(aligned_phase_2))

    # Truncate both arrays to the same length
    aligned_phase_1 = aligned_phase_1[:min_length]
    aligned_phase_2 = aligned_phase_2[:min_length]

    # Calculate phase difference
    phase_diff = np.abs(aligned_phase_1 - aligned_phase_2)
    phase_diff = clean_phases(phase_diff)

    # Plot phase data for each channel
    plt.figure(2)
    plt.subplot(5, 10, idx + 1)
    plt.plot(aligned_phase_1, color='red', label="RFID 1")
    plt.plot(aligned_phase_2, color='blue', label="RFID 2")
    plt.title(f"Channel {channel}")
    
    # Plot phase differences
    plt.figure(3)
    plt.subplot(5, 10, idx + 1)
    plt.plot(phase_diff, color='green', label="Phase Diff")
    plt.title(f"Channel {channel}")
    
    phase_diffs.append(np.mean(phase_diff))

# Calculate the overall average phase difference across all channels
overall_avg_phase_diff = np.mean(phase_diffs)
print(f"Overall Average Phase Difference: {overall_avg_phase_diff:.2f} degrees")

# Show plots
plt.tight_layout()
plt.subplots_adjust(hspace=0.5, wspace=0.5)  # Additional padding between subplots
plt.show()

