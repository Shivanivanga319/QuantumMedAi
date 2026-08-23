# ================================================================
# QUANTUM MED AI
# LIVER CANCER - LEAKAGE SAFE HYBRID QUANTUM V3
# ================================================================
#
# Dataset:
# D:\QuantumMedAi\datasets\liver_cancer.csv
#
# Features:
# - TRAIN-only preprocessing
# - TRAIN-only feature selection
# - TRAIN-only SMOTE
# - Classical neural network
# - PennyLane quantum layer
# - Residual fusion
# - Strict float32 enforcement
# - Validation-only model selection
# - Validation-only threshold selection
# - Test NEVER used for tuning
#
# ================================================================

import os
import random
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

import torch
import torch.nn as nn
import torch.nn.functional as F

from torch.utils.data import DataLoader, TensorDataset

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, mutual_info_classif
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

from imblearn.over_sampling import SMOTE

import pennylane as qml


# ================================================================
# CONFIGURATION
# ================================================================

SEED = 42

DATASET_PATH = r"D:\QuantumMedAi\datasets\liver_cancer.csv"

MODEL_PATH = (
    r"D:\QuantumMedAi\saved_models\quantum\liver_cancer"
    r"\hybrid_v3_final.pth"
)

RESULT_DIR = (
    r"D:\QuantumMedAi\results\liver_cancer"
    r"\hybrid_v3"
)

RESULT_PATH = os.path.join(
    RESULT_DIR,
    "results.csv"
)

CONFUSION_PATH = os.path.join(
    RESULT_DIR,
    "confusion_matrix.csv"
)

PREDICTIONS_PATH = os.path.join(
    RESULT_DIR,
    "predictions.csv"
)

REPORT_PATH = os.path.join(
    RESULT_DIR,
    "classification_report.txt"
)

os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)


# ================================================================
# REPRODUCIBILITY
# ================================================================

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False


# ================================================================
# DEVICE
# ================================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 70)
print("HYBRID QUANTUM + CLASSICAL LIVER CANCER V3")
print("=" * 70)

print("\nDevice:", DEVICE)
print("Quantum Available: True")


# ================================================================
# LOAD DATA
# ================================================================

print("\nDataset:", DATASET_PATH)

df = pd.read_csv(DATASET_PATH)

print("\nOriginal Shape:", df.shape)

duplicate_rows = df.duplicated().sum()

print("Duplicate Rows:", duplicate_rows)

df = df.drop_duplicates().reset_index(drop=True)

print("After duplicates:", df.shape)


# ================================================================
# TARGET
# ================================================================

TARGET = "Class"

if TARGET not in df.columns:
    raise ValueError(
        f"Target column '{TARGET}' not found."
    )

print("\nTarget Column:", TARGET)


# ================================================================
# REMOVE DUPLICATE COLUMNS
# ================================================================

feature_df = df.drop(columns=[TARGET])

duplicate_feature_columns = (
    feature_df.T.duplicated()
)

duplicate_columns = list(
    feature_df.columns[duplicate_feature_columns]
)

print(
    "Duplicate feature columns:",
    duplicate_columns if duplicate_columns else "None"
)

if duplicate_columns:
    feature_df = feature_df.drop(
        columns=duplicate_columns
    )


# ================================================================
# TARGET LEAKAGE CHECK
# ================================================================

leakage_columns = []

for col in feature_df.columns:

    try:

        if np.array_equal(
            pd.to_numeric(
                feature_df[col],
                errors="coerce"
            ).fillna(-999).values,

            pd.to_numeric(
                df[TARGET],
                errors="coerce"
            ).fillna(-999).values
        ):
            leakage_columns.append(col)

    except Exception:
        pass

print(
    "Features exactly equal to target:",
    leakage_columns if leakage_columns else "None"
)

if leakage_columns:
    feature_df = feature_df.drop(
        columns=leakage_columns
    )


# ================================================================
# NUMERIC FEATURES
# ================================================================

numeric_df = feature_df.apply(
    pd.to_numeric,
    errors="coerce"
)

print(
    "\nNumeric Features:",
    numeric_df.shape[1]
)


# ================================================================
# TARGET
# ================================================================

y = pd.to_numeric(
    df[TARGET],
    errors="coerce"
)

