import subprocess
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: querif run app")
        sys.exit(1)
    
    if sys.argv[1] == "run" and sys.argv[2] == "app":
        # Get the directory where this module is located
        package_dir = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(package_dir, "app.py")
        subprocess.run(["streamlit", "run", app_path])
    else:
        print("Unknown command")

if __name__ == "__main__":
    main()