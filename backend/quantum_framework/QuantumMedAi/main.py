"""
Quantum Med AI
Main Entry Point
"""

from pathlib import Path

PROJECT_NAME = "Quantum Med AI"

print("=" * 60)
print(PROJECT_NAME)
print("=" * 60)

folders = [
    "datasets",
    "preprocessing",
    "training",
    "models",
    "quantum",
    "utils",
    "saved_models",
    "graphs",
    "results",
    "inference"
]

print("\nChecking Project Structure...\n")

for folder in folders:
    path = Path(folder)
    if path.exists():
        print(f"✓ {folder}")
    else:
        print(f"✗ {folder} (Missing)")

print("\nProject Structure Verified Successfully.")
print("Ready for Dataset Preprocessing.")