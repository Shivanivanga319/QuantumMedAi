import os
import random
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ============================================================
# PYTORCH
# ============================================================
import torch
import torch.nn as nn
import torch.optim as optim

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
    classification_report
)

from imblearn.over_sampling import SMOTE

# ============================================================
# PENNYLANE
# ============================================================
import pennylane as qml


# ============================================================
# CONFIG
# ============================================================

SEED = 42

DATASET_PATH = r"D:\QuantumMedAi\datasets\kidney_infection.csv"

MODEL_DIR = (
    r"D:\QuantumMedAi\saved_models\quantum"
    r"\kidney_infection\hybrid_v4"
)

RESULT_DIR = (
    r"D:\QuantumMedAi\results"
    r"\kidney_infection\hybrid_v4"
)

TARGET = "Nephritis of renal pelvis origin"

N_QUBITS = 4
N_Q_LAYERS = 3

EPOCHS = 30
PATIENCE_LIMIT = 30

TOP_FEATURES = 6

LR = 0.0006
WEIGHT_DECAY = 1e-4

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)


# ============================================================
# SEED
# ============================================================

def set_seed(seed=42):

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


set_seed(SEED)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 70)
print("HYBRID QUANTUM + CLASSICAL KIDNEY INFECTION TRAINING")
print("=" * 70)

print("\nDevice:", DEVICE)
print("Quantum Available: True")
print("Dataset:", DATASET_PATH)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(DATASET_PATH)

print("\nOriginal Shape:", df.shape)

# Remove exact duplicate rows
duplicate_count = df.duplicated().sum()

print("Duplicate Rows:", duplicate_count)

df = df.drop_duplicates().reset_index(drop=True)

print("After duplicates:", df.shape)


# ============================================================
# TARGET CHECK
# ============================================================

if TARGET not in df.columns:
    raise ValueError(
        f"Target column '{TARGET}' not found.\n"
        f"Available columns:\n{df.columns.tolist()}"
    )

print("\nTarget Column:", TARGET)


# ============================================================
# TARGET ENCODING
# ============================================================

target_values = (
    df[TARGET]
    .astype(str)
    .str.strip()
    .str.lower()
)

print("\nTarget Distribution:")
print(target_values.value_counts())


# no / yes -> 0 / 1
unique_target = sorted(target_values.unique())

print("\nTarget Classes:", unique_target)

if set(unique_target) == {"no", "yes"}:

    y = target_values.map({
        "no": 0,
        "yes": 1
    }).astype(np.int64)

else:

    # Generic binary encoding
    if len(unique_target) != 2:
        raise ValueError(
            "Target must contain exactly 2 classes."
        )

    mapping = {
        unique_target[0]: 0,
        unique_target[1]: 1
    }

    print("Target Mapping:", mapping)

    y = target_values.map(mapping).astype(np.int64)


# ============================================================
# FEATURE ENCODING
# ============================================================

X_df = df.drop(columns=[TARGET]).copy()

print("\nFeature Columns:")
for c in X_df.columns:
    print(" -", c)


