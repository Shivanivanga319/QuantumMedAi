import os
import random
import copy

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt

from torch.utils.data import TensorDataset, DataLoader

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, mutual_info_classif
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from imblearn.over_sampling import SMOTE

from models.hybrid_model import HybridQuantumModel


# ============================================================
# SETTINGS
# ============================================================

DATASET_PATH = "datasets/brain_stroke.csv"
TARGET_COLUMN = "at_risk"

RANDOM_STATE = 42

TEST_SIZE = 0.20
VALIDATION_SIZE = 0.20

MAX_FEATURES = 10

BATCH_SIZE = 64
EPOCHS = 30

LEARNING_RATE = 0.001
WEIGHT_DECAY = 0.0005

PATIENCE = 10
MIN_DELTA = 0.0001

# IMPORTANT:
# This column is derived risk information and should not be
# used as an input feature for genuine evaluation.
LEAKAGE_COLUMNS = [
    "stroke_risk_percentage",
]


# ============================================================
# REPRODUCIBILITY
# ============================================================

random.seed(RANDOM_STATE)
np.random.seed(RANDOM_STATE)

torch.manual_seed(RANDOM_STATE)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(RANDOM_STATE)

try:
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
except Exception:
    pass


# ============================================================
# DIRECTORIES
# ============================================================

os.makedirs("saved_models/quantum", exist_ok=True)
os.makedirs("results", exist_ok=True)
os.makedirs("graphs", exist_ok=True)


# ============================================================
# HEADER
# ============================================================

print("\n======================================")
print("BRAIN STROKE FINAL VALIDATION")
print("======================================")

print("\nLeakage Protection:")
print("1. Test split first")
print("2. Preprocessing fitted only on training data")
print("3. Leakage-derived columns removed")
print("4. Feature selection fitted only on training data")
print("5. SMOTE applied only to training data")
print("6. Validation used for model selection")
print("7. Threshold selected using validation data only")
print("8. Final test evaluated only once")


# ============================================================
# LOAD DATASET
# ============================================================

if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(
        f"\nDataset not found:\n{DATASET_PATH}\n"
        f"\nExpected location:\n"
        f"D:\\Quantum Med Ai\\datasets\\brain_stroke.csv"
    )

df = pd.read_csv(DATASET_PATH)

print("\n======================================")
print("DATASET")
print("======================================")

print("Dataset path :", DATASET_PATH)
print("Original Shape:", df.shape)


# ============================================================
# REMOVE DUPLICATES
# ============================================================

duplicate_count = int(df.duplicated().sum())

print("Duplicate Rows:", duplicate_count)

if duplicate_count > 0:
    df = df.drop_duplicates().reset_index(drop=True)

print("After duplicates:", df.shape)


# ============================================================
# CHECK TARGET
# ============================================================

if TARGET_COLUMN not in df.columns:
    raise ValueError(
        f"\nTarget column '{TARGET_COLUMN}' not found.\n"
        f"Available columns:\n{list(df.columns)}"
    )


# ============================================================
# REMOVE ID-LIKE COLUMNS
# ============================================================

id_columns = []

for col in df.columns:

    col_lower = str(col).strip().lower()

    if (
        col_lower in [
            "id",
            "patient_id",
            "patient id",
            "serial no",
            "serial number",
            "sl. no",
            "sl.no",
            "unnamed: 0",
        ]
        and col != TARGET_COLUMN
    ):
        id_columns.append(col)

if id_columns:

    print("\nRemoving ID columns:", id_columns)

    df = df.drop(
        columns=id_columns
    )


# ============================================================
# REMOVE LEAKAGE-DERIVED COLUMNS
# ============================================================

leakage_to_remove = [
    col
    for col in LEAKAGE_COLUMNS
    if col in df.columns
    and col != TARGET_COLUMN
]

if leakage_to_remove:

    print(
        "\nRemoving leakage-derived columns:",
        leakage_to_remove
    )

    df = df.drop(
        columns=leakage_to_remove
    )


# ============================================================
# TARGET CLEANING
# ============================================================

y_raw = df[TARGET_COLUMN].copy()


# ============================================================
# TARGET ENCODING
# ============================================================

