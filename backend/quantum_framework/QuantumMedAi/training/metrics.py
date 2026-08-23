from sklearn.metrics import (
    confusion_matrix,
    classification_report
)

def evaluate(y_true, y_pred):

    print("\nClassification Report\n")

    print(
        classification_report(
            y_true,
            y_pred
        )
    )

    print("\nConfusion Matrix\n")

    print(
        confusion_matrix(
            y_true,
            y_pred
        )
    )