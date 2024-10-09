import sounddevice as sd
import numpy as np
import threading
import tkinter as tk
from tkinter import ttk
import ffmpeg
import os
import sys

# Global variables
DELAY_MS = 1000  # Default delay of 1000 ms (1 second)
buffer = None
input_ready = threading.Event()

def print_device_details():
    devices = sd.query_devices()
    input_devices = []
    output_devices = []
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            input_devices.append((i, f"{device['name']} (in: {device['max_input_channels']})"))
        if device['max_output_channels'] > 0:
            output_devices.append((i, f"{device['name']} (out: {device['max_output_channels']})"))
    return input_devices, output_devices

def input_callback(indata, frames, time, status):
    if status:
        print(f"Input status: {status}")
    global buffer
    buffer = np.roll(buffer, -len(indata), axis=0)
    buffer[-len(indata):] = indata
    input_ready.set()

def output_callback(outdata, frames, time, status):
    if status:
        print(f"Output status: {status}")
    global buffer
    input_ready.wait()
    outdata[:] = buffer[:len(outdata)]
    input_ready.clear()

class AudioDelayApp:
    def __init__(self, master):
        self.master = master
        master.title("Audio Delay App")
        master.columnconfigure(1, weight=1)
        master.rowconfigure(4, weight=1)

        self.input_devices, self.output_devices = print_device_details()

        # Input device selection
        ttk.Label(master, text="Input Device:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.input_var = tk.StringVar()
        self.input_dropdown = ttk.Combobox(master, textvariable=self.input_var, values=[d[1] for d in self.input_devices])
        self.input_dropdown.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.input_dropdown.set(self.input_devices[0][1])

        # Output device selection
        ttk.Label(master, text="Output Device:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.output_var = tk.StringVar()
        self.output_dropdown = ttk.Combobox(master, textvariable=self.output_var, values=[d[1] for d in self.output_devices])
        self.output_dropdown.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.output_dropdown.set(self.output_devices[0][1])

        # Delay input
        ttk.Label(master, text="Delay (ms):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.delay_var = tk.StringVar(value=str(DELAY_MS))
        self.delay_entry = ttk.Entry(master, textvariable=self.delay_var)
        self.delay_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        # Start/Stop button
        self.running = False
        self.start_stop_btn = ttk.Button(master, text="Start", command=self.toggle_audio)
        self.start_stop_btn.grid(row=3, column=0, columnspan=2, pady=10)

        # Copyright notice
        copyright_label = ttk.Label(master, text="Created by Simon Yong", font=("Arial", 8))
        copyright_label.grid(row=4, column=0, columnspan=2, sticky="se", padx=5, pady=5)

    def toggle_audio(self):
        if not self.running:
            self.start_audio()
        else:
            self.stop_audio()

    def start_audio(self):
        global DELAY_MS, buffer
        DELAY_MS = int(self.delay_var.get())
        input_device = next(d[0] for d in self.input_devices if d[1] == self.input_var.get())
        output_device = next(d[0] for d in self.output_devices if d[1] == self.output_var.get())

        input_info = sd.query_devices(input_device)
        output_info = sd.query_devices(output_device)

        SAMPLE_RATE = int(min(input_info['default_samplerate'], output_info['default_samplerate']))
        CHANNELS = min(input_info['max_input_channels'], output_info['max_output_channels'])

        buffer_duration = DELAY_MS / 1000  # Convert ms to seconds
        buffer = np.zeros((int(SAMPLE_RATE * buffer_duration), CHANNELS))

        self.input_stream = sd.InputStream(device=input_device, samplerate=SAMPLE_RATE, channels=CHANNELS, callback=input_callback)
        self.output_stream = sd.OutputStream(device=output_device, samplerate=SAMPLE_RATE, channels=CHANNELS, callback=output_callback)

        self.input_stream.start()
        self.output_stream.start()

        self.running = True
        self.start_stop_btn.config(text="Stop")

    def stop_audio(self):
        if hasattr(self, 'input_stream'):
            self.input_stream.stop()
            self.input_stream.close()
        if hasattr(self, 'output_stream'):
            self.output_stream.stop()
            self.output_stream.close()
        self.running = False
        self.start_stop_btn.config(text="Start")

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app 
        # path into variable _MEIPASS'.
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    # Set the path to the FFmpeg executable
    ffmpeg_path = os.path.join(application_path, 'ffmpeg.exe')
    os.environ['FFMPEG_BINARY'] = ffmpeg_path

    root = tk.Tk()
    app = AudioDelayApp(root)
    root.geometry("400x200")  # Set initial window size
    root.mainloop()
