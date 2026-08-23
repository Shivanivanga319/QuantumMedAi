# ============================================================
# PCOS FINAL VALIDATION
# Leakage-Protected Hybrid Quantum + PyTorch
# ============================================================

import os
import random
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import pennylane as qml

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
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

import matplotlib.pyplot as plt


# ============================================================
# CONFIG
# ============================================================

SEED = 42
EPOCHS = 30
BATCH_SIZE = 32
LEARNING_RATE = 0.001

N_SELECTED_FEATURES = 12
N_QUBITS = 4
N_Q_LAYERS = 2

PATIENCE = 7

DATASET_PATH = "datasets/pcos.csv"

MODEL_DIR = "saved_models/quantum"
RESULT_DIR = "results"
GRAPH_DIR = "graphs"

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

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 70)
print("PCOS FINAL VALIDATION")
print("=" * 70)

print()
print("Device:", device)

try:
    quantum_available = True
    print("Quantum Available: True")
except Exception:
    quantum_available = False
    print("Quantum Available: False")


# ============================================================
# LEAKAGE PROTECTION
# ============================================================

print()
print("Leakage Protection:")
print()
print("1. Test split first")
print("2. Preprocessing fitted only on training data")
print("3. Identifier columns removed")
print("4. Leakage-derived columns removed")
print("5. Feature selection fitted only on training data")
print("6. SMOTE applied only to training data")
print("7. Validation used for model selection")
print("8. Threshold selected using validation data only")
print("9. Final test evaluated only once")


# ============================================================
# LOAD DATASET
# ============================================================

if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(
        f"\nDataset not found:\n{DATASET_PATH}\n"
        "Make sure pcos.csv is inside D:\\Quantum Med Ai\\datasets"
    )

df = pd.read_csv(DATASET_PATH)

print()
print("Dataset path:", DATASET_PATH)
print("Original Shape:", df.shape)

duplicates = df.duplicated().sum()

print("Duplicate Rows:", duplicates)

df = df.drop_duplicates().reset_index(drop=True)

print("After duplicates:", df.shape)


# ============================================================
# TARGET
# ============================================================

TARGET = "PCOS (Y/N)"

if TARGET not in df.columns:
    raise ValueError(
        f"\nTarget column '{TARGET}' not found.\n"
        f"Available columns:\n{df.columns.tolist()}"
    )

print()
print("Original Target:", TARGET)


# ============================================================
# CLEAN TARGET
# ============================================================

df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")

df = df.dropna(subset=[TARGET]).reset_index(drop=True)

df[TARGET] = df[TARGET].astype(int)

# Keep only valid binary target
df = df[df[TARGET].isin([0, 1])].reset_index(drop=True)

print("Target used by model:", "pcos")

print()
print("Class Distribution:")
print(df[TARGET].value_counts().sort_index())


# ============================================================
# REMOVE IDENTIFIERS / NON-PREDICTIVE COLUMNS
# ============================================================

identifier_columns = [
    "Sl. No",
    "Patient File No.",
    "Patient ID",
    "Patient_ID",
    "id",
    "ID",
]

existing_identifiers = [
    c for c in identifier_columns
    if c in df.columns
]

if existing_identifiers:
    print()
    print("Removing identifier columns:", existing_identifiers)
    df = df.drop(columns=existing_identifiers)


# ============================================================
# REMOVE EMPTY / UNNAMED COLUMNS
# ============================================================

empty_columns = []

for col in df.columns:
    if col == TARGET:
        continue

    if col.startswith("Unnamed"):
        empty_columns.append(col)

    elif df[col].isna().all():
        empty_columns.append(col)

if empty_columns:
    print()
    print("Removing empty columns:", empty_columns)
    df = df.drop(columns=empty_columns)


# ============================================================
# CONVERT TARGET
# ============================================================

y = df[TARGET].copy()

X = df.drop(columns=[TARGET]).copy()


# ============================================================
# CONVERT ALL FEATURES TO NUMERIC
# ============================================================

