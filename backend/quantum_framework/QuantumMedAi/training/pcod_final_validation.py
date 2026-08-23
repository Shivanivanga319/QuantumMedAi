import os
import random
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

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

import pennylane as qml


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 42
EPOCHS = 30
BATCH_SIZE = 32
LEARNING_RATE = 0.002

PATIENCE = 7

N_SELECTED_FEATURES = 16
N_QUBITS = 4
N_Q_LAYERS = 2

DATASET_PATH = "datasets/pcod.csv"

MODEL_DIR = "saved_models/quantum"
RESULT_DIR = "results"
GRAPH_DIR = "graphs"

BEST_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "pcod_validation_best.pth"
)

FINAL_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "pcod_quantum_final_validation.pth"
)

RESULT_PATH = os.path.join(
    RESULT_DIR,
    "pcod_final_validation.csv"
)

CONFUSION_PATH = os.path.join(
    RESULT_DIR,
    "pcod_confusion_matrix.csv"
)

PREDICTION_PATH = os.path.join(
    RESULT_DIR,
    "pcod_test_predictions.csv"
)

LOSS_GRAPH = os.path.join(
    GRAPH_DIR,
    "pcod_validation_loss.png"
)

ACCURACY_GRAPH = os.path.join(
    GRAPH_DIR,
    "pcod_validation_accuracy.png"
)

F1_GRAPH = os.path.join(
    GRAPH_DIR,
    "pcod_validation_f1.png"
)


# ============================================================
# CREATE DIRECTORIES
# ============================================================

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(GRAPH_DIR, exist_ok=True)


# ============================================================
# REPRODUCIBILITY
# ============================================================

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 70)
print("PCOD FINAL VALIDATION")
print("=" * 70)

print()
print("Device:", DEVICE)
print("Quantum Available: True")
print()


# ============================================================
# LEAKAGE PROTECTION
# ============================================================

print("Leakage Protection:")
print()
print("1. Test split first")
print("2. Preprocessing fitted only on training data")
print("3. Identifier columns removed")
print("4. Feature selection fitted only on training data")
print("5. SMOTE applied only to training data")
print("6. Validation used for model selection")
print("7. Threshold selected using validation data only")
print("8. Final test evaluated only once")
print()


# ============================================================
# LOAD DATASET
# ============================================================

if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(
        f"\nDataset not found:\n{DATASET_PATH}\n\n"
        "Make sure pcod.csv is inside datasets folder."
    )

df = pd.read_csv(DATASET_PATH)

print("Dataset path:", DATASET_PATH)
print("Original Shape:", df.shape)


# ============================================================
# REMOVE DUPLICATES
# ============================================================

duplicate_count = df.duplicated().sum()

print("Duplicate Rows:", duplicate_count)

df = df.drop_duplicates().reset_index(drop=True)

print("After duplicates:", df.shape)
print()


# ============================================================
# TARGET
# ============================================================

TARGET_ORIGINAL = "PCOS (Y/N)"

if TARGET_ORIGINAL not in df.columns:
    raise ValueError(
        f"Target column '{TARGET_ORIGINAL}' not found.\n"
        f"Available columns:\n{list(df.columns)}"
    )

print("Original Target:", TARGET_ORIGINAL)

# Project label only.
# Original dataset target is PCOS (Y/N).
df["pcod"] = pd.to_numeric(
    df[TARGET_ORIGINAL],
    errors="coerce"
)

# Some versions may contain strings Y/N.
if df["pcod"].isna().all():

    df["pcod"] = (
        df[TARGET_ORIGINAL]
        .astype(str)
        .str.strip()
        .str.upper()
        .map({
            "Y": 1,
            "N": 0
        })
    )

# If numeric values exist, keep them.
df["pcod"] = pd.to_numeric(
    df["pcod"],
    errors="coerce"
)

# Remove rows with unknown target.
df = df.dropna(
    subset=["pcod"]
).reset_index(drop=True)

df["pcod"] = df["pcod"].astype(np.int64)

print("Target used by model: PCOD")
print()

print("Class Distribution:")
print(df["pcod"].value_counts())
print()


# ============================================================
# REMOVE IDENTIFIER / TARGET COLUMNS
# ============================================================

identifier_columns = [
    "Sl. No",
    "Patient File No."
]

