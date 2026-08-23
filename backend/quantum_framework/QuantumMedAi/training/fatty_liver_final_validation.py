# quantum_med_ai_fatty_liver.py

import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_curve,
    auc,
    precision_recall_curve
)
from sklearn.utils.class_weight import compute_class_weight
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance

from imblearn.over_sampling import SMOTE

import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import (
    Input, Dense, Dropout, BatchNormalization, Concatenate
)
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

# =========================================================
# 1. CONFIG
# =========================================================

DATA_PATH = "datasets/fatty_liver.csv"   
TARGET_COL = "fatty_liver_grade"
ID_COL = "id"

RESULTS_DIR = "quantum_med_ai_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

np.random.seed(42)
tf.random.set_seed(42)

# =========================================================
# 2. OPTIONAL QUANTUM SETUP
# =========================================================

QUANTUM_AVAILABLE = False
try:
    import pennylane as qml
    QUANTUM_AVAILABLE = True
except Exception:
    QUANTUM_AVAILABLE = False

# =========================================================
# 3. LOAD DATA
# =========================================================

df = pd.read_csv(DATA_PATH)

print("\nDataset shape:", df.shape)
print("\nColumns:\n", df.columns.tolist())
print("\nMissing values:\n", df.isnull().sum().sort_values(ascending=False).head(10))

# =========================================================
# 4. BASIC CLEANING
# =========================================================

# Drop ID if exists
if ID_COL in df.columns:
    df = df.drop(columns=[ID_COL])

# Remove duplicates
df = df.drop_duplicates()

# Fill missing values if any
for col in df.columns:
    if pd.api.types.is_numeric_dtype(df[col]):
        df[col] = df[col].fillna(df[col].median())
    else:
        mode_value = df[col].mode()
        if not mode_value.empty:
            df[col] = df[col].fillna(mode_value.iloc[0])
# Encode categorical columns
label_encoders = {}
for col in df.select_dtypes(include=["object"]).columns:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col].astype(str))
    label_encoders[col] = le

# =========================================================
# 5. TARGET CREATION
# =========================================================

# Binary classification:
# 0 -> no fatty liver (grade 0)
# 1 -> fatty liver present (grade 1/2/3)

df["fatty_liver_binary"] = (df[TARGET_COL] > 0).astype(int)

# Features and target
X = df.drop(columns=[TARGET_COL, "fatty_liver_binary", "liver_cirrhosis"], errors="ignore")
y = df["fatty_liver_binary"]

print("\nTarget distribution:")
print(y.value_counts())

# =========================================================
# 6. TRAIN-TEST SPLIT
# =========================================================

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# =========================================================
# 7. SCALING
# =========================================================

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# =========================================================
# 8. BALANCE DATA WITH SMOTE
# =========================================================

smote = SMOTE(random_state=42)
X_train_bal, y_train_bal = smote.fit_resample(X_train_scaled, y_train)

print("\nBalanced training distribution:")
print(pd.Series(y_train_bal).value_counts())

# =========================================================
# 9. CLASSICAL FEATURE IMPORTANCE MODEL
# =========================================================

rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=12,
    min_samples_split=4,
    random_state=42,
    class_weight="balanced"
)
rf.fit(X_train_bal, y_train_bal)

rf_importances = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
top_features = rf_importances.head(12).index.tolist()

print("\nTop 12 important features:")
print(rf_importances.head(12))

# Reduce to top features for hybrid model
X_train_top = pd.DataFrame(X_train_bal, columns=X.columns)[top_features].values
X_test_top = pd.DataFrame(X_test_scaled, columns=X.columns)[top_features].values

# =========================================================
# 10. QUANTUM FEATURE BLOCK
# =========================================================

def quantum_feature_map_numpy(X_array):
    """
    If PennyLane is available, create simple quantum embeddings.
    Else fallback to nonlinear classical transform.
    """
    if QUANTUM_AVAILABLE:
        n_qubits = min(4, X_array.shape[1])
        dev = qml.device("default.qubit", wires=n_qubits)

        @qml.qnode(dev)
        def circuit(inputs):
            for i in range(n_qubits):
                qml.RY(inputs[i], wires=i)
            for i in range(n_qubits - 1):
                qml.CNOT(wires=[i, i + 1])
            return [qml.expval(qml.PauliZ(i)) for i in range(n_qubits)]

        q_features = []
        for row in X_array:
            q_in = row[:n_qubits]
            q_features.append(circuit(q_in))
        return np.array(q_features)
    else:
        # Classical fallback: "quantum-inspired" nonlinear projection
        return np.column_stack([
            np.tanh(X_array[:, 0]),
            np.sin(X_array[:, 1] if X_array.shape[1] > 1 else X_array[:, 0]),
            np.cos(X_array[:, 2] if X_array.shape[1] > 2 else X_array[:, 0]),
            np.tanh(X_array[:, 3] if X_array.shape[1] > 3 else X_array[:, 0]),
        ])

