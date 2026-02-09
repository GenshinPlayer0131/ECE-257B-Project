import jpype
from jpype.types import JInt

from time import time,sleep
from threading import Thread,Event
from multiprocessing import Queue
from traceback import format_exc
from lib.params import CONFIGS
from lib.params import SENSOR_CONFIGS,SENSOR_DEF

class ConnectReader():
    def __init__(self, hostname, jar_files, tag_data, if_gui=False, data_queue=None):
        self.hostname = hostname
        self.jars = jar_files
        self.tag_data = tag_data  # Instance of TagData class
        self.data_queue = data_queue  # Queue to send data to the GUI process
        self.if_gui = if_gui
        self.reader = None
        self.output_stream = None
        self.reader_stream = None
        self.tag_listener = None
        self.stop_event = Event()
        self.stream_thread = None

    def start_jvm(self):
        try:
            jpype.startJVM(classpath=self.jars)
            self.TagReportListenerImplementation = jpype.JClass("TagReportListenerImplementation")
            self.PipedOutputStream = jpype.JClass('java.io.PipedOutputStream')
            self.PipedInputStream = jpype.JClass('java.io.PipedInputStream')
            self.InputStreamReader = jpype.JClass('java.io.InputStreamReader')
            self.BufferedReader = jpype.JClass('java.io.BufferedReader')
        except Exception:
            print("Could not import the Java dependencies")
            print(format_exc())
            jpype.shutdownJVM()
            raise

    def connect_reader(self):
        try:
            self.reader = jpype.JClass('com.impinj.octane.ImpinjReader')()
            print(f"Starting connection to host: {self.hostname}")
            self.reader.connect(self.hostname)
        except Exception:
            print(f"Could not establish connection with the reader at {self.hostname}")
            print(format_exc())
            jpype.shutdownJVM()
            raise
    
    def configure_reader(self):
        try:
            settings = self.reader.queryDefaultSettings()
            rcfg = settings.getReport()
            rcfg.setIncludeChannel(CONFIGS['report']['channel'])
            rcfg.setIncludePeakRssi(CONFIGS['report']['rssi'])
            rcfg.setIncludeLastSeenTime(CONFIGS['report']['timestamp'])
            rcfg.setIncludeSeenCount(CONFIGS['report']['count'])
            rcfg.setIncludePhaseAngle(CONFIGS['report']['phase'])
            rcfg.setMode(jpype.JClass('com.impinj.octane.ReportMode').Individual)
            settings.setReport(rcfg)
            print("Configured report settings")

            settings.setRfMode(JInt(CONFIGS['reader']['rf_mode']))
            settings.setSession(JInt(CONFIGS['reader']['session']))
            settings.setTagPopulationEstimate(JInt(CONFIGS['reader']['tagPopulation']))
            settings.setSearchMode(jpype.JClass('com.impinj.octane.SearchMode').DualTarget)
            print("Configured reader settings")

            acfg = settings.getAntennas()
            for i in range(4):
                acfg.getAntennaConfigs().get(i).setEnabled(i == CONFIGS['reader']['antenna'])

            self.reader.applySettings(settings)
            print(f"Configured antenna settings")
        except Exception:
            print(f"Could not configure the reader")
            print(format_exc())
            self.reader.disconnect()
            jpype.shutdownJVM()
            raise

    def setup_listener(self):
        try:
            self.output_stream = self.PipedOutputStream()
            input_stream = self.PipedInputStream(self.output_stream)
            self.reader_stream = self.BufferedReader(self.InputStreamReader(input_stream, "UTF-8"))

            self.tag_listener = self.TagReportListenerImplementation(self.output_stream)
            self.reader.setTagReportListener(self.tag_listener)
        except Exception:
            print("Could not initialize the listener")
            print(format_exc())
            self.reader.disconnect()
            jpype.shutdownJVM()
            raise

    def read_stream(self):
        try:
            buffer = []
            counter = 0
            while not self.stop_event.is_set():
                line = self.reader_stream.readLine()
                if line:
                    try:
                        epc, timestamp, channel, phase, rssi, readCount = line.strip().split(',')
                        epc = "".join(str(epc).strip().split(" "))
                        self.tag_data.add_tag(epc, str(timestamp), str(channel), str(phase), str(rssi), str(readCount))
                        # print(epc, time()*1_000, channel, phase, rssi)
                        # print(len(self.tag_data.get_all_tags()))
                        # Latency charaterization for dtw_phase_calc
                        # t_start = time() * 1_000
                        # avg_phase_diff = self.tag_data.calculate_avg_phase_difference()
                        # t_stop  = time() * 1_000
                        # print(f"lag: {t_stop - t_start}")
                        # counter += 1
                        # if self.if_gui and counter % 10 == 0:
                        if self.if_gui:
                            # Add the avg phase difference to the buffer
                            avg_phase_diff = self.tag_data.calculate_avg_phase_difference()
                            print(avg_phase_diff)
                            # t_start = time()*1_000
                            # self.data_queue.put([avg_phase_diff,t_start])
                            
                            if avg_phase_diff is not None:
                                t_start = time()*1_000
                                buffer.append([avg_phase_diff,t_start])

                            # Send the buffer if it reaches a certain size
                            if len(buffer) >= 50:
                                t_start = time()
                                print(f"t_start: {t_start}, {len(self.tag_data.get_all_tags())}")
                                self.data_queue.put(buffer)
                                sleep(0.001)
                                buffer.clear()
                            
                    except Exception as e:
                        print(f"Error processing line {line}. Error: {str(e)}")
                        print(format_exc())
                else:
                    break
        except KeyboardInterrupt:
            print("Read interrupted. Stopping the connection.")
        except Exception:
            print(format_exc())
        finally:
            try:
                self.reader_stream.close()
            except Exception:
                print("Failed to close reader stream.")

    def start_reading(self, continuous=False, duration=10):
        try:
            print("Starting the reader...")
            self.reader.start()
            self.stop_event.clear()
            self.stream_thread = Thread(target=self.read_stream)
            self.stream_thread.start()

            if not continuous:
                jpype.java.lang.Thread.sleep(JInt(duration) * 1000)
                self.stop_event.set()
            else:
                # Latency test for GUI to find out total count of tags read in a 10s window
                # jpype.java.lang.Thread.sleep(JInt(duration) * 1000)
                # self.stop_event.set()
                try:
                    # pass
                    while True:
                        pass
                except KeyboardInterrupt:
                    print("Keyboard interrupt received. Stopping the stream")
                    self.stop_event.set()
                except Exception:
                    print(format_exc())
            # print(f"count: {len(self.tag_data.get_all_tags())}")
            self.output_stream.close()
            self.stream_thread.join()

        except jpype.JException as e:
            print(f"Java exception: {e.getMessage()}")
            print(format_exc())
        except Exception:
            print("Failed to start or complete reading")
            print(format_exc())
        finally:
            self.reader.stop()
            self.reader.disconnect()
            print("Disconnected")

    def stop_reading(self):
        try:
            self.stop_event.set()
            self.output_stream.close()
            self.stream_thread.join()
        except:
            print(format_exc())
        finally:
            self.reader.stop()
            self.reader.disconnect()
            print("Disconnected")

    def shutdown(self):
        jpype.shutdownJVM()