existing_identifier_columns = [
    c for c in identifier_columns
    if c in df.columns
]

if existing_identifier_columns:
    print(
        "Removing identifier columns:",
        existing_identifier_columns
    )

df = df.drop(
    columns=existing_identifier_columns,
    errors="ignore"
)

# Original target must never be an input feature.
df = df.drop(
    columns=[TARGET_ORIGINAL],
    errors="ignore"
)

print()


# ============================================================
# X / y
# ============================================================

X = df.drop(
    columns=["pcod"]
)

y = df["pcod"]


# ============================================================
# CONVERT FEATURES TO NUMERIC
# ============================================================

for column in X.columns:

    if X[column].dtype == "object":

        X[column] = (
            X[column]
            .astype(str)
            .str.strip()
        )

        # Y/N style values
        upper_values = X[column].str.upper()

        if set(
            upper_values.dropna().unique()
        ).issubset({"Y", "N"}):

            X[column] = upper_values.map({
                "Y": 1,
                "N": 0
            })

        else:

            # Try numeric conversion
            numeric_version = pd.to_numeric(
                X[column],
                errors="coerce"
            )

            # If mostly numeric, use numeric version.
            valid_ratio = numeric_version.notna().mean()

            if valid_ratio >= 0.8:
                X[column] = numeric_version

            else:
                # Last-resort categorical encoding.
                categories = {
                    value: idx
                    for idx, value in enumerate(
                        X[column].dropna().unique()
                    )
                }

                X[column] = X[column].map(
                    categories
                )


# ============================================================
# REPLACE INF
# ============================================================

X = X.replace(
    [np.inf, -np.inf],
    np.nan
)


# ============================================================
# TEST SPLIT FIRST
# ============================================================

X_development, X_test, y_development, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    stratify=y,
    random_state=SEED
)

# Validation split only from development data.
X_train, X_val, y_train, y_val = train_test_split(
    X_development,
    y_development,
    test_size=0.20,
    stratify=y_development,
    random_state=SEED
)


print("Samples :", len(X))
print("Features:", X.shape[1])
print()

print("Development Set:", X_development.shape)
print("Training Set   :", X_train.shape)
print("Validation Set :", X_val.shape)
print("Final Test Set :", X_test.shape)
print()

print("Test Distribution:")
print(y_test.value_counts())
print()


# ============================================================
# MISSING VALUE IMPUTATION
# FIT ONLY ON TRAINING DATA
# ============================================================

train_medians = X_train.median(numeric_only=True)

X_train = X_train.fillna(train_medians)
X_val = X_val.fillna(train_medians)
X_test = X_test.fillna(train_medians)


# ============================================================
# FEATURE SELECTION
# FIT ONLY ON TRAINING DATA
# ============================================================

print("Features before:", X_train.shape[1])

k = min(
    N_SELECTED_FEATURES,
    X_train.shape[1]
)

selector = SelectKBest(
    score_func=mutual_info_classif,
    k=k
)

X_train_selected = selector.fit_transform(
    X_train,
    y_train
)

X_val_selected = selector.transform(
    X_val
)

X_test_selected = selector.transform(
    X_test
)

selected_features = X_train.columns[
    selector.get_support()
]

print("Features selected:", len(selected_features))
print("Final feature count:", len(selected_features))
print()

print("Selected Features:")
print()

for feature in selected_features:
    print("-", feature)

print()


# ============================================================
# SCALING
# FIT ONLY ON TRAINING DATA
# ============================================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(
    X_train_selected
)

X_val_scaled = scaler.transform(
    X_val_selected
)

X_test_scaled = scaler.transform(
    X_test_selected
)


# ============================================================
# FORCE FLOAT32
# FIXES:
# mat1 and mat2 must have same dtype
# ============================================================

X_train_scaled = np.asarray(
    X_train_scaled,
    dtype=np.float32
)

X_val_scaled = np.asarray(
    X_val_scaled,
    dtype=np.float32
)

X_test_scaled = np.asarray(
    X_test_scaled,
    dtype=np.float32
)

y_train_np = np.asarray(
    y_train,
    dtype=np.int64
)

y_val_np = np.asarray(
    y_val,
    dtype=np.int64
)

y_test_np = np.asarray(
    y_test,
    dtype=np.int64
)


# ============================================================
# SMOTE
# TRAINING DATA ONLY
# ============================================================