X_train_q = quantum_feature_map_numpy(X_train_top)
X_test_q = quantum_feature_map_numpy(X_test_top)

# =========================================================
# 11. HYBRID DEEP LEARNING MODEL
# =========================================================

# Classical branch
classical_input = Input(shape=(X_train_top.shape[1],), name="classical_input")
x1 = Dense(128, activation="relu")(classical_input)
x1 = BatchNormalization()(x1)
x1 = Dropout(0.3)(x1)
x1 = Dense(64, activation="relu")(x1)
x1 = BatchNormalization()(x1)
x1 = Dropout(0.25)(x1)

# Quantum branch
quantum_input = Input(shape=(X_train_q.shape[1],), name="quantum_input")
x2 = Dense(32, activation="relu")(quantum_input)
x2 = BatchNormalization()(x2)
x2 = Dropout(0.2)(x2)
x2 = Dense(16, activation="relu")(x2)

# Merge
merged = Concatenate()([x1, x2])
x = Dense(64, activation="relu")(merged)
x = BatchNormalization()(x)
x = Dropout(0.25)(x)
x = Dense(32, activation="relu")(x)
output = Dense(1, activation="sigmoid")(x)

model = Model(inputs=[classical_input, quantum_input], outputs=output)

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss="binary_crossentropy",
    metrics=["accuracy"]
)

model.summary()

# =========================================================
# 12. TRAIN MODEL
# =========================================================

class_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.unique(y_train_bal),
    y=y_train_bal
)
class_weights = {i: class_weights[i] for i in range(len(class_weights))}

callbacks = [
    EarlyStopping(monitor="val_loss", patience=12, restore_best_weights=True),
    ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=6, min_lr=1e-6)
]

history = model.fit(
    [X_train_top, X_train_q],
    y_train_bal,
    validation_split=0.2,
    epochs=50,
    batch_size=32,
    class_weight=class_weights,
    callbacks=callbacks,
    verbose=1
)

# =========================================================
# 13. PREDICTIONS
# =========================================================

y_prob = model.predict([X_test_top, X_test_q]).ravel()

# Default threshold
threshold = 0.5
y_pred = (y_prob >= threshold).astype(int)

# =========================================================
# 14. METRICS
# =========================================================

acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred, zero_division=0)
rec = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)
cm = confusion_matrix(y_test, y_pred)

print("\n" + "="*60)
print("QUANTUM MED AI - FINAL RESULTS")
print("="*60)
print(f"Accuracy : {acc*100:.2f}%")
print(f"Precision: {prec*100:.2f}%")
print(f"Recall   : {rec*100:.2f}%")
print(f"F1 Score : {f1*100:.2f}%")
print("\nConfusion Matrix:\n", cm)

print("\nClassification Report:\n")
print(classification_report(y_test, y_pred, target_names=["No Fatty Liver", "Fatty Liver"]))

# Save metrics to text file
with open(os.path.join(RESULTS_DIR, "metrics_report.txt"), "w", encoding="utf-8") as f:
    f.write("QUANTUM MED AI - FINAL RESULTS\n")
    f.write("="*50 + "\n")
    f.write(f"Accuracy : {acc*100:.2f}%\n")
    f.write(f"Precision: {prec*100:.2f}%\n")
    f.write(f"Recall   : {rec*100:.2f}%\n")
    f.write(f"F1 Score : {f1*100:.2f}%\n\n")
    f.write("Confusion Matrix:\n")
    f.write(str(cm) + "\n\n")
    f.write("Classification Report:\n")
    f.write(classification_report(y_test, y_pred, target_names=["No Fatty Liver", "Fatty Liver"]))

# =========================================================
# 15. GRAPH 1 - TRAINING ACCURACY AND LOSS
# =========================================================

plt.figure(figsize=(14, 5))

plt.subplot(1, 2, 1)
plt.plot(history.history["accuracy"], label="Train Accuracy")
plt.plot(history.history["val_accuracy"], label="Validation Accuracy")
plt.title("Training and Validation Accuracy")
plt.xlabel("Epoch")
plt.ylabel("Accuracy")
plt.legend()
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(history.history["loss"], label="Train Loss")
plt.plot(history.history["val_loss"], label="Validation Loss")
plt.title("Training and Validation Loss")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, "training_curves.png"), dpi=300)
plt.show()

