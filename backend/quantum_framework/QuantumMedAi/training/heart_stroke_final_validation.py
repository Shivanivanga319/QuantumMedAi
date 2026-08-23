import os
import random
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
from sklearn.feature_selection import SelectKBest, mutual_info_classif
from imblearn.over_sampling import SMOTE

import matplotlib.pyplot as plt

# ============================================================
# CONFIG
# ============================================================

SEED = 42
EPOCHS = 40
BATCH_SIZE = 32
LEARNING_RATE = 0.002
PATIENCE = 8
N_QUBITS = 4

DATASET_PATH = "datasets/heart_stroke.csv"

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

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 70)
print("HEART STROKE FINAL VALIDATION")
print("=" * 70)
print("Device:", DEVICE)

# ============================================================
# LEAKAGE PROTECTION
# ============================================================

print("\nLeakage Protection:")
print("1. Test split first")
print("2. Preprocessing fitted only on training data")
print("3. Feature selection fitted only on training data")
print("4. SMOTE applied only to training data")
print("5. Validation used for model selection")
print("6. Threshold selected using validation data only")
print("7. Final test evaluated only once")

# ============================================================
# LOAD DATA
# ============================================================

if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(
        f"\nDataset not found:\n{DATASET_PATH}\n\n"
        "Make sure the file is:\n"
        "D:\\Quantum Med Ai\\datasets\\heart_stroke.csv"
    )

df = pd.read_csv(DATASET_PATH)

print("\nDataset path:", DATASET_PATH)
print("Original Shape:", df.shape)

# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

print("\nColumns:")
print(list(df.columns))

# ============================================================
# TARGET
# ============================================================

TARGET = "target"

if TARGET not in df.columns:
    raise ValueError(
        f"\nTarget column '{TARGET}' not found.\n"
        f"Available columns: {list(df.columns)}"
    )

# ============================================================
# REMOVE DUPLICATES
# ============================================================

duplicate_count = df.duplicated().sum()

print("\nDuplicate Rows:", duplicate_count)

df = df.drop_duplicates().reset_index(drop=True)

print("After duplicates:", df.shape)

# ============================================================
# CLEAN TARGET
# ============================================================

df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")

df = df.dropna(subset=[TARGET]).reset_index(drop=True)

df[TARGET] = df[TARGET].astype(int)

# Keep only binary target
df = df[df[TARGET].isin([0, 1])].reset_index(drop=True)

print("\nTarget Distribution:")
print(df[TARGET].value_counts().sort_index())

# ============================================================
# FEATURES
# ============================================================

X = df.drop(columns=[TARGET])
y = df[TARGET]

# Remove accidental target-like columns if present
leakage_columns = [
    col for col in X.columns
    if col in [
        "risk",
        "risk_percentage",
        "heart_risk",
        "heart_risk_percentage",
        "prediction",
        "predicted_target",
    ]
]

if leakage_columns:
    print("\nRemoving leakage-derived columns:", leakage_columns)
    X = X.drop(columns=leakage_columns)

print("\nSamples :", len(X))
print("Features:", X.shape[1])

print("\nFeature Columns:")
for col in X.columns:
    print("-", col)

# ============================================================
# TEST SPLIT FIRST
# ============================================================

X_dev, X_test, y_dev, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    stratify=y,
    random_state=SEED,
)

# Validation split from development only
X_train, X_val, y_train, y_val = train_test_split(
    X_dev,
    y_dev,
    test_size=0.20,
    stratify=y_dev,
    random_state=SEED,
)

print("\nDevelopment Set:", X_dev.shape)
print("Training Set   :", X_train.shape)
print("Validation Set :", X_val.shape)
print("Final Test Set :", X_test.shape)

print("\nTest Distribution:")
print(y_test.value_counts().sort_index())

# ============================================================
# IDENTIFY COLUMN TYPES
# ============================================================

categorical_columns = X_train.select_dtypes(
    include=["object", "category"]
).columns.tolist()

numeric_columns = X_train.select_dtypes(
    include=[np.number]
).columns.tolist()

print("\nNumeric Columns:")
print(numeric_columns)

print("\nCategorical Columns:")
print(categorical_columns)

# ============================================================
# PREPROCESSING
# FIT ONLY ON TRAINING DATA
# ============================================================

try:
    encoder = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False
    )