if y_raw.dtype == "object":

    y_clean = (
        y_raw
        .astype(str)
        .str.strip()
        .str.lower()
    )

    target_mapping = {
        "0": 0,
        "1": 1,
        "no": 0,
        "yes": 1,
        "n": 0,
        "y": 1,
        "false": 0,
        "true": 1,
        "not at risk": 0,
        "at risk": 1,
    }

    y = y_clean.map(target_mapping)

    if y.isnull().any():

        unique_values = sorted(
            y_clean.dropna().unique().tolist()
        )

        raise ValueError(
            "\nUnknown target values found:\n"
            f"{unique_values}\n\n"
            "Please update target_mapping."
        )

else:

    y = pd.to_numeric(
        y_raw,
        errors="coerce"
    )


# ============================================================
# FEATURES
# ============================================================

X = df.drop(
    columns=[TARGET_COLUMN]
).copy()


# ============================================================
# CONVERT FEATURES
# ============================================================

for col in X.columns:

    if X[col].dtype == "object":

        # Try numeric conversion first
        converted = pd.to_numeric(
            X[col],
            errors="coerce"
        )

        numeric_ratio = (
            converted.notna().mean()
        )

        if numeric_ratio >= 0.95:

            X[col] = converted

        else:

            # Binary categorical encoding
            categories = (
                X[col]
                .astype(str)
                .str.strip()
                .str.lower()
                .unique()
            )

            categories = sorted(
                [x for x in categories if x != "nan"]
            )

            category_map = {
                value: index
                for index, value
                in enumerate(categories)
            }

            X[col] = (
                X[col]
                .astype(str)
                .str.strip()
                .str.lower()
                .map(category_map)
            )


# ============================================================
# NUMERIC CONVERSION
# ============================================================

for col in X.columns:

    X[col] = pd.to_numeric(
        X[col],
        errors="coerce"
    )


# ============================================================
# REMOVE INVALID ROWS
# ============================================================

valid_rows = (
    ~X.isnull().any(axis=1)
    & ~y.isnull()
)

removed_rows = int(
    (~valid_rows).sum()
)

if removed_rows > 0:

    print(
        "\nRemoving invalid rows:",
        removed_rows
    )

X = (
    X.loc[valid_rows]
    .reset_index(drop=True)
)

y = (
    y.loc[valid_rows]
    .astype(int)
    .reset_index(drop=True)
)


# ============================================================
# TARGET VALIDATION
# ============================================================

unique_targets = sorted(
    y.unique().tolist()
)

if not set(unique_targets).issubset({0, 1}):

    raise ValueError(
        "\nTarget must contain only 0 and 1.\n"
        f"Found: {unique_targets}"
    )


if len(unique_targets) != 2:

    raise ValueError(
        "\nBoth target classes are required.\n"
        f"Found: {unique_targets}"
    )


# ============================================================
# DATASET INFORMATION
# ============================================================

print("\n======================================")
print("DATASET INFORMATION")
print("======================================")

print("Samples :", len(X))
print("Features:", X.shape[1])

print("\nFeature Columns:")

for col in X.columns:
    print(" -", col)

print("\nClass Distribution:")

print(
    y.value_counts()
    .sort_index()
)


# ============================================================
# STEP 1
# FINAL TEST SPLIT
# ============================================================

X_dev, X_test, y_dev, y_test = train_test_split(

    X,
    y,

    test_size=TEST_SIZE,

    random_state=RANDOM_STATE,

    stratify=y,

    shuffle=True,
)


# ============================================================
# STEP 2
# TRAIN / VALIDATION SPLIT
# ============================================================

X_train, X_val, y_train, y_val = train_test_split(

    X_dev,
    y_dev,

    test_size=VALIDATION_SIZE,

    random_state=RANDOM_STATE,

    stratify=y_dev,

    shuffle=True,
)


print("\n======================================")
print("DATA SPLIT")
print("======================================")

print("Development Set :", X_dev.shape)
print("Training Set    :", X_train.shape)
print("Validation Set  :", X_val.shape)
print("Final Test Set  :", X_test.shape)

print("\nTest Distribution:")

print(
    y_test.value_counts()
    .sort_index()
)


# ============================================================
# STANDARD SCALER
# FIT ONLY ON TRAINING DATA
# ============================================================

print("\n======================================")
print("SCALING")
print("======================================")

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(
    X_train
)

