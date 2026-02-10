#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import exit,argv,path
import os

# Add the parent directory of the src to sys.path
path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from traceback import format_exc

from TagData import TagData
from ConnectReader import ConnectReader
from lib.params import STORE_DATA
from lib.params import IMPINJ_HOST_IP,jar_files
from lib.params import SENSOR_CONFIGS,SENSOR_DEF

# default time to collect data in seconds
time_to_collect = 10

def main():
    num_args = len(argv)
    if(num_args<2):
        print("Please supply file name")
        exit(0)
    fname = argv[1]
    try:
        collection_time = argv[2]
        data_time = argv[2]
        if 's' in collection_time:
            collection_time = collection_time.replace('s','')
            collection_time = float(collection_time)
        elif 'm' in collection_time:
            collection_time = collection_time.replace('m','')
            collection_time = float(collection_time) * 60
        elif 'h' in collection_time:
            collection_time = collection_time.replace('h','')
            collection_time = float(collection_time) * 60 * 60
        else:
            collection_time = float(collection_time)
            data_time = data_time + "s"
    except:
        collection_time = time_to_collect
        data_time = str(collection_time) + "s"
    fname = "_".join([fname,data_time])
    print("Experiment: "+fname)
    if not STORE_DATA:
        print("Not storing data")
    
    print(f"Collecting data for {collection_time} seconds")
    tag_data = TagData(SENSOR_CONFIGS[SENSOR_DEF])
    reader = ConnectReader(
        IMPINJ_HOST_IP,
        jar_files,
        tag_data
    )

    try:
        reader.start_jvm()
        reader.connect_reader()
        reader.configure_reader()
        reader.setup_listener()
        reader.start_reading(False,collection_time)
    except Exception:
        print(format_exc())
    finally:
        try:
            reader.shutdown()
        except:
            print("Reader already disconnected")

    try:
        print(len(tag_data.get_all_tags()))
        if STORE_DATA:
            tag_data.save_data(fname)
    except:
        print(format_exc())


if __name__ == "__main__":
    main()