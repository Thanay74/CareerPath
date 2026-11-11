# Generated ML experiment results

```json
{
  "dataset": "UCI Student Performance, Mathematics",
  "records": 395,
  "features": [
    "school",
    "sex",
    "age",
    "address",
    "famsize",
    "Pstatus",
    "Medu",
    "Fedu",
    "Mjob",
    "Fjob",
    "reason",
    "guardian",
    "traveltime",
    "studytime",
    "failures",
    "schoolsup",
    "famsup",
    "paid",
    "activities",
    "nursery",
    "higher",
    "internet",
    "romantic",
    "famrel",
    "freetime",
    "goout",
    "Dalc",
    "Walc",
    "health",
    "absences"
  ],
  "target": "G3 bands: low <10, pass 10-13, high >13",
  "excluded": [
    "G1",
    "G2"
  ],
  "split": "stratified 80/20, random_state=42",
  "cross_validation": "5-fold stratified on train partition",
  "results": {
    "majority_baseline": {
      "accuracy": 0.4177215189873418,
      "precision_macro": 0.13924050632911392,
      "recall_macro": 0.3333333333333333,
      "f1_macro": 0.19642857142857142,
      "cv_f1_macro_mean": 0.19641437214470922,
      "cv_f1_macro_std": 0.0021460599768015026,
      "confusion_matrix": [
        [
          0,
          26,
          0
        ],
        [
          0,
          33,
          0
        ],
        [
          0,
          20,
          0
        ]
      ],
      "classification_report": "              precision    recall  f1-score   support\n\n        high       0.00      0.00      0.00        20\n         low       0.00      0.00      0.00        26\n        pass       0.42      1.00      0.59        33\n\n    accuracy                           0.42        79\n   macro avg       0.14      0.33      0.20        79\nweighted avg       0.17      0.42      0.25        79\n",
      "permutation_importance": {
        "school": 0.0,
        "sex": 0.0,
        "age": 0.0,
        "address": 0.0,
        "famsize": 0.0,
        "Pstatus": 0.0,
        "Medu": 0.0,
        "Fedu": 0.0,
        "Mjob": 0.0,
        "Fjob": 0.0,
        "reason": 0.0,
        "guardian": 0.0,
        "traveltime": 0.0,
        "studytime": 0.0,
        "failures": 0.0,
        "schoolsup": 0.0,
        "famsup": 0.0,
        "paid": 0.0,
        "activities": 0.0,
        "nursery": 0.0,
        "higher": 0.0,
        "internet": 0.0,
        "romantic": 0.0,
        "famrel": 0.0,
        "freetime": 0.0,
        "goout": 0.0,
        "Dalc": 0.0,
        "Walc": 0.0,
        "health": 0.0,
        "absences": 0.0
      }
    },
    "random_forest": {
      "accuracy": 0.46835443037974683,
      "precision_macro": 0.4702453102453102,
      "recall_macro": 0.47202797202797203,
      "f1_macro": 0.47097952262945086,
      "cv_f1_macro_mean": 0.5022433641166448,
      "cv_f1_macro_std": 0.04744732621532094,
      "confusion_matrix": [
        [
          12,
          10,
          4
        ],
        [
          11,
          15,
          7
        ],
        [
          2,
          8,
          10
        ]
      ],
      "classification_report": "              precision    recall  f1-score   support\n\n        high       0.48      0.50      0.49        20\n         low       0.48      0.46      0.47        26\n        pass       0.45      0.45      0.45        33\n\n    accuracy                           0.47        79\n   macro avg       0.47      0.47      0.47        79\nweighted avg       0.47      0.47      0.47        79\n",
      "permutation_importance": {
        "failures": 0.08499483349493475,
        "Medu": 0.04063781354552816,
        "paid": 0.01837705014180046,
        "Mjob": 0.01651846233260402,
        "absences": 0.01587666694188451,
        "sex": 0.014541314814986495,
        "famsup": 0.0137776390492449,
        "address": 0.010321887081272824,
        "schoolsup": 0.009855568417030775,
        "Fedu": 0.009068343206066087,
        "internet": 0.008587360776493441,
        "guardian": 0.007909687120028286,
        "Walc": 0.007759534681194807,
        "activities": 0.0073335722089540815,
        "school": 0.0011205872362887003,
        "higher": 0.0008167065688309161,
        "freetime": 0.0007937839594738538,
        "Pstatus": -0.0012134923899629834,
        "studytime": -0.0036933736446267186,
        "traveltime": -0.00547555873244579,
        "goout": -0.005662952405884841,
        "famrel": -0.0062234606216426454,
        "Dalc": -0.0069511136054995985,
        "Fjob": -0.007705594628513873,
        "nursery": -0.011611994243882989,
        "reason": -0.02330884432346919,
        "famsize": -0.02694794023424102,
        "romantic": -0.03018801644894667,
        "age": -0.03226772259885448,
        "health": -0.03950690229667732
      }
    }
  }
}
```
