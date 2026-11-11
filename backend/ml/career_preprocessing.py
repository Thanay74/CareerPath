"""Reusable, train-fold-fitted preprocessing for career-family pipelines."""
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

def make_career_preprocessor(features):
    categorical=[name for name in features if name=='stream']
    numeric=[name for name in features if name!='stream']
    return ColumnTransformer([
        ('numeric',Pipeline([('impute',SimpleImputer(strategy='median',add_indicator=True))]),numeric),
        ('categorical',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('encode',OneHotEncoder(handle_unknown='ignore'))]),categorical),
    ])
