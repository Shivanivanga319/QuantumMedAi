import torch
import pandas as pd

from models.hybrid_model import HybridQuantumModel
from training.dataset_loader import load_dataset

# ==========================
# Configuration
# ==========================

MODEL_PATH = "saved_models/quantum/kidney_stone_quantum.pth"
DATASET_PATH = "datasets/processed/kidney_stone.csv"
TARGET_COLUMN = "Kidney Stone (Y/N)"

# ==========================
# Load Dataset
# ==========================

X_train, X_test, y_train, y_test = load_dataset(
    DATASET_PATH,
    TARGET_COLUMN
)

X_test = torch.tensor(X_test, dtype=torch.float32)

# ==========================
# Load Model
# ==========================

model = HybridQuantumModel(
    input_features=X_test.shape[1],
    num_classes=2
)

model.load_state_dict(
    torch.load(MODEL_PATH)
)

model.eval()

# ==========================
# Prediction
# ==========================

with torch.no_grad():

    outputs = model(X_test)

    _, prediction = torch.max(outputs, 1)

print("\nPredictions")

print(prediction)