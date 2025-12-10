# Why the frick did I write a gui in python, this sucks.
import os
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import importlib.util
import logging
from GenerateHTMLSummary import count_plays_from_directory, VERSION
from logging_config import log_exception

CONFIG_PATH = "config.py"

def load_config():
    spec = importlib.util.spec_from_file_location("config", CONFIG_PATH)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    return config

config = load_config()

def load_style(root):
    style = ttk.Style(root)
    style.theme_use("default")

    root.configure(bg="#121212")

    style.configure("TLabel", background="#121212", foreground="#e0e0e0", font=("Helvetica", 12))
    style.configure("TCheckbutton", background="#121212", foreground="#e0e0e0", font=("Helvetica", 16))
    style.map("TCheckbutton", background=[('active', '#3a3a3a'), ('!active', '#2a2a2a')], foreground=[('active', '#ffffff'), ('!active', '#e0e0e0')])
    style.configure("TEntry", fieldbackground="#1e1e1e", foreground="#e0e0e0", background="#121212", font=("Helvetica", 16))
    style.configure("TButton", background="#2a2a2a", foreground="#e0e0e0", font=("Helvetica", 16))
    style.map("TButton", background=[('active', '#3a3a3a'), ('!active', '#2a2a2a')], foreground=[('active', '#ffffff'), ('!active', '#e0e0e0')])
    style.configure("TFrame", background="#121212", font=("Helvetica", 16))
    style.configure("TLabelframe", background="#121212", foreground="#e0e0e0", font=("Helvetica", 16))
    style.configure("TLabelframe.Label", background="#121212", foreground="#e0e0e0", font=("Helvetica", 16))

