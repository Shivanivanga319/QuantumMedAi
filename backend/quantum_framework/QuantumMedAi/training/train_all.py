import os

DATASETS = [
    ("datasets/processed/kidney_stone.csv", "Kidney Stone (Y/N)"),
    ("datasets/processed/kidney_infection.csv", "Nephritis of renal pelvis origin"),
    ("datasets/processed/brain_stroke.csv", "stroke"),
    ("datasets/processed/heart_stroke.csv", "stroke"),
    ("datasets/processed/liver_cancer.csv", "Selector"),
    ("datasets/processed/fatty_liver.csv", "status"),
    ("datasets/processed/pcos.csv", "PCOS (Y/N)"),
    ("datasets/processed/pcod.csv", "PCOS (Y/N)")
]

for dataset_path, target in DATASETS:

    print("\n" + "=" * 60)
    print("Training :", os.path.basename(dataset_path))
    print("=" * 60)

    os.system(
        f'python -m training.train "{dataset_path}" "{target}"'
    )

print("\nAll Datasets Training Completed Successfully.")