import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from joblib import dump
import os

# -------------------------------
# 1. Create "models" folder
# -------------------------------
os.makedirs("models", exist_ok=True)

# -------------------------------
# 2. Dummy dataset (replace later with MySQL data)
# -------------------------------
data = {
    "blood_match": [1, 1, 0, 1, 0, 1, 0, 1],
    "dist": [10, 50, 300, 15, 200, 5, 400, 25],
    "urg_score": [4, 3, 2, 4, 1, 3, 2, 4],
    "days_since": [100, 200, 500, 150, 700, 90, 800, 120],
    "availability": [1, 1, 0, 1, 0, 1, 0, 1],
    "number_of_donation": [3, 5, 1, 4, 0, 2, 1, 6],
    "pints_donated": [2, 3, 1, 2, 0, 1, 1, 4],
    "match": [1, 1, 0, 1, 0, 1, 0, 1]  # Target variable
}

df = pd.DataFrame(data)

# Features & target
X = df[[
    "blood_match", "dist", "urg_score",
    "days_since", "availability",
    "number_of_donation", "pints_donated"
]]
y = df["match"]

# -------------------------------
# 3. Train/Test split
# -------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42
)

# -------------------------------
# 4. Decision Tree Classifier
# -------------------------------
tree = DecisionTreeClassifier(max_depth=5, random_state=42)
tree.fit(X_train, y_train)

y_pred_tree = tree.predict(X_test)
print("🌳 Decision Tree Accuracy:", accuracy_score(y_test, y_pred_tree))
print(classification_report(y_test, y_pred_tree))

dump(tree, "models/tree_matcher.joblib")
print("✅ tree_matcher.joblib saved!")

# -------------------------------
# 5. Logistic Regression
# -------------------------------
logreg = LogisticRegression(max_iter=1000, solver="lbfgs")
logreg.fit(X_train, y_train)

y_pred_logreg = logreg.predict(X_test)
print("📊 Logistic Regression Accuracy:", accuracy_score(y_test, y_pred_logreg))
print(classification_report(y_test, y_pred_logreg))

dump(logreg, "models/logreg_matcher.joblib")
print("✅ logreg_matcher.joblib saved!")
