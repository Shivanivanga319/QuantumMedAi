"""
Quantum Med AI
Dataset Preprocessing Module
"""

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler


class DataPreprocessor:

    def __init__(self):
        self.scaler = StandardScaler()

    def load_dataset(self, file_path):
        df = pd.read_csv(file_path)
        print(f"\nDataset Loaded: {file_path}")
        print(f"Shape : {df.shape}")
        return df

    def clean_data(self, df):

        # Remove duplicate rows
        df = df.drop_duplicates()

        # Fill missing numeric values
        numeric_cols = df.select_dtypes(include=np.number).columns
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())

        # Fill missing categorical values
        cat_cols = df.select_dtypes(include="object").columns
        for col in cat_cols:
            df[col] = df[col].fillna(df[col].mode()[0])

        return df

    def encode_data(self, df):

        encoder = LabelEncoder()

        for col in df.select_dtypes(include="object").columns:
            df[col] = encoder.fit_transform(df[col])

        return df

    def split_features_target(self, df):

        X = df.iloc[:, :-1]
        y = df.iloc[:, -1]

        return X, y

    def scale_features(self, X):

        X = self.scaler.fit_transform(X)

        return X

    def split_dataset(self, X, y):

        return train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=42,
            stratify=y
        )


if __name__ == "__main__":

    processor = DataPreprocessor()

    df = processor.load_dataset("datasets/kidney_stone.csv")

    df = processor.clean_data(df)

    df = processor.encode_data(df)

    X, y = processor.split_features_target(df)

    X = processor.scale_features(X)

    X_train, X_test, y_train, y_test = processor.split_dataset(X, y)

    print("\nTrain Shape :", X_train.shape)
    print("Test Shape  :", X_test.shape)

    print("\nPreprocessing Completed Successfully.")
    import os

# processed folder create
os.makedirs("datasets/processed", exist_ok=True)

# processed dataset save
df.to_csv("datasets/processed/kidney_stone.csv", index=False)

print("\nProcessed dataset saved successfully.")