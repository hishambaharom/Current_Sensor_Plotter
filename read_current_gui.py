import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
from threading import Thread, Event
import time

class CurrentSensorApp:
    def __init__(self, master):
        self.master = master
        master.title("Current Sensor Reader")
        
        # Data variables
        self.serial_port = None
        self.is_reading = False
        self.stop_event = Event()
        self.time_data = []
        self.current_data = []
        self.max_points = 500  # Limit points to keep GUI responsive
        
        # Create GUI
        self.create_widgets()
        
    def create_widgets(self):
        # Serial port selection
        port_frame = ttk.LabelFrame(self.master, text="Serial Port Settings")
        port_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        ttk.Label(port_frame, text="Port:").grid(row=0, column=0, padx=5, pady=2)
        self.port_combobox = ttk.Combobox(port_frame, values=self.get_serial_ports())
        self.port_combobox.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(port_frame, text="Baudrate:").grid(row=1, column=0, padx=5, pady=2)
        self.baudrate_entry = ttk.Entry(port_frame)
        self.baudrate_entry.insert(0, "9600")
        self.baudrate_entry.grid(row=1, column=1, padx=5, pady=2)
        
        # Control buttons
        control_frame = ttk.LabelFrame(self.master, text="Controls")
        control_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        self.start_button = ttk.Button(control_frame, text="Start", command=self.start_reading)
        self.start_button.grid(row=0, column=0, padx=5, pady=2)
        
        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_reading, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5, pady=2)
        
        self.save_button = ttk.Button(control_frame, text="Save Plot", command=self.save_plot)
        self.save_button.grid(row=0, column=2, padx=5, pady=2)
        
        # Plot area
        plot_frame = ttk.LabelFrame(self.master, text="Current Reading")
        plot_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.line, = self.ax.plot([], [], 'b-')
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Current (A)')
        self.ax.grid(True)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights for resizing
        self.master.grid_rowconfigure(2, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        
    def get_serial_ports(self):
        """Return list of available serial ports"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def start_reading(self):
        """Start reading from serial port"""
        port = self.port_combobox.get()
        baudrate = self.baudrate_entry.get()
        
        if not port:
            tk.messagebox.showerror("Error", "Please select a serial port")
            return
            
        try:
            self.serial_port = serial.Serial(port, int(baudrate), timeout=1)
            self.is_reading = True
            self.stop_event.clear()
            
            # Update UI
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.port_combobox.config(state=tk.DISABLED)
            self.baudrate_entry.config(state=tk.DISABLED)
            
            # Clear previous data
            self.time_data = []
            self.current_data = []
            
            # Start reading thread
            self.read_thread = Thread(target=self.read_serial_data)
            self.read_thread.start()
            
            # Start update thread
            self.update_thread = Thread(target=self.update_plot)
            self.update_thread.start()
            
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to open serial port: {str(e)}")
    
    def stop_reading(self):
        """Stop reading from serial port"""
        self.is_reading = False
        self.stop_event.set()
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        # Update UI
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.port_combobox.config(state=tk.NORMAL)
        self.baudrate_entry.config(state=tk.NORMAL)
    
    def read_serial_data(self):
        """Thread for reading serial data"""
        start_time = time.time()
        
        while self.is_reading and not self.stop_event.is_set():
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    try:
                        current = float(line)
                        elapsed_time = time.time() - start_time
                        
                        self.time_data.append(elapsed_time)
                        self.current_data.append(current)
                        
                        # Limit data points to keep GUI responsive
                        if len(self.time_data) > self.max_points:
                            self.time_data.pop(0)
                            self.current_data.pop(0)
                            
                    except ValueError:
                        pass  # Ignore non-numeric data
                    
            except Exception as e:
                print(f"Error reading serial data: {e}")
                self.stop_reading()
                break
    
    def update_plot(self):
        """Thread for updating the plot"""
        while self.is_reading and not self.stop_event.is_set():
            if len(self.time_data) > 0:
                self.line.set_data(self.time_data, self.current_data)
                self.ax.relim()
                self.ax.autoscale_view()
                self.canvas.draw()
            time.sleep(0.1)
    
    def save_plot(self):
        """Save the current plot to a file"""
        if not self.time_data:
            tk.messagebox.showwarning("Warning", "No data to save")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.fig.savefig(file_path)
                tk.messagebox.showinfo("Success", f"Plot saved to {file_path}")
            except Exception as e:
                tk.messagebox.showerror("Error", f"Failed to save plot: {str(e)}")
    
    def on_closing(self):
        """Handle window closing"""
        self.stop_reading()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CurrentSensorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
