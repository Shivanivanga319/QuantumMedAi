import torch
import torch.nn as nn

from quantum.quantum_layer import QuantumLayer


class HybridQuantumModel(nn.Module):

    def __init__(self, input_features, num_classes):

        super().__init__()

        # ==========================================
        # Classical Feature Extractor
        # ==========================================

        self.classical = nn.Sequential(

            nn.Linear(input_features, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.15),

            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.15),

            # 4 features for quantum circuit
            nn.Linear(32, 4)
        )

        # ==========================================
        # Quantum Layer
        # ==========================================

        self.quantum = QuantumLayer()

        # ==========================================
        # Final Classifier
        # ==========================================

        self.classifier = nn.Sequential(

            nn.Linear(4, 16),
            nn.ReLU(),
            nn.Dropout(0.10),

            nn.Linear(16, 8),
            nn.ReLU(),

            nn.Linear(8, num_classes)
        )

    # ==========================================
    # Forward Pass
    # ==========================================

    def forward(self, x):

        x = self.classical(x)

        # Keep quantum input stable
        x = torch.tanh(x)

        x = self.quantum(x)

        x = self.classifier(x)

        return x


# ==============================================
# TEST
# ==============================================

if __name__ == "__main__":

    model = HybridQuantumModel(
        input_features=6,
        num_classes=2
    )

    sample = torch.randn(4, 6)

    output = model(sample)

    print("\n================================")
    print("Hybrid Quantum Model Test")
    print("================================")

    print("Input Shape  :", sample.shape)
    print("Output Shape :", output.shape)

    print("\nOutput:")
    print(output)

    print("\nModel Test Successful!")