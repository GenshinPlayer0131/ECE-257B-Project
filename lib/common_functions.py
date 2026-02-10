#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from scipy.io import savemat
import os
import json

from lib.params import DATA

def get_date_string():
    now = datetime.now()
    date_string = now.strftime("%d%m%Y_%H%M%S")

    return date_string

def save_raw_data_to_json(tag_data,fname):
    date_string = get_date_string()

    json_dir = os.path.join(DATA, "json")
    raw_json_name = fname + "_" + date_string + "_raw" + ".json"
    raw_json_path = os.path.join(json_dir, raw_json_name)

    if (tag_data):
        with open (raw_json_path, "w") as rawfile:
            json.dump(tag_data, rawfile, indent=4)
    else:
        print("Raw data not captured")

def save_raw_data_to_mat(tag_data,fname):
    date_string = get_date_string()

    mat_dir = os.path.join(DATA, "matlab")
    base_mat_name = fname + "_" + date_string

    for i, (epc, data) in enumerate(tag_data.items(), start=1):
        modified_data = data.copy()
        
        # Rename 'phases' to 'raw_phases'
        if 'phases' in modified_data:
            modified_data['raw_phases'] = modified_data.pop('phases')
        
        # Convert 'channels' to sequential numbers
        if 'channels' in modified_data:
            original_channels = modified_data['channels']
            unique_channels = sorted(set(original_channels))
            channel_mapping = {ch: idx + 1 for idx, ch in enumerate(unique_channels)}
            modified_data['channels'] = [channel_mapping[ch] for ch in original_channels]
        
        if (i == 1):
            mat_name = f"{base_mat_name}.mat"
        else:
            mat_name = f"{base_mat_name}_diff.mat"
        mat_path = os.path.join(mat_dir, mat_name)
        savemat(mat_path, mdict=modified_data)