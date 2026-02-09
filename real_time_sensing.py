#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sys import path,argv
import os

# Add the parent directory of the src to sys.path
path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from traceback import format_exc
from time import sleep
from multiprocessing import Process, Queue, Event

from TagData import TagData
from ConnectReader import ConnectReader
from RealTimePlotApp import RealTimePlotApp
from lib.params import STORE_DATA
from lib.params import IMPINJ_HOST_IP,jar_files
from lib.params import SENSOR_CONFIGS,SENSOR_DEF

def data_collection_process(data_queue, stop_event):
    try:
        tag_data = TagData(SENSOR_CONFIGS[SENSOR_DEF])
        reader = ConnectReader(
            hostname=IMPINJ_HOST_IP,
            jar_files=jar_files,
            tag_data=tag_data,
            if_gui=True,
            data_queue=data_queue
        )

        try:
            reader.start_jvm()
            reader.connect_reader()
            reader.configure_reader()
            reader.setup_listener()
            reader.start_reading(continuous=True)
        except Exception:
            print(format_exc())
        finally:
            try:
                reader.stop_reading()
            except:
                print("Reader already disconnected")
        try:
            stop_event.wait()  # Wait until the stop event is set
            reader.shutdown()
        except:
            print("Already shutdown JVM")
    except Exception as e:
        print(f"Error in data collection process: {e}")
        print(format_exc())

def main():
    try:
        num_args = len(argv)
        if(num_args<2):
            print("Please supply file name")
            exit(1)
        fname = argv[1]
    except Exception as e:
        fname = "default"
        print(f"Could not get the experiment name due to Error: {e}")

    try:
        print(f"Experiment: {fname}")
        if not STORE_DATA:
            print("Not storing data")
    except Exception as e:
        print(f"Could not set the experiment name due to {e}")

    try:
        data_queue = Queue()
        stop_event = Event()

    except Exception as e:
        print(f"Could not initialize the multiprocessor objects due to {e}")

    try:
        data_collector = Process(target=data_collection_process, args=(data_queue, stop_event))
        data_collector.start()
    except:
        print("Could not get the data collection process up and running")
        print(format_exc())

    # sleep for 3s before starting the process for GUI
    # This gives the data collection process to start collecting data
    # before spinning up the UI, else it causes an EOF error and a crash
    sleep(3)

    try:
        print("Starting gui...")
        gui_process = Process(target=RealTimePlotApp.run_gui, args=(data_queue, stop_event))
        gui_process.start()
    except:
        print("Could not get the GUI up and running")
        print(format_exc())

    # TODO: need to figure out a way to gracefully exit the data collection process as well
    # currently the keyboard interrupt kills everything
    try:
        gui_process.join()
        stop_event.set()
        data_collector.join()
    except:
        print("Could not close the data collection and/or the GUI processes")
        print(format_exc())

    # TODO: data storage not working with the gui because of two processes
    # existing and keyboard interrupt being needed to exit the data collection process
    # keyboard interrupts in python exit the entire program based on experience
    # try:
    #     print(len(tag_data.get_all_tags()))
    #     if STORE_DATA:
    #         tag_data.save_data(fname)
    # except:
    #     print(format_exc())


if __name__ == "__main__":
    main()