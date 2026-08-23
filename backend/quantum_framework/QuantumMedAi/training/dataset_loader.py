import os
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.feature_selection import SelectKBest, mutual_info_classif
from imblearn.over_sampling import SMOTE


def load_dataset(
    file_path,
    target_column,
    test_size=0.20,
    random_state=42,
    use_smote=True,
    feature_selection=True,
    max_features=6
):

    # =========================================================
    # 1. Check Dataset
    # =========================================================

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Dataset not found: {file_path}"
        )

    print("\n======================================")
    print("Loading Dataset")
    print("======================================")

    df = pd.read_csv(file_path)

    print("Original Shape:", df.shape)

    # =========================================================
    # 2. Check Target Column
    # =========================================================

    if target_column not in df.columns:
        raise ValueError(
            f"Target column '{target_column}' not found.\n"
            f"Available columns:\n{list(df.columns)}"
        )

    # =========================================================
    # 3. Remove Duplicate Values
    # =========================================================

    duplicate_count = df.duplicated().sum()

    if duplicate_count > 0:
        print(
            f"Removing Duplicates: {duplicate_count}"
        )

        df = df.drop_duplicates()

    # =========================================================
    # 4. Remove ID / Serial Columns
    # =========================================================

    serial_columns = [
        "Sl. No",
        "Sl.No",
        "Serial No",
        "Serial Number",
        "id",
        "ID",
        "Unnamed: 0"
    ]

    columns_to_remove = [
        col
        for col in serial_columns
        if col in df.columns and col != target_column
    ]

    if columns_to_remove:

        print(
            "Removing ID columns:",
            columns_to_remove
        )

        df = df.drop(
            columns=columns_to_remove
        )

    # =========================================================
    # 5. Remove Missing Values
    # =========================================================

    missing_count = df.isnull().sum().sum()

    if missing_count > 0:

        print(
            f"Removing Missing Values: {missing_count}"
        )

        df = df.dropna()

    print(
        "Shape after cleaning:",
        df.shape
    )

    # =========================================================
    # 6. Separate Features and Target
    # =========================================================

    X = df.drop(
        columns=[target_column]
    ).copy()

    y = df[target_column].copy()

    # =========================================================
    # 7. Encode Target
    # =========================================================

    if y.dtype == "object":

        target_encoder = LabelEncoder()

        y = pd.Series(
            target_encoder.fit_transform(
                y.astype(str)
            ),
            index=y.index,
            name=target_column
        )

    # =========================================================
    # 8. Encode Categorical Features
    # =========================================================

    categorical_columns = X.select_dtypes(
        include=["object", "category", "bool"]
    ).columns.tolist()

    for col in categorical_columns:

        encoder = LabelEncoder()

        X[col] = encoder.fit_transform(
            X[col].astype(str)
        )

    # =========================================================
    # 9. Convert Features to Numeric
    # =========================================================

    X = X.apply(
        pd.to_numeric,
        errors="coerce"
    )

    # Remove invalid rows
    valid_rows = ~X.isnull().any(axis=1)

    X = X.loc[valid_rows]
    y = y.loc[valid_rows]

    # =========================================================
    # 10. Train / Test Split
    # =========================================================

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
        shuffle=True
    )

    print("\n======================================")
    print("Train / Test Split")
    print("======================================")

    print(
        "Training samples:",
        len(X_train)
    )

    print(
        "Testing samples:",
        len(X_test)
    )

    print(
        "Original features:",
        X_train.shape[1]
    )

    # =========================================================
    # 11. StandardScaler
    # Fit ONLY on training data
    # =========================================================

    scaler = StandardScaler()

    X_train = scaler.fit_transform(
        X_train
    )

    X_test = scaler.transform(
        X_test
    )

    # =========================================================
    # 12. SMOTE
    # Apply ONLY on training data
    # =========================================================

    if use_smote:

        print("\n======================================")
        print("Applying SMOTE")
        print("======================================")

        print(
            "Before SMOTE:",
            pd.Series(y_train).value_counts().to_dict()
        )

        class_counts = pd.Series(
            y_train
        ).value_counts()

        if len(class_counts) >= 2:

            minority_count = class_counts.min()

            if minority_count >= 2:

                k_neighbors = min(
                    5,
                    minority_count - 1
                )

                smote = SMOTE(
                    random_state=random_state,
                    k_neighbors=k_neighbors
                )

                X_train, y_train = smote.fit_resample(
                    X_train,
                    y_train
                )

                print(
                    "After SMOTE:",
                    pd.Series(y_train).value_counts().to_dict()
                )

            else:

                print(
                    "SMOTE skipped: "
                    "not enough minority samples."
                )

        else:

            print(
                "SMOTE skipped: "
                "only one class found."
            )

    # =========================================================
    # 13. Feature Selection
    # Maximum Features = 6
    # =========================================================

    if feature_selection:

        total_features = X_train.shape[1]

        k = 6

        print("\n======================================")
        print("Feature Selection")
        print("======================================")

        print(
            "Features before:",
            total_features
        )

        if k < total_features:

            selector = SelectKBest(
                score_func=mutual_info_classif,
                k=k
            )

            X_train = selector.fit_transform(
                X_train,
                y_train
            )

            X_test = selector.transform(
                X_test
            )

            print(
                "Features after:",
                X_train.shape[1]
            )

        else:

            print(
                f"All {total_features} features retained."
            )

    # =========================================================
    # 14. Reset Target Index
    # =========================================================

    y_train = pd.Series(
        y_train
    ).reset_index(drop=True)

    y_test = pd.Series(
        y_test
    ).reset_index(drop=True)

    # =========================================================
    # 15. Final Dataset Information
    # =========================================================

    print("\n======================================")
    print("FINAL DATASET")
    print("======================================")

    print(
        "X_train:",
        X_train.shape
    )

    print(
        "X_test :",
        X_test.shape
    )

    print(
        "y_train:",
        y_train.shape
    )

    print(
        "y_test :",
        y_test.shape
    )

    print(
        "Train classes:",
        y_train.value_counts().to_dict()
    )

    print(
        "Test classes:",
        y_test.value_counts().to_dict()
    )

    print("======================================")

    return (
        X_train,
        X_test,
        y_train,
        y_test
    )


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    X_train, X_test, y_train, y_test = load_dataset(
        "datasets/processed/kidney_stone.csv",
        "Kidney Stone (Y/N)"
    )

    print("\nDataset Loader Test Successful!")

    print(
        "X_train shape:",
        X_train.shape
    )

    print(
        "X_test shape:",
        X_test.shape
    )