print("Before SMOTE:")
print(
    dict(
        zip(
            *np.unique(
                y_train_np,
                return_counts=True
            )
        )
    )
)

smote = SMOTE(
    random_state=SEED
)

X_train_balanced, y_train_balanced = smote.fit_resample(
    X_train_scaled,
    y_train_np
)

print("After SMOTE:")
print(
    dict(
        zip(
            *np.unique(
                y_train_balanced,
                return_counts=True
            )
        )
    )
)

print()


# ============================================================
# PYTORCH TENSORS
# ============================================================

X_train_tensor = torch.tensor(
    X_train_balanced,
    dtype=torch.float32
)

y_train_tensor = torch.tensor(
    y_train_balanced,
    dtype=torch.long
)

X_val_tensor = torch.tensor(
    X_val_scaled,
    dtype=torch.float32
)

y_val_tensor = torch.tensor(
    y_val_np,
    dtype=torch.long
)

X_test_tensor = torch.tensor(
    X_test_scaled,
    dtype=torch.float32
)

y_test_tensor = torch.tensor(
    y_test_np,
    dtype=torch.long
)


# ============================================================
# DATA LOADERS
# ============================================================

train_dataset = torch.utils.data.TensorDataset(
    X_train_tensor,
    y_train_tensor
)

train_loader = torch.utils.data.DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    drop_last=False
)


# ============================================================
# QUANTUM DEVICE
# ============================================================

dev = qml.device(
    "default.qubit",
    wires=N_QUBITS
)


# ============================================================
# QUANTUM CIRCUIT
# ============================================================

@qml.qnode(
    dev,
    interface="torch",
    diff_method="backprop"
)
def quantum_circuit(inputs, weights):

    # Angle encoding
    for i in range(N_QUBITS):
        qml.RY(
            inputs[i],
            wires=i
        )

    # Variational layers
    for layer in range(N_Q_LAYERS):

        for i in range(N_QUBITS):
            qml.RX(
                weights[layer, i, 0],
                wires=i
            )

            qml.RY(
                weights[layer, i, 1],
                wires=i
            )

            qml.RZ(
                weights[layer, i, 2],
                wires=i
            )

        # Entanglement
        for i in range(N_QUBITS - 1):
            qml.CNOT(
                wires=[i, i + 1]
            )

        qml.CNOT(
            wires=[N_QUBITS - 1, 0]
        )

    return [
        qml.expval(
            qml.PauliZ(i)
        )
        for i in range(N_QUBITS)
    ]


# ============================================================
# QUANTUM LAYER
# ============================================================

class QuantumLayer(nn.Module):

    def __init__(self):
        super().__init__()

        self.weights = nn.Parameter(
            0.01 * torch.randn(
                N_Q_LAYERS,
                N_QUBITS,
                3,
                dtype=torch.float32
            )
        )

    def forward(self, x):

        # Ensure Float32.
        x = x.float()

        # Map 16 classical features -> 4 quantum inputs.
        chunks = torch.chunk(
            x,
            N_QUBITS,
            dim=1
        )

        quantum_input = torch.stack(
            [
                chunk.mean(dim=1)
                for chunk in chunks
            ],
            dim=1
        )

        # Bound angles.
        quantum_input = torch.tanh(
            quantum_input
        ) * np.pi

        # IMPORTANT:
        # Execute one quantum circuit per sample.
        #
        # This avoids the PennyLane batch-shape error:
        # shape '[64, -1]' is invalid for input of size 4

        outputs = []

        for sample in quantum_input:

            sample = sample.float()

            result = quantum_circuit(
                sample,
                self.weights
            )

            result = torch.stack(
                list(result)
            ).float()

            outputs.append(result)

        return torch.stack(
            outputs,
            dim=0
        )


# ============================================================
# HYBRID QUANTUM MODEL
# ============================================================

class HybridQuantumModel(nn.Module):

    def __init__(self, input_features):

        super().__init__()

        self.classical = nn.Sequential(

            nn.Linear(
                input_features,
                32
            ),

            nn.ReLU(),

            nn.Dropout(0.15),

            nn.Linear(
                32,
                16
            ),

            nn.ReLU()
        )

        self.quantum = QuantumLayer()

        self.classifier = nn.Sequential(

            nn.Linear(
                N_QUBITS,
                8
            ),

            nn.ReLU(),

            nn.Dropout(0.10),

            nn.Linear(
                8,
                2
            )
        )

    def forward(self, x):

        # FORCE FLOAT32
        x = x.float()

        x = self.classical(x)

        x = self.quantum(x)

        x = x.float()

        x = self.classifier(x)

        return x