X_val_scaled = scaler.transform(
    X_val
)

X_test_scaled = scaler.transform(
    X_test
)


# ============================================================
# FEATURE SELECTION
# FIT ONLY ON TRAINING DATA
# ============================================================

print("\n======================================")
print("FEATURE SELECTION")
print("======================================")

total_features = X_train_scaled.shape[1]

k = min(
    MAX_FEATURES,
    total_features
)

print("Features before:", total_features)
print("Features selected:", k)

if k < total_features:

    selector = SelectKBest(
        score_func=mutual_info_classif,
        k=k
    )

    X_train_selected = selector.fit_transform(
        X_train_scaled,
        y_train
    )

    X_val_selected = selector.transform(
        X_val_scaled
    )

    X_test_selected = selector.transform(
        X_test_scaled
    )

else:

    selector = None

    X_train_selected = X_train_scaled
    X_val_selected = X_val_scaled
    X_test_selected = X_test_scaled

print(
    "Final feature count:",
    X_train_selected.shape[1]
)


# ============================================================
# SMOTE
# TRAINING DATA ONLY
# ============================================================

print("\n======================================")
print("SMOTE")
print("======================================")

print(
    "Before SMOTE:",
    y_train.value_counts()
    .sort_index()
    .to_dict()
)

train_counts = (
    pd.Series(y_train)
    .value_counts()
)

minority_count = int(
    train_counts.min()
)

if minority_count >= 2:

    k_neighbors = min(
        5,
        minority_count - 1
    )

    smote = SMOTE(
        random_state=RANDOM_STATE,
        k_neighbors=k_neighbors
    )

    X_train_balanced, y_train_balanced = (
        smote.fit_resample(
            X_train_selected,
            y_train
        )
    )

else:

    print(
        "SMOTE skipped: minority class too small."
    )

    X_train_balanced = X_train_selected
    y_train_balanced = np.asarray(
        y_train
    )


print(
    "After SMOTE:",
    pd.Series(
        y_train_balanced
    ).value_counts()
    .sort_index()
    .to_dict()
)


# ============================================================
# TENSORS
# ============================================================

X_train_tensor = torch.tensor(
    X_train_balanced,
    dtype=torch.float32
)

X_val_tensor = torch.tensor(
    X_val_selected,
    dtype=torch.float32
)

X_test_tensor = torch.tensor(
    X_test_selected,
    dtype=torch.float32
)

y_train_tensor = torch.tensor(
    np.asarray(y_train_balanced),
    dtype=torch.long
)

y_val_tensor = torch.tensor(
    np.asarray(y_val),
    dtype=torch.long
)

y_test_tensor = torch.tensor(
    np.asarray(y_test),
    dtype=torch.long
)


# ============================================================
# DATALOADER
# ============================================================

train_dataset = TensorDataset(
    X_train_tensor,
    y_train_tensor
)

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=0,
    pin_memory=torch.cuda.is_available()
)

# ============================================================
# MODEL
# ============================================================

input_features = (
    X_train_tensor.shape[1]
)

model = HybridQuantumModel(
    input_features=input_features,
    num_classes=2
)


print("\n======================================")
print("MODEL")
print("======================================")

print(
    "Input Features:",
    input_features
)

print(
    "Classes:",
    2
)

print(
    "Quantum Model: HybridQuantumModel"
)


# ============================================================
# LOSS
# ============================================================

criterion = nn.CrossEntropyLoss()


# ============================================================
# OPTIMIZER
# ============================================================

optimizer = optim.AdamW(

    model.parameters(),

    lr=LEARNING_RATE,

    weight_decay=WEIGHT_DECAY
)


# ============================================================
# SCHEDULER
# ============================================================

scheduler = optim.lr_scheduler.CosineAnnealingLR(

    optimizer,

    T_max=EPOCHS
)


# ============================================================
# TRAINING VARIABLES
# ============================================================

best_val_f1 = -1.0
best_val_balanced = -1.0
best_val_accuracy = -1.0

best_state = None

patience_counter = 0

loss_history = []
train_accuracy_history = []
val_accuracy_history = []
val_f1_history = []


# ============================================================
# TRAINING
# ============================================================

print("\n======================================")
print("TRAINING STARTED")
print("======================================")


