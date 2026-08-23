import pandas as pd
from sklearn.feature_selection import SelectKBest, mutual_info_classif

class FeatureSelector:

    def __init__(self, k="all"):
        self.k = k
        self.selector = SelectKBest(score_func=mutual_info_classif, k=self.k)

    def load_dataset(self, path):
        df = pd.read_csv(path)
        print(f"\nDataset Loaded: {path}")
        print("Shape :", df.shape)
        return df

    def split_features_target(self, df):
        X = df.drop("target", axis=1)
        y = df["target"]
        return X, y

    def select_features(self, X, y):

        X_selected = self.selector.fit_transform(X, y)

        scores = pd.DataFrame({
            "Feature": X.columns,
            "Score": self.selector.scores_
        })

        scores = scores.sort_values(by="Score", ascending=False)

        print("\nFeature Importance")
        print(scores)

        return X_selected, scores


if __name__ == "__main__":

    selector = FeatureSelector(k="all")

    df = selector.load_dataset("datasets/kidney_stone.csv")

    X, y = selector.split_features_target(df)

    X_selected, scores = selector.select_features(X, y)

    print("\nSelected Feature Matrix Shape :", X_selected.shape)

    print("\nFeature Selection Completed Successfully.")