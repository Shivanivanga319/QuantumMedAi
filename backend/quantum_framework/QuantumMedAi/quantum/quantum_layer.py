import torch
import torch.nn as nn
import pennylane as qml

from quantum.quantum_circuit import quantum_circuit, WEIGHT_SHAPES


class QuantumLayer(nn.Module):

    def __init__(self):
        super().__init__()

        self.q_layer = qml.qnn.TorchLayer(
            quantum_circuit,
            WEIGHT_SHAPES
        )

    def forward(self, x):
        return self.q_layer(x)


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    model = QuantumLayer()

    sample = torch.rand((2, 4))

    output = model(sample)

    print("\n================================")
    print("Quantum Layer Test")
    print("================================")

    print(
        "Input Shape  :",
        sample.shape
    )

    print(
        "Output Shape :",
        output.shape
    )

    print("\nOutput:")
    print(output)

    print("\nQuantum Layer Test Successful!")