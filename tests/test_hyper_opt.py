import os
import time
import pickle
import unittest
from os.path import abspath
from inspect import getsourcefile
import site   # so that dl4seq directory is in path
site.addsitedir(os.path.dirname(os.path.dirname(__file__)) )

import skopt
import numpy as np
import pandas as pd
from sklearn.svm import SVC
from scipy.stats import uniform
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from hyperopt import hp, STATUS_OK, fmin, tpe, Trials

np.random.seed(313)

from dl4seq.hyper_opt import HyperOpt, Real, Categorical, Integer
from dl4seq import Model
from dl4seq.utils.utils import Jsonize
from dl4seq.utils.TSErrors import FindErrors


file_path = abspath(getsourcefile(lambda:0))
dpath = os.path.join(os.path.join(os.path.dirname(os.path.dirname(file_path)), "dl4seq"), "data")
fname = os.path.join(dpath, "input_target_u1.csv")


def run_dl4seq(method):
    dims = {'n_estimators': [1000,  2000],
            'max_depth': [3,  6],
            'learning_rate': [0.1,  0.0005],
            'booster': ["gbtree", "dart"]}


    data = pd.read_csv(fname)
    inputs = list(data.columns)
    inputs.remove('index')
    inputs.remove('target')
    inputs.remove('target_by_group')
    outputs = ['target']

    dl4seq_args = {"inputs": inputs,
                   "outputs": outputs,
                   "lookback": 1,
                   "batches": "2d",
                   "val_data": "same",
                   "test_fraction": 0.3,
                   "model": {"xgboostregressor": {}},
                   "transformation": None
                   }

    opt = HyperOpt(method,
                   param_space=dims,
                   dl4seq_args=dl4seq_args,
                   data=data,
                   use_named_args=True,
                   acq_func='EI',  # Expected Improvement.
                   n_calls=12,
                   n_iter=12,
                   # acq_optimizer='auto',
                   x0=[1000, 3, 0.01, "gbtree"],
                   n_random_starts=3,  # the number of random initialization points
                   random_state=2
                   )

    # executes bayesian optimization
    opt.fit()
    return