except TypeError:
    encoder = OneHotEncoder(
        handle_unknown="ignore",
        sparse=False
    )

preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), numeric_columns),
        ("cat", encoder, categorical_columns),
    ],
    remainder="drop",
)

X_train_p = preprocessor.fit_transform(X_train)

X_val_p = preprocessor.transform(X_val)
X_test_p = preprocessor.transform(X_test)

X_train_p = np.asarray(X_train_p, dtype=np.float32)
X_val_p = np.asarray(X_val_p, dtype=np.float32)
X_test_p = np.asarray(X_test_p, dtype=np.float32)

print("\nAfter preprocessing:")
print("Train:", X_train_p.shape)
print("Val  :", X_val_p.shape)
print("Test :", X_test_p.shape)

# ============================================================
# FEATURE SELECTION
# FIT ONLY ON TRAINING DATA
# ============================================================

MAX_FEATURES = min(12, X_train_p.shape[1])

selector = SelectKBest(
    score_func=mutual_info_classif,
    k=MAX_FEATURES
)

X_train_fs = selector.fit_transform(
    X_train_p,
    y_train
)

X_val_fs = selector.transform(X_val_p)
X_test_fs = selector.transform(X_test_p)

print("\nFeatures before:", X_train_p.shape[1])
print("Features selected:", MAX_FEATURES)

# ============================================================
# SMOTE ONLY ON TRAINING DATA
# ============================================================

print("\nBefore SMOTE:")
print(pd.Series(y_train).value_counts().to_dict())

smote = SMOTE(
    random_state=SEED,
    k_neighbors=min(5, max(1, y_train.value_counts().min() - 1))
)

X_train_bal, y_train_bal = smote.fit_resample(
    X_train_fs,
    y_train
)

print("After SMOTE:")
print(pd.Series(y_train_bal).value_counts().to_dict())

# ============================================================
# TORCH DATA
# ============================================================

X_train_tensor = torch.tensor(
    X_train_bal,
    dtype=torch.float32
)

y_train_tensor = torch.tensor(
    np.asarray(y_train_bal),
    dtype=torch.float32
).view(-1, 1)

X_val_tensor = torch.tensor(
    X_val_fs,
    dtype=torch.float32
).to(DEVICE)

y_val_np = np.asarray(y_val).astype(int)

X_test_tensor = torch.tensor(
    X_test_fs,
    dtype=torch.float32
).to(DEVICE)

y_test_np = np.asarray(y_test).astype(int)

# ============================================================
# QUANTUM-STYLE HYBRID MODEL
# ============================================================

class HybridQuantumModel(nn.Module):

    def __init__(self, input_dim, n_qubits=4):
        super().__init__()

        self.feature_layer = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.15),

            nn.Linear(32, 16),
            nn.ReLU(),
        )

        self.quantum_layer = nn.Sequential(
            nn.Linear(16, n_qubits),
            nn.Tanh(),

            nn.Linear(n_qubits, n_qubits),
            nn.Tanh(),
        )

        self.classifier = nn.Sequential(
            nn.Linear(n_qubits, 8),
            nn.ReLU(),
            nn.Dropout(0.10),
            nn.Linear(8, 1),
        )

    def forward(self, x):

        x = self.feature_layer(x)

        q = self.quantum_layer(x)

        output = self.classifier(q)

        return output


model = HybridQuantumModel(
    input_dim=X_train_bal.shape[1],
    n_qubits=N_QUBITS
).to(DEVICE)

print("\nInput Features:", X_train_bal.shape[1])
print("Classes: 2")
print("Quantum Model: HybridQuantumModel")

# ============================================================
# DATALOADER
# ============================================================

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
# LOSS / OPTIMIZER
# ============================================================

criterion = nn.BCEWithLogitsLoss()

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4
)

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="max",
    factor=0.5,
    patience=3
)

# ============================================================
# TRAINING
# ============================================================

best_val_f1 = -1.0
best_val_acc = -1.0
best_state = None

patience_counter = 0

train_losses = []
val_accuracies = []
val_f1s = []

print("\n" + "=" * 70)
print("TRAINING")
print("=" * 70)