# ============================================================
# CREATE MODEL
# ============================================================

INPUT_FEATURES = X_train_balanced.shape[1]

print("Input Features:", INPUT_FEATURES)
print("Classes:", len(np.unique(y_train_balanced)))
print("Quantum Model: HybridQuantumModel")
print()


model = HybridQuantumModel(
    INPUT_FEATURES
).to(DEVICE)


# ============================================================
# LOSS / OPTIMIZER
# ============================================================

criterion = nn.CrossEntropyLoss()

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4
)


# ============================================================
# HISTORY
# ============================================================

train_losses = []
val_losses = []

train_accuracies = []
val_accuracies = []
val_f1_scores = []


# ============================================================
# VALIDATION FUNCTION
# ============================================================

def evaluate_model(
    model,
    X_tensor,
    y_tensor
):

    model.eval()

    all_logits = []
    all_labels = []

    total_loss = 0.0

    criterion_eval = nn.CrossEntropyLoss()

    with torch.no_grad():

        for start in range(
            0,
            len(X_tensor),
            BATCH_SIZE
        ):

            xb = X_tensor[
                start:start + BATCH_SIZE
            ].to(DEVICE).float()

            yb = y_tensor[
                start:start + BATCH_SIZE
            ].to(DEVICE)

            logits = model(xb)

            loss = criterion_eval(
                logits,
                yb
            )

            total_loss += (
                loss.item() * len(xb)
            )

            all_logits.append(
                logits.detach().cpu()
            )

            all_labels.append(
                yb.detach().cpu()
            )

    logits = torch.cat(
        all_logits
    )

    labels = torch.cat(
        all_labels
    )

    probabilities = torch.softmax(
        logits,
        dim=1
    )[:, 1].numpy()

    predictions = (
        probabilities >= 0.50
    ).astype(int)

    labels_np = labels.numpy()

    accuracy = accuracy_score(
        labels_np,
        predictions
    )

    balanced = balanced_accuracy_score(
        labels_np,
        predictions
    )

    f1 = f1_score(
        labels_np,
        predictions,
        zero_division=0
    )

    avg_loss = total_loss / len(
        X_tensor
    )

    return (
        avg_loss,
        accuracy,
        balanced,
        f1,
        probabilities,
        labels_np
    )


# ============================================================
# TRAINING
# ============================================================

best_val_f1 = -1.0
best_val_accuracy = -1.0

best_epoch = 0
patience_counter = 0

print("=" * 70)
print("TRAINING")
print("=" * 70)
print()


for epoch in range(EPOCHS):

    model.train()

    running_loss = 0.0
    correct = 0
    total = 0

    for xb, yb in train_loader:

        xb = xb.to(
            DEVICE
        ).float()

        yb = yb.to(
            DEVICE
        ).long()

        optimizer.zero_grad()

        logits = model(xb)

        loss = criterion(
            logits,
            yb
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0
        )

        optimizer.step()

        running_loss += (
            loss.item() * len(xb)
        )

        predictions = torch.argmax(
            logits,
            dim=1
        )

        correct += (
            predictions == yb
        ).sum().item()

        total += len(yb)

    avg_train_loss = (
        running_loss / total
    )

    train_accuracy = (
        correct / total
    ) * 100.0


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    (
        val_loss,
        val_accuracy,
        val_balanced,
        val_f1,
        _,
        _
    ) = evaluate_model(
        model,
        X_val_tensor,
        y_val_tensor
    )

    val_accuracy_percent = (
        val_accuracy * 100.0
    )

    val_balanced_percent = (
        val_balanced * 100.0
    )

    val_f1_percent = (
        val_f1 * 100.0
    )


    train_losses.append(
        avg_train_loss
    )

    val_losses.append(
        val_loss
    )

    train_accuracies.append(
        train_accuracy
    )

    val_accuracies.append(
        val_accuracy_percent
    )

    val_f1_scores.append(
        val_f1_percent
    )


    # --------------------------------------------------------
    # MODEL SELECTION
    # --------------------------------------------------------

    improved = False

    if val_f1 > best_val_f1:

        best_val_f1 = val_f1
        best_val_accuracy = val_accuracy
        best_epoch = epoch + 1

        torch.save(
            model.state_dict(),
            BEST_MODEL_PATH
        )

        improved = True

        patience_counter = 0

    else:

        patience_counter += 1


    # Print every epoch.
    # Change to % 5 == 0 if you want less output.

    print(
        f"Epoch [{epoch + 1:03d}/{EPOCHS}] "
        f"Loss {avg_train_loss:.4f} | "
        f"Train Acc {train_accuracy:.2f}% | "
        f"Val Acc {val_accuracy_percent:.2f}% | "
        f"Val Balanced {val_balanced_percent:.2f}% | "
        f"Val F1 {val_f1_percent:.2f}%"
    )


    if patience_counter >= PATIENCE:

        print()
        print(
            f"Early stopping at epoch "
            f"{epoch + 1}"
        )

        break