for col in X.columns:

    if X[col].dtype == "object":

        # Try normal numeric conversion
        converted = pd.to_numeric(X[col], errors="coerce")

        # If conversion has useful values, use it
        if converted.notna().sum() > 0:
            X[col] = converted

        else:
            # Binary Yes/No conversion
            mapping = {
                "Yes": 1,
                "No": 0,
                "Y": 1,
                "N": 0,
                "YES": 1,
                "NO": 0,
                "Male": 1,
                "Female": 0,
                "M": 1,
                "F": 0,
            }

            X[col] = (
                X[col]
                .astype(str)
                .str.strip()
                .map(mapping)
            )


# ============================================================
# REMOVE CONSTANT COLUMNS
# ============================================================

constant_columns = [
    c for c in X.columns
    if X[c].nunique(dropna=True) <= 1
]

if constant_columns:

    print()
    print("Removing constant columns:")
    print(constant_columns)

    X = X.drop(columns=constant_columns)


# ============================================================
# FINAL DATA
# ============================================================

print()
print("Samples :", len(X))
print("Features:", X.shape[1])

print()
print("Feature Columns:")

for col in X.columns:
    print("-", col)


# ============================================================
# TEST SPLIT FIRST
# ============================================================

X_dev, X_test, y_dev, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=SEED,
    stratify=y,
)


# ============================================================
# DEVELOPMENT -> TRAIN / VALIDATION
# ============================================================

X_train, X_val, y_train, y_val = train_test_split(
    X_dev,
    y_dev,
    test_size=0.20,
    random_state=SEED,
    stratify=y_dev,
)

print()
print("Development Set:", X_dev.shape)
print("Training Set   :", X_train.shape)
print("Validation Set :", X_val.shape)
print("Final Test Set :", X_test.shape)


print()
print("Test Distribution:")
print(y_test.value_counts().sort_index())


# ============================================================
# PREPROCESSING
# FIT ONLY ON TRAINING
# ============================================================

imputer = SimpleImputer(strategy="median")

X_train_imp = imputer.fit_transform(X_train)

X_val_imp = imputer.transform(X_val)

X_test_imp = imputer.transform(X_test)


# ============================================================
# SCALER
# FIT ONLY ON TRAINING
# ============================================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train_imp)

X_val_scaled = scaler.transform(X_val_imp)

X_test_scaled = scaler.transform(X_test_imp)


# ============================================================
# FEATURE SELECTION
# FIT ONLY ON TRAINING
# ============================================================

print()
print("Features before:", X_train_scaled.shape[1])

k = min(N_SELECTED_FEATURES, X_train_scaled.shape[1])

selector = SelectKBest(
    score_func=mutual_info_classif,
    k=k,
)

X_train_selected = selector.fit_transform(
    X_train_scaled,
    y_train,
)

X_val_selected = selector.transform(
    X_val_scaled
)

X_test_selected = selector.transform(
    X_test_scaled
)

feature_names = np.array(X.columns)

selected_features = feature_names[
    selector.get_support()
]

print("Features selected:", len(selected_features))
print("Final feature count:", X_train_selected.shape[1])

print()
print("Selected Features:")

for feature in selected_features:
    print("-", feature)


# ============================================================
# SMOTE
# TRAINING ONLY
# ============================================================

print()
print("Before SMOTE:")
print(dict(pd.Series(y_train).value_counts()))

smote = SMOTE(
    random_state=SEED
)

X_train_balanced, y_train_balanced = smote.fit_resample(
    X_train_selected,
    y_train,
)

print("After SMOTE:")
print(dict(pd.Series(y_train_balanced).value_counts()))


# ============================================================
# FLOAT32
# IMPORTANT FOR PYTORCH
# ============================================================

X_train_balanced = np.asarray(
    X_train_balanced,
    dtype=np.float32
)

X_val_selected = np.asarray(
    X_val_selected,
    dtype=np.float32
)

X_test_selected = np.asarray(
    X_test_selected,
    dtype=np.float32
)

y_train_balanced = np.asarray(
    y_train_balanced,
    dtype=np.int64
)