for epoch in range(EPOCHS):

    # --------------------------------------------------------
    # TRAIN
    # --------------------------------------------------------

    model.train()

    running_loss = 0.0

    train_correct = 0
    train_total = 0

    for batch_X, batch_y in train_loader:

        optimizer.zero_grad()

        outputs = model(
            batch_X
        )

        loss = criterion(
            outputs,
            batch_y
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0
        )

        optimizer.step()

        running_loss += loss.item()

        predictions = torch.argmax(
            outputs,
            dim=1
        )

        train_correct += (
            predictions == batch_y
        ).sum().item()

        train_total += batch_y.size(0)


    avg_loss = (
        running_loss /
        max(1, len(train_loader))
    )

    train_accuracy = (
        100.0 *
        train_correct /
        max(1, train_total)
    )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    model.eval()

    with torch.no_grad():

        val_logits = model(
            X_val_tensor
        )

        val_probabilities = torch.softmax(
            val_logits,
            dim=1
        )[:, 1].cpu().numpy()


    val_pred = (
        val_probabilities >= 0.50
    ).astype(int)

    y_val_np = (
        y_val_tensor.numpy()
    )

    val_accuracy = (
        accuracy_score(
            y_val_np,
            val_pred
        ) * 100.0
    )

    val_balanced = (
        balanced_accuracy_score(
            y_val_np,
            val_pred
        ) * 100.0
    )

    val_f1 = (
        f1_score(
            y_val_np,
            val_pred,
            zero_division=0
        ) * 100.0
    )


    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    loss_history.append(
        avg_loss
    )

    train_accuracy_history.append(
        train_accuracy
    )

    val_accuracy_history.append(
        val_accuracy
    )

    val_f1_history.append(
        val_f1
    )


    # --------------------------------------------------------
    # PRINT
    # --------------------------------------------------------

    if (
        epoch == 0
        or (epoch + 1) % 10 == 0
    ):

        print(
            f"Epoch [{epoch + 1:03d}/{EPOCHS}] "
            f"Loss {avg_loss:.4f} | "
            f"Train Acc {train_accuracy:.2f}% | "
            f"Val Acc {val_accuracy:.2f}% | "
            f"Val Balanced {val_balanced:.2f}% | "
            f"Val F1 {val_f1:.2f}%"
        )


    # --------------------------------------------------------
    # MODEL SELECTION
    #
    # Prefer balanced accuracy + F1 rather than raw accuracy.
    # This prevents an imbalanced dataset from selecting a
    # model that predicts only the majority class.
    # --------------------------------------------------------

    is_better = False

    if val_balanced > best_val_balanced + MIN_DELTA:

        is_better = True

    elif (
        abs(val_balanced - best_val_balanced)
        <= MIN_DELTA
        and val_f1 > best_val_f1 + MIN_DELTA
    ):

        is_better = True

    elif (
        abs(val_balanced - best_val_balanced)
        <= MIN_DELTA
        and abs(val_f1 - best_val_f1)
        <= MIN_DELTA
        and val_accuracy > best_val_accuracy + MIN_DELTA
    ):

        is_better = True


    if is_better:

        best_val_balanced = val_balanced
        best_val_f1 = val_f1
        best_val_accuracy = val_accuracy

        best_state = copy.deepcopy(
            model.state_dict()
        )

        patience_counter = 0

    else:

        patience_counter += 1


    # --------------------------------------------------------
    # SCHEDULER
    # --------------------------------------------------------

    scheduler.step()


    # --------------------------------------------------------
    # EARLY STOPPING
    # --------------------------------------------------------

    if patience_counter >= PATIENCE:

        print(
            f"\nEarly stopping at epoch "
            f"{epoch + 1}"
        )

        break


# ============================================================
# RESTORE BEST VALIDATION MODEL
# ============================================================

print("\n======================================")
print("BEST VALIDATION MODEL")
print("======================================")

if best_state is None:

    raise RuntimeError(
        "No valid model state was selected."
    )

model.load_state_dict(
    best_state
)

best_model_path = (
    "saved_models/quantum/"
    "brain_stroke_validation_best.pth"
)

torch.save(
    model.state_dict(),
    best_model_path
)

print(
    "Best validation model saved:",
    best_model_path
)


# ============================================================
# VALIDATION THRESHOLD SELECTION
#
# TEST DATA IS NOT USED HERE.
# ============================================================

