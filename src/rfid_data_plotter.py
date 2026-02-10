#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import path,argv
from pathlib import Path
import os

# Add the parent directory of the src to sys.path
path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import math
import numpy as np
import matplotlib.pyplot as plt
from fastdtw import fastdtw
from traceback import format_exc

from lib.params import DATA
from lib.params import SENSOR_CONFIGS,SENSOR_DEF
from lib.params import read_rate


def clean_phases(phase_list):
    """Cleans phase data by normalizing it to a 0-180 degree range."""
    cleaned = np.array(phase_list)
    mask_gt_270 = cleaned > 270
    mask_gt_135 = (cleaned > 135) & (cleaned <= 270)
    
    cleaned[mask_gt_270] = np.abs(cleaned[mask_gt_270] - 360)
    cleaned[mask_gt_135] = np.abs(cleaned[mask_gt_135] - 180)
    cleaned[~(mask_gt_270 | mask_gt_135)] = np.abs(cleaned[~(mask_gt_270 | mask_gt_135)])
    
    return cleaned

def dynamic_time_warp(signal1, signal2):
    """Aligns two signals using Dynamic Time Warping."""
    distance, path = fastdtw(signal1, signal2)
    aligned_signal1 = np.array([signal1[i] for i, j in path])
    aligned_signal2 = np.array([signal2[j] for i, j in path])
    return aligned_signal1, aligned_signal2

def analyze_channelwise_phases(data, epc_list, processing_method='dtw', start=0.0, end=1.0):
    """
    Analyzes and plots RFID phase data for two tags, comparing their phases
    across common frequency channels. The plot legends dynamically use the last
    4 characters of the EPCs.

    Args:
        data (dict): A dictionary where keys are RFID EPCs and values are dicts
                     containing 'phases' and 'channels' lists.
        epc_list (list): A list containing two EPC strings for the tags to be compared.
        processing_method (str, optional): The method for processing phase data.
                                           Can be 'dtw' for Dynamic Time Warping
                                           alignment or 'raw' for direct comparison.
                                           Defaults to 'dtw'.
        start (float, optional): The starting point for the data slice as a fraction
                                 of the total length (e.g., 0.2 for 20%). Defaults to 0.0.
        end (float, optional): The ending point for the data slice as a fraction
                               of the total length (e.g., 0.5 for 50%). Defaults to 1.0.
    """
    
    # --- 1. Input Validation ---
    if not (0.0 <= start < 1.0 and 0.0 < end <= 1.0 and start < end):
        raise ValueError("Start and end must be fractions between 0.0 and 1.0, with start < end.")
    if len(epc_list) != 2:
        raise ValueError("epc_list must contain exactly two EPCs.")
    if epc_list[0] not in data or epc_list[1] not in data:
        raise ValueError("One or both EPCs were not found in the data dictionary.")
    if processing_method not in ['raw', 'dtw']:
        raise ValueError("processing_method must be either 'raw' or 'dtw'.")

    # --- 2. Data Extraction and Slicing ---
    tag_1_full = data[epc_list[0]]
    tag_2_full = data[epc_list[1]]
    
    # Create dynamic labels from EPCs
    label1 = f"Tag: {epc_list[0][-3:]}"
    label2 = f"Tag: {epc_list[1][-3:]}"

    len1, len2 = len(tag_1_full["phases"]), len(tag_2_full["phases"])
    start_idx1, end_idx1 = int(start * len1), int(end * len1)
    start_idx2, end_idx2 = int(start * len2), int(end * len2)

    tag_1_data = {
        "phases": tag_1_full["phases"][start_idx1:end_idx1],
        "channels": tag_1_full["channels"][start_idx1:end_idx1]
    }
    tag_2_data = {
        "phases": tag_2_full["phases"][start_idx2:end_idx2],
        "channels": tag_2_full["channels"][start_idx2:end_idx2]
    }

    # --- 3. Segregate Phases and Find Common Channels ---
    tag_1_phases_by_channel = {}
    tag_2_phases_by_channel = {}

    for i, channel in enumerate(tag_1_data["channels"]):
        tag_1_phases_by_channel.setdefault(channel, []).append(tag_1_data["phases"][i])

    for i, channel in enumerate(tag_2_data["channels"]):
        tag_2_phases_by_channel.setdefault(channel, []).append(tag_2_data["phases"][i])

    common_channels = sorted(list(set(tag_1_phases_by_channel.keys()) & set(tag_2_phases_by_channel.keys())))
    if not common_channels:
        print("No common channels found in the provided data slice.")
        return 0

    # --- 4. Dynamic Plot Layout ---
    n_channels = len(common_channels)
    cols = int(math.ceil(math.sqrt(n_channels)))
    rows = int(math.ceil(n_channels / cols)) if cols > 0 else 0

    if n_channels == 0:
        return 0

    # --- 5. Plotting ---
    fig_phases, axes_phases = plt.subplots(rows, cols, figsize=(cols * 4.5, rows * 3.5), squeeze=False)
    fig_diff, axes_diff = plt.subplots(rows, cols, figsize=(cols * 4.5, rows * 3.5), squeeze=False)

    fig_phases.suptitle(f'Phase Comparison ({processing_method.upper()})', fontsize=16)
    fig_diff.suptitle('Phase Difference', fontsize=16)

    phase_diffs_means = []
    
    axes_phases_flat = axes_phases.flatten()
    axes_diff_flat = axes_diff.flatten()

    for idx, channel in enumerate(common_channels):
        phase_1 = np.array(tag_1_phases_by_channel[channel])
        phase_2 = np.array(tag_2_phases_by_channel[channel])

        if processing_method == 'dtw':
            if len(phase_1) > 0 and len(phase_2) > 0:
                aligned_phase_1, aligned_phase_2 = dynamic_time_warp(phase_1, phase_2)
            else:
                continue
        else: # 'raw'
            min_length = min(len(phase_1), len(phase_2))
            if min_length == 0:
                continue
            aligned_phase_1 = phase_1[:min_length]
            aligned_phase_2 = phase_2[:min_length]

        phase_diff = clean_phases(np.abs(aligned_phase_1 - aligned_phase_2))
        if len(phase_diff) > 0:
            phase_diffs_means.append(np.mean(phase_diff))

        # Plot with dynamic labels
        axes_phases_flat[idx].plot(aligned_phase_1, 'b-', label=label1)
        axes_phases_flat[idx].plot(aligned_phase_2, 'r-', label=label2)
        axes_phases_flat[idx].set_title(f"Channel {channel}")
        axes_phases_flat[idx].legend()
        axes_phases_flat[idx].grid(True)

        axes_diff_flat[idx].plot(phase_diff, color='green', label="Phase Diff")
        axes_diff_flat[idx].set_title(f"Channel {channel}")
        axes_diff_flat[idx].set_ylim(0, 1.1 * max(phase_diff) if len(phase_diff) > 0 else 1)
        axes_diff_flat[idx].legend()
        axes_diff_flat[idx].grid(True)

    for i in range(n_channels, len(axes_phases_flat)):
        axes_phases_flat[i].set_visible(False)
        axes_diff_flat[i].set_visible(False)

    overall_avg_phase_diff = np.mean(phase_diffs_means) if phase_diffs_means else 0
    print(f"Overall Average Phase Difference: {overall_avg_phase_diff:.2f} degrees")

    fig_phases.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig_diff.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    plt.show()

    return overall_avg_phase_diff