class ConfigApp:
    def __init__(self, root):
        self.root = root
        root.title("SESH Summary Config - V:" + VERSION)

        self.min_millis_var = tk.IntVar(value=config.MIN_MILLISECONDS)
        self.input_dir_var = tk.StringVar(value=config.INPUT_DIR)
        self.output_file_var = tk.StringVar(value=config.OUTPUT_FILE)
        # Minimum Year filter controls
        self.use_min_year_var = tk.BooleanVar(value=(getattr(config, 'MIN_YEAR', None) is not None))
        self.min_year_var = tk.StringVar(value=str(getattr(config, 'MIN_YEAR', '') or ''))

        self.build_ui()

    def browse_directory(self):
        """
        Open a directory selection dialog and update the input directory field.
        """
        directory = filedialog.askdirectory(
            initialdir=self.input_dir_var.get() if os.path.exists(self.input_dir_var.get()) else os.getcwd(),
            title="Select Input Directory"
        )
        if directory:  # If a directory was selected (not cancelled)
            self.input_dir_var.set(directory)

    def build_ui(self):
        padding = {'padx': 10, 'pady': 5}

        # Minimum Milliseconds (hidden if playtime mode is on)
        self.millis_frame = ttk.LabelFrame(self.root, text="Minimum Milliseconds")
        self.millis_frame.grid(row=1, column=0, sticky="ew", **padding)

        ttk.Label(
            self.millis_frame,
            text="Minimum number of milliseconds for a listen to count.\n"
                 "Changing this will drastically alter the final results."
        ).pack(anchor="w", padx=10, pady=(5, 0))

        ttk.Entry(self.millis_frame, textvariable=self.min_millis_var, width=10, font=("Helvetica", 14)).pack(anchor="w", padx=10, pady=5)

        # Minimum Year (optional filter)
        self.min_year_frame = ttk.LabelFrame(self.root, text="Minimum Year (optional)")
        self.min_year_frame.grid(row=2, column=0, sticky="ew", **padding)

        yr_top = ttk.Frame(self.min_year_frame)
        yr_top.pack(anchor="w", padx=10, pady=(5, 0), fill="x")
        ttk.Checkbutton(yr_top, text="Filter out plays before this year", variable=self.use_min_year_var,
                        command=self._toggle_min_year_state).pack(side="left")

        yr_input = ttk.Frame(self.min_year_frame)
        yr_input.pack(anchor="w", padx=10, pady=5)
        ttk.Label(yr_input, text="Minimum Year:").pack(side="left", padx=(0, 10))
        self.min_year_entry = ttk.Entry(yr_input, textvariable=self.min_year_var, width=10, font=("Helvetica", 14))
        self.min_year_entry.pack(side="left")

        # Initialize enable/disable state
        self._toggle_min_year_state()

        # Input Directory
        input_frame = ttk.LabelFrame(self.root, text="Input Directory")
        input_frame.grid(row=3, column=0, sticky="ew", **padding)

        ttk.Label(
            input_frame,
            text="Folder where you extracted your Spotify JSON files are located."
        ).pack(anchor="w", padx=10, pady=(5, 0))

        # Create a frame to hold the entry field and browse button side by side
        dir_frame = ttk.Frame(input_frame)
        dir_frame.pack(anchor="w", padx=10, pady=5, fill="x")

        # Add the entry field
        ttk.Entry(dir_frame, textvariable=self.input_dir_var, width=30, font=("Helvetica", 14)).pack(side="left", fill="x", expand=True)

        # Add the browse button
        ttk.Button(dir_frame, text="Browse...", command=self.browse_directory).pack(side="right", padx=(5, 0))

        # Output File
        output_frame = ttk.LabelFrame(self.root, text="Output File")
        output_frame.grid(row=4, column=0, sticky="ew", **padding)

        ttk.Label(
            output_frame,
            text="Name of the output HTML file.\n"
                 "If unchanged, it will be created in the same folder as the 'GenerateHTMLSummary.py' script."
        ).pack(anchor="w", padx=10, pady=(5, 0))

        ttk.Entry(output_frame, textvariable=self.output_file_var, width=40, font=("Helvetica", 14)).pack(anchor="w", padx=10, pady=5)

        # Run Button
        ttk.Button(self.root, text="Generate Summary", command=self.run).grid(row=6, column=0, pady=15)

    def _toggle_min_year_state(self):
        enabled = self.use_min_year_var.get()
        state = "!disabled" if enabled else "disabled"
        try:
            self.min_year_entry.state([state])
        except Exception:
            # Fallback for older Tk versions
            self.min_year_entry.configure(state=("normal" if enabled else "disabled"))

    def validate_inputs(self):
        """
        Validate user inputs before processing.

        Returns:
            bool: True if all inputs are valid, False otherwise
        """
        # Validate minimum milliseconds
        try:
            raw = self.min_millis_var.get()  # may raise TclError if blank
            min_ms = int(raw)  # ValueError if non-numeric
            if min_ms < 0:
                tk.messagebox.showerror("Invalid Input",
                                        "Minimum milliseconds must be a positive number. This value determines how long a track must be played to count as a listen.")
                return False
        except (ValueError, tk.TclError):
            tk.messagebox.showerror(
                "Invalid Input",
                "Minimum milliseconds must be a non-negative integer (e.g. 20000)."
            )
            return False

        # Validate input directory
        input_dir = self.input_dir_var.get().strip()
        if not input_dir:
            tk.messagebox.showerror("Invalid Input", "Input directory cannot be empty. Please specify the folder where your Spotify JSON files are located.")
            return False
        if not os.path.exists(input_dir):
            response = tk.messagebox.askquestion("Directory Not Found", 
                f"The directory '{input_dir}' does not exist. Would you like to create it?")
            if response == 'yes':
                try:
                    os.makedirs(input_dir, exist_ok=True)
                except Exception as e:
                    tk.messagebox.showerror("Error", f"Failed to create directory: {e}")
                    return False
            else:
                return False

        # Validate output file
        output_file = self.output_file_var.get().strip()
        if not output_file:
            tk.messagebox.showerror("Invalid Input", "Output file name cannot be empty. Please specify a name for the HTML report file that will be generated.")
            return False
        try:
            # Check if the directory part of the path exists
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                response = tk.messagebox.askquestion("Directory Not Found", 
                    f"The directory for output file '{output_dir}' does not exist. Would you like to create it?")
                if response == 'yes':
                    os.makedirs(output_dir, exist_ok=True)
                else:
                    return False
        except Exception as e:
            tk.messagebox.showerror("Error", f"Invalid output file path: {e}")
            return False

        # Validate minimum year if enabled
        if self.use_min_year_var.get():
            year_str = self.min_year_var.get().strip()
            if not year_str:
                tk.messagebox.showerror("Invalid Input", "Please enter a minimum year or uncheck the filter option.")
                return False
            try:
                year = int(year_str)
            except ValueError:
                tk.messagebox.showerror("Invalid Input", "Minimum year must be a valid integer, e.g., 2018.")
                return False
            if year < 1900 or year > 3000:
                tk.messagebox.showerror("Invalid Input", "Minimum year must be between 1900 and 3000.")
                return False

        return True

    def run(self):
        # Validate inputs before processing
        if not self.validate_inputs():
            return

        # Update config values from UI
        config.MIN_MILLISECONDS = int(self.min_millis_var.get())
        config.INPUT_DIR = self.input_dir_var.get().strip()
        config.OUTPUT_FILE = self.output_file_var.get().strip()
        # Set MIN_YEAR in config
        if self.use_min_year_var.get():
            try:
                config.MIN_YEAR = int(self.min_year_var.get().strip())
            except ValueError:
                config.MIN_YEAR = None
        else:
            config.MIN_YEAR = None

        # Create a progress window
        progress_win = tk.Toplevel(self.root)
        progress_win.title("Generating Summary")
        progress_win.geometry("500x150")
        progress_win.configure(bg="#1e1e1e")  # dark background
        progress_win.transient(self.root)  # Set to be on top of the main window
        progress_win.grab_set()  # Make it modal

        # Center the progress window
        progress_win.update_idletasks()
        width = progress_win.winfo_width()
        height = progress_win.winfo_height()
        x = (progress_win.winfo_screenwidth() // 2) - (width // 2)
        y = (progress_win.winfo_screenheight() // 2) - (height // 2)
        progress_win.geometry('{}x{}+{}+{}'.format(width, height, x, y))

        # Status label
        status_var = tk.StringVar(value="Starting...")
        status_label = ttk.Label(progress_win, textvariable=status_var, justify="center", anchor="center")
        status_label.pack(pady=(20, 10))

        # Progress bar
        progress_var = tk.DoubleVar(value=0.0)
        progress_bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=1.0, length=400, mode="determinate")
        progress_bar.pack(pady=10, padx=20)

        # Progress percentage label
        percentage_var = tk.StringVar(value="0%")
        percentage_label = ttk.Label(progress_win, textvariable=percentage_var, justify="center", anchor="center")
        percentage_label.pack(pady=5)

        # Progress callback function
        def update_progress(step, progress):
            status_var.set(step)
            progress_var.set(progress)
            percentage_var.set(f"{int(progress * 100)}%")
            progress_win.update()  # Force update of the UI

        # Run the main function with progress callback
        # We need to use after() to allow the progress window to render first
        def run_processing():
            try:
                count_plays_from_directory(config, update_progress)
                # Close progress window and show result window
                progress_win.destroy()
                self.show_result_window()
            except Exception as e:
                # Log the exception with detailed traceback
                logging.error(f"Error during processing: {e}")
                log_exception()

                # Show an error and close the progress window
                progress_win.destroy()
                tk.messagebox.showerror("Error", f"An error occurred during processing: {e}\n\nCheck the log file for details.")

        # Schedule the processing to start after the window is shown
        progress_win.after(100, run_processing)

    def show_result_window(self):
        """Show the result window after processing is complete."""
        result_win = tk.Toplevel(self.root)
        result_win.title("Report Generated")
        result_win.geometry("400x150")
        result_win.configure(bg="#1e1e1e")  # dark background

        # Message
        label = ttk.Label(result_win,
                          text=f"✅ HTML report generated:\n{config.OUTPUT_FILE + '.html'}\n\nWould you like to open it or close the app?",
                          justify="center",
                          anchor="center")
        label.pack(pady=20)

        # Buttons
        button_frame = ttk.Frame(result_win)
        button_frame.pack()

        def open_file():
            webbrowser.open('file://' + os.path.realpath(config.OUTPUT_FILE + ".html"))
            result_win.destroy()

        def close_app():
            self.root.quit()

        ttk.Button(button_frame, text="Open Report", command=open_file).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Close App", command=close_app).pack(side="right", padx=10)
