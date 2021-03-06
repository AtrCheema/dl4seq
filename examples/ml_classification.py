#How to use AI4Water for classification problems

import pandas as pd
import numpy as np
from sklearn.datasets import load_breast_cancer

from AI4Water import Model

data_class = load_breast_cancer()
cols = data_class['feature_names'].tolist() + ['target']
df = pd.DataFrame(np.concatenate([data_class['data'], data_class['target'].reshape(-1,1)], axis=1), columns=cols)

model = Model(
    data=df,
    inputs=data_class['feature_names'].tolist(),
    outputs=['target'],
    val_fraction=0.0,
    model={"DecisionTreeClassifier":{"max_depth": 4, "random_state": 313}},
    transformation=None,
    problem="classification"
)

h = model.fit()

model.view_model()