def plot_moving_average_dtw_phase_difference(
    data,
    epc_list,
    window_duration_s=1.0,
    window_stride_s=0.05,
    enable_dtw=True
):
    """
    Calculates the moving average phase difference using a time-based sliding window,
    correctly handling variable and different sampling rates.

    Args:
        data (dict): A dictionary containing RFID tag data, grouped by EPC.
        epc_list (list): A list of exactly two RFID EPC codes.
        window_duration_s (float): The duration in seconds for the analysis window.
        window_stride_s (float): The time step in seconds to slide the window forward.
        enable_dtw (bool, optional): If True, applies DTW matching. Defaults to True.

    Returns:
        tuple: (list of moving average phase differences, list of corresponding timestamps in seconds).

    Raises:
        ValueError: For invalid input parameters.
    """
    if len(epc_list) != 2:
        raise ValueError("`epc_list` must contain exactly two RFID EPC codes.")
    tag1_id, tag2_id = epc_list[0], epc_list[1]
    if tag1_id not in data or tag2_id not in data:
        raise ValueError(f"One or both EPCs ({tag1_id}, {tag2_id}) not found in `data`.")
    if window_duration_s <= 0 or window_stride_s <= 0:
        raise ValueError("`window_duration_s` and `window_stride_s` must be positive floats.")

    tag1_ts = np.asarray(data[tag1_id]["timestamps"])
    tag1_ph = np.asarray(data[tag1_id]["phases"])
    tag1_ch = np.asarray(data[tag1_id]["channels"])

    tag2_ts = np.asarray(data[tag2_id]["timestamps"])
    tag2_ph = np.asarray(data[tag2_id]["phases"])
    tag2_ch = np.asarray(data[tag2_id]["channels"])

    if len(tag1_ts) == 0 or len(tag2_ts) == 0:
        return [], []

    # Determine the overlapping time range for both tags
    start_time_ms = max(tag1_ts[0], tag2_ts[0])
    end_time_ms = min(tag1_ts[-1], tag2_ts[-1])

    if start_time_ms >= end_time_ms:
        return [], []

    moving_avg_phase_diffs = []
    corresponding_timestamps_s = []

    window_duration_ms = window_duration_s * 1000
    window_stride_ms = window_stride_s * 1000

    current_window_start_ms = start_time_ms
    while current_window_start_ms + window_duration_ms <= end_time_ms:
        current_window_end_ms = current_window_start_ms + window_duration_ms

        # Filter data for each tag within the current time window
        idx1 = np.where((tag1_ts >= current_window_start_ms) & (tag1_ts < current_window_end_ms))[0]
        idx2 = np.where((tag2_ts >= current_window_start_ms) & (tag2_ts < current_window_end_ms))[0]

        if len(idx1) == 0 or len(idx2) == 0:
            # If one tag has no data in this window, we can't calculate a difference.
            # We slide to the next window.
            current_window_start_ms += window_stride_ms
            continue

        win_tag1_ph, win_tag1_ch = tag1_ph[idx1], tag1_ch[idx1]
        win_tag2_ph, win_tag2_ch = tag2_ph[idx2], tag2_ch[idx2]

        # Group phases by channel within the window
        tag1_phases_by_ch = {ch: win_tag1_ph[win_tag1_ch == ch] for ch in np.unique(win_tag1_ch)}
        tag2_phases_by_ch = {ch: win_tag2_ph[win_tag2_ch == ch] for ch in np.unique(win_tag2_ch)}

        common_channels = set(tag1_phases_by_ch.keys()) & set(tag2_phases_by_ch.keys())
        window_channel_avg_diffs = []

        if common_channels:
            for channel in common_channels:
                phase_seq1 = tag1_phases_by_ch[channel]
                phase_seq2 = tag2_phases_by_ch[channel]

                if enable_dtw:
                    aligned_phase_1, aligned_phase_2 = dynamic_time_warp(phase_seq1, phase_seq2)
                else:
                    min_len = min(len(phase_seq1), len(phase_seq2))
                    aligned_phase_1, aligned_phase_2 = phase_seq1[:min_len], phase_seq2[:min_len]

                if len(aligned_phase_1) > 0:
                    diffs = np.abs(aligned_phase_1 - aligned_phase_2)
                    cleaned_diffs = clean_phases(diffs)
                    window_channel_avg_diffs.append(np.mean(cleaned_diffs))

        # Calculate the average for the current window and store it
        overall_avg_for_window = np.mean(window_channel_avg_diffs) if window_channel_avg_diffs else 0.0
        moving_avg_phase_diffs.append(phase_normalization(overall_avg_for_window))
        corresponding_timestamps_s.append(current_window_end_ms / 1000.0)

        current_window_start_ms += window_stride_ms

    if enable_dtw:
        method = "DTW"
    else:   method = "Time"

    print(f"Generated {len(moving_avg_phase_diffs)} data points for the moving average.")
    if moving_avg_phase_diffs:
        plt.figure(figsize=(12, 6))
        plt.plot(corresponding_timestamps_s, moving_avg_phase_diffs, 'g-', label=f'{method}-Based MA ({window_duration_s}s window, {window_stride_s}s stride)', markersize=4)
        plt.title(f'{method}-Based Moving Average Phase Difference', fontweight='bold')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Avg Phase Difference (degrees)')
        plt.grid(True)
        plt.legend()
        plt.ylim(bottom=0)
        plt.show()

def unwrap_phase(phases):
    """
    Unwraps a sequence of phase values (in degrees) to make it continuous.
    
    Args:
        phases (np.ndarray): An array of phase values, typically 0-360.
        
    Returns:
        np.ndarray: The unwrapped, continuous phase sequence.
    """
    if len(phases) == 0:
        return np.array([])
    
    unwrapped = np.copy(phases).astype(float) # Ensure float type for calculations
    cumulative_correction = 0.0

    for i in range(1, len(unwrapped)):
        # Calculate the difference between the current original wrapped phase
        # and the previous original wrapped phase.
        # This determines if a wrap occurred between *original* samples.
        diff = phases[i] - phases[i-1] 

        # If difference indicates a phase wrap (jump > 180 or < -180)
        # We need to adjust the cumulative_correction for all subsequent points.
        if diff > 180:  # A jump down (e.g., from ~350 to ~10 degrees)
            cumulative_correction -= 360.0
        elif diff < -180: # A jump up (e.g., from ~10 to ~350 degrees)
            cumulative_correction += 360.0
        
        # Apply the cumulative_correction to the current original phase value
        unwrapped[i] = phases[i] + cumulative_correction
        
    return unwrapped


def phase_normalization(phi_deg):
    """
    Normalizes and folds a given phase value into the [0, 90] degree range.

    This function first wraps the input phase to the [0, 180) interval,
    then folds it around 90 degrees to find the closest magnitude
    representation within [0, 90]. Useful for scenarios where phase
    differences of (e.g., 20 deg) and (160 deg) are considered equivalent
    in terms of absolute deviation from 0/180 boundaries.

    Args:
        phi_deg (float or int): The input phase value in degrees.

    Returns:
        float: The folded phase value, guaranteed to be in the range [0, 90] degrees.
    """
    phi_norm = phi_deg % 180
    return min(phi_norm, 180 - phi_norm)

def plot_interpolated_moving_average_phase_difference(
                                                    data,
                                                    epc_list,
                                                    window_duration_s=1.0,
                                                    window_stride_s=0.05,
                                                    expected=None,
                                                    stats=True
                                                ):
    """
    Calculates the moving average phase difference using a time-based sliding window
    with phase unwrapping and linear interpolation for robust, accurate results.

    Args:
        data (dict): A dictionary containing RFID tag data, grouped by EPC.
        epc_list (list): A list of exactly two RFID EPC codes.
        window_duration_s (float): The duration in seconds for the analysis window.
        window_stride_s (float): The time step in seconds to slide the window forward.

    Returns:
        tuple: (list of moving average phase differences, list of corresponding timestamps).
    """
    if len(epc_list) != 2:
        raise ValueError("`epc_list` must contain exactly two RFID EPC codes.")
    tag1_id, tag2_id = epc_list[0], epc_list[1]
    if tag1_id not in data or tag2_id not in data:
        raise ValueError(f"One or both EPCs ({tag1_id}, {tag2_id}) not found in `data`.")
    if window_duration_s <= 0 or window_stride_s <= 0:
        raise ValueError("`window_duration_s` and `window_stride_s` must be positive.")

    tag1_ts = np.asarray(data[tag1_id]["timestamps"])
    tag1_ph = np.asarray(data[tag1_id]["phases"])
    tag1_ch = np.asarray(data[tag1_id]["channels"])

    tag2_ts = np.asarray(data[tag2_id]["timestamps"])
    tag2_ph = np.asarray(data[tag2_id]["phases"])
    tag2_ch = np.asarray(data[tag2_id]["channels"])

    if len(tag1_ts) < 2 or len(tag2_ts) < 2:
        print("Not enough data for interpolation (each tag needs at least 2 points).")
        return [], []

    start_time_ms = max(tag1_ts[0], tag2_ts[0])
    end_time_ms = min(tag1_ts[-1], tag2_ts[-1])
    if start_time_ms >= end_time_ms:
        return [], []

    moving_avg_phase_diffs = []
    corresponding_timestamps_s = []

    window_duration_ms = window_duration_s * 1000
    window_stride_ms = window_stride_s * 1000
    current_window_start_ms = start_time_ms

    while current_window_start_ms + window_duration_ms <= end_time_ms:
        current_window_end_ms = current_window_start_ms + window_duration_ms
        
        idx1 = np.where((tag1_ts >= current_window_start_ms) & (tag1_ts < current_window_end_ms))[0]
        idx2 = np.where((tag2_ts >= current_window_start_ms) & (tag2_ts < current_window_end_ms))[0]

        if len(idx1) < 2 or len(idx2) < 2:
            current_window_start_ms += window_stride_ms
            continue

        win_tag1_ts, win_tag1_ph, win_tag1_ch = tag1_ts[idx1], tag1_ph[idx1], tag1_ch[idx1]
        win_tag2_ts, win_tag2_ph, win_tag2_ch = tag2_ts[idx2], tag2_ph[idx2], tag2_ch[idx2]

        tag1_phases_by_ch = {ch: (win_tag1_ts[win_tag1_ch == ch], win_tag1_ph[win_tag1_ch == ch]) for ch in np.unique(win_tag1_ch)}
        tag2_phases_by_ch = {ch: (win_tag2_ts[win_tag2_ch == ch], win_tag2_ph[win_tag2_ch == ch]) for ch in np.unique(win_tag2_ch)}

        common_channels = set(tag1_phases_by_ch.keys()) & set(tag2_phases_by_ch.keys())
        window_all_diffs = []

        if common_channels:
            for channel in common_channels:
                ts1_ch, ph1_ch = tag1_phases_by_ch[channel]
                ts2_ch, ph2_ch = tag2_phases_by_ch[channel]

                # Need at least 2 points on this channel for each tag to interpolate
                if len(ts1_ch) < 2 or len(ts2_ch) < 2:
                    continue

                # --- Core Logic: Unwrap and Interpolate ---
                unwrapped_ph1 = unwrap_phase(ph1_ch)
                unwrapped_ph2 = unwrap_phase(ph2_ch)

                # Interpolate Tag 2's phase at the timestamps of Tag 1
                # np.interp(x, xp, fp) -> x=new_x, xp=old_x, fp=old_y
                interp_ph2 = np.interp(ts1_ch, ts2_ch, unwrapped_ph2)

                # Calculate the difference
                diffs = unwrapped_ph1 - interp_ph2
                window_all_diffs.extend(diffs)

        if window_all_diffs:
            overall_avg_for_window = np.mean(window_all_diffs)
            moving_avg_phase_diffs.append(phase_normalization(overall_avg_for_window))
            corresponding_timestamps_s.append(current_window_end_ms / 1000.0)

        current_window_start_ms += window_stride_ms

    print(f"Generated {len(moving_avg_phase_diffs)} data points for the interpolated moving average.")
    if stats:
        if moving_avg_phase_diffs:
            print(f"Standard Deviation: {np.std(moving_avg_phase_diffs)}")
            print(f"Min/Max: {np.min(moving_avg_phase_diffs)}/{np.max(moving_avg_phase_diffs)}")
            print(f"Mean: {np.mean(moving_avg_phase_diffs)}")
            print(f"Median: {np.median(moving_avg_phase_diffs)}")
            if expected:
                expected = 20
                errors = np.array(moving_avg_phase_diffs) - expected
                rmse = np.sqrt(np.mean(errors**2))
                mean_actual = np.mean(moving_avg_phase_diffs)
                ss_tot = np.sum((np.array(moving_avg_phase_diffs) - mean_actual)**2)
                ss_res = np.sum(errors**2)
                r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                print(f"RMSE (expected {expected}): {rmse:.2f}")
                print(f"R^2 (expected {expected}): {r2:.4f}")


    if moving_avg_phase_diffs:
        plt.figure(figsize=(18, 6)) # Wider figure
        plt.plot(corresponding_timestamps_s, moving_avg_phase_diffs, 'g-', label=f'Interpolation-Based MA ({window_duration_s}s window, {window_stride_s}s stride)', markersize=3)
        plt.title('Interpolation-Based Moving Average Phase Difference', fontweight='bold')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Avg Phase Difference (degrees)')
        plt.grid(True)
        plt.legend()
        
        # **MODIFICATION 2: Dynamically clamp y-axis to handle spikes**
        diffs_array = np.array(moving_avg_phase_diffs)
        # Calculate a high percentile (e.g., 95th) to find the "normal" data range
        p90 = np.percentile(diffs_array, 90)
        # Set the upper limit slightly above this percentile for good visualization
        ylim_top = p90 * 1.2
        
        # Ensure the bottom limit is 0 and the top limit is reasonable
        ylim_bottom = 0
        if ylim_top < 10: # If data is very stable, give it a bit of room
            ylim_top = 10
            
        print(f"Clamping plot y-axis to ({ylim_bottom}, {ylim_top:.2f}) to improve readability.")
        plt.ylim(ylim_bottom, ylim_top)

        plt.show()
    
    return moving_avg_phase_diffs, corresponding_timestamps_s

def plot_interpolated_moving_average_rssi_difference(
                                                    data,
                                                    epc_list,
                                                    window_duration_s=1.0,
                                                    window_stride_s=0.05
                                                ):
    """
    Calculates the moving average RSSI difference using a time-based sliding window
    with linear interpolation for robust, accurate results. 
    Matches the structure of the phase-based version.

    Args:
        data (dict): A dictionary containing RFID tag data, grouped by EPC.
        epc_list (list): A list of exactly two RFID EPC codes.
        window_duration_s (float): The duration in seconds for the analysis window.
        window_stride_s (float): The time step in seconds to slide the window forward.

    Returns:
        tuple: (list of moving average RSSI differences, list of corresponding timestamps).
    """
    if len(epc_list) != 2:
        raise ValueError("`epc_list` must contain exactly two RFID EPC codes.")
    tag1_id, tag2_id = epc_list[0], epc_list[1]
    if tag1_id not in data or tag2_id not in data:
        raise ValueError(f"One or both EPCs ({tag1_id}, {tag2_id}) not found in `data`.")
    if window_duration_s <= 0 or window_stride_s <= 0:
        raise ValueError("`window_duration_s` and `window_stride_s` must be positive.")

    tag1_ts = np.asarray(data[tag1_id]["timestamps"])
    tag1_rs = np.asarray(data[tag1_id]["rssis"])
    tag1_ch = np.asarray(data[tag1_id]["channels"])

    tag2_ts = np.asarray(data[tag2_id]["timestamps"])
    tag2_rs = np.asarray(data[tag2_id]["rssis"])
    tag2_ch = np.asarray(data[tag2_id]["channels"])

    if len(tag1_ts) < 2 or len(tag2_ts) < 2:
        print("Not enough data for interpolation (each tag needs at least 2 points).")
        return [], []

    start_time_ms = max(tag1_ts[0], tag2_ts[0])
    end_time_ms = min(tag1_ts[-1], tag2_ts[-1])
    if start_time_ms >= end_time_ms:
        return [], []

    moving_avg_rssi_diffs = []
    corresponding_timestamps_s = []

    window_duration_ms = window_duration_s * 1000
    window_stride_ms = window_stride_s * 1000
    current_window_start_ms = start_time_ms

    while current_window_start_ms + window_duration_ms <= end_time_ms:
        current_window_end_ms = current_window_start_ms + window_duration_ms
        
        idx1 = np.where((tag1_ts >= current_window_start_ms) & (tag1_ts < current_window_end_ms))[0]
        idx2 = np.where((tag2_ts >= current_window_start_ms) & (tag2_ts < current_window_end_ms))[0]

        if len(idx1) < 2 or len(idx2) < 2:
            current_window_start_ms += window_stride_ms
            continue

        win_tag1_ts, win_tag1_rs, win_tag1_ch = tag1_ts[idx1], tag1_rs[idx1], tag1_ch[idx1]
        win_tag2_ts, win_tag2_rs, win_tag2_ch = tag2_ts[idx2], tag2_rs[idx2], tag2_ch[idx2]

        tag1_rssi_by_ch = {ch: (win_tag1_ts[win_tag1_ch == ch], win_tag1_rs[win_tag1_ch == ch]) for ch in np.unique(win_tag1_ch)}
        tag2_rssi_by_ch = {ch: (win_tag2_ts[win_tag2_ch == ch], win_tag2_rs[win_tag2_ch == ch]) for ch in np.unique(win_tag2_ch)}

        common_channels = set(tag1_rssi_by_ch.keys()) & set(tag2_rssi_by_ch.keys())
        window_all_diffs = []

        if common_channels:
            for channel in common_channels:
                ts1_ch, rs1_ch = tag1_rssi_by_ch[channel]
                ts2_ch, rs2_ch = tag2_rssi_by_ch[channel]

                # Need at least 2 points on this channel for each tag to interpolate
                if len(ts1_ch) < 2 or len(ts2_ch) < 2:
                    continue

                # --- Core Logic: Interpolate RSSI ---
                # Interpolate Tag 2's RSSI at the timestamps of Tag 1
                interp_rs2 = np.interp(ts1_ch, ts2_ch, rs2_ch)

                # Calculate the difference (Differential RSSI)
                diffs = rs1_ch - interp_rs2
                window_all_diffs.extend(diffs)

        if window_all_diffs:
            overall_avg_for_window = np.mean(window_all_diffs)
            moving_avg_rssi_diffs.append(overall_avg_for_window)
            corresponding_timestamps_s.append(current_window_end_ms / 1000.0)

        current_window_start_ms += window_stride_ms

    print(f"Generated {len(moving_avg_rssi_diffs)} data points for the interpolated moving average RSSI.")
    if moving_avg_rssi_diffs:
        plt.figure(figsize=(18, 6))
        plt.plot(corresponding_timestamps_s, moving_avg_rssi_diffs, 'b-', label=f'Interpolation-Based RSSI MA ({window_duration_s}s window, {window_stride_s}s stride)', markersize=3)
        plt.title('Interpolation-Based Moving Average RSSI Difference', fontweight='bold')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Avg RSSI Difference (dBm)')
        plt.grid(True)
        plt.legend()
        
        # Dynamic clamping for RSSI
        diffs_array = np.array(moving_avg_rssi_diffs)
        p5 = np.percentile(diffs_array, 5)
        p95 = np.percentile(diffs_array, 95)
        plt.ylim(p5 - 2, p95 + 2)

        plt.show()
    
    return moving_avg_rssi_diffs, corresponding_timestamps_s