print()
print(
    "Best validation model saved:",
    BEST_MODEL_PATH
)


# ============================================================
# LOAD BEST VALIDATION MODEL
# ============================================================

model.load_state_dict(
    torch.load(
        BEST_MODEL_PATH,
        map_location=DEVICE
    )
)

model.to(DEVICE)


# ============================================================
# VALIDATION THRESHOLD SELECTION
# ============================================================

(
    _,
    _,
    _,
    _,
    val_probabilities,
    val_labels
) = evaluate_model(
    model,
    X_val_tensor,
    y_val_tensor
)


best_threshold = 0.50
best_threshold_f1 = -1.0
best_threshold_balanced = -1.0

for threshold in np.arange(
    0.30,
    0.71,
    0.01
):

    val_predictions = (
        val_probabilities >= threshold
    ).astype(int)

    threshold_f1 = f1_score(
        val_labels,
        val_predictions,
        zero_division=0
    )

    threshold_balanced = balanced_accuracy_score(
        val_labels,
        val_predictions
    )

    # Select by F1.
    if threshold_f1 > best_threshold_f1:

        best_threshold_f1 = threshold_f1

        best_threshold_balanced = (
            threshold_balanced
        )

        best_threshold = float(
            threshold
        )


print()
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

print()


# ============================================================
# FINAL TEST
# EVALUATED ONLY ONCE
# ============================================================

model.eval()

with torch.no_grad():

    all_test_logits = []

    for start in range(
        0,
        len(X_test_tensor),
        BATCH_SIZE
    ):

        xb = X_test_tensor[
            start:start + BATCH_SIZE
        ].to(DEVICE).float()

        logits = model(xb)

        all_test_logits.append(
            logits.cpu()
        )

    test_logits = torch.cat(
        all_test_logits
    )

    test_probabilities = torch.softmax(
        test_logits,
        dim=1
    )[:, 1].numpy()


test_predictions = (
    test_probabilities >= best_threshold
).astype(int)


# ============================================================
# TEST METRICS
# ============================================================

test_accuracy = accuracy_score(
    y_test_np,
    test_predictions
)

test_balanced = balanced_accuracy_score(
    y_test_np,
    test_predictions
)

test_precision = precision_score(
    y_test_np,
    test_predictions,
    zero_division=0
)

test_recall = recall_score(
    y_test_np,
    test_predictions,
    zero_division=0
)

test_f1 = f1_score(
    y_test_np,
    test_predictions,
    zero_division=0
)

cm = confusion_matrix(
    y_test_np,
    test_predictions
)


# ============================================================
# FINAL RESULTS
# ============================================================

print("=" * 70)
print("FINAL RESULTS")
print("=" * 70)

print()

print(
    f"Best Validation Accuracy : "
    f"{best_val_accuracy * 100:.2f}%"
)

print(
    f"Best Validation F1       : "
    f"{best_val_f1 * 100:.2f}%"
)

print(
    f"Selected Threshold       : "
    f"{best_threshold:.2f}"
)

print(
    f"Test Accuracy            : "
    f"{test_accuracy * 100:.2f}%"
)

print(
    f"Test Balanced Accuracy   : "
    f"{test_balanced * 100:.2f}%"
)

print(
    f"Precision                : "
    f"{test_precision * 100:.2f}%"
)