class TestHyperOpt(unittest.TestCase):

    def test_real_num_samples(self):
        r = Real(low=10, high=100, num_samples=20)
        grit = r.grid
        assert grit.shape == (20,)

    def test_real_steps(self):
        r = Real(low=10, high=100, step=20)
        grit = r.grid
        assert grit.shape == (5,)

    def test_real_grid(self):
        grit = [1,2,3,4,5]
        r = Real(grid=grit)
        np.testing.assert_array_equal(grit, r.grid)

    def test_integer_num_samples(self):
        r = Integer(low=10, high=100, num_samples=20)
        grit = r.grid
        assert grit.shape == (20,)

    def test_integer_steps(self):
        r = Integer(low=10, high=100, step=20)
        grit = r.grid
        grit.shape = (5,)

    def test_integer_grid(self):
        grit = [1, 2, 3, 4, 5]
        r = Integer(grid=grit)
        np.testing.assert_array_equal(grit, r.grid)

    def test_categorical(self):
        cats = ['a', 'b', 'c']
        c = Categorical(cats)
        assert len(cats) == len(c.grid)

    def test_random(self):
        # testing for sklearn-based model with random search
        # https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.RandomizedSearchCV.html#sklearn.model_selection.RandomizedSearchCV
        iris = load_iris()
        logistic = LogisticRegression(solver='saga', tol=1e-2, max_iter=200,
                                      random_state=0)
        distributions1 = dict(C=uniform(loc=0, scale=4),
                             penalty=['l2', 'l1'])

        clf = HyperOpt('random', model=logistic, param_space=distributions1, random_state=0)

        search = clf.fit(iris.data, iris.target)
        np.testing.assert_almost_equal(search.best_params_['C'], 2.195254015709299, 5)
        assert search.best_params_['penalty'] == 'l1'
        print("RandomizeSearchCV test passed")
        return clf


    def test_grid(self):
        # testing for sklearn-based model with grid search
        # https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html#sklearn.model_selection.GridSearchCV
        iris = load_iris()
        parameters = {'kernel': ('linear', 'rbf'), 'C': [1, 10]}
        svc = SVC()
        clf = HyperOpt("grid", model=svc, param_space=parameters)
        search = clf.fit(iris.data, iris.target)

        sorted(clf.cv_results_.keys())

        assert search.best_params_['C'] == 1
        assert search.best_params_['kernel'] == 'linear'
        print("GridSearchCV test passed")
        return clf


    # def test_bayes(self):
    #     # testing for sklearn-based model with gp_min
    #     # https://scikit-optimize.github.io/stable/modules/generated/skopt.BayesSearchCV.html
    #     X, y = load_iris(True)
    #     X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=0.75, random_state=0)
    #
    #     opt = HyperOpt("bayes",  model=SVC(),
    #                    param_space={
    #         'C': Real(1e-6, 1e+6, prior='log-uniform'),
    #         'gamma': Real(1e-6, 1e+1, prior='log-uniform'),
    #         'degree': Integer(1, 8),
    #         'kernel': Categorical(['linear', 'poly', 'rbf']),
    #         },
    #         n_iter=32,
    #         random_state=0
    #     )
    #     # executes bayesian optimization
    #     _ = opt.fit(X_train, y_train)
    #
    #     # model can be saved, used for predictions or scoring
    #     np.testing.assert_almost_equal(0.9736842105263158, opt.score(X_test, y_test), 5)
    #     print("BayesSearchCV test passed")
    #     return


    def test_gpmin_skopt(self):
        # testing for custom model with gp_min
        # https://github.com/scikit-optimize/scikit-optimize/blob/9334d50a1ad5c9f7c013a1c1cb95313a54b83168/examples/bayesian-optimization.py#L109
        def f(x, noise_level=0.1):
            return np.sin(5 * x[0]) * (1 - np.tanh(x[0] ** 2)) \
                   + np.random.randn() * noise_level

        opt = HyperOpt("bayes", model=f, param_space=[(-2.0, 2.0)],
                       acq_func="EI",  # the acquisition function
                       n_calls=15,  # the number of evaluations of f
                       n_random_starts=5,  # the number of random initialization points
                       noise=0.1 ** 2,  # the noise level (optional)
                       random_state=1234
                       )

        # executes bayesian optimization
        sr = opt.fit()
        if int(skopt.__version__.split('.')[1]) < 8:
            pass
        else:
            np.testing.assert_almost_equal(-0.909471164417979, sr.fun, 7)  # when called from same file where hyper_opt is saved
        return

    def test_grid_custom_model(self):
        # testing grid search algorithm for custom model
        def f(x, noise_level=0.1):
            return np.sin(5 * x) * (1 - np.tanh(x ** 2)) \
                   + np.random.randn() * noise_level

        opt = HyperOpt("grid",
                       model=f,
                       param_space=[Real(low=-2.0, high=2.0, num_samples=20)],
                       n_calls=15,  # the number of evaluations of f
                       )

        # executes bayesian optimization
        sr = opt.fit()
        assert len(sr) == 20
        return

    def test_named_custom_bayes(self):
        dims = [Integer(low=1000, high=2000, name='n_estimators'),
                Integer(low=3, high=6, name='max_depth'),
                Real(low=1e-5, high=0.1, name='learning_rate'),
                Categorical(categories=["gbtree", "dart"], name="booster")
                ]

        def f(**kwargs):
            data = pd.read_csv(fname)

            inputs = list(data.columns)
            inputs.remove('index')
            inputs.remove('target')
            inputs.remove('target_by_group')
            outputs = ['target']
            kwargs['objective'] = 'reg:squarederror'

            kwargs = Jsonize(kwargs)()

            model = Model(
                inputs=inputs,
                outputs=outputs,
                lookback=1,
                batches="2d",
                val_data="same",
                test_fraction=0.3,
                model={"xgboostregressor": kwargs},
                transformation=None,
                data=data,
                prefix='testing',
                verbosity=0)

            model.fit(indices="random")

            t, p = model.predict(indices=model.test_indices, pref='test')
            mse = FindErrors(t, p).mse()
            print(f"Validation mse {mse}")

            return mse

        opt = HyperOpt("bayes",
                       model=f,
                       param_space=dims,
                       use_named_args=True,
                       acq_func='EI',  # Expected Improvement.
                       n_calls=12,
                       # acq_optimizer='auto',
                       x0=[1000, 3, 0.01, "gbtree"],
                       n_random_starts=3,  # the number of random initialization points
                       random_state=2
                       )

        res = opt.fit()
        return


    def test_dl4seq_bayes(self):
        dims = [Integer(low=1000, high=2000, name='n_estimators'),
                Integer(low=3, high=6, name='max_depth'),
                Real(low=1e-5, high=0.1, name='learning_rate'),
                Categorical(categories=["gbtree", "dart"], name="booster")
                ]

        data = pd.read_csv(fname)
        inputs = list(data.columns)
        inputs.remove('index')
        inputs.remove('target')
        inputs.remove('target_by_group')
        outputs = ['target']

        dl4seq_args = {"inputs": inputs,
                       "outputs": outputs,
                       "lookback": 1,
                       "batches": "2d",
                       "val_data": "same",
                       "test_fraction": 0.3,
                       "model": {"xgboostregressor": {}},
                       #"ml_model_args": {'objective': 'reg:squarederror'}, TODO
                       "transformation": None
                       }

        opt = HyperOpt("bayes",
                       param_space=dims,
                       dl4seq_args=dl4seq_args,
                       data=data,
                       use_named_args=True,
                       acq_func='EI',  # Expected Improvement.
                       n_calls=12,
                       # acq_optimizer='auto',
                       x0=[1000, 3, 0.01, "gbtree"],
                       n_random_starts=3,  # the number of random initialization points
                       random_state=2
                       )

        opt.fit()
        return

    def test_dl4seq_grid(self):
        run_dl4seq("grid")
        print("dl4seq for grid passing")

    def test_dl4seq_random(self):
        run_dl4seq("random")
        print("dl4seq for random passing")
        return

    def test_hyperopt_basic(self):
        # https://github.com/hyperopt/hyperopt/blob/master/tutorial/01.BasicTutorial.ipynb
        def objective(x):
            return {
                'loss': x ** 2,
                'status': STATUS_OK,
                # -- store other results like this
                'eval_time': time.time(),
                'other_stuff': {'type': None, 'value': [0, 1, 2]},
                # -- attachments are handled differently
                'attachments':
                    {'time_module': pickle.dumps(time.time)}
                }

        optimizer = HyperOpt('tpe', model=objective, param_space=hp.uniform('x', -10, 10), max_evals=100)
        best = optimizer.fit()
        self.assertGreater(len(best), 0)
        return

    def test_hyperopt_multipara(self):
        # https://github.com/hyperopt/hyperopt/blob/master/tutorial/02.MultipleParameterTutorial.ipynb
        def objective(params):
            x, y = params['x'], params['y']
            return np.sin(np.sqrt(x**2 + y**2))

        space = {
            'x': hp.uniform('x', -6, 6),
            'y': hp.uniform('y', -6, 6)
        }

        optimizer = HyperOpt('tpe', model=objective, param_space=space, max_evals=100)
        best = optimizer.fit()
        self.assertEqual(len(best), 2)

    def test_hyperopt_multipara_multispace(self):
        def f(params):
            x1, x2 = params['x1'], params['x2']
            if x1 == 'james':
                return -1 * x2
            if x1 == 'max':
                return 2 * x2
            if x1 == 'wansoo':
                return -3 * x2

        search_space = {
            'x1': hp.choice('x1', ['james', 'max', 'wansoo']),
            'x2': hp.randint('x2', -5, 5)
        }

        optimizer = HyperOpt('tpe', model=f, param_space=search_space, max_evals=100)
        best = optimizer.fit()
        self.assertEqual(len(best), 2)

    def test_dl4seqModel_with_hyperopt(self):
        def fn(suggestion):

            data = pd.read_csv(fname)

            inputs = list(data.columns)
            inputs.remove('index')
            inputs.remove('target')
            inputs.remove('target_by_group')
            outputs = ['target']

            model = Model(
                inputs=inputs,
                outputs=outputs,
                model={"xgboostregressor": suggestion},
                data=data,
                prefix='test_tpe_xgboost',
                verbosity=0)

            model.fit(indices="random")

            t, p = model.predict(indices=model.test_indices, pref='test')
            mse = FindErrors(t, p).mse()
            print(f"Validation mse {mse}")

            return mse

        search_space = {
            'booster': hp.choice('booster', ['gbtree', 'dart']),
            'n_estimators': hp.randint('n_estimators', low=1000, high=2000),
            'learning_rate': hp.uniform('learning_rate', low=1e-5, high=0.1)
        }
        optimizer = HyperOpt('tpe', model=fn, param_space=search_space, max_evals=20,
                             opt_path=os.path.join(os.getcwd(), 'results\\test_tpe_xgboost'))
        optimizer.fit()
        self.assertEqual(len(optimizer.trials.trials), 20)


if __name__ == "__main__":
    unittest.main()