print("\n======================================")
print("VALIDATION THRESHOLD SELECTION")
print("======================================")

model.eval()

with torch.no_grad():

    val_logits = model(
        X_val_tensor
    )

    val_probs = torch.softmax(
        val_logits,
        dim=1
    )[:, 1].cpu().numpy()

y_val_np = y_val_tensor.numpy()

thresholds = np.arange(
    0.30,
    0.71,
    0.01
)

best_threshold = 0.50
best_threshold_f1 = -1.0
best_threshold_balanced = -1.0

for threshold in thresholds:

    threshold_pred = (
        val_probs >= threshold
    ).astype(int)

    threshold_f1 = f1_score(
        y_val_np,
        threshold_pred,
        zero_division=0
    )

    threshold_balanced = (
        balanced_accuracy_score(
            y_val_np,
            threshold_pred
        )
    )

    if (
        threshold_f1 > best_threshold_f1
        or (
            np.isclose(
                threshold_f1,
                best_threshold_f1
            )
            and threshold_balanced
            > best_threshold_balanced
        )
    ):

        best_threshold = float(
            threshold
        )

        best_threshold_f1 = (
            threshold_f1
        )

        best_threshold_balanced = (
            threshold_balanced
        )


print(
    f"Selected Validation Threshold: "
    f"{best_threshold:.2f}"
)

print(
    f"Validation Threshold F1: "
    f"{best_threshold_f1 * 100:.2f}%"
)

print(
    f"Validation Threshold Balanced Accuracy: "
    f"{best_threshold_balanced * 100:.2f}%"
)


# ============================================================
# FINAL UNTOUCHED TEST EVALUATION
#
# TEST IS USED ONLY NOW.
# ============================================================

print("\n======================================")
print("FINAL UNTOUCHED TEST EVALUATION")
print("======================================")

with torch.no_grad():

    test_logits = model(
        X_test_tensor
    )

    test_probs = torch.softmax(
        test_logits,
        dim=1
    )[:, 1].cpu().numpy()


y_true = y_test_tensor.numpy()

y_pred = (
    test_probs >= best_threshold
).astype(int)


# ============================================================
# TEST METRICS
# ============================================================

test_accuracy = (
    accuracy_score(
        y_true,
        y_pred
    ) * 100.0
)

test_balanced = (
    balanced_accuracy_score(
        y_true,
        y_pred
    ) * 100.0
)

test_precision = (
    precision_score(
        y_true,
        y_pred,
        zero_division=0
    ) * 100.0
)

test_recall = (
    recall_score(
        y_true,
        y_pred,
        zero_division=0
    ) * 100.0
)

test_f1 = (
    f1_score(
        y_true,
        y_pred,
        zero_division=0
    ) * 100.0
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    y_true,
    y_pred,
    labels=[0, 1]
)


# ============================================================
# FINAL RESULTS
# ============================================================

print("\n======================================")
print("FINAL RESULTS")
print("======================================")

print(
    f"Best Validation Accuracy : "
    f"{best_val_accuracy:.2f}%"
)

print(
    f"Best Validation Balanced : "
    f"{best_val_balanced:.2f}%"
)

print(
    f"Best Validation F1       : "
    f"{best_val_f1:.2f}%"
)

print(
    f"Selected Threshold       : "
    f"{best_threshold:.2f}"
)

print(
    f"Test Accuracy            : "
    f"{test_accuracy:.2f}%"
)

print(
    f"Test Balanced Accuracy   : "
    f"{test_balanced:.2f}%"
)

print(
    f"Precision                : "
    f"{test_precision:.2f}%"
)

print(
    f"Recall                   : "
    f"{test_recall:.2f}%"
)

print(
    f"F1 Score                 : "
    f"{test_f1:.2f}%"
)

print("\nConfusion Matrix:")

print(cm)

print("\nTest Predictions:")

print(
    pd.Series(
        y_pred
    ).value_counts()
    .sort_index()
)


# ============================================================
# SAVE FINAL MODEL
# ============================================================

final_model_path = (
    "saved_models/quantum/"
    "brain_stroke_quantum_final_validation.pth"
)

torch.save(
    model.state_dict(),
    final_model_path
)

print(
    "\nQuantum Model Saved Successfully."
)

