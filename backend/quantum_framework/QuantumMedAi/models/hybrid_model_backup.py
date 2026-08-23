import torch
import torch.nn as nn

from quantum.quantum_layer import QuantumLayer
from models.classifier import Classifier


class HybridQuantumModel(nn.Module):

    def __init__(self, input_features, num_classes=2):
        super().__init__()

        # Classical Feature Extractor
        self.classical = nn.Sequential(

            nn.Linear(input_features, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.30),

            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.20),

            nn.Linear(32, 4),
            nn.ReLU()
        )

        # Quantum Layer
        self.quantum = QuantumLayer()

        # Final Classifier
        self.classifier = Classifier(num_classes)

    def forward(self, x):

        x = self.classical(x)

        x = self.quantum(x)

        x = self.classifier(x)

        return x


if __name__ == "__main__":

    model = HybridQuantumModel(input_features=7)

    sample = torch.rand((5, 7))

    output = model(sample)

    print(output.shape)
    print(output)