valid_rows = y.notna()

numeric_df = numeric_df.loc[
    valid_rows
].reset_index(drop=True)

y = y.loc[
    valid_rows
].astype(np.int64).reset_index(drop=True)


# ================================================================
# MISSING VALUES
# ================================================================

numeric_df = numeric_df.replace(
    [np.inf, -np.inf],
    np.nan
)


# ================================================================
# TRAIN / VALIDATION / TEST
# ================================================================

X_train_raw, X_temp_raw, y_train, y_temp = (
    train_test_split(
        numeric_df,
        y,
        test_size=0.40,
        stratify=y,
        random_state=SEED
    )
)

X_val_raw, X_test_raw, y_val, y_test = (
    train_test_split(
        X_temp_raw,
        y_temp,
        test_size=0.50,
        stratify=y_temp,
        random_state=SEED
    )
)


print("\nTraining:", X_train_raw.shape)
print("Validation:", X_val_raw.shape)
print("Test:", X_test_raw.shape)


print("\nTraining Distribution:")
print(y_train.value_counts().sort_index())

print("\nValidation Distribution:")
print(y_val.value_counts().sort_index())

print("\nTest Distribution:")
print(y_test.value_counts().sort_index())


# ================================================================
# TRAIN-ONLY MEDIAN IMPUTATION
# ================================================================

train_medians = X_train_raw.median()

X_train = X_train_raw.fillna(train_medians)
X_val = X_val_raw.fillna(train_medians)
X_test = X_test_raw.fillna(train_medians)


# ================================================================
# REMOVE CONSTANT FEATURES - TRAIN ONLY
# ================================================================

train_variance = X_train.var()

keep_columns = train_variance[
    train_variance > 1e-12
].index

X_train = X_train[
    keep_columns
]

X_val = X_val[
    keep_columns
]

X_test = X_test[
    keep_columns
]

print(
    "\nFeatures after constant removal:",
    len(keep_columns)
)


# ================================================================
# TRAIN-ONLY FEATURE SELECTION
# ================================================================

K_FEATURES = min(
    12,
    X_train.shape[1]
)