print(
    "Saved To:",
    final_model_path
)


# ============================================================
# SAVE RESULTS
# ============================================================

results_df = pd.DataFrame({

    "Metric": [

        "Best Validation Accuracy",
        "Best Validation Balanced Accuracy",
        "Best Validation F1",
        "Selected Threshold",
        "Test Accuracy",
        "Test Balanced Accuracy",
        "Test Precision",
        "Test Recall",
        "Test F1",

    ],

    "Score": [

        best_val_accuracy,
        best_val_balanced,
        best_val_f1,
        best_threshold,
        test_accuracy,
        test_balanced,
        test_precision,
        test_recall,
        test_f1,

    ]
})


results_path = (
    "results/"
    "brain_stroke_final_validation.csv"
)

results_df.to_csv(
    results_path,
    index=False
)

print(
    "Results Saved:",
    results_path
)


# ============================================================
# SAVE CONFUSION MATRIX
# ============================================================

cm_df = pd.DataFrame(
    cm,
    index=[
        "Actual_0",
        "Actual_1"
    ],
    columns=[
        "Predicted_0",
        "Predicted_1"
    ]
)

cm_path = (
    "results/"
    "brain_stroke_confusion_matrix.csv"
)

cm_df.to_csv(
    cm_path
)

print(
    "Confusion Matrix Saved:",
    cm_path
)


# ============================================================
# SAVE TEST PREDICTIONS
# ============================================================

prediction_df = pd.DataFrame({

    "Actual": y_true,

    "Predicted": y_pred,

    "Probability_Class_1": test_probs,

})


prediction_path = (
    "results/"
    "brain_stroke_test_predictions.csv"
)

prediction_df.to_csv(
    prediction_path,
    index=False
)

print(
    "Test Predictions Saved:",
    prediction_path
)


# ============================================================
# LOSS GRAPH
# ============================================================

loss_graph_path = (
    "graphs/"
    "brain_stroke_validation_loss.png"
)

plt.figure(
    figsize=(9, 5)
)

plt.plot(
    range(
        1,
        len(loss_history) + 1
    ),
    loss_history
)

plt.xlabel("Epoch")
plt.ylabel("Training Loss")

plt.title(
    "Brain Stroke Hybrid Quantum Training Loss"
)

plt.grid(True)

plt.tight_layout()

plt.savefig(
    loss_graph_path,
    dpi=300
)

plt.close()


# ============================================================
# ACCURACY GRAPH
# ============================================================

accuracy_graph_path = (
    "graphs/"
    "brain_stroke_validation_accuracy.png"
)

plt.figure(
    figsize=(9, 5)
)

plt.plot(
    range(
        1,
        len(train_accuracy_history) + 1
    ),
    train_accuracy_history,
    label="Train Accuracy"
)

plt.plot(
    range(
        1,
        len(val_accuracy_history) + 1
    ),
    val_accuracy_history,
    label="Validation Accuracy"
)

plt.xlabel("Epoch")
plt.ylabel("Accuracy (%)")

plt.title(
    "Brain Stroke Hybrid Quantum Accuracy"
)

plt.legend()

plt.grid(True)

plt.tight_layout()

plt.savefig(
    accuracy_graph_path,
    dpi=300
)

plt.close()


# ============================================================
# F1 GRAPH
# ============================================================

f1_graph_path = (
    "graphs/"
    "brain_stroke_validation_f1.png"
)

plt.figure(
    figsize=(9, 5)
)

plt.plot(
    range(
        1,
        len(val_f1_history) + 1
    ),
    val_f1_history,
    label="Validation F1"
)

plt.xlabel("Epoch")
plt.ylabel("F1 Score (%)")

plt.title(
    "Brain Stroke Validation F1 Score"
)

plt.legend()

plt.grid(True)

plt.tight_layout()

plt.savefig(
    f1_graph_path,
    dpi=300
)

plt.close()


# ============================================================
# COMPLETION
# ============================================================

print(
    "\nLoss Graph Saved:",
    loss_graph_path
)

print(
    "Accuracy Graph Saved:",
    accuracy_graph_path
)

print(
    "F1 Graph Saved:",
    f1_graph_path
)

print("\n======================================")
print("BRAIN STROKE FINAL VALIDATION COMPLETED")
print("======================================")