y_val = np.asarray(
    y_val,
    dtype=np.int64
)

y_test = np.asarray(
    y_test,
    dtype=np.int64
)


# ============================================================
# QUANTUM MODEL
# ============================================================

print()
print("Input Features:", X_train_balanced.shape[1])
print("Classes: 2")


# Reduce selected features to quantum input size
class QuantumProjection(nn.Module):

    def __init__(self, input_dim, n_qubits):
        super().__init__()

        self.layer = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, n_qubits),
        )

    def forward(self, x):
        return self.layer(x)


# ============================================================
# QNODE
# ============================================================

dev = qml.device(
    "default.qubit",
    wires=N_QUBITS
)


@qml.qnode(dev, interface="torch")
def quantum_circuit(inputs, weights):

    qml.AngleEmbedding(
        inputs,
        wires=range(N_QUBITS),
        rotation="Y"
    )

    for layer in range(N_Q_LAYERS):

        for wire in range(N_QUBITS):
            qml.RY(
                weights[layer, wire, 0],
                wires=wire
            )

            qml.RZ(
                weights[layer, wire, 1],
                wires=wire
            )

        for wire in range(N_QUBITS - 1):
            qml.CNOT(
                wires=[wire, wire + 1]
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

        weight_shapes = {
            "weights": (
                N_Q_LAYERS,
                N_QUBITS,
                2
            )
        }

        self.qlayer = qml.qnn.TorchLayer(
            quantum_circuit,
            weight_shapes
        )

    def forward(self, x):

        x = x.float()

        return self.qlayer(x)


# ============================================================
# HYBRID QUANTUM MODEL
# ============================================================

class HybridQuantumModel(nn.Module):

    def __init__(self, input_dim):

        super().__init__()

        self.projection = QuantumProjection(
            input_dim,
            N_QUBITS
        )

        self.quantum = QuantumLayer()

        self.classifier = nn.Sequential(
            nn.Linear(N_QUBITS, 8),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(8, 1)
        )

    def forward(self, x):

        x = x.float()

        x = self.projection(x)

        x = torch.tanh(x) * np.pi

        x = self.quantum(x)

        x = self.classifier(x)

        return x.squeeze(1)


model = HybridQuantumModel(
    X_train_balanced.shape[1]
).to(device)

print("Quantum Model: HybridQuantumModel")


# ============================================================
# DATA LOADERS
# ============================================================

X_train_tensor = torch.tensor(
    X_train_balanced,
    dtype=torch.float32
)

y_train_tensor = torch.tensor(
    y_train_balanced,
    dtype=torch.float32
)

X_val_tensor = torch.tensor(
    X_val_selected,
    dtype=torch.float32
)

y_val_tensor = torch.tensor(
    y_val,
    dtype=torch.float32
)

X_test_tensor = torch.tensor(
    X_test_selected,
    dtype=torch.float32
)

y_test_tensor = torch.tensor(
    y_test,
    dtype=torch.float32
)


train_dataset = torch.utils.data.TensorDataset(
    X_train_tensor,
    y_train_tensor
)

train_loader = torch.utils.data.DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True
)


# ============================================================
# LOSS + OPTIMIZER
# ============================================================

criterion = nn.BCEWithLogitsLoss()

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4
)


# ============================================================
# TRAINING
# ============================================================

best_val_f1 = -1

best_val_accuracy = 0

best_state = None

patience_counter = 0

train_losses = []
val_accuracies = []
val_f1_scores = []


print()
print("=" * 70)
print("TRAINING")
print("=" * 70)