selector = SelectKBest(
    score_func=mutual_info_classif,
    k=K_FEATURES
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

selected_features = list(
    X_train.columns[
        selector.get_support()
    ]
)

print(
    "\nFeatures before:",
    X_train.shape[1]
)

print(
    "Features selected:",
    len(selected_features)
)

print("\nSelected features:")

for i, feature in enumerate(
    selected_features,
    1
):
    print(
        f"{i:02d}. {feature}"
    )


# ================================================================
# TRAIN-ONLY STANDARDIZATION
# ================================================================

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


# ================================================================
# TRAIN-ONLY SMOTE
# ================================================================

class_counts = np.bincount(
    np.asarray(y_train)
)

minority_count = class_counts.min()

smote_k = min(
    5,
    max(1, minority_count - 1)
)

print(
    "\nBefore SMOTE:",
    dict(
        enumerate(
            class_counts
        )
    )
)

print(
    "SMOTE k_neighbors:",
    smote_k
)

smote = SMOTE(
    random_state=SEED,
    k_neighbors=smote_k
)

X_train_balanced, y_train_balanced = (
    smote.fit_resample(
        X_train_scaled,
        y_train
    )
)

print(
    "After SMOTE:",
    dict(
        zip(
            *np.unique(
                y_train_balanced,
                return_counts=True
            )
        )
    )
)


# ================================================================
# STRICT FLOAT32
# ================================================================

X_train_balanced = np.asarray(
    X_train_balanced,
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

print("\nFinal NumPy dtypes:")
print(
    "X_train:",
    X_train_balanced.dtype
)

print(
    "X_val:",
    X_val_scaled.dtype
)

print(
    "X_test:",
    X_test_scaled.dtype
)


# ================================================================
# TENSORS
# ================================================================

X_train_tensor = torch.tensor(
    X_train_balanced,
    dtype=torch.float32,
    device=DEVICE
)

X_val_tensor = torch.tensor(
    X_val_scaled,
    dtype=torch.float32,
    device=DEVICE
)

X_test_tensor = torch.tensor(
    X_test_scaled,
    dtype=torch.float32,
    device=DEVICE
)

y_train_tensor = torch.tensor(
    y_train_balanced,
    dtype=torch.long,
    device=DEVICE
)

y_val_tensor = torch.tensor(
    y_val,
    dtype=torch.long,
    device=DEVICE
)

y_test_tensor = torch.tensor(
    y_test,
    dtype=torch.long,
    device=DEVICE
)

print("\nFinal Tensor dtypes:")
print(
    "X_train:",
    X_train_tensor.dtype
)

print(
    "X_val:",
    X_val_tensor.dtype
)

print(
    "X_test:",
    X_test_tensor.dtype
)


# ================================================================
# DATA LOADER
# ================================================================

train_dataset = TensorDataset(
    X_train_tensor,
    y_train_tensor
)

train_loader = DataLoader(
    train_dataset,
    batch_size=16,
    shuffle=True,
    drop_last=False
)


# ================================================================
# QUANTUM CONFIG
# ================================================================

N_FEATURES = X_train_tensor.shape[1]

N_QUBITS = 4

N_Q_LAYERS = 3

print(
    "\nInput Features:",
    N_FEATURES
)

print(
    "Quantum Qubits:",
    N_QUBITS
)

print(
    "Quantum Layers:",
    N_Q_LAYERS
)

print(
    "Architecture:",
    "Classical + Quantum + Residual Fusion"
)


# ================================================================
# QUANTUM DEVICE
# ================================================================

qdev = qml.device(
    "default.qubit",
    wires=N_QUBITS
)


# ================================================================
# QUANTUM CIRCUIT
# ================================================================

@qml.qnode(qdev, interface="torch")
def quantum_circuit(inputs, weights):

    # Angle embedding
    qml.AngleEmbedding(
        inputs,
        wires=range(N_QUBITS),
        rotation="Y"
    )

    for layer in range(N_Q_LAYERS):

        for q in range(N_QUBITS):

            qml.RY(
                weights[
                    layer,
                    q,
                    0
                ],
                wires=q
            )

            qml.RZ(
                weights[
                    layer,
                    q,
                    1
                ],
                wires=q
            )

        # Ring entanglement
        for q in range(
            N_QUBITS - 1
        ):

            qml.CNOT(
                wires=[q, q + 1]
            )

        qml.CNOT(
            wires=[
                N_QUBITS - 1,
                0
            ]
        )

    return [
        qml.expval(
            qml.PauliZ(q)
        )
        for q in range(N_QUBITS)
    ]


# ================================================================
# QUANTUM LAYER
# ================================================================

class QuantumLayer(
    nn.Module
):

    def __init__(self):

        super().__init__()

        self.weights = nn.Parameter(
            0.05
            * torch.randn(
                N_Q_LAYERS,
                N_QUBITS,
                2,
                dtype=torch.float32
            )
        )

    def forward(
        self,
        x
    ):

        # ABSOLUTE FLOAT32 SAFETY
        x = x.to(
            dtype=torch.float32
        )

        self.weights.data = (
            self.weights.data.to(
                dtype=torch.float32
            )
        )

        outputs = []

        for sample in x:

            sample = sample.to(
                dtype=torch.float32
            )

            q_input = sample[
                :N_QUBITS
            ]

            q_input = torch.tanh(
                q_input
            )

            q_input = q_input * np.pi

            result = quantum_circuit(
                q_input,
                self.weights
            )

            result = torch.stack(
                [
                    r.to(
                        dtype=torch.float32
                    )
                    for r in result
                ]
            )

            outputs.append(result)

        return torch.stack(
            outputs
        ).to(
            dtype=torch.float32
        )


# ================================================================
# HYBRID MODEL
# ================================================================

class HybridQuantumModel(
    nn.Module
):

    def __init__(
        self,
        input_features
    ):

        super().__init__()

        # --------------------------------------------------------
        # Classical encoder
        # --------------------------------------------------------

        self.classical = nn.Sequential(

            nn.Linear(
                input_features,
                32
            ),

            nn.BatchNorm1d(
                32
            ),

            nn.GELU(),

            nn.Dropout(
                0.15
            ),

            nn.Linear(
                32,
                16
            ),

            nn.GELU()
        )

        # --------------------------------------------------------
        # Quantum projection
        # --------------------------------------------------------

        self.quantum_projection = nn.Sequential(

            nn.Linear(
                16,
                N_QUBITS
            ),

            nn.Tanh()
        )

        # --------------------------------------------------------
        # Quantum layer
        # --------------------------------------------------------

        self.quantum = QuantumLayer()

        # --------------------------------------------------------
        # Classical residual branch
        # --------------------------------------------------------

        self.residual = nn.Sequential(

            nn.Linear(
                input_features,
                16
            ),

            nn.GELU(),

            nn.Dropout(
                0.10
            )
        )

        # --------------------------------------------------------
        # Fusion
        # --------------------------------------------------------

        self.fusion = nn.Sequential(

            nn.Linear(
                16 + N_QUBITS + 16,
                32
            ),

            nn.LayerNorm(
                32
            ),

            nn.GELU(),

            nn.Dropout(
                0.15
            ),

            nn.Linear(
                32,
                16
            ),

            nn.GELU(),

            nn.Linear(
                16,
                2
            )
        )

    def forward(
        self,
        x
    ):

        # ========================================================
        # CRITICAL DTYPE FIX
        # ========================================================

        x = x.to(
            dtype=torch.float32
        )

        classical = self.classical(
            x
        )

        classical = classical.to(
            dtype=torch.float32
        )

        q_input = self.quantum_projection(
            classical
        )

        q_input = q_input.to(
            dtype=torch.float32
        )

        quantum = self.quantum(
            q_input
        )

        quantum = quantum.to(
            dtype=torch.float32
        )

        residual = self.residual(
            x
        )

        residual = residual.to(
            dtype=torch.float32
        )

        fused = torch.cat(
            [
                classical,
                quantum,
                residual
            ],
            dim=1
        )

        # ========================================================
        # SECOND DTYPE SAFETY CHECK
        # ========================================================

        fused = fused.to(
            dtype=torch.float32
        )

        logits = self.fusion(
            fused
        )

        return logits.to(
            dtype=torch.float32
        )


# ================================================================
# MODEL
# ================================================================

model = HybridQuantumModel(
    N_FEATURES
).to(
    DEVICE
)

# ABSOLUTE MODEL FLOAT32
model = model.float()

print(
    "\nModel dtype:",
    next(
        model.parameters()
    ).dtype
)


# ================================================================
# CLASS WEIGHTS
# ================================================================

original_class_counts = np.bincount(
    np.asarray(y_train)
)

total_train = original_class_counts.sum()

class_weights = (
    total_train
    /
    (
        len(original_class_counts)
        * original_class_counts
    )
)

class_weights = (
    torch.tensor(
        class_weights,
        dtype=torch.float32,
        device=DEVICE
    )
)

print(
    "Class weights:",
    class_weights.cpu().numpy()
)


# ================================================================
# LOSS
# ================================================================

criterion = nn.CrossEntropyLoss(
    weight=class_weights,
    label_smoothing=0.03
)


# ================================================================
# OPTIMIZER
# ================================================================

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=6e-4,
    weight_decay=2e-4
)


# ================================================================
# SCHEDULER
# ================================================================

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="max",
    factor=0.5,
    patience=8,
    min_lr=5e-5
)


