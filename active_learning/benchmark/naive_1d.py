# Copyright 2024 Eurobios
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn.model_selection
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF

from active_learning import ActiveSurfaceLearner
from active_learning.benchmark.base import TestingClass
from active_learning.benchmark.utils import plot_iter
from active_learning.components.active_criterion import ServiceGaussianProcessVariance
from active_learning.components.active_criterion import ServiceVarianceCriterion
from active_learning.components.query_strategies import ServiceQueryVariancePDF


def GP_regression_std(regressor, X):
    _, std = regressor.predict(X, return_std=True)
    return np.argmax(std)


RNG = np.random.default_rng(seed=0)

bounds = [[0, 1]]


def unknown_function(x):
    return x ** 5 * np.sin(10 * np.pi * x)


def sampler(n):
    x0 = np.random.uniform(*bounds[0], size=n)
    return pd.DataFrame(x0)


def make_1d_example():
    kernel = 1 * RBF(0.01)
    krg = GaussianProcessRegressor(kernel=kernel)

    # ======================================================================================
    #
    #                           Gaussian
    # ======================================================================================
    n0 = 10
    budget = 20
    steps = 8
    plt.style.use("bmh")
    plt.rcParams["font.family"] = "ubuntu"
    plt.rcParams['axes.facecolor'] = "white"

    learner_bagging = ActiveSurfaceLearner(
        active_criterion=ServiceVarianceCriterion(
            krg, splitter=sklearn.model_selection.ShuffleSplit(
                n_splits=2,
                train_size=0.8)),
        query_strategy=ServiceQueryVariancePDF(bounds, num_eval=2000),
        bounds=bounds

    )

    testing_bootstrap = TestingClass(
        function=unknown_function,
        budget=budget,
        budget_0=n0, learner=learner_bagging,
        x_sampler=sampler, n_steps=steps, bounds=bounds

    )

    testing_bootstrap.run()

    plot_iter(testing_bootstrap)
    plt.tight_layout()
    plt.show()

    plt.savefig(".public//example_krg.png", dpi=300)

    testing = TestingClass(
        budget,
        n0,
        unknown_function,
        ServiceGaussianProcessVariance(kernel=kernel),
        ServiceQueryVariancePDF(bounds, num_eval=2000),
        sampler, steps, bounds=bounds)

    testing.run()

    plot_iter(testing)

    plt.tight_layout()
    plt.show()
    plt.savefig(".public/example_krg_2")

    err1 = pd.DataFrame(testing_bootstrap.metric)
    err2 = pd.DataFrame(testing.metric)
    budgets = pd.DataFrame(testing.learner.result).loc["budget"].astype(float)

    plt.figure(dpi=300)
    plt.plot(budgets, err1.values, c="r", label="bootstrap")
    plt.plot(budgets, err2.values, label="regular")
    plt.legend()
    plt.savefig(".public/example_krg_3")


if __name__ == '__main__':
    make_1d_example()
