from pathlib import Path
import os

base_dir = Path(__file__).resolve().parent.parent.parent
env_path = os.path.join(str(base_dir), ".env")

print(f"Base Dir: {base_dir}")
print(f"Env Path: {env_path}")
print(f"Env File Exists: {os.path.exists(env_path)}")

if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        print("First 3 lines of .env:")
        for i, line in enumerate(f):
            if i < 3:
                print(line.strip())