# ================================================================
# METRIC FUNCTION
# ================================================================

def validation_metrics(
    probabilities,
    y_true,
    threshold=0.5
):

    predictions = (
        probabilities >= threshold
    ).astype(int)

    acc = accuracy_score(
        y_true,
        predictions
    )

    balanced = balanced_accuracy_score(
        y_true,
        predictions
    )

    macro_f1 = f1_score(
        y_true,
        predictions,
        average="macro",
        zero_division=0
    )

    combined = (
        0.40 * balanced
        +
        0.60 * macro_f1
    )

    return (
        acc,
        balanced,
        macro_f1,
        combined
    )


# ================================================================
# TRAINING CONFIG
# ================================================================

EPOCHS = 5

PATIENCE = 30

best_combined = -np.inf

best_epoch = 0

patience_counter = 0

best_state = None

history = []


# ================================================================
# TRAINING
# ================================================================

for epoch in range(
    1,
    EPOCHS + 1
):

    model.train()

    running_loss = 0.0

    correct = 0

    total = 0

    for batch_x, batch_y in train_loader:

        # --------------------------------------------------------
        # STRICT FLOAT32
        # --------------------------------------------------------

        batch_x = batch_x.to(
            DEVICE,
            dtype=torch.float32
        )

        batch_y = batch_y.to(
            DEVICE,
            dtype=torch.long
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        logits = model(
            batch_x
        )

        logits = logits.to(
            dtype=torch.float32
        )

        loss = criterion(
            logits,
            batch_y
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0
        )

        optimizer.step()

        running_loss += (
            loss.item()
            * batch_x.size(0)
        )

        predictions = (
            logits.argmax(
                dim=1
            )
        )

        correct += (
            predictions
            ==
            batch_y
        ).sum().item()

        total += batch_y.size(0)

    train_loss = (
        running_loss
        /
        total
    )

    train_accuracy = (
        correct
        /
        total
    )


    # ============================================================
    # VALIDATION
    # ============================================================

    model.eval()

    with torch.no_grad():

        val_logits = model(
            X_val_tensor.to(
                dtype=torch.float32
            )
        )

        val_logits = val_logits.to(
            dtype=torch.float32
        )

        val_probabilities = torch.softmax(
            val_logits,
            dim=1
        )[:, 1]

        val_probabilities = (
            val_probabilities
            .detach()
            .cpu()
            .numpy()
        )


    (
        val_accuracy,
        val_balanced,
        val_macro_f1,
        val_combined
    ) = validation_metrics(
        val_probabilities,
        y_val,
        threshold=0.5
    )


    # ============================================================
    # LR SCHEDULER
    # ============================================================

    scheduler.step(
        val_combined
    )

    current_lr = optimizer.param_groups[
        0
    ]["lr"]


    # ============================================================
    # LOG
    # ============================================================

    print(
        f"Epoch [{epoch:03d}/{EPOCHS}] "
        f"Loss: {train_loss:.4f} "
        f"Train Acc: {train_accuracy*100:.2f}% "
        f"Val Acc: {val_accuracy*100:.2f}% "
        f"Balanced: {val_balanced*100:.2f}% "
        f"Macro-F1: {val_macro_f1*100:.2f}% "
        f"Combined: {val_combined*100:.2f}% "
        f"LR: {current_lr:.7f}"
    )


    history.append(
        {
            "epoch": epoch,
            "loss": train_loss,
            "train_accuracy":
                train_accuracy,
            "val_accuracy":
                val_accuracy,
            "val_balanced":
                val_balanced,
            "val_macro_f1":
                val_macro_f1,
            "val_combined":
                val_combined,
            "lr":
                current_lr
        }
    )


    # ============================================================
    # BEST MODEL
    # ============================================================

    if (
        val_combined
        >
        best_combined
        +
        1e-4
    ):

        best_combined = (
            val_combined
        )

        best_epoch = epoch

        patience_counter = 0

        best_state = {
            key: value.detach()
            .cpu()
            .clone()
            for key, value
            in model.state_dict().items()
        }

        print(
            "--> Best hybrid quantum model saved"
        )

    else:

        patience_counter += 1

        print(
            f"Patience: "
            f"{patience_counter}/{PATIENCE}"
        )


    if patience_counter >= PATIENCE:

        print(
            f"\nEarly stopping at epoch {epoch}"
        )

        break


# ================================================================
# RESTORE BEST MODEL
# ================================================================

if best_state is None:

    raise RuntimeError(
        "No best model was saved."
    )

model.load_state_dict(
    best_state
)

model = model.float()

model.eval()


# ================================================================
# VALIDATION THRESHOLD SELECTION
# ================================================================

with torch.no_grad():

    val_logits = model(
        X_val_tensor.to(
            dtype=torch.float32
        )
    )

    val_probabilities = torch.softmax(
        val_logits,
        dim=1
    )[:, 1]

    val_probabilities = (
        val_probabilities
        .detach()
        .cpu()
        .numpy()
    )


thresholds = np.arange(
    0.30,
    0.71,
    0.01
)

best_threshold = 0.50

best_threshold_score = -np.inf

for threshold in thresholds:

    (
        acc,
        balanced,
        macro_f1,
        combined
    ) = validation_metrics(
        val_probabilities,
        y_val,
        threshold
    )

    if combined > best_threshold_score:

        best_threshold_score = (
            combined
        )

        best_threshold = float(
            threshold
        )


print(
    "\nBest Epoch:",
    best_epoch
)

print(
    f"Best Validation Combined: "
    f"{best_combined*100:.2f}%"
)

print(
    f"Selected Validation Threshold: "
    f"{best_threshold:.2f}"
)


# ================================================================
# TEST
# ================================================================

with torch.no_grad():

    test_logits = model(
        X_test_tensor.to(
            dtype=torch.float32
        )
    )

    test_logits = test_logits.to(
        dtype=torch.float32
    )

    test_probabilities = torch.softmax(
        test_logits,
        dim=1
    )[:, 1]

    test_probabilities = (
        test_probabilities
        .detach()
        .cpu()
        .numpy()
    )


test_predictions = (
    test_probabilities
    >= best_threshold
).astype(int)


# ================================================================
# TEST METRICS
# ================================================================

test_accuracy = accuracy_score(
    y_test,
    test_predictions
)

test_balanced = balanced_accuracy_score(
    y_test,
    test_predictions
)

macro_precision = precision_score(
    y_test,
    test_predictions,
    average="macro",
    zero_division=0
)

macro_recall = recall_score(
    y_test,
    test_predictions,
    average="macro",
    zero_division=0
)

macro_f1 = f1_score(
    y_test,
    test_predictions,
    average="macro",
    zero_division=0
)

weighted_f1 = f1_score(
    y_test,
    test_predictions,
    average="weighted",
    zero_division=0
)

try:

    roc_auc = roc_auc_score(
        y_test,
        test_probabilities
    )

except Exception:

    roc_auc = float("nan")


# ================================================================
# CONFUSION MATRIX
# ================================================================

cm = confusion_matrix(
    y_test,
    test_predictions
)


# ================================================================
# REPORT
# ================================================================

report = classification_report(
    y_test,
    test_predictions,
    zero_division=0
)


print("\n" + "=" * 70)

print("FINAL TEST RESULTS")

print("=" * 70)

print(
    f"\nTest Accuracy: "
    f"{test_accuracy*100:.2f}%"
)

print(
    f"Test Balanced Accuracy: "
    f"{test_balanced*100:.2f}%"
)

print(
    f"Macro Precision: "
    f"{macro_precision*100:.2f}%"
)

print(
    f"Macro Recall: "
    f"{macro_recall*100:.2f}%"
)

print(
    f"Macro F1: "
    f"{macro_f1*100:.2f}%"
)

print(
    f"Weighted F1: "
    f"{weighted_f1*100:.2f}%"
)

print(
    f"ROC-AUC: "
    f"{roc_auc*100:.2f}%"
)

print("\nConfusion Matrix:")

print(cm)

print("\nClassification Report:")

print(report)


# ================================================================
# PREDICTION DISTRIBUTION
# ================================================================

prediction_counts = pd.Series(
    test_predictions
).value_counts().sort_index()

print("\nTest Predictions:")

print(prediction_counts)

if len(
    prediction_counts
) == 2:

    print(
        "\nSUCCESS: Both classes were predicted."
    )

else:

    print(
        "\nWARNING: Only one class was predicted."
    )


# ================================================================
# SAVE MODEL
# ================================================================

checkpoint = {

    "model_state_dict":
        model.state_dict(),

    "input_features":
        N_FEATURES,

    "selected_features":
        selected_features,

    "n_qubits":
        N_QUBITS,

    "quantum_layers":
        N_Q_LAYERS,

    "threshold":
        best_threshold,

    "best_epoch":
        best_epoch,

    "best_validation_combined":
        best_combined,

    "scaler":
        scaler,

    "selector":
        selector,

    "train_medians":
        train_medians,

    "seed":
        SEED
}

torch.save(
    checkpoint,
    MODEL_PATH
)


# ================================================================
# SAVE RESULTS
# ================================================================

results_df = pd.DataFrame(
    {
        "metric": [
            "test_accuracy",
            "test_balanced_accuracy",
            "macro_precision",
            "macro_recall",
            "macro_f1",
            "weighted_f1",
            "roc_auc",
            "best_epoch",
            "best_validation_combined",
            "threshold"
        ],

        "value": [
            test_accuracy,
            test_balanced,
            macro_precision,
            macro_recall,
            macro_f1,
            weighted_f1,
            roc_auc,
            best_epoch,
            best_combined,
            best_threshold
        ]
    }
)

results_df.to_csv(
    RESULT_PATH,
    index=False
)


# ================================================================
# SAVE CONFUSION MATRIX
# ================================================================

pd.DataFrame(
    cm,
    index=[
        "Actual_0",
        "Actual_1"
    ],
    columns=[
        "Predicted_0",
        "Predicted_1"
    ]
).to_csv(
    CONFUSION_PATH
)


# ================================================================
# SAVE PREDICTIONS
# ================================================================

pd.DataFrame(
    {
        "actual": y_test,
        "probability_class_1":
            test_probabilities,
        "prediction":
            test_predictions
    }
).to_csv(
    PREDICTIONS_PATH,
    index=False
)


# ================================================================
# SAVE REPORT
# ================================================================

with open(
    REPORT_PATH,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "HYBRID QUANTUM V3\n"
    )

    f.write(
        "=================\n\n"
    )

    f.write(
        f"Best Epoch: "
        f"{best_epoch}\n"
    )

    f.write(
        f"Best Validation Combined: "
        f"{best_combined*100:.2f}%\n"
    )

    f.write(
        f"Selected Threshold: "
        f"{best_threshold:.2f}\n\n"
    )

    f.write(
        f"Test Accuracy: "
        f"{test_accuracy*100:.2f}%\n"
    )

    f.write(
        f"Balanced Accuracy: "
        f"{test_balanced*100:.2f}%\n"
    )

    f.write(
        f"Macro Precision: "
        f"{macro_precision*100:.2f}%\n"
    )

    f.write(
        f"Macro Recall: "
        f"{macro_recall*100:.2f}%\n"
    )

    f.write(
        f"Macro F1: "
        f"{macro_f1*100:.2f}%\n"
    )

    f.write(
        f"Weighted F1: "
        f"{weighted_f1*100:.2f}%\n"
    )

    f.write(
        f"ROC-AUC: "
        f"{roc_auc*100:.2f}%\n\n"
    )

    f.write(
        "Confusion Matrix:\n"
    )

    f.write(
        str(cm)
    )

    f.write(
        "\n\nClassification Report:\n"
    )

    f.write(report)


# ================================================================
# SAVE TRAINING HISTORY
# ================================================================

history_path = os.path.join(
    RESULT_DIR,
    "training_history.csv"
)

pd.DataFrame(
    history
).to_csv(
    history_path,
    index=False
)


# ================================================================
# LEAKAGE AUDIT
# ================================================================

print(
    "\n" + "=" * 70
)

print("LEAKAGE AUDIT")

print("=" * 70)

print(
    "Preprocessing fitted on: TRAIN ONLY"
)

print(
    "Feature selection fitted on: TRAIN ONLY"
)

print(
    "Scaler fitted on: TRAIN ONLY"
)

print(
    "SMOTE applied to: TRAIN ONLY"
)

print(
    "Validation used for model selection: YES"
)

print(
    "Threshold selected from: VALIDATION ONLY"
)

print(
    "Test used for tuning: NO"
)

print(
    "\nStrict dtype protection:"
)

print(
    "All model inputs: torch.float32"
)

print(
    "All model parameters: torch.float32"
)

print(
    "Quantum outputs: torch.float32"
)

print(
    "Fusion input: torch.float32"
)


# ================================================================
# FINAL PATHS
# ================================================================

print(
    "\n" + "=" * 70
)

print(
    "Hybrid Quantum Model Saved:"
)

print(
    MODEL_PATH
)

print(
    "\nResults Saved:"
)

print(
    RESULT_PATH
)

print(
    "\nConfusion Matrix Saved:"
)

print(
    CONFUSION_PATH
)

print(
    "\nTest Predictions Saved:"
)

print(
    PREDICTIONS_PATH
)

print(
    "\nClassification Report Saved:"
)

print(
    REPORT_PATH
)

print(
    "\nTraining History Saved:"
)

print(
    history_path
)

print(
    "\nTraining completed successfully."
)

print("=" * 70)