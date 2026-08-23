import pandas as pd
import os

files = [
    "kidney_stone.csv",
    "kidney_infection.csv",
    "brain_stroke.csv",
    "heart_stroke.csv",
    "liver_cancer.csv",
    "fatty_liver.csv",
    "pcos.csv",
    "pcod.csv"
]

for file in files:

    path = os.path.join("datasets", file)

    print("=" * 60)
    print(file)

    df = pd.read_csv(path)

    print("Shape :", df.shape)
    print("\nColumns:")
    print(df.columns.tolist())

    print("\nMissing Values:")
    print(df.isnull().sum())

    print()