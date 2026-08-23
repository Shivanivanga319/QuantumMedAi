# training/classifier_train.py

import os
import warnings
import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report
)

from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline


# =========================================================
# PATHS
# =========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "datasets")
MODEL_DIR = os.path.join(BASE_DIR, "saved_models")

os.makedirs(MODEL_DIR, exist_ok=True)


# =========================================================
# DATASETS
# =========================================================

DATASETS = {
    "fatty_liver": {
        "file": "fatty_liver.csv",
        "target": "status"
    },

    "heart_stroke": {
        "file": "heart_stroke.csv",
        "target": "stroke"
    },
    "brain_stroke": {
        "file": "brain_stroke.csv",
        "target": "stroke"
    },

    "kidney_infection": {
        "file": "kidney_infection.csv",
        "target": "Nephritis_of_renal_pelvis_origin"
    },

    "kidney_stone": {
        "file": "kidney_stone.csv",
        "target": "Kidney_Stone_(Y/N)"
    },

    "liver_cancer": {
        "file": "liver_cancer.csv",
        "target": "Selector"
    },

    "pcod": {
    "file": "pcod.csv",
    "target": "PCOS_(Y/N)"
},

"pcos": {
    "file": "pcos.csv",
    "target": "PCOS_(Y/N)"
}
}
# =========================================================
# POSSIBLE TARGET COLUMN NAMES
# =========================================================

TARGET_NAMES = [
    "target",
    "Target",
    "TARGET",
    "label",
    "Label",
    "LABEL",
    "class",
    "Class",
    "CLASS",
    "outcome",
    "Outcome",
    "diagnosis",
    "Diagnosis",
    "prediction",
    "Prediction",
    "result",
    "Result",
    "status",
    "Status"
]


# =========================================================
# FIND TARGET COLUMN
# =========================================================

def find_target_column(df):

    # First check common target names
    for col in TARGET_NAMES:
        if col in df.columns:
            return col

    # Check columns containing target-related words
    for col in df.columns:

        col_lower = str(col).strip().lower()

        if any(word in col_lower for word in [
            "target",
            "label",
            "class",
            "diagnos",
            "outcome",
            "prediction",
            "result",
            "status"
        ]):
            return col

    # If target is not found, use last column
    # Most Kaggle disease datasets keep target at the end.
    print("WARNING: Target column not automatically detected.")
    print("Using last column as target:", df.columns[-1])

    return df.columns[-1]


# =========================================================
# CLEAN COLUMN NAMES
# =========================================================

def clean_columns(df):

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace(" ", "_")
    )

    return df


# =========================================================
# TRAIN ONE DATASET
# =========================================================

