"""
    Function: detrend dataset.

             (1) Detrends a signal with the smoothness priors approach implemented based on M. P.
                 Tarvainen, TBME, 2002ss

    Author: Bike Chen
    Email: chenbike@xinktech.com
    Date: 18-July-2019
"""
import numpy as np
import scipy.sparse as sparse

def Detrend(x, param_lambda=100):
    """
    :param x: Signal to detrend
    :param param_lambda: lambda value to use for detrending
    :return: the detrended signal
    """
    T = len(x)
    I = sparse.eye(T)
    B = np.ones((T-2, 1)) * np.array([1, -2, 1])
    D2 = sparse.diags(B.T, [0, 1, 2], shape=(T-2, T))
    # D2 = sparse.spdiags(B.T, [0, 1, 2], T-2, T) # spdiags is different from Matlab spdiags.
    sr = np.asarray(x, dtype=np.float32) # (5,)
    C = np.linalg.inv((I + np.power(param_lambda, 2) * np.dot(D2.T, D2)).A) # ".A" used for np.linalg.inv
    y =  np.dot((I - C), sr)
    return y

if __name__ == "__main__":
    # T = 6
    # I = sparse.eye(T)
    # print(I) # dict(I.todok())
    # print(I.A)
    # B = np.ones((T-2, 1)) * np.array([1, -2, 1])
    # D2 = sparse.diags(B.T, [0, 1, 2], shape=(T-2, T))
    # print(D2)
    # print(D2.A)

    x = np.linspace(1, 3, 5)
    y = np.sin(x)
    out = Detrend(y)
    print(out)






















