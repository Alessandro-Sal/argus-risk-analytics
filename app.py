import os
import runpy
import subprocess
import sys


def run_ui():
    """Launch the Streamlit web dashboard via CLI."""
    target = os.path.join(os.path.dirname(__file__), "src", "0_Control_Room.py")
    cmd = [sys.executable, "-m", "streamlit", "run", target] + sys.argv[1:]
    subprocess.run(cmd)


if __name__ == "__main__":
    entry_point = "src/0_Control_Room.py" if os.path.exists("src/0_Control_Room.py") else "0_Control_Room.py"
    runpy.run_path(entry_point, run_name="__main__")
