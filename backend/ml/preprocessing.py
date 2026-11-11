"""Leakage-safe train-fit tabular preprocessing pipeline."""
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder,StandardScaler
def make_preprocessor(X):
    cats=X.select_dtypes(include='object').columns.tolist(); nums=X.select_dtypes(exclude='object').columns.tolist()
    return ColumnTransformer([('num',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]),nums),('cat',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('onehot',OneHotEncoder(handle_unknown='ignore'))]),cats)])