def train_dataset(disease_name, filename, target):

    print("\n")
    print("=" * 70)
    print("TRAINING:", disease_name.upper())
    print("=" * 70)

    file_path = os.path.join(DATA_DIR, filename)

    if not os.path.exists(file_path):

        print("Dataset not found:")
        print(file_path)

        return None

    # -----------------------------------------------------
    # LOAD
    # -----------------------------------------------------

    df = pd.read_csv(file_path)

    print("Original shape:", df.shape)

    # -----------------------------------------------------
    # CLEAN COLUMN NAMES
    # -----------------------------------------------------

    df = clean_columns(df)

    # -----------------------------------------------------
    # REMOVE DUPLICATES
    # -----------------------------------------------------

    duplicate_count = df.duplicated().sum()

    if duplicate_count > 0:

        print("Duplicate rows removed:", duplicate_count)

        df = df.drop_duplicates()

    # -----------------------------------------------------
    # REMOVE EMPTY ROWS
    # -----------------------------------------------------

    df = df.dropna(how="all")

    print("After cleaning:", df.shape)

    # -----------------------------------------------------
    # FIND TARGET
    # -----------------------------------------------------


    print("Target column:", target)

    # -----------------------------------------------------
    # REMOVE ROWS WHERE TARGET IS MISSING
    # -----------------------------------------------------

    df = df.dropna(subset=[target])

    # -----------------------------------------------------
    # X / Y
    # -----------------------------------------------------

    X = df.drop(columns=[target])
    y = df[target]

    # -----------------------------------------------------
    # REMOVE ID-LIKE COLUMNS
    # -----------------------------------------------------

    columns_to_remove = []

    for col in X.columns:

        col_lower = str(col).lower()

        if (
            col_lower == "id"
            or col_lower.endswith("_id")
            or "patient_id" in col_lower
            or "unnamed" in col_lower
        ):
            columns_to_remove.append(col)

    if columns_to_remove:

        print("ID columns removed:", columns_to_remove)

        X = X.drop(columns=columns_to_remove)

    # -----------------------------------------------------
    # CONVERT TARGET TO NUMERIC
    # -----------------------------------------------------

    label_encoder = None

    if not pd.api.types.is_numeric_dtype(y):

        label_encoder = LabelEncoder()

        y = label_encoder.fit_transform(y.astype(str))

        print("Target classes:", list(label_encoder.classes_))

    else:

        y = pd.to_numeric(y)

    # -----------------------------------------------------
    # CHECK CLASS COUNT
    # -----------------------------------------------------

    print("\nClass distribution:")
    print(pd.Series(y).value_counts())

    if len(np.unique(y)) < 2:

        print("ERROR: Dataset has only one target class.")
        return None

    # -----------------------------------------------------
    # TRAIN / TEST SPLIT
    # -----------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    # -----------------------------------------------------
    # DETECT NUMERIC / CATEGORICAL FEATURES
    # -----------------------------------------------------

    numeric_features = X_train.select_dtypes(
        include=["int64", "int32", "float64", "float32", "bool"]
    ).columns.tolist()

    categorical_features = X_train.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    print("\nNumeric features:", len(numeric_features))
    print("Categorical features:", len(categorical_features))

    # -----------------------------------------------------
    # PREPROCESSING
    # -----------------------------------------------------

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median")
            ),
            (
                "scaler",
                StandardScaler()
            )
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="most_frequent")
            ),
            (
                "encoder",
                __import__(
                    "sklearn.preprocessing",
                    fromlist=["OneHotEncoder"]
                ).OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False
                )
            )
        ]
    )

    transformers = []

    if numeric_features:

        transformers.append(
            (
                "numeric",
                numeric_pipeline,
                numeric_features
            )
        )

    if categorical_features:

        transformers.append(
            (
                "categorical",
                categorical_pipeline,
                categorical_features
            )
        )

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop"
    )

    # -----------------------------------------------------
    # MODELS
    # -----------------------------------------------------

    models = {

        "Random Forest": RandomForestClassifier(
            n_estimators=500,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            max_features="sqrt",
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ),

        "SVM": SVC(
            C=10,
            kernel="rbf",
            gamma="scale",
            probability=True,
            class_weight="balanced",
            random_state=42
        ),

        "Logistic Regression": LogisticRegression(
            C=1.0,
            max_iter=3000,
            class_weight="balanced",
            random_state=42
        ),

        "XGBoost": XGBClassifier(
            n_estimators=500,
            learning_rate=0.03,
            max_depth=5,
            min_child_weight=1,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.05,
            reg_lambda=1.0,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1
        )
    }

    # -----------------------------------------------------
    # TRAIN MODELS
    # -----------------------------------------------------

    results = []

    best_model = None
    best_accuracy = -1
    best_name = None

    print("\n========== MODEL RESULTS ==========")

    for model_name, classifier in models.items():

        print("\nTraining:", model_name)

        pipeline = ImbPipeline(
            steps=[
                ("preprocessing", preprocessor),
                ("smote", SMOTE(random_state=42)),
                ("model", classifier)
            ]
        )

        try:

            pipeline.fit(X_train, y_train)

            predictions = pipeline.predict(X_test)

            accuracy = accuracy_score(
                y_test,
                predictions
            )

            precision = precision_score(
                y_test,
                predictions,
                average="weighted",
                zero_division=0
            )

            recall = recall_score(
                y_test,
                predictions,
                average="weighted",
                zero_division=0
            )

            f1 = f1_score(
                y_test,
                predictions,
                average="weighted",
                zero_division=0
            )

            print(
                f"{model_name:<22} "
                f"Accuracy: {accuracy * 100:.2f}%"
            )

            print(
                f"{'':<22} "
                f"Precision: {precision * 100:.2f}%"
            )

            print(
                f"{'':<22} "
                f"Recall: {recall * 100:.2f}%"
            )

            print(
                f"{'':<22} "
                f"F1 Score: {f1 * 100:.2f}%"
            )

            results.append(
                {
                    "model": model_name,
                    "accuracy": accuracy,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1
                }
            )

            if accuracy > best_accuracy:

                best_accuracy = accuracy
                best_model = pipeline
                best_name = model_name

        except Exception as e:

            print(
                "ERROR while training",
                model_name
            )

            print(e)

    # -----------------------------------------------------
    # BEST MODEL
    # -----------------------------------------------------

    print("\n")
    print("=" * 70)
    print("BEST MODEL:", best_name)
    print(
        "BEST ACCURACY:",
        round(best_accuracy * 100, 2),
        "%"
    )
    print("=" * 70)

    # -----------------------------------------------------
    # CLASSIFICATION REPORT
    # -----------------------------------------------------

    if best_model is not None:

        best_predictions = best_model.predict(X_test)

        print("\nClassification Report:\n")

        print(
            classification_report(
                y_test,
                best_predictions,
                zero_division=0
            )
        )

    # -----------------------------------------------------
    # SAVE MODEL
    # -----------------------------------------------------

    model_path = os.path.join(
        MODEL_DIR,
        f"{disease_name}_model.pkl"
    )

    encoder_path = os.path.join(
        MODEL_DIR,
        f"{disease_name}_label_encoder.pkl"
    )

    joblib.dump(
        best_model,
        model_path
    )

    joblib.dump(
        label_encoder,
        encoder_path
    )

    print("Model saved:")
    print(model_path)

    return {
        "disease": disease_name,
        "best_model": best_name,
        "accuracy": best_accuracy,
        "precision": results[
            np.argmax(
                [
                    r["accuracy"]
                    for r in results
                ]
            )
        ]["precision"] if results else 0,
        "recall": results[
            np.argmax(
                [
                    r["accuracy"]
                    for r in results
                ]
            )
        ]["recall"] if results else 0,
        "f1": results[
            np.argmax(
                [
                    r["accuracy"]
                    for r in results
                ]
            )
        ]["f1"] if results else 0
    }


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 70)
    print("        QUANTUMMEDAI - MULTI DISEASE TRAINING")
    print("=" * 70)

    all_results = []
    if __name__ == "__main__":
        print("\n")
        print("=" * 70)
        print("        QUANTUMMEDAI - MULTI DISEASE TRAINING")
        print("=" * 70)
        all_results = []
        for disease_name, config in DATASETS.items():
            filename = config["file"]
            target = config["target"]
            result = train_dataset(
                disease_name,
                filename,
                    target
                    )

        if result is not None:
            all_results.append(result)

    # -----------------------------------------------------
    # FINAL SUMMARY
    # -----------------------------------------------------

    print("\n\n")
    print("=" * 80)
    print("                    FINAL SUMMARY")
    print("=" * 80)

    if all_results:

        summary = pd.DataFrame(all_results)

        summary["accuracy"] = (
            summary["accuracy"] * 100
        )

        summary["precision"] = (
            summary["precision"] * 100
        )

        summary["recall"] = (
            summary["recall"] * 100
        )

        summary["f1"] = (
            summary["f1"] * 100
        )

        print(
            summary.to_string(
                index=False,
                formatters={
                    "accuracy": "{:.2f}%".format,
                    "precision": "{:.2f}%".format,
                    "recall": "{:.2f}%".format,
                    "f1": "{:.2f}%".format
                }
            )
        )

        summary_path = os.path.join(
            MODEL_DIR,
            "training_summary.csv"
        )

        summary.to_csv(
            summary_path,
            index=False
        )

        print("\nSummary saved:")
        print(summary_path)

    else:

        print("No datasets were successfully trained.")

    print("\nTraining completed.")
    if result is not None:
        all_results.append(result)

    # -----------------------------------------------------
    # FINAL SUMMARY
    # -----------------------------------------------------

    print("\n\n")
    print("=" * 80)
    print("                    FINAL SUMMARY")
    print("=" * 80)

    if all_results:

        summary = pd.DataFrame(all_results)

        summary["accuracy"] = (
            summary["accuracy"] * 100
        )

        summary["precision"] = (
            summary["precision"] * 100
        )

        summary["recall"] = (
            summary["recall"] * 100
        )

        summary["f1"] = (
            summary["f1"] * 100
        )

        print(
            summary.to_string(
                index=False,
                formatters={
                    "accuracy": "{:.2f}%".format,
                    "precision": "{:.2f}%".format,
                    "recall": "{:.2f}%".format,
                    "f1": "{:.2f}%".format
                }
            )
        )

        summary_path = os.path.join(
            MODEL_DIR,
            "training_summary.csv"
        )

        summary.to_csv(
            summary_path,
            index=False
        )

        print("\nSummary saved:")
        print(summary_path)

    else:

        print("No datasets were successfully trained.")

    print("\nTraining completed.")