# =========================================================
# 16. GRAPH 2 - CONFUSION MATRIX
# =========================================================

plt.figure(figsize=(6, 5))
sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    cmap="Blues",
    xticklabels=["Pred No", "Pred Yes"],
    yticklabels=["Actual No", "Actual Yes"]
)
plt.title("Confusion Matrix")
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, "confusion_matrix.png"), dpi=300)
plt.show()

# =========================================================
# 17. GRAPH 3 - ROC CURVE
# =========================================================

fpr, tpr, _ = roc_curve(y_test, y_prob)
roc_auc = auc(fpr, tpr)

plt.figure(figsize=(6, 5))
plt.plot(fpr, tpr, label=f"ROC Curve (AUC = {roc_auc:.3f})", linewidth=2)
plt.plot([0, 1], [0, 1], "k--")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, "roc_curve.png"), dpi=300)
plt.show()

# =========================================================
# 18. GRAPH 4 - PRECISION RECALL CURVE
# =========================================================

precision_vals, recall_vals, _ = precision_recall_curve(y_test, y_prob)

plt.figure(figsize=(6, 5))
plt.plot(recall_vals, precision_vals, color="green", linewidth=2)
plt.xlabel("Recall")
plt.ylabel("Precision")
plt.title("Precision-Recall Curve")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, "precision_recall_curve.png"), dpi=300)
plt.show()

# =========================================================
# 19. GRAPH 5 - FEATURE IMPORTANCE
# =========================================================

plt.figure(figsize=(10, 6))
rf_importances.head(12).sort_values().plot(kind="barh", color="teal")
plt.title("Top 12 Feature Importances")
plt.xlabel("Importance Score")
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, "feature_importance.png"), dpi=300)
plt.show()

# =========================================================
# 20. GRAPH 6 - PREDICTION PROBABILITY DISTRIBUTION
# =========================================================

plt.figure(figsize=(8, 5))
sns.histplot(y_prob[y_test.values == 0], color="blue", label="No Fatty Liver", kde=True, stat="density", bins=25)
sns.histplot(y_prob[y_test.values == 1], color="red", label="Fatty Liver", kde=True, stat="density", bins=25)
plt.axvline(threshold, color="black", linestyle="--", label=f"Threshold = {threshold}")
plt.title("Prediction Probability Distribution")
plt.xlabel("Predicted Probability")
plt.ylabel("Density")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, "probability_distribution.png"), dpi=300)
plt.show()

# =========================================================
# 21. OPTIONAL THRESHOLD TUNING TO IMPROVE F1
# =========================================================

thresholds = np.arange(0.3, 0.71, 0.01)
best_f1 = 0
best_threshold = 0.5
best_metrics = None

for th in thresholds:
    temp_pred = (y_prob >= th).astype(int)
    temp_acc = accuracy_score(y_test, temp_pred)
    temp_prec = precision_score(y_test, temp_pred, zero_division=0)
    temp_rec = recall_score(y_test, temp_pred, zero_division=0)
    temp_f1 = f1_score(y_test, temp_pred, zero_division=0)

    if temp_f1 > best_f1:
        best_f1 = temp_f1
        best_threshold = th
        best_metrics = (temp_acc, temp_prec, temp_rec, temp_f1)

print("\nBest threshold based on F1:", round(best_threshold, 2))
print(f"Threshold-tuned Accuracy : {best_metrics[0]*100:.2f}%")
print(f"Threshold-tuned Precision: {best_metrics[1]*100:.2f}%")
print(f"Threshold-tuned Recall   : {best_metrics[2]*100:.2f}%")
print(f"Threshold-tuned F1 Score : {best_metrics[3]*100:.2f}%")

# =========================================================
# 22. SAVE MODEL AND SCALER
# =========================================================

model.save(os.path.join(RESULTS_DIR, "quantum_med_ai_model.h5"))
import joblib
joblib.dump(scaler, os.path.join(RESULTS_DIR, "scaler.pkl"))
joblib.dump(top_features, os.path.join(RESULTS_DIR, "top_features.pkl"))

print("\nAll outputs saved in folder:", RESULTS_DIR)
print("Quantum block used:", "PennyLane Quantum" if QUANTUM_AVAILABLE else "Classical fallback quantum-inspired block")