# Convert categorical yes/no columns
for col in X_df.columns:

    if X_df[col].dtype == object:

        values = (
            X_df[col]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        unique = set(values.unique())

        if unique.issubset({"yes", "no"}):

            X_df[col] = values.map({
                "no": 0.0,
                "yes": 1.0
            })

        else:

            # Safe category encoding
            categories = {
                value: idx
                for idx, value
                in enumerate(sorted(unique))
            }

            X_df[col] = values.map(categories)


# ============================================================
# NUMERIC CONVERSION
# ============================================================

X_df = X_df.apply(
    pd.to_numeric,
    errors="coerce"
)

# Missing values handled using TRAIN ONLY later.
print("\nNumeric Features:", X_df.shape[1])


# ============================================================
# REMOVE CONSTANT FEATURES
# ============================================================

constant_columns = [
    c for c in X_df.columns
    if X_df[c].nunique(dropna=False) <= 1
]

if constant_columns:

    print(
        "\nRemoving constant features:",
        constant_columns
    )

    X_df = X_df.drop(
        columns=constant_columns
    )

print(
    "Features after constant removal:",
    X_df.shape[1]
)


# ============================================================
# NUMPY
# ============================================================

X = X_df.to_numpy(
    dtype=np.float32
)

y = y.to_numpy(
    dtype=np.int64
)


# ============================================================
# TRAIN / VALIDATION / TEST
# ============================================================

indices = np.arange(len(y))

train_idx, temp_idx = train_test_split(
    indices,
    test_size=0.40,
    stratify=y,
    random_state=SEED
)

val_idx, test_idx = train_test_split(
    temp_idx,
    test_size=0.50,
    stratify=y[temp_idx],
    random_state=SEED
)

X_train = X[train_idx]
X_val = X[val_idx]
X_test = X[test_idx]

y_train = y[train_idx]
y_val = y[val_idx]
y_test = y[test_idx]


print("\nTraining:", X_train.shape)
print("Validation:", X_val.shape)
print("Test:", X_test.shape)

print("\nTraining Distribution:")
print(pd.Series(y_train).value_counts().sort_index())

print("\nValidation Distribution:")
print(pd.Series(y_val).value_counts().sort_index())

print("\nTest Distribution:")
print(pd.Series(y_test).value_counts().sort_index())


# ============================================================
# IMPUTE MISSING VALUES - TRAIN ONLY
# ============================================================

train_medians = np.nanmedian(
    X_train,
    axis=0
)

train_medians = np.where(
    np.isfinite(train_medians),
    train_medians,
    0.0
).astype(np.float32)


def fill_missing(X_input):

    X_copy = X_input.copy()

    for j in range(X_copy.shape[1]):

        mask = ~np.isfinite(
            X_copy[:, j]
        )

        X_copy[mask, j] = train_medians[j]

    return X_copy.astype(np.float32)


X_train = fill_missing(X_train)
X_val = fill_missing(X_val)
X_test = fill_missing(X_test)


# ============================================================
# FEATURE SELECTION - TRAIN ONLY
# ============================================================

k = min(
    TOP_FEATURES,
    X_train.shape[1]
)

selector = SelectKBest(
    score_func=mutual_info_classif,
    k=k
)

X_train = selector.fit_transform(
    X_train,
    y_train
).astype(np.float32)

X_val = selector.transform(
    X_val
).astype(np.float32)

X_test = selector.transform(
    X_test
).astype(np.float32)


selected_columns = [
    col
    for col, selected
    in zip(
        X_df.columns,
        selector.get_support()
    )
    if selected
]

print("\nFeatures before:", X_df.shape[1])
print("Features selected:", len(selected_columns))

print("\nSelected features:")

for i, feature in enumerate(
    selected_columns,
    1
):
    print(
        f"{i:02d}. {feature}"
    )


# ============================================================
# SCALER - TRAIN ONLY
# ============================================================

scaler = StandardScaler()

X_train = scaler.fit_transform(
    X_train
).astype(np.float32)

X_val = scaler.transform(
    X_val
).astype(np.float32)

X_test = scaler.transform(
    X_test
).astype(np.float32)


# ============================================================
# SMOTE - TRAIN ONLY
# ============================================================

train_counts = np.bincount(
    y_train
)

minority_count = train_counts.min()

smote_k = max(
    1,
    min(5, minority_count - 1)
)

print("\nBefore SMOTE:")
print(
    dict(
        enumerate(
            np.bincount(y_train)
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

X_train, y_train = smote.fit_resample(
    X_train,
    y_train
)

X_train = X_train.astype(
    np.float32
)

y_train = y_train.astype(
    np.int64
)

print("\nAfter SMOTE:")
print(
    dict(
        enumerate(
            np.bincount(y_train)
        )
    )
)


# ============================================================
# STRICT FLOAT32
# ============================================================

X_train = np.asarray(
    X_train,
    dtype=np.float32
)

X_val = np.asarray(
    X_val,
    dtype=np.float32
)

X_test = np.asarray(
    X_test,
    dtype=np.float32
)


print("\nFinal NumPy dtypes:")
print("X_train:", X_train.dtype)
print("X_val:", X_val.dtype)
print("X_test:", X_test.dtype)


# ============================================================
# TENSORS
# ============================================================

X_train_t = torch.tensor(
    X_train,
    dtype=torch.float32,
    device=DEVICE
)

X_val_t = torch.tensor(
    X_val,
    dtype=torch.float32,
    device=DEVICE
)

X_test_t = torch.tensor(
    X_test,
    dtype=torch.float32,
    device=DEVICE
)

y_train_t = torch.tensor(
    y_train,
    dtype=torch.long,
    device=DEVICE
)

y_val_t = torch.tensor(
    y_val,
    dtype=torch.long,
    device=DEVICE
)

y_test_t = torch.tensor(
    y_test,
    dtype=torch.long,
    device=DEVICE
)


print("\nFinal Tensor dtypes:")
print("X_train:", X_train_t.dtype)
print("X_val:", X_val_t.dtype)
print("X_test:", X_test_t.dtype)


# ============================================================
# QUANTUM CIRCUIT
# ============================================================

dev = qml.device(
    "default.qubit",
    wires=N_QUBITS
)


@qml.qnode(
    dev,
    interface="torch",
    diff_method="backprop"
)
def quantum_circuit(inputs, weights):

    qml.AngleEmbedding(
        inputs,
        wires=range(N_QUBITS),
        rotation="Y"
    )

    qml.StronglyEntanglingLayers(
        weights,
        wires=range(N_QUBITS)
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

    def __init__(
        self,
        n_qubits=4,
        n_layers=3
    ):

        super().__init__()

        self.n_qubits = n_qubits
        self.n_layers = n_layers

        self.weights = nn.Parameter(
            0.05 * torch.randn(
                n_layers,
                n_qubits,
                3,
                dtype=torch.float32
            )
        )

    def forward(self, x):

        x = x.to(
            dtype=torch.float32
        )

        outputs = []

        for sample in x:

            q_input = sample[
                :self.n_qubits
            ]

            result = quantum_circuit(
                q_input,
                self.weights
            )

            result = torch.stack(
                result
            ).to(torch.float32)

            outputs.append(result)

        return torch.stack(
            outputs
        ).to(torch.float32)


# ============================================================
# HYBRID MODEL
# ============================================================

class HybridQuantumModel(
    nn.Module
):

    def __init__(
        self,
        input_features,
        n_qubits=4,
        n_layers=3
    ):

        super().__init__()

        self.input_features = (
            input_features
        )

        # Classical feature compression
        self.classical = nn.Sequential(

            nn.Linear(
                input_features,
                32
            ),

            nn.BatchNorm1d(32),

            nn.GELU(),

            nn.Dropout(0.20),

            nn.Linear(
                32,
                16
            ),

            nn.GELU(),

            nn.Dropout(0.10)
        )

        # Quantum input
        self.quantum_input = nn.Sequential(

            nn.Linear(
                16,
                n_qubits
            ),

            nn.Tanh()
        )

        self.quantum = QuantumLayer(
            n_qubits,
            n_layers
        )

        # Quantum projection
        self.quantum_projection = nn.Sequential(

            nn.Linear(
                n_qubits,
                8
            ),

            nn.GELU()
        )

        # Residual branch
        self.residual = nn.Sequential(

            nn.Linear(
                input_features,
                16
            ),

            nn.GELU(),

            nn.Dropout(0.10)
        )

        # Fusion
        self.fusion = nn.Sequential(

            nn.Linear(
                16 + 8 + 16,
                32
            ),

            nn.BatchNorm1d(32),

            nn.GELU(),

            nn.Dropout(0.20),

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

    def forward(self, x):

        x = x.to(
            dtype=torch.float32
        )

        classical = self.classical(x)

        q_input = self.quantum_input(
            classical
        )

        quantum = self.quantum(
            q_input
        )

        quantum = self.quantum_projection(
            quantum
        )

        residual = self.residual(x)

        combined = torch.cat(
            [
                classical,
                quantum,
                residual
            ],
            dim=1
        )

        combined = combined.to(
            dtype=torch.float32
        )

        logits = self.fusion(
            combined
        )

        return logits.to(
            dtype=torch.float32
        )


# ============================================================
# MODEL
# ============================================================

INPUT_FEATURES = X_train.shape[1]

model = HybridQuantumModel(
    input_features=INPUT_FEATURES,
    n_qubits=N_QUBITS,
    n_layers=N_Q_LAYERS
).to(
    DEVICE
)

model = model.float()

print("\nInput Features:", INPUT_FEATURES)
print("Quantum Qubits:", N_QUBITS)
print("Quantum Layers:", N_Q_LAYERS)
print(
    "Architecture:",
    "Classical + Quantum + Residual Fusion"
)

print(
    "\nModel dtype:",
    next(model.parameters()).dtype
)


# ============================================================
# CLASS WEIGHTS
# ============================================================

original_train_counts = np.bincount(
    y[train_idx]
)

class_weights = (
    len(y[train_idx])
    /
    (
        2.0
        *
        original_train_counts
    )
)

class_weights = torch.tensor(
    class_weights,
    dtype=torch.float32,
    device=DEVICE
)

print(
    "Class weights:",
    class_weights.detach()
    .cpu()
    .numpy()
)


# ============================================================
# LOSS
# ============================================================

criterion = nn.CrossEntropyLoss(
    weight=class_weights,
    label_smoothing=0.03
)


# ============================================================
# OPTIMIZER
# ============================================================

optimizer = optim.AdamW(
    model.parameters(),
    lr=LR,
    weight_decay=WEIGHT_DECAY
)


scheduler = optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="max",
    factor=0.5,
    patience=8,
    min_lr=5e-5
)


# ============================================================
# METRIC FUNCTION
# ============================================================

def evaluate(
    logits,
    labels,
    threshold=0.5
):

    probabilities = torch.softmax(
        logits,
        dim=1
    )[:, 1]

    probs = (
        probabilities
        .detach()
        .cpu()
        .numpy()
    )

    true = (
        labels
        .detach()
        .cpu()
        .numpy()
    )

    predictions = (
        probs >= threshold
    ).astype(int)

    accuracy = accuracy_score(
        true,
        predictions
    )

    balanced = balanced_accuracy_score(
        true,
        predictions
    )

    precision = precision_score(
        true,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        true,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        true,
        predictions,
        zero_division=0
    )

    return {
        "accuracy": accuracy,
        "balanced": balanced,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "probabilities": probs,
        "predictions": predictions,
        "true": true
    }


# ============================================================
# THRESHOLD SEARCH
# ============================================================

def find_best_threshold(
    probabilities,
    labels
):

    best_threshold = 0.50
    best_score = -1

    thresholds = np.arange(
        0.20,
        0.81,
        0.01
    )

    for threshold in thresholds:

        predictions = (
            probabilities >= threshold
        ).astype(int)

        score = (
            0.50
            *
            balanced_accuracy_score(
                labels,
                predictions
            )
            +
            0.50
            *
            f1_score(
                labels,
                predictions,
                zero_division=0
            )
        )

        if score > best_score:

            best_score = score
            best_threshold = threshold

    return best_threshold


# ============================================================
# TRAINING
# ============================================================

best_combined = -np.inf
best_epoch = 0
best_state = None

patience = 0

history = []

for epoch in range(
    1,
    EPOCHS + 1
):

    model.train()

    optimizer.zero_grad()

    logits = model(
        X_train_t
    )

    loss = criterion(
        logits,
        y_train_t
    )

    loss.backward()

    torch.nn.utils.clip_grad_norm_(
        model.parameters(),
        max_norm=1.0
    )

    optimizer.step()


    # --------------------------------------------------------
    # TRAIN
    # --------------------------------------------------------

    train_predictions = (
        torch.argmax(
            logits.detach(),
            dim=1
        )
        .cpu()
        .numpy()
    )

    train_acc = accuracy_score(
        y_train,
        train_predictions
    )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    model.eval()

    with torch.no_grad():

        val_logits = model(
            X_val_t
        )

    val_probs = torch.softmax(
        val_logits,
        dim=1
    )[:, 1].cpu().numpy()

    threshold = find_best_threshold(
        val_probs,
        y_val
    )

    val_predictions = (
        val_probs >= threshold
    ).astype(int)

    val_acc = accuracy_score(
        y_val,
        val_predictions
    )

    val_balanced = balanced_accuracy_score(
        y_val,
        val_predictions
    )

    val_f1 = f1_score(
        y_val,
        val_predictions,
        zero_division=0
    )

    val_precision = precision_score(
        y_val,
        val_predictions,
        zero_division=0
    )

    val_recall = recall_score(
        y_val,
        val_predictions,
        zero_division=0
    )

    combined = (
        0.40 * val_acc
        +
        0.30 * val_balanced
        +
        0.30 * val_f1
    )

    scheduler.step(
        combined
    )

    current_lr = (
        optimizer.param_groups[0]["lr"]
    )


    history.append({

        "epoch": epoch,
        "loss": float(loss.item()),
        "train_accuracy": train_acc,
        "val_accuracy": val_acc,
        "val_balanced_accuracy": val_balanced,
        "val_precision": val_precision,
        "val_recall": val_recall,
        "val_f1": val_f1,
        "combined": combined,
        "threshold": threshold,
        "lr": current_lr
    })


    print(
        f"Epoch [{epoch:03d}/{EPOCHS}] "
        f"Loss: {loss.item():.4f} "
        f"Train Acc: {train_acc*100:.2f}% "
        f"Val Acc: {val_acc*100:.2f}% "
        f"Balanced: {val_balanced*100:.2f}% "
        f"Macro-F1: {val_f1*100:.2f}% "
        f"Combined: {combined*100:.2f}% "
        f"Threshold: {threshold:.2f} "
        f"LR: {current_lr:.7f}"
    )


    # --------------------------------------------------------
    # BEST MODEL
    # --------------------------------------------------------

    if combined > best_combined:

        best_combined = combined
        best_epoch = epoch
        patience = 0

        best_state = {
            k: v.detach()
            .cpu()
            .clone()
            for k, v
            in model.state_dict().items()
        }

        print(
            "--> Best hybrid quantum model saved"
        )

    else:

        patience += 1

        print(
            f"Patience: "
            f"{patience}/{PATIENCE_LIMIT}"
        )


    if patience >= PATIENCE_LIMIT:

        print(
            f"\nEarly stopping at epoch {epoch}"
        )

        break


# ============================================================
# RESTORE BEST
# ============================================================

if best_state is None:

    raise RuntimeError(
        "No best model was found."
    )

model.load_state_dict(
    best_state
)

model = model.float()
model.to(DEVICE)


# ============================================================
# FINAL VALIDATION THRESHOLD
# ============================================================

model.eval()

with torch.no_grad():

    val_logits = model(
        X_val_t
    )

    test_logits = model(
        X_test_t
    )


val_probs = torch.softmax(
    val_logits,
    dim=1
)[:, 1].cpu().numpy()

test_probs = torch.softmax(
    test_logits,
    dim=1
)[:, 1].cpu().numpy()


selected_threshold = find_best_threshold(
    val_probs,
    y_val
)


# ============================================================
# FINAL TEST
# ============================================================

test_predictions = (
    test_probs >= selected_threshold
).astype(int)


test_accuracy = accuracy_score(
    y_test,
    test_predictions
)

test_balanced = balanced_accuracy_score(
    y_test,
    test_predictions
)

test_precision = precision_score(
    y_test,
    test_predictions,
    zero_division=0
)

test_recall = recall_score(
    y_test,
    test_predictions,
    zero_division=0
)

test_f1 = f1_score(
    y_test,
    test_predictions,
    zero_division=0
)

try:

    test_auc = roc_auc_score(
        y_test,
        test_probs
    )

except:

    test_auc = float("nan")


# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    y_test,
    test_predictions
)


# ============================================================
# REPORT
# ============================================================

report = classification_report(
    y_test,
    test_predictions,
    digits=4,
    zero_division=0
)


print("\n" + "=" * 70)
print("BEST MODEL")
print("=" * 70)

print(
    f"\nBest Epoch: {best_epoch}"
)

print(
    f"Best Validation Combined: "
    f"{best_combined*100:.2f}%"
)

print(
    f"Selected Validation Threshold: "
    f"{selected_threshold:.2f}"
)

print(
    f"\nTest Accuracy: "
    f"{test_accuracy*100:.2f}%"
)

print(
    f"Test Balanced Accuracy: "
    f"{test_balanced*100:.2f}%"
)

print(
    f"Test Precision: "
    f"{test_precision*100:.2f}%"
)

print(
    f"Test Recall: "
    f"{test_recall*100:.2f}%"
)

print(
    f"Test F1 Score: "
    f"{test_f1*100:.2f}%"
)

print(
    f"ROC-AUC: "
    f"{test_auc*100:.2f}%"
)

print("\nConfusion Matrix:")
print(cm)

print("\nClassification Report:")
print(report)


# ============================================================
# PREDICTIONS
# ============================================================

prediction_df = pd.DataFrame({

    "Actual": y_test,

    "Predicted": test_predictions,

    "Probability_Class_1": test_probs
})

prediction_path = os.path.join(
    RESULT_DIR,
    "predictions.csv"
)

prediction_df.to_csv(
    prediction_path,
    index=False
)


# ============================================================
# RESULTS CSV
# ============================================================

results_df = pd.DataFrame([{

    "Dataset": "Kidney Infection",

    "Best_Epoch": best_epoch,

    "Validation_Combined":
        best_combined * 100,

    "Selected_Threshold":
        selected_threshold,

    "Test_Accuracy":
        test_accuracy * 100,

    "Balanced_Accuracy":
        test_balanced * 100,

    "Precision":
        test_precision * 100,

    "Recall":
        test_recall * 100,

    "F1_Score":
        test_f1 * 100,

    "ROC_AUC":
        test_auc * 100,

    "Train_Size":
        len(y_train),

    "Validation_Size":
        len(y_val),

    "Test_Size":
        len(y_test),

    "Quantum_Qubits":
        N_QUBITS,

    "Quantum_Layers":
        N_Q_LAYERS
}])


results_path = os.path.join(
    RESULT_DIR,
    "results.csv"
)

results_df.to_csv(
    results_path,
    index=False
)


# ============================================================
# CONFUSION MATRIX CSV
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

cm_path = os.path.join(
    RESULT_DIR,
    "confusion_matrix.csv"
)

cm_df.to_csv(
    cm_path
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

report_path = os.path.join(
    RESULT_DIR,
    "classification_report.txt"
)

with open(
    report_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(report)


# ============================================================
# TRAINING HISTORY
# ============================================================

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


# ============================================================
# MODEL CHECKPOINT
# ============================================================

model_path = os.path.join(
    MODEL_DIR,
    "final.pth"
)

torch.save(
    {
        "model_state_dict":
            model.state_dict(),

        "input_features":
            INPUT_FEATURES,

        "selected_features":
            selected_columns,

        "n_qubits":
            N_QUBITS,

        "n_layers":
            N_Q_LAYERS,

        "threshold":
            selected_threshold,

        "seed":
            SEED,

        "target":
            TARGET,

        "scaler_mean":
            scaler.mean_,

        "scaler_scale":
            scaler.scale_
    },
    model_path
)


# ============================================================
# PREDICTION DISTRIBUTION
# ============================================================

print("\nTest Predictions:")

print(
    pd.Series(
        test_predictions
    ).value_counts()
    .sort_index()
)


print(
    "\nSUCCESS: Both classes were predicted."
    if len(np.unique(test_predictions)) == 2
    else "\nWARNING: Only one class predicted."
)


# ============================================================
# LEAKAGE AUDIT
# ============================================================

print("\n" + "=" * 70)
print("LEAKAGE AUDIT")
print("=" * 70)

print(
    "Missing-value statistics fitted on: TRAIN ONLY"
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
    "Strict dtype protection:"
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


print("\n" + "=" * 70)

print(
    "Hybrid Quantum Model Saved:"
)

print(model_path)

print(
    "\nResults Saved:"
)

print(results_path)

print(
    "\nConfusion Matrix Saved:"
)

print(cm_path)

print(
    "\nTest Predictions Saved:"
)

print(prediction_path)

print(
    "\nClassification Report Saved:"
)

print(report_path)

print(
    "\nTraining History Saved:"
)

print(history_path)

print(
    "\nTraining completed successfully."
)

print("=" * 70)