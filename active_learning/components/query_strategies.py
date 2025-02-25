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

from abc import ABC, abstractmethod

import numpy as np
from scipy import optimize
from scipy.stats import rankdata
from sklearn.base import BaseEstimator

from active_learning.components import utils


class IQueryStrategy(ABC, BaseEstimator):

    def __init__(self, bounds):
        super().__init__()
        self.__active_function = None
        self.__bounds = bounds

    def set_active_function(self, fun: callable):
        self.__active_function = fun

    def set_bounds(self, bounds):
        self.__bounds = bounds

    @abstractmethod
    def query(self, *args):
        pass

    @property
    def bounds(self):
        return self.__bounds

    @property
    def active_function(self):
        return self.__active_function

    def __add__(self, other):
        l, r = isinstance(self, CompositeStrategy), isinstance(other, CompositeStrategy)
        if isinstance(self, CompositeStrategy) and isinstance(other, CompositeStrategy):
            if len(self.strategy_list) == 1:
                return CompositeStrategy(self.bounds,
                                         [*self.strategy_list, *other.strategy_list],
                                         [*self.strategy_weights, *other.strategy_weights])
            return CompositeStrategy(
                self.bounds, self.strategy_list, self.strategy_weights) + CompositeStrategy(
                self.bounds, other.strategy_list, other.strategy_weights)
        elif isinstance(self, CompositeStrategy) and not r:
            return CompositeStrategy(self.bounds,
                                     [*self.strategy_list, other],
                                     [*self.strategy_weights, 1])
        elif isinstance(other, CompositeStrategy) and not l:
            return CompositeStrategy(self.bounds,
                                     [self, *other.strategy_list],
                                     [1, *other.strategy_weights])
        else:
            return CompositeStrategy(self.bounds, [self, other], [1, 1])

    def __mul__(self, other):
        return CompositeStrategy(self.bounds, [self], [other])

    def __rmul__(self, other):
        return self.__mul__(other)


class CompositeStrategy(IQueryStrategy):
    def __init__(self, bounds, strategy_list: list[IQueryStrategy], strategy_weights: list[float]):
        super().__init__(bounds)
        self.strategy_list = strategy_list
        self.strategy_weights = strategy_weights

    def query(self, *args):
        if len(args) != 0 and isinstance(args[0], int):
            x = np.array([np.random.choice(self.strategy_list, p=np.array(self.strategy_weights)).query(1)
                          for _ in range(args[0])])[:, :, 0]
        else:
            select = np.random.choice(self.strategy_list, p=np.array(self.strategy_weights))
            x = select.query(*args)
        return x


class ServiceQueryMax(IQueryStrategy):
    def __init__(self, x0, bounds=None, xtol=0.001, maxiter=40, disp=True):
        super().__init__(bounds)
        self.__xtol = xtol
        self.__maxiter = maxiter
        self.__disp = disp
        self.__x0 = x0.reshape(1, -1)

    def query(self, *args_) -> np.ndarray:
        def fun(*args, **kwargs):
            return - self.active_function(*args, **kwargs)

        res = optimize.minimize(
            fun, x0=self.__x0.flatten(),
            bounds=self.bounds, options={'gtol': self.__xtol, 'disp': self.__disp}).x
        return res.reshape(self.__x0.shape)


class ServiceQueryVariancePDF(IQueryStrategy):
    def __init__(self, bounds=None, num_eval: int = int(1e5)):
        super().__init__(bounds)
        self.num_eval = num_eval

        self.__rng = np.random.default_rng()

    def query(self, size):
        assert size > 0
        candidates = utils.scipy_lhs_sampler(x_limits=np.array(self.bounds), size=self.num_eval)
        probability = self.active_function(candidates)
        probability = probability + 1e-5
        probability /= np.sum(probability)
        return self.__rng.choice(candidates, size=size, replace=False, p=probability, axis=0)


class ServiceReject(IQueryStrategy):
    def __init__(self, bounds=None, num_eval: int = int(1e5)):
        super().__init__(bounds)

        self.num_eval = num_eval
        self.__rng = np.random.default_rng()

    def query(self, size):
        candidates = utils.scipy_lhs_sampler(x_limits=np.array(self.bounds), size=self.num_eval)
        af = self.active_function(candidates)
        order = rankdata(-af, method="ordinal")
        selector = order <= size
        return candidates[selector]


class ServiceUniform(IQueryStrategy):
    def __init__(self, bounds=None):
        super().__init__(bounds)

    def query(self, size):
        candidates = utils.scipy_lhs_sampler(x_limits=np.array(self.bounds), size=size)
        return candidates

