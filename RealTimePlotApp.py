import tkinter as tk
from tkinter import ttk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from traceback import format_exc
from time import time,sleep

from lib.params import SENSOR_CONFIGS,SENSOR_DEF

class RealTimePlotApp:
    def __init__(self, result_queue, stop_event):
        self.result_queue = result_queue
        self.stop_event = stop_event

        self.root = tk.Tk()
        self.root.title("Real-Time Phase Difference Plot")
        
        # Set the window size to be larger
        self.root.geometry("800x600")
        self.start_time = time()

        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Diff-Z-Tag Sensing")
        self.ax.set_xlabel("Tag Reads")
        self.ax.set_ylabel("Phase Difference (degrees)")

        self.y_axis_max = SENSOR_CONFIGS[SENSOR_DEF]['y_range']
        # Set the fixed range for the Y-axis
        self.ax.set_ylim(0, self.y_axis_max)

        # Ensure X-axis shows only integers
        self.ax.get_xaxis().get_major_locator().set_params(integer=True)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.line, = self.ax.plot([], [], 'r-')
        
        self.x_data = []
        self.y_data = []
        self.text_annotation = None  # To store the text annotation object

        self.stop_button = ttk.Button(self.root, text="Stop", command=self.stop)
        self.stop_button.pack(side=tk.BOTTOM)

        # Label to display the average of current Y values
        self.avg_label = ttk.Label(self.root, text="\u03C6: N/A")
        self.avg_label.pack(side=tk.BOTTOM)

        # Bind the window close event to ensure graceful shutdown
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.update_plot()

    def update_plot(self):
        try:
            if not self.stop_event.is_set():
                try:
                    if not self.result_queue.empty():
                        try:
                            data_batch = self.result_queue.get()
                            # Latency test for single data push
                            # avg_phase_diff = data_batch[0]
                            # t_start = data_batch[1]
                            # t_stop  = time()*1_000
                            # lag = t_stop - t_start
                            # print(f"lag: {lag}")
                            # self.x_data.append(len(self.x_data) + 1)
                            # self.y_data.append(avg_phase_diff)

                            # Process each batch of data
                            for phase_diff in data_batch:
                                self.x_data.append(len(self.x_data) + 1)
                                self.y_data.append(phase_diff[0])
                                t_start = phase_diff[1]
                                t_stop  = time()*1_000
                                lag = t_stop - t_start
                                print("lag, pd: ", lag, phase_diff[0])
                            # Limit the X-axis to the last 20 data points
                            self.line.set_xdata(self.x_data[-20:])
                            self.line.set_ydata(self.y_data[-20:])

                            # Set the X-axis range to always show 20 data points
                            self.ax.set_xlim(max(0, len(self.x_data) - 20), max(20, len(self.x_data)))

                            # Update the average label with the Greek letter Phi (Φ)
                            current_avg = np.mean(self.y_data[-20:])
                            self.avg_label.config(text=f"\u03C6_avg: {current_avg:.2f}")

                            # Remove the previous annotation if it exists
                            if self.text_annotation:
                                self.text_annotation.remove()

                            # Add text annotation above the current phase value
                            self.text_annotation = self.ax.text(
                                self.x_data[-1],  # x-coordinate
                                self.y_data[-1] + (self.y_axis_max * 0.05),  # y-coordinate (slightly above the line)
                                f"\u03C6: {self.y_data[-1]:.2f}",  # Text to display (the current phase value)
                                ha='center', va='bottom', color='black'
                            )

                            self.ax.relim()
                            self.ax.autoscale_view()
                            self.canvas.draw()
                            self.canvas.draw_idle()
                        except:
                            pass
                except:
                    pass
                self.root.after(1, self.update_plot)
        except:
            pass

    def on_closing(self):
        """Handle the window close event to stop processes and exit gracefully."""
        self.stop()

    def stop(self):
        print(f"t_stop:{time()}")
        print("total", (time() - self.start_time), len(self.y_data))
        self.stop_event.set()
        self.root.quit()

    def run(self):
        self.root.mainloop()

    @staticmethod
    def run_gui(result_queue, stop_event):
        app = RealTimePlotApp(result_queue, stop_event)
        app.run()