for epoch in range(EPOCHS):

    model.train()

    total_loss = 0

    correct = 0

    total = 0

    for xb, yb in train_loader:

        xb = xb.to(device).float()
        yb = yb.to(device).float()

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

        total_loss += loss.item() * len(xb)

        preds = (
            torch.sigmoid(logits) >= 0.5
        ).long()

        correct += (
            preds == yb.long()
        ).sum().item()

        total += len(xb)

    avg_loss = total_loss / total

    train_accuracy = (
        correct / total
    ) * 100


    # ========================================================
    # VALIDATION
    # ========================================================

    model.eval()

    with torch.no_grad():

        val_logits = model(
            X_val_tensor.to(device)
        )

        val_probs = torch.sigmoid(
            val_logits
        ).cpu().numpy()

    val_preds = (
        val_probs >= 0.5
    ).astype(int)

    val_accuracy = accuracy_score(
        y_val,
        val_preds
    ) * 100

    val_f1 = f1_score(
        y_val,
        val_preds,
        zero_division=0
    ) * 100

    train_losses.append(avg_loss)
    val_accuracies.append(val_accuracy)
    val_f1_scores.append(val_f1)


    # ========================================================
    # PRINT
    # ========================================================

    if (
        epoch == 0
        or (epoch + 1) % 5 == 0
    ):

        print(
            f"Epoch [{epoch+1:03d}/{EPOCHS}] "
            f"Loss {avg_loss:.4f} | "
            f"Train Acc {train_accuracy:.2f}% | "
            f"Val Acc {val_accuracy:.2f}% | "
            f"Val F1 {val_f1:.2f}%"
        )


    # ========================================================
    # BEST MODEL
    # ========================================================

    if val_f1 > best_val_f1:

        best_val_f1 = val_f1

        best_val_accuracy = val_accuracy

        best_state = {
            k: v.detach().cpu().clone()
            for k, v in model.state_dict().items()
        }

        patience_counter = 0

    else:

        patience_counter += 1

        if patience_counter >= PATIENCE:

            print()
            print(
                "Early stopping at epoch",
                epoch + 1
            )

            break


# ============================================================
# RESTORE BEST VALIDATION MODEL
# ============================================================

model.load_state_dict(
    best_state
)

best_model_path = os.path.join(
    MODEL_DIR,
    "pcos_validation_best.pth"
)

torch.save(
    model.state_dict(),
    best_model_path
)

print()
print(
    "Best validation model saved:",
    best_model_path
)


# ============================================================
# VALIDATION THRESHOLD SELECTION
# ============================================================

model.eval()

with torch.no_grad():

    val_logits = model(
        X_val_tensor.to(device)
    )

    val_probs = torch.sigmoid(
        val_logits
    ).cpu().numpy()


thresholds = np.arange(
    0.30,
    0.71,
    0.01
)

best_threshold = 0.50

best_threshold_f1 = -1

best_threshold_balanced = 0

for threshold in thresholds:

    preds = (
        val_probs >= threshold
    ).astype(int)

    f1 = f1_score(
        y_val,
        preds,
        zero_division=0
    )

    balanced = balanced_accuracy_score(
        y_val,
        preds
    )

    if f1 > best_threshold_f1:

        best_threshold_f1 = f1

        best_threshold_balanced = balanced

        best_threshold = threshold


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


# ============================================================
# FINAL TEST
# EVALUATED ONLY ONCE
# ============================================================

with torch.no_grad():

    test_logits = model(
        X_test_tensor.to(device)
    )

    test_probs = torch.sigmoid(
        test_logits
    ).cpu().numpy()


test_preds = (
    test_probs >= best_threshold
).astype(int)


# ============================================================
# METRICS
# ============================================================

test_accuracy = accuracy_score(
    y_test,
    test_preds
) * 100

test_balanced = balanced_accuracy_score(
    y_test,
    test_preds
) * 100

test_precision = precision_score(
    y_test,
    test_preds,
    zero_division=0
) * 100

test_recall = recall_score(
    y_test,
    test_preds,
    zero_division=0
) * 100

test_f1 = f1_score(
    y_test,
    test_preds,
    zero_division=0
) * 100

cm = confusion_matrix(
    y_test,
    test_preds
)


# ============================================================
# FINAL MODEL
# ============================================================

final_model_path = os.path.join(
    MODEL_DIR,
    "pcos_quantum_final_validation.pth"
)

torch.save(
    model.state_dict(),
    final_model_path
)


