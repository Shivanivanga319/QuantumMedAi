import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score,
    roc_curve, precision_recall_curve, auc
)

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.svm import SVC

# Optional: XGBoost
# -----------------------------
# Option C: XGBoost
# -----------------------------

from xgboost import XGBClassifier

xgb_available = True

xgb_model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.9,
    colsample_bytree=0.9,
    eval_metric="logloss",
    random_state=42
)
#xgb_model.fit(X_train_scaled, y_train)
#xgb_preds = xgb_model.predict(X_test_scaled)

# -----------------------------
# 1. Load dataset
# -----------------------------
file_path = "datasets/kidney_stone.csv"
df = pd.read_csv(file_path)

print("Dataset Shape:", df.shape)
print(df.head())
print(df.columns)

# -----------------------------
# 2. Clean column names
# -----------------------------
df.columns = df.columns.str.strip()

# Rename columns if needed for easier handling
rename_map = {
    "ID": "id",
    "Specific Gravity": "specific_gravity",
    "Urine pH": "urine_ph",
    "Osmolarity (mOsm)": "osmolarity",
    "Conductivity (mMho)": "conductivity",
    "Urea (mmol/L)": "urea",
    "Calcium (mmol/L)": "calcium",
    "Kidney Stone (Y/N)": "target",
    "Data Type": "data_type"
}
df.rename(columns=rename_map, inplace=True)

# -----------------------------
# 3. Basic preprocessing
# -----------------------------
# Convert target to numeric
df["target"] = pd.to_numeric(df["target"], errors="coerce")

# Keep only usable columns
feature_cols = [
    "specific_gravity", "urine_ph", "osmolarity",
    "conductivity", "urea", "calcium"
]

# Convert features to numeric
for col in feature_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Drop missing rows
df = df.dropna(subset=feature_cols + ["target"])

print("\nCleaned Shape:", df.shape)
print("\nClass Distribution:")
print(df["target"].value_counts())

# Optional: remove ID and data_type from features
X = df[feature_cols]
y = df["target"].astype(int)

# -----------------------------
# 4. Train-test split
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print("\nTrain Shape:", X_train.shape)
print("Test Shape:", X_test.shape)

# -----------------------------
# 5. Define models
# -----------------------------
models = {
    "Logistic Regression": Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=1000, random_state=42))
    ]),
    
    "SVM": Pipeline([
        ("scaler", StandardScaler()),
        ("model", SVC(probability=True, kernel="rbf", random_state=42))
    ]),
    
    "Random Forest": RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42
    ),
    
    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=3,
        random_state=42
    ),
    
    "Extra Trees": ExtraTreesClassifier(
        n_estimators=300,
        max_depth=12,
        random_state=42
    )
}

if xgb_available:
    models["XGBoost"] = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="logloss",
        random_state=42
    )

# -----------------------------
# 6. Train and compare models
# -----------------------------
results = []

for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_test)[:, 1]
    else:
        y_prob = None
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc = roc_auc_score(y_test, y_prob) if y_prob is not None else np.nan
    
    results.append([name, acc, prec, rec, f1, roc])

results_df = pd.DataFrame(
    results,
    columns=["Model", "Accuracy", "Precision", "Recall", "F1 Score", "ROC-AUC"]
).sort_values(by="Accuracy", ascending=False)

print("\nModel Comparison:")
print(results_df)

# -----------------------------
# 7. Select best model
# -----------------------------
best_model_name = results_df.iloc[0]["Model"]
best_model = models[best_model_name]

print(f"\nBest Model: {best_model_name}")

# Refit best model
best_model.fit(X_train, y_train)
y_pred = best_model.predict(X_test)

if hasattr(best_model, "predict_proba"):
    y_prob = best_model.predict_proba(X_test)[:, 1]
else:
    y_prob = None

# -----------------------------
# 8. Final metrics
# -----------------------------
acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred, zero_division=0)
rec = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)
cm = confusion_matrix(y_test, y_pred)

print("\nFinal Evaluation Metrics")
print("------------------------")
print("Accuracy :", round(acc * 100, 2), "%")
print("Precision:", round(prec * 100, 2), "%")
print("Recall   :", round(rec * 100, 2), "%")
print("F1 Score :", round(f1 * 100, 2), "%")

if y_prob is not None:
    roc_auc = roc_auc_score(y_test, y_prob)
    print("ROC-AUC  :", round(roc_auc * 100, 2), "%")

print("\nConfusion Matrix:")
print(cm)

print("\nClassification Report:")
print(classification_report(y_test, y_pred, digits=4))

# -----------------------------
# 9. Cross-validation
# -----------------------------
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(best_model, X, y, cv=cv, scoring="accuracy")

print("\n5-Fold Cross Validation Accuracy Scores:", cv_scores)
print("Mean CV Accuracy:", round(cv_scores.mean() * 100, 2), "%")
print("Std CV Accuracy :", round(cv_scores.std() * 100, 2), "%")

# -----------------------------
# 10. Graphs
# -----------------------------

# A. Confusion Matrix Heatmap
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=["No Stone", "Stone"],
            yticklabels=["No Stone", "Stone"])
plt.title(f"Confusion Matrix - {best_model_name}")
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.tight_layout()
plt.show()

# B. ROC Curve
if y_prob is not None:
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, label=f"AUC = {roc_auc:.4f}")
    plt.plot([0, 1], [0, 1], linestyle="--", color="red")
    plt.title(f"ROC Curve - {best_model_name}")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.legend()
    plt.tight_layout()
    plt.show()

# C. Precision-Recall Curve
if y_prob is not None:
    precision_vals, recall_vals, _ = precision_recall_curve(y_test, y_prob)
    pr_auc = auc(recall_vals, precision_vals)
    
    plt.figure(figsize=(6, 5))
    plt.plot(recall_vals, precision_vals, label=f"PR AUC = {pr_auc:.4f}")
    plt.title(f"Precision-Recall Curve - {best_model_name}")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.legend()
    plt.tight_layout()
    plt.show()

# D. Feature Importance (tree-based models only)
tree_model_names = ["Random Forest", "Extra Trees", "XGBoost"]

if best_model_name in tree_model_names:
    importances = best_model.feature_importances_
    feat_imp = pd.DataFrame({
        "Feature": feature_cols,
        "Importance": importances
    }).sort_values(by="Importance", ascending=False)

    print("\nFeature Importance:")
    print(feat_imp)

    plt.figure(figsize=(8, 5))
    sns.barplot(data=feat_imp, x="Importance", y="Feature", palette="viridis")
    plt.title(f"Feature Importance - {best_model_name}")
    plt.tight_layout()
    plt.show()

# E. Accuracy comparison graph
plt.figure(figsize=(10, 5))
sns.barplot(data=results_df, x="Accuracy", y="Model", palette="magma")
plt.title("Model Accuracy Comparison")
plt.xlim(0, 1)
plt.tight_layout()
plt.show()
