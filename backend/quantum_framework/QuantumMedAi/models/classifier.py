import torch.nn as nn

class Classifier(nn.Module):

    def __init__(self, num_classes=2):
        super().__init__()

        self.net = nn.Sequential(

            nn.Linear(4, 32),
            nn.ReLU(),
            nn.Dropout(0.30),

            nn.Linear(32, 16),
            nn.ReLU(),

            nn.Linear(16, num_classes)
        )

    def forward(self, x):
        return self.net(x)