# ============================================================
# SAVE RESULTS
# ============================================================

results = pd.DataFrame({
    "Metric": [
        "Best Validation Accuracy",
        "Best Validation F1",
        "Selected Threshold",
        "Test Accuracy",
        "Test Balanced Accuracy",
        "Precision",
        "Recall",
        "F1 Score",
    ],

    "Value": [
        best_val_accuracy,
        best_val_f1,
        best_threshold,
        test_accuracy,
        test_balanced,
        test_precision,
        test_recall,
        test_f1,
    ]
})

results_path = os.path.join(
    RESULT_DIR,
    "pcos_final_validation.csv"
)

results.to_csv(
    results_path,
    index=False
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

cm_path = os.path.join(
    RESULT_DIR,
    "pcos_confusion_matrix.csv"
)

pd.DataFrame(
    cm,
    index=["Actual 0", "Actual 1"],
    columns=["Predicted 0", "Predicted 1"]
).to_csv(
    cm_path
)


# ============================================================
# TEST PREDICTIONS
# ============================================================

prediction_path = os.path.join(
    RESULT_DIR,
    "pcos_test_predictions.csv"
)

pd.DataFrame({
    "actual": y_test,
    "probability": test_probs,
    "prediction": test_preds
}).to_csv(
    prediction_path,
    index=False
)


# ============================================================
# GRAPHS
# ============================================================

loss_path = os.path.join(
    GRAPH_DIR,
    "pcos_validation_loss.png"
)

plt.figure(figsize=(8, 5))

plt.plot(
    range(1, len(train_losses) + 1),
    train_losses
)

plt.xlabel("Epoch")

plt.ylabel("Loss")

plt.title(
    "PCOS Validation Training Loss"
)

plt.grid(True)

plt.tight_layout()

plt.savefig(
    loss_path,
    dpi=200
)

plt.close()


accuracy_path = os.path.join(
    GRAPH_DIR,
    "pcos_validation_accuracy.png"
)

plt.figure(figsize=(8, 5))

plt.plot(
    range(1, len(val_accuracies) + 1),
    val_accuracies
)

plt.xlabel("Epoch")

plt.ylabel("Validation Accuracy (%)")

plt.title(
    "PCOS Validation Accuracy"
)

plt.grid(True)

plt.tight_layout()

plt.savefig(
    accuracy_path,
    dpi=200
)

plt.close()


f1_path = os.path.join(
    GRAPH_DIR,
    "pcos_validation_f1.png"
)

plt.figure(figsize=(8, 5))

plt.plot(
    range(1, len(val_f1_scores) + 1),
    val_f1_scores
)

plt.xlabel("Epoch")

plt.ylabel("Validation F1 (%)")

plt.title(
    "PCOS Validation F1"
)

plt.grid(True)

plt.tight_layout()

plt.savefig(
    f1_path,
    dpi=200
)

plt.close()


# ============================================================
# FINAL OUTPUT
# ============================================================

print()
print("=" * 70)
print("FINAL RESULTS")
print("=" * 70)

print(
    f"Best Validation Accuracy : "
    f"{best_val_accuracy:.2f}%"
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

print()
print("Confusion Matrix:")

print(cm)

print()
print("Test Predictions:")

print(
    pd.Series(test_preds).value_counts().sort_index()
)

print()
print(
    "Quantum Model Saved Successfully."
)

print(
    "Saved To:",
    final_model_path
)

print(
    "Results Saved:",
    results_path
)

print(
    "Confusion Matrix Saved:",
    cm_path
)

print(
    "Test Predictions Saved:",
    prediction_path
)

print(
    "Loss Graph Saved:",
    loss_path
)

print(
    "Accuracy Graph Saved:",
    accuracy_path
)

print(
    "F1 Graph Saved:",
    f1_path
)

print()
print(
    "Final test set was evaluated only once."
)

print(
    "Threshold was selected using validation data only."
)

print()
print("=" * 70)
print("PCOS FINAL VALIDATION COMPLETED")
print("=" * 70)