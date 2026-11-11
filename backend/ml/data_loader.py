"""Load and validate preserved UCI Mathematics data without feature leakage."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
EXPECTED={'G1','G2','G3','school','age','sex'}
def load_data(path=ROOT/'data/raw/student_performance/extracted/student-mat.csv'):
    path=Path(path)
    if not path.exists(): raise FileNotFoundError(f'{path} missing; run python data/download_public_data.py')
    df=pd.read_csv(path,sep=';')
    if not EXPECTED.issubset(df.columns): raise ValueError(f'Unexpected source schema; missing {EXPECTED-set(df.columns)}')
    if df.G3.isna().any() or not df.G3.between(0,20).all(): raise ValueError('G3 target must be complete and in 0-20')
    return df
def features_target(df):
    y=pd.cut(df.G3,bins=[-1,9,13,20],labels=['low','pass','high']).astype(str)
    return df.drop(columns=['G1','G2','G3']),y