print(
    f"Recall                   : "
    f"{test_recall * 100:.2f}%"
)

print(
    f"F1 Score                 : "
    f"{test_f1 * 100:.2f}%"
)

print()

print("Confusion Matrix:")
print(cm)

print()

print("Test Predictions:")

print(
    pd.Series(
        test_predictions
    ).value_counts().sort_index()
)

print()


# ============================================================
# SAVE MODEL
# ============================================================

torch.save(
    {
        "model_state_dict": model.state_dict(),
        "selected_features": list(
            selected_features
        ),
        "threshold": best_threshold,
        "n_qubits": N_QUBITS,
        "n_q_layers": N_Q_LAYERS,
        "input_features": INPUT_FEATURES,
        "seed": SEED
    },
    FINAL_MODEL_PATH
)

print(
    "Quantum Model Saved Successfully."
)

print(
    "Saved To:",
    FINAL_MODEL_PATH
)


# ============================================================
# SAVE RESULTS
# ============================================================

results_df = pd.DataFrame(
    [
        {
            "best_validation_accuracy":
                best_val_accuracy * 100,

            "best_validation_f1":
                best_val_f1 * 100,

            "selected_threshold":
                best_threshold,

            "test_accuracy":
                test_accuracy * 100,

            "test_balanced_accuracy":
                test_balanced * 100,

            "precision":
                test_precision * 100,

            "recall":
                test_recall * 100,

            "f1_score":
                test_f1 * 100,

            "best_epoch":
                best_epoch,

            "selected_features":
                len(selected_features)
        }
    ]
)

results_df.to_csv(
    RESULT_PATH,
    index=False
)

print(
    "Results Saved:",
    RESULT_PATH
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

cm_df.to_csv(
    CONFUSION_PATH
)

print(
    "Confusion Matrix Saved:",
    CONFUSION_PATH
)


# ============================================================
# SAVE TEST PREDICTIONS
# ============================================================

test_predictions_df = pd.DataFrame(
    {
        "actual": y_test_np,
        "predicted": test_predictions,
        "probability_class_1":
            test_probabilities
    }
)

test_predictions_df.to_csv(
    PREDICTION_PATH,
    index=False
)

print(
    "Test Predictions Saved:",
    PREDICTION_PATH
)


# ============================================================
# SAVE GRAPHS
# ============================================================

try:

    import matplotlib.pyplot as plt


    # --------------------------------------------------------
    # LOSS
    # --------------------------------------------------------

    plt.figure(figsize=(8, 5))

    plt.plot(
        train_losses,
        label="Train Loss"
    )

    plt.plot(
        val_losses,
        label="Validation Loss"
    )

    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("PCOD Quantum Model Loss")
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        LOSS_GRAPH,
        dpi=200
    )

    plt.close()


    # --------------------------------------------------------
    # ACCURACY
    # --------------------------------------------------------

    plt.figure(figsize=(8, 5))

    plt.plot(
        train_accuracies,
        label="Train Accuracy"
    )

    plt.plot(
        val_accuracies,
        label="Validation Accuracy"
    )

    plt.xlabel("Epoch")
    plt.ylabel("Accuracy (%)")
    plt.title("PCOD Quantum Model Accuracy")
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        ACCURACY_GRAPH,
        dpi=200
    )

    plt.close()


    # --------------------------------------------------------
    # F1
    # --------------------------------------------------------

    plt.figure(figsize=(8, 5))

    plt.plot(
        val_f1_scores,
        label="Validation F1"
    )

    plt.xlabel("Epoch")
    plt.ylabel("F1 Score (%)")
    plt.title("PCOD Quantum Model Validation F1")
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        F1_GRAPH,
        dpi=200
    )

    plt.close()


    print(
        "Loss Graph Saved:",
        LOSS_GRAPH
    )

    print(
        "Accuracy Graph Saved:",
        ACCURACY_GRAPH
    )

    print(
        "F1 Graph Saved:",
        F1_GRAPH
    )

except Exception as graph_error:

    print(
        "Graph generation skipped:",
        graph_error
    )


# ============================================================
# COMPLETED
# ============================================================

print()
print("=" * 70)
print("PCOD FINAL VALIDATION COMPLETED")
print("=" * 70)
print()
print(
    "Final test set was evaluated only once."
)
print(
    "Threshold was selected using validation data only."
)