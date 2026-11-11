"""Validate UCI records and write a derived (not original) experiment table."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.ml.data_loader import load_data,features_target

def main():
    df=load_data(); X,y=features_target(df)
    out=ROOT/'data'/'processed'; out.mkdir(exist_ok=True)
    result=X.copy(); result['grade_band']=y
    path=out/'uci_student_math_grade_bands.csv'; result.to_csv(path,index=False)
    print(f'Validated {len(df)} official records; wrote derived experiment table {path}')
if __name__=='__main__': main()