for epoch in range(EPOCHS):

    model.train()

    total_loss = 0.0
    correct = 0
    total = 0

    for batch_x, batch_y in train_loader:

        batch_x = batch_x.to(DEVICE)
        batch_y = batch_y.to(DEVICE)

        optimizer.zero_grad()

        logits = model(batch_x)

        loss = criterion(logits, batch_y)

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0
        )

        optimizer.step()

        total_loss += loss.item() * batch_x.size(0)

        predictions = (
            torch.sigmoid(logits) >= 0.5
        ).float()

        correct += (
            predictions == batch_y
        ).sum().item()

        total += batch_y.size(0)

    avg_loss = total_loss / total

    train_accuracy = (
        correct / total
    ) * 100

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    model.eval()

    with torch.no_grad():

        val_logits = model(X_val_tensor)

        val_prob = torch.sigmoid(
            val_logits
        ).cpu().numpy().ravel()

    val_pred = (
        val_prob >= 0.5
    ).astype(int)

    val_accuracy = accuracy_score(
        y_val_np,
        val_pred
    ) * 100

    val_balanced = balanced_accuracy_score(
        y_val_np,
        val_pred
    ) * 100

    val_f1 = f1_score(
        y_val_np,
        val_pred,
        zero_division=0
    ) * 100

    train_losses.append(avg_loss)
    val_accuracies.append(val_accuracy)
    val_f1s.append(val_f1)

    scheduler.step(val_f1)

    if epoch == 0 or (epoch + 1) % 5 == 0:

        print(
            f"Epoch [{epoch+1:03d}/{EPOCHS}] "
            f"Loss {avg_loss:.4f} | "
            f"Train Acc {train_accuracy:.2f}% | "
            f"Val Acc {val_accuracy:.2f}% | "
            f"Val Balanced {val_balanced:.2f}% | "
            f"Val F1 {val_f1:.2f}%"
        )

    # --------------------------------------------------------
    # SAVE BEST MODEL
    # --------------------------------------------------------

    if val_f1 > best_val_f1:

        best_val_f1 = val_f1
        best_val_acc = val_accuracy

        best_state = {
            k: v.detach().cpu().clone()
            for k, v in model.state_dict().items()
        }

        patience_counter = 0

    else:

        patience_counter += 1

    if patience_counter >= PATIENCE:

        print(
            f"\nEarly stopping at epoch {epoch + 1}"
        )

        break

# ============================================================
# RESTORE BEST MODEL
# ============================================================

if best_state is None:
    raise RuntimeError(
        "Best model was not saved."
    )

model.load_state_dict(best_state)

best_model_path = (
    f"{MODEL_DIR}/"
    "heart_stroke_validation_best.pth"
)

torch.save(
    model.state_dict(),
    best_model_path
)

print(
    "\nBest validation model saved:",
    best_model_path
)

# ============================================================
# VALIDATION THRESHOLD SEARCH
# VALIDATION ONLY
# ============================================================

model.eval()

with torch.no_grad():

    val_logits = model(X_val_tensor)

    val_prob = torch.sigmoid(
        val_logits
    ).cpu().numpy().ravel()

best_threshold = 0.50
best_threshold_f1 = -1
best_threshold_balanced = -1

for threshold in np.arange(
    0.30,
    0.71,
    0.01
):

    pred = (
        val_prob >= threshold
    ).astype(int)

    f1 = f1_score(
        y_val_np,
        pred,
        zero_division=0
    )

    balanced = balanced_accuracy_score(
        y_val_np,
        pred
    )

    if f1 > best_threshold_f1:

        best_threshold_f1 = f1
        best_threshold_balanced = balanced
        best_threshold = threshold

