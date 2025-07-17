# main.py - Entry point
import os
import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import logging
import os
import sys

# Set up logging to file
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'captionapp.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

# Add this at the start of your main function or entry point
logging.info("Application starting")

# Add the project root directory to sys.path
# This ensures that imports work correctly regardless of where the script is run from
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Create required directories
resources_dir = os.path.join(project_root, 'resources')
fonts_dir = os.path.join(resources_dir, 'fonts')
os.makedirs(fonts_dir, exist_ok=True)

# Import app components after setting up paths and checking license
from gui.app_window import TranscriptionApp

def main():
    try:
        # Create the root Tkinter window
        root = tk.Tk()
        
        # Set window icon (if available)
        icon_path = os.path.join(resources_dir, 'icon.ico')
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        
        # Set window title
        root.title("Transcription and Caption Tool")
        
        # Create the app instance, passing the license status
        app = TranscriptionApp(root)
        
        # Start the main event loop
        root.mainloop()

    except Exception as e:
            logging.critical(f"Critical error in main application: {e}", exc_info=True)
            # Show error in message box for the user
            import tkinter.messagebox as mb
            mb.showerror("Error", f"An error occurred: {str(e)}\nCheck logs for details.")


if __name__ == "__main__":
    main()