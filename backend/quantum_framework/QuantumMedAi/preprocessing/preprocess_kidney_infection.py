import os
import pandas as pd

from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split


# ==========================================
# KIDNEY INFECTION PREPROCESSING
# ==========================================

INPUT_FILE = "datasets/kidney_infection.csv"
OUTPUT_FILE = "datasets/processed/kidney_infection.csv"

TARGET_COLUMN = "Nephritis of renal pelvis origin"


print("\n======================================")
print("KIDNEY INFECTION PREPROCESSING")
print("======================================")


# ==========================================
# 1. Load Dataset
# ==========================================

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(
        f"Dataset not found: {INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

print("Original Shape:", df.shape)


# ==========================================
# 2. Check Target
# ==========================================

if TARGET_COLUMN not in df.columns:
    raise ValueError(
        f"Target column not found: {TARGET_COLUMN}"
    )


# ==========================================
# 3. Remove Duplicates
# ==========================================

duplicates = df.duplicated().sum()

print("Duplicates:", duplicates)

if duplicates > 0:
    df = df.drop_duplicates()


# ==========================================
# 4. Remove Missing Values
# ==========================================

missing = df.isnull().sum().sum()

print("Missing Values:", missing)

if missing > 0:
    df = df.dropna()


# ==========================================
# 5. Encode Categorical Columns
# ==========================================

print("\nEncoding categorical columns...")

for column in df.columns:

    if df[column].dtype == "object":

        encoder = LabelEncoder()

        df[column] = encoder.fit_transform(
            df[column].astype(str)
        )


# ==========================================
# 6. Convert to Numeric
# ==========================================

df = df.apply(
    pd.to_numeric,
    errors="coerce"
)

df = df.dropna()


# ==========================================
# 7. Separate Features and Target
# ==========================================

X = df.drop(
    columns=[TARGET_COLUMN]
)

y = df[TARGET_COLUMN]


print("\nFeatures:", X.shape[1])
print("Samples :", len(df))

print("\nClass Distribution:")
print(y.value_counts())


# ==========================================
# 8. Standard Scaling
# ==========================================

scaler = StandardScaler()

X_scaled = scaler.fit_transform(X)

X_scaled = pd.DataFrame(
    X_scaled,
    columns=X.columns
)


# ==========================================
# 9. Combine Features + Target
# ==========================================

processed_df = X_scaled.copy()

processed_df[TARGET_COLUMN] = y.values


# ==========================================
# 10. Create Processed Folder
# ==========================================

os.makedirs(
    "datasets/processed",
    exist_ok=True
)


# ==========================================
# 11. Save Processed Dataset
# ==========================================

processed_df.to_csv(
    OUTPUT_FILE,
    index=False
)


print("\n======================================")
print("PREPROCESSING COMPLETED")
print("======================================")

print("Processed Shape:", processed_df.shape)

print("Saved To:")
print(OUTPUT_FILE)

print("\nColumns:")
print(processed_df.columns.tolist())

print("======================================")