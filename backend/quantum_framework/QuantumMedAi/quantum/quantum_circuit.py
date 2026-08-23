import pennylane as qml
from pennylane import numpy as np

# ==========================
# Quantum Device
# ==========================

N_QUBITS = 4

dev = qml.device("default.qubit", wires=N_QUBITS)

# ==========================
# Variational Quantum Circuit
# ==========================

@qml.qnode(dev, interface="torch")
def quantum_circuit(inputs, weights):
    """
    inputs  : Classical features (length = 4)
    weights : Trainable quantum parameters
    """

    # Angle Encoding
    qml.AngleEmbedding(
        inputs,
        wires=range(N_QUBITS),
        rotation="Y"
    )

    # First Entangling Layer
    qml.BasicEntanglerLayers(
        weights[:, :, 0],
        wires=range(N_QUBITS)
    )

    # Strongly Entangling Layer
    qml.StronglyEntanglingLayers(
        weights,
        wires=range(N_QUBITS)
    )

    # Second Entangling Layer
    qml.BasicEntanglerLayers(
        weights[:, :, 1],
        wires=range(N_QUBITS)
    )

    # Measurement
    return [
        qml.expval(qml.PauliZ(i))
        for i in range(N_QUBITS)
    ]


# ==========================
# Weight Shape
# ==========================

WEIGHT_SHAPES = {
    "weights": (8, N_QUBITS, 3)
}

# ==========================
# Testing
# ==========================

if __name__ == "__main__":

    sample_input = np.array([0.1, 0.2, 0.3, 0.4])

    sample_weights = np.random.randn(
        8,
        N_QUBITS,
        3
    )

    output = quantum_circuit(
        sample_input,
        sample_weights
    )

    print("\nQuantum Circuit Output")
    print(output)