print(
    f"\nSelected Validation Threshold: "
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

model.eval()

with torch.no_grad():

    test_logits = model(X_test_tensor)

    test_prob = torch.sigmoid(
        test_logits
    ).cpu().numpy().ravel()

test_pred = (
    test_prob >= best_threshold
).astype(int)

# ============================================================
# FINAL METRICS
# ============================================================

test_accuracy = accuracy_score(
    y_test_np,
    test_pred
) * 100

test_balanced = balanced_accuracy_score(
    y_test_np,
    test_pred
) * 100

precision = precision_score(
    y_test_np,
    test_pred,
    zero_division=0
) * 100

recall = recall_score(
    y_test_np,
    test_pred,
    zero_division=0
) * 100

f1 = f1_score(
    y_test_np,
    test_pred,
    zero_division=0
) * 100

cm = confusion_matrix(
    y_test_np,
    test_pred
)

# ============================================================
# PRINT RESULTS
# ============================================================

print("\n")
print("=" * 70)
print("FINAL RESULTS")
print("=" * 70)

print(
    f"Best Validation Accuracy : "
    f"{best_val_acc:.2f}%"
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
    f"{test_accuracy:.2f}%"
)

print(
    f"Test Balanced Accuracy   : "
    f"{test_balanced:.2f}%"
)

print(
    f"Precision                : "
    f"{precision:.2f}%"
)

print(
    f"Recall                   : "
    f"{recall:.2f}%"
)

print(
    f"F1 Score                 : "
    f"{f1:.2f}%"
)

print("\nConfusion Matrix:")
print(cm)

print("\nTest Predictions:")
print(
    pd.Series(test_pred).value_counts()
)

# ============================================================
# SAVE FINAL MODEL
# ============================================================

final_model_path = (
    f"{MODEL_DIR}/"
    "heart_stroke_quantum_final_validation.pth"
)

torch.save(
    model.state_dict(),
    final_model_path
)

# ============================================================
# SAVE RESULTS
# ============================================================

results_df = pd.DataFrame({
    "actual": y_test_np,
    "probability": test_prob,
    "prediction": test_pred
})

results_path = (
    f"{RESULT_DIR}/"
    "heart_stroke_final_validation.csv"
)

results_df.to_csv(
    results_path,
    index=False
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
    f"{RESULT_DIR}/"
    "heart_stroke_confusion_matrix.csv"
)

cm_df.to_csv(cm_path)

# ============================================================
# SAVE TEST PREDICTIONS
# ============================================================

pred_path = (
    f"{RESULT_DIR}/"
    "heart_stroke_test_predictions.csv"
)

pd.DataFrame({
    "actual": y_test_np,
    "prediction": test_pred,
    "probability": test_prob
}).to_csv(
    pred_path,
    index=False
)

# ============================================================
# LOSS GRAPH
# ============================================================

plt.figure(figsize=(9, 5))

plt.plot(
    range(1, len(train_losses) + 1),
    train_losses,
    label="Training Loss"
)

plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.title("Heart Stroke Training Loss")
plt.legend()
plt.grid(True, alpha=0.3)

loss_path = (
    f"{GRAPH_DIR}/"
    "heart_stroke_validation_loss.png"
)

plt.savefig(
    loss_path,
    dpi=150,
    bbox_inches="tight"
)

plt.close()

# ============================================================
# ACCURACY GRAPH
# ============================================================

plt.figure(figsize=(9, 5))

plt.plot(
    range(1, len(val_accuracies) + 1),
    val_accuracies,
    label="Validation Accuracy"
)

plt.xlabel("Epoch")
plt.ylabel("Accuracy (%)")
plt.title("Heart Stroke Validation Accuracy")
plt.legend()
plt.grid(True, alpha=0.3)

accuracy_path = (
    f"{GRAPH_DIR}/"
    "heart_stroke_validation_accuracy.png"
)

plt.savefig(
    accuracy_path,
    dpi=150,
    bbox_inches="tight"
)

plt.close()

# ============================================================
# F1 GRAPH
# ============================================================

plt.figure(figsize=(9, 5))

plt.plot(
    range(1, len(val_f1s) + 1),
    val_f1s,
    label="Validation F1"
)

plt.xlabel("Epoch")
plt.ylabel("F1 (%)")
plt.title("Heart Stroke Validation F1")
plt.legend()
plt.grid(True, alpha=0.3)

f1_path = (
    f"{GRAPH_DIR}/"
    "heart_stroke_validation_f1.png"
)

plt.savefig(
    f1_path,
    dpi=150,
    bbox_inches="tight"
)

plt.close()

# ============================================================
# FINAL
# ============================================================

print("\nQuantum Model Saved Successfully.")
print("Saved To:", final_model_path)

print("Results Saved:", results_path)
print("Confusion Matrix Saved:", cm_path)
print("Test Predictions Saved:", pred_path)

print("Loss Graph Saved:", loss_path)
print("Accuracy Graph Saved:", accuracy_path)
print("F1 Graph Saved:", f1_path)

print("\n" + "=" * 70)
print("HEART STROKE FINAL VALIDATION COMPLETED")
print("=" * 70)