#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from collections import defaultdict
from fastdtw import fastdtw
from lib.params import read_rate
from lib.common_functions import save_raw_data_to_json,save_raw_data_to_mat

import json
from lib.params import DATA

class TagData:
    def __init__(self, sensor_cfg):
        """Initialize the TagData class with an empty list to store tag records."""
        simulate = False
        if simulate:
            with open(DATA+"/json/data_60.json", "r") as f:
                self.tag_records = json.load(f)
        else:
            self.tag_records = []

        self.epcs = sensor_cfg['epc']
        self.buffer_size = int(read_rate * sensor_cfg['window'])

    def convert_phase_to_degrees(self, phase):
        """Convert a phase angle from radians to degrees."""
        return math.degrees(float(phase))

    def add_tag(self, epc, timestamp, channel, phase, rssi, readCount):
        """Add a new tag record to the list after converting the phase."""
        try:
            if epc not in self.epcs:
                return
            phase_degrees = self.convert_phase_to_degrees(phase)
            tag_record = {
                "epc": epc,
                "timestamp": timestamp,
                "channel": float(channel),  # Keep the channel as the frequency seen
                "phase": phase_degrees,
                "rssi": float(rssi),
                "readCount": int(readCount)
            }

            self.tag_records.append(tag_record)
        except Exception as e:
            print(f"Error adding tag: {e}")

    def get_all_tags(self):
        """Retrieve all stored tag records."""
        return self.tag_records

    def restructure_tag_data(self,window=False):
        """
        Organize and return tag data by EPC.
        
        :return: A dictionary with data grouped by each predefined EPC.
        """
        epc_data = defaultdict(lambda: {
            "timestamps": [],
            "channels": [],
            "phases": [],
            "rssis": [],
            "readCounts": []
        })

        records_to_process = self.tag_records[-self.buffer_size:] if window else self.tag_records

        for record in records_to_process:
            if record['epc'] in self.epcs:
                epc_data[record['epc']]["timestamps"].append(record["timestamp"])
                epc_data[record['epc']]["channels"].append(record["channel"])
                epc_data[record['epc']]["phases"].append(record["phase"])
                epc_data[record['epc']]["rssis"].append(record["rssi"])
                epc_data[record['epc']]["readCounts"].append(record["readCount"])

        return dict(epc_data)
    
    def dtw_matching(self, sequence1, sequence2):
        """
        Performs dynamic time warping (DTW) matching between two sequences.
        """
        _, warp_paths = fastdtw(sequence1, sequence2)

        warped_sequence1 = []
        warped_sequence2 = []

        for index in warp_paths:
            warped_sequence1.append(sequence1[index[0]])
            warped_sequence2.append(sequence2[index[1]])

        return (warped_sequence1, warped_sequence2)
    
    def calculate_avg_phase_difference(self, window=True):
        epc_data = self.restructure_tag_data(window=window)

        if len(self.epcs) < 2:
            return None
        
        epc1, epc2 = self.epcs[0], self.epcs[1]

        data1 = epc_data.get(epc1)
        data2 = epc_data.get(epc2)

        if data1 is None or data2 is None:
            return None

        # Iterate over all channels (frequencies) present in both EPCs
        common_channels = set(data1['channels']) & set(data2['channels'])

        total_diff = 0.0
        count = 0

        for channel in common_channels:
            # Extract the phase data for the current channel
            phase_seq1 = [float(data1['phases'][i]) for i, ch in enumerate(data1['channels']) if ch == channel]
            phase_seq2 = [float(data2['phases'][i]) for i, ch in enumerate(data2['channels']) if ch == channel]

            warped_rf1, warped_rf2 = self.dtw_matching(phase_seq1, phase_seq2)

            for rf1, rf2 in zip(warped_rf1, warped_rf2):
                diff = abs(rf1 - rf2)
                if diff > 270:
                    diff = abs(diff - 360)
                elif diff > 135:
                    diff = abs(diff - 180)
                total_diff += diff
                count += 1

        avg_phase_diff = total_diff / count if count > 0 else None

        return avg_phase_diff

    def save_data(self,fname):
        tag_data = self.restructure_tag_data()
        save_raw_data_to_json(tag_data,fname)
        save_raw_data_to_mat(tag_data,fname)
    
    def clear_data(self):
        """Clear all stored tag data."""
        self.tag_records.clear()