def plot_phase_comparison(data, epc_list):
    """
    Compare phases between two RFID tags
    """
    tag_1 = data[epc_list[0]]
    tag_2 = data[epc_list[1]]
    
    tag1_times = np.array(tag_1["timestamps"]) / 1000.0  # Convert to seconds
    tag1_phases = np.array(tag_1["phases"])
    
    tag2_times = np.array(tag_2["timestamps"]) / 1000.0
    tag2_phases = np.array(tag_2["phases"])
    
    # Get labels
    tag1_label = f"Tag {epc_list[0][-3:]}"
    tag2_label = f"Tag {epc_list[1][-3:]}"
    
    plt.figure(figsize=(14, 6))
    plt.plot(tag1_times, tag1_phases, 'b-', linewidth=1.5, alpha=0.8, label=tag1_label, marker='o', markersize=2)
    plt.plot(tag2_times, tag2_phases, 'r-', linewidth=1.5, alpha=0.8, label=tag2_label, marker='s', markersize=2)
    
    plt.title('Phase Comparison Between RFID Tags', fontweight='bold', fontsize=14)
    plt.xlabel('Time (seconds)')
    plt.ylabel('Phase (degrees)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

def plot_rssi_comparison(data, epc_list):
    """
    Compare RSSI between two RFID tags
    """
    tag_1 = data[epc_list[0]]
    tag_2 = data[epc_list[1]]
    
    tag1_times = np.array(tag_1["timestamps"]) / 1000.0  # Convert to seconds
    tag1_rssis = np.array(tag_1["rssis"])
    
    tag2_times = np.array(tag_2["timestamps"]) / 1000.0
    tag2_rssis = np.array(tag_2["rssis"])
    
    # Get labels
    tag1_label = f"Tag {epc_list[0][-3:]}"
    tag2_label = f"Tag {epc_list[1][-3:]}"
    
    plt.figure(figsize=(14, 6))
    plt.plot(tag1_times, tag1_rssis, 'b-', linewidth=1.5, alpha=0.8, label=tag1_label, marker='o', markersize=2)
    plt.plot(tag2_times, tag2_rssis, 'r-', linewidth=1.5, alpha=0.8, label=tag2_label, marker='s', markersize=2)
    
    plt.title('RSSI Comparison Between RFID Tags', fontweight='bold', fontsize=14)
    plt.xlabel('Time (seconds)')
    plt.ylabel('RSSI (dBm)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

def plot_channelwise_analysis(data, epc_list):
    """
    Show channel-wise phase and RSSI streams for both RFID tags
    """
    tag_1 = data[epc_list[0]]
    tag_2 = data[epc_list[1]]
    
    # Get labels
    tag1_label = f"Tag {epc_list[0][-3:]}"
    tag2_label = f"Tag {epc_list[1][-3:]}"
    
    # Get unique channels
    all_channels = set(tag_1["channels"] + tag_2["channels"])
    channels = sorted(list(all_channels))
    
    print(f"Found {len(channels)} unique channels: {channels}")
    
    # Group data by channels for both tags
    def group_by_channel(tag_data):
        channel_data = {}
        for i, channel in enumerate(tag_data["channels"]):
            if channel not in channel_data:
                channel_data[channel] = {
                    "timestamps": [],
                    "phases": [],
                    "rssis": []
                }
            channel_data[channel]["timestamps"].append(tag_data["timestamps"][i] / 1000.0)  # Convert to seconds
            channel_data[channel]["phases"].append(tag_data["phases"][i])
            channel_data[channel]["rssis"].append(tag_data["rssis"][i])
        return channel_data
    
    tag1_by_channel = group_by_channel(tag_1)
    tag2_by_channel = group_by_channel(tag_2)
    
    # Create subplots for each channel
    num_channels = len(channels)
    fig, axes = plt.subplots(2 * num_channels, 2, figsize=(16, 4 * num_channels))
    
    if num_channels == 1:
        axes = axes.reshape(2, 2)
    
    for idx, channel in enumerate(channels):
        # Phase plots for this channel
        row_phase = idx * 2
        row_rssi = idx * 2 + 1
        
        # Tag 1 phase for this channel
        if channel in tag1_by_channel:
            axes[row_phase, 0].plot(tag1_by_channel[channel]["timestamps"], 
                                   tag1_by_channel[channel]["phases"], 
                                   'b-', linewidth=1.5, alpha=0.8, marker='o', markersize=1)
        axes[row_phase, 0].set_title(f'{tag1_label} - Phase - Channel {channel} MHz', fontweight='bold')
        axes[row_phase, 0].set_ylabel('Phase (degrees)')
        axes[row_phase, 0].grid(True, alpha=0.3)
        
        # Tag 2 phase for this channel
        if channel in tag2_by_channel:
            axes[row_phase, 1].plot(tag2_by_channel[channel]["timestamps"], 
                                   tag2_by_channel[channel]["phases"], 
                                   'r-', linewidth=1.5, alpha=0.8, marker='s', markersize=1)
        axes[row_phase, 1].set_title(f'{tag2_label} - Phase - Channel {channel} MHz', fontweight='bold')
        axes[row_phase, 1].set_ylabel('Phase (degrees)')
        axes[row_phase, 1].grid(True, alpha=0.3)
        
        # Tag 1 RSSI for this channel
        if channel in tag1_by_channel:
            axes[row_rssi, 0].plot(tag1_by_channel[channel]["timestamps"], 
                                  tag1_by_channel[channel]["rssis"], 
                                  'b-', linewidth=1.5, alpha=0.8, marker='o', markersize=1)
        axes[row_rssi, 0].set_title(f'{tag1_label} - RSSI - Channel {channel} MHz', fontweight='bold')
        axes[row_rssi, 0].set_xlabel('Time (seconds)')
        axes[row_rssi, 0].set_ylabel('RSSI (dBm)')
        axes[row_rssi, 0].grid(True, alpha=0.3)
        
        # Tag 2 RSSI for this channel
        if channel in tag2_by_channel:
            axes[row_rssi, 1].plot(tag2_by_channel[channel]["timestamps"], 
                                  tag2_by_channel[channel]["rssis"], 
                                  'r-', linewidth=1.5, alpha=0.8, marker='s', markersize=1)
        axes[row_rssi, 1].set_title(f'{tag2_label} - RSSI - Channel {channel} MHz', fontweight='bold')
        axes[row_rssi, 1].set_xlabel('Time (seconds)')
        axes[row_rssi, 1].set_ylabel('RSSI (dBm)')
        axes[row_rssi, 1].grid(True, alpha=0.3)
    
    plt.suptitle('Channel-wise Analysis for Both RFID Tags', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.show()

def plot_combined_analysis(data, epc_list):
    """
    Combined view of all measurements
    """
    tag_1 = data[epc_list[0]]
    tag_2 = data[epc_list[1]]
    
    tag1_times = np.array(tag_1["timestamps"]) / 1000.0
    tag1_phases = np.array(tag_1["phases"])
    tag1_rssis = np.array(tag_1["rssis"])
    
    tag2_times = np.array(tag_2["timestamps"]) / 1000.0
    tag2_phases = np.array(tag_2["phases"])
    tag2_rssis = np.array(tag_2["rssis"])
    
    # Get labels
    tag1_label = f"Tag {epc_list[0][-3:]}"
    tag2_label = f"Tag {epc_list[1][-3:]}"
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))
    
    # Combined phase comparison
    ax1.plot(tag1_times, tag1_phases, 'b-', linewidth=1.5, alpha=0.8, label=tag1_label, marker='o', markersize=1)
    ax1.plot(tag2_times, tag2_phases, 'r-', linewidth=1.5, alpha=0.8, label=tag2_label, marker='s', markersize=1)
    ax1.set_title('Phase Comparison Between RFID Tags', fontweight='bold', fontsize=14)
    ax1.set_ylabel('Phase (degrees)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Combined RSSI comparison
    ax2.plot(tag1_times, tag1_rssis, 'b-', linewidth=1.5, alpha=0.8, label=tag1_label, marker='o', markersize=1)
    ax2.plot(tag2_times, tag2_rssis, 'r-', linewidth=1.5, alpha=0.8, label=tag2_label, marker='s', markersize=1)
    ax2.set_title('RSSI Comparison Between RFID Tags', fontweight='bold', fontsize=14)
    ax2.set_xlabel('Time (seconds)')
    ax2.set_ylabel('RSSI (dBm)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.suptitle('Combined RFID Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.show()
    
    # Print basic statistics
    print(f"\nBasic Statistics:")
    print(f"{tag1_label}: {len(tag1_times)} samples, Duration: {tag1_times[-1]:.1f}s")
    print(f"  Phase range: {tag1_phases.min():.1f}° to {tag1_phases.max():.1f}°")
    print(f"  RSSI average: {tag1_rssis.mean():.1f} dBm")
    
    print(f"{tag2_label}: {len(tag2_times)} samples, Duration: {tag2_times[-1]:.1f}s")
    print(f"  Phase range: {tag2_phases.min():.1f}° to {tag2_phases.max():.1f}°")
    print(f"  RSSI average: {tag2_rssis.mean():.1f} dBm")

def plot_realtime_phase_difference(data, experiment_duration=None):
    """
    Plot a simple line graph against time or index
    
    Args:
        data_list: List of data values to plot
        experiment_duration: Duration in seconds (X from filename), if None uses index
    """
    
    if not data:
        print("Error: Empty data list provided")
        return
    
    # Create X-axis
    if experiment_duration is not None:
        # Create time axis from 0 to experiment_duration with equal spacing
        x_axis = np.linspace(0, experiment_duration, len(data))
        x_label = f'Time (seconds)'
        title = f'Phase Difference vs Time'
    else:
        # Use index as X-axis
        x_axis = np.arange(len(data))
        x_label = 'Index'
        title = 'Phase Difference vs Index'
    
    # Create the plot
    plt.figure(figsize=(12, 6))
    plt.plot(x_axis, data, 'b-', linewidth=1.5, alpha=0.8, marker='o', markersize=2)
    
    plt.title(title, fontweight='bold', fontsize=14)
    plt.xlabel(x_label)
    plt.ylabel('Value')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
    
    # Print basic info
    print(f"Data points: {len(data)}")
    if experiment_duration is not None:
        print(f"Sampling rate: {len(data)/experiment_duration:.2f} Hz")
        print(f"Time per sample: {experiment_duration/len(data):.3f} seconds")

def subset_epc_data(data, start = 0, end = 1):
    """
    Subset EPC data dictionary between start and end (seconds or fractions).

    Args:
        data (dict): Dictionary of EPC data:
                     {
                       "epc1": {"rssis": [], "phases": [], "timestamps": [], "channels": []},
                       ...
                     }
        start (float): Start index (seconds or fraction of total duration).
        end (float): End index (seconds or fraction of total duration).

    Returns:
        dict: Subset of the original data with the same structure.
    """
    # Get overall duration from timestamps (assuming ms values)
    all_timestamps = []
    for epc in data.values():
        all_timestamps.extend(epc["timestamps"])
    if not all_timestamps:
        return {}

    min_ts = min(all_timestamps)
    max_ts = max(all_timestamps)
    duration_sec = (max_ts - min_ts) / 1000.0

    # Handle fractional indices
    if 0 <= start <= 1 and 0 <= end <= 1 and start <= end:
        start_time = min_ts + start * duration_sec * 1000
        end_time = min_ts + end * duration_sec * 1000
    else:
        start_time = min_ts + start * 1000
        end_time = min_ts + end * 1000

    # Build subset
    subset = {}
    for epc, values in data.items():
        ts = values["timestamps"]
        indices = [i for i, t in enumerate(ts) if start_time <= t <= end_time]

        subset[epc] = {
            "rssis":   [values["rssis"][i] for i in indices],
            "phases":  [values["phases"][i] for i in indices],
            "timestamps": [values["timestamps"][i] for i in indices],
            "channels":   [values["channels"][i] for i in indices]
        }

    return subset


def extract_experiment_duration(base_file_name):
    """
    Extract the time (X in seconds) from filenames of the form:
    "experiment_Xs_YYYYmmdd_HHmmss_phases.json".
    
    Args:
        base_file_name (str): The input filename.
    
    Returns:
        float or None: The extracted time in seconds, or None if not found.
    """
    tag_path = os.path.join(DATA, "json", "tags", base_file_name + "_seq" + ".json")

    with open(tag_path, 'r') as f:
        tag_data = json.load(f)
    
    try:
        return round(tag_data[-1]['timestamp'] / 1000, 3)
    except:
        return None


def plotter(base_file_name, epc_list=None, start_index=0, end_index=1):
    """
    Main function to load data file and create all visualizations
    
    Args:
        base_file_name: Base name of the json data files to be visualized
        epc_list: List of EPC IDs to analyze (if None, will use first 2 EPCs found)
    """
    
    try:

        data_file_path = os.path.join(DATA, "json")
        raw_path = os.path.join(data_file_path, "raw", base_file_name + "_raw" + ".json")
        phase_path = os.path.join(data_file_path, "phases", base_file_name + "_phases" + ".json")

        experiment_duration = extract_experiment_duration(base_file_name)

        # Load data from file
        with open(raw_path, 'r') as f:
            raw_data = json.load(f)

        # Load data from file
        with open(phase_path, 'r') as f:
            phase_data = json.load(f)
        
        # Validate EPCs exist in data
        try:
            for epc in epc_list:
                if epc not in raw_data:
                    raise ValueError(f"EPC '{epc}' not found in data")
        except:
            # If no EPC list provided, use first 2 EPCs found in data
            available_epcs = list(raw_data.keys())
            if len(available_epcs) < 2:
                raise ValueError("Data must contain at least 2 EPCs for analysis")
            epc_list = available_epcs[:2]
            print(f"No EPC list provided. Using first 2 EPCs found: {epc_list}")

        raw_data = subset_epc_data(raw_data, start_index, end_index)

        print(f"Starting analysis for {epc_list[0]} vs {epc_list[1]}")
        print("=" * 60)
        
        # Create all visualizations
        print("Creating phase difference plot...")
        plot_realtime_phase_difference(phase_data, experiment_duration)

        print("Creating combined analysis...")
        plot_combined_analysis(raw_data, epc_list)
        
        print("Creating phase comparison...")
        plot_phase_comparison(raw_data, epc_list)
        
        print("Creating RSSI comparison...")
        plot_rssi_comparison(raw_data, epc_list)
        
        # print("Creating channel-wise analysis...")
        # plot_channelwise_analysis(raw_data, epc_list)

        # print("Creating moving average phase difference analysis...")
        # plot_moving_average_dtw_phase_difference(raw_data, 
        #                                          epc_list, 
        #                                          window_duration_s=SENSOR_CONFIGS[SENSOR_DEF]['window'], 
        #                                          window_stride_s=(1.0 / read_rate * 10), 
        #                                          enable_dtw=True
        #                                          )
        
        print("Creating Interpolation-based moving average phase difference analysis...")
        plot_interpolated_moving_average_phase_difference(
                                            raw_data, 
                                            epc_list, 
                                            window_duration_s=SENSOR_CONFIGS[SENSOR_DEF]['window'], 
                                            window_stride_s=(1.0 / read_rate * 10)
        )


        print("Creating Interpolation-based moving average RSSI difference analysis...")
        plot_interpolated_moving_average_rssi_difference(
                                            raw_data, 
                                            epc_list, 
                                            window_duration_s=SENSOR_CONFIGS[SENSOR_DEF]['window'], 
                                            window_stride_s=(1.0 / read_rate * 10)
        )
        
        # TODO: Fix DTW channel-wise analysis - fails for plotting raw data with current implementation
        # print("Creating channel-wise DTW'ed phase difference analysis...")
        # analyze_channelwise_phases(raw_data, epc_list, processing_method='dtw')

        print("Analysis complete!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print(format_exc())

# **Main execution function**
if __name__ == "__main__":
    
    try:
        base_file_name = argv[1]
    except:
        dataDir = os.path.join(DATA, "json", "raw")
        files = list(Path(dataDir).glob("*_raw.json"))  # convert to list
        base_file_name = max(files, key=lambda f: f.stat().st_mtime).stem.replace("_raw", "")

        # base_file_name = "mob_c2a_10s_20250905_125331_raw"
        print(f"No filename provided. Using most recent file: {base_file_name}")

    try:
        start_index = float(argv[2])
    except:
        start_index = 0

    try:
        end_index = float(argv[3])
    except:
        end_index = 1

    # strip unwanted substrings if present - just for ease of use, not an actual requirement in code
    for suffix in ["_raw", "_phases", "_seq", ".json"]:
        base_file_name = base_file_name.replace(suffix, "")

    epc_list = SENSOR_CONFIGS[SENSOR_DEF]['epc']
    
    plotter(base_file_name, epc_list, start_index, end_index)
