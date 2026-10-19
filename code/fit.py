"""
fit.py -- fitting discrete distributions of dependency length / flux size / flux weight /
potential flux.

Main model: truncated power law (power law with exponential cut-off)
    p(x) = C * x^(-beta) * exp(-lambda * x),   x = 1 .. xmax

Two estimators are provided:
  * fit_tpl_ols : ordinary least squares on log frequencies,
                  ln f(x) = a - beta ln x - lambda x   (linear in a, beta, lambda),
                  restricted to points with count >= min_count. This is the "regression"
                  view used in the June 2026 pages (R^2 in log space).
  * fit_tpl_mle : discrete maximum likelihood, normalised on 1..xmax (xmax = largest
                  observed value), with standard errors from the observed information.
Competing models (MLE, same support), for AIC comparison:
  * power law          (lambda = 0)
  * exponential        (beta = 0, i.e. geometric)
  * two-regime exponential with break point d* (Petrini & Ferrer-i-Cancho):
    ln p(x) = c - l1 x            for x <= d*
              c - l1 d* - l2 (x-d*) for x > d*
Also returned: the mode, mean, and a model-free tail decay rate lambda_tail
(OLS slope of ln f(x) on x for x > mode, count >= min_count).
"""
import math
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp


def _arrays(dist, min_x=1):
    xs = np.array(sorted(k for k, v in dist.items() if v > 0 and k >= min_x), dtype=float)
    cs = np.array([dist[int(x)] for x in xs], dtype=float)
    return xs, cs


def fit_tpl_ols(dist, min_count=10, min_x=1, min_p=0.0):
    xs, cs = _arrays(dist, min_x)
    m = (cs >= min_count) & (cs / cs.sum() >= min_p)
    xs, cs = xs[m], cs[m]
    if len(xs) < 4:
        return None
    y = np.log(cs / cs.sum())
    X = np.column_stack([np.ones_like(xs), -np.log(xs), -xs])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    # pure power law OLS for comparison (beta only), same points
    X2 = np.column_stack([np.ones_like(xs), -np.log(xs)])
    c2, *_ = np.linalg.lstsq(X2, y, rcond=None)
    r2_pl = 1 - float(((y - X2 @ c2) ** 2).sum()) / ss_tot if ss_tot > 0 else float("nan")
    return {"a": float(coef[0]), "beta": float(coef[1]), "lambda": float(coef[2]),
            "r2": r2, "beta_pl": float(c2[1]), "r2_pl": r2_pl, "npoints": int(len(xs)),
            "xmax_fit": int(xs.max())}


def _nll_tpl(params, xs, cs, support):
    beta, lam = params
    logw = -beta * np.log(support) - lam * support
    logz = logsumexp(logw)
    return -float((cs * (-beta * np.log(xs) - lam * xs - logz)).sum())


def _nll_two_regime(params, xs, cs, support, d):
    l1, l2 = params
    def lp(x):
        return np.where(x <= d, -l1 * x, -l1 * d - l2 * (x - d))
    logz = logsumexp(lp(support))
    return -float((cs * (lp(xs) - logz)).sum())


def _hessian(f, p, eps=1e-4):
    p = np.asarray(p, dtype=float)
    k = len(p)
    H = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            pp = p.copy(); pp[i] += eps; pp[j] += eps; fpp = f(pp)
            pm = p.copy(); pm[i] += eps; pm[j] -= eps; fpm = f(pm)
            mp = p.copy(); mp[i] -= eps; mp[j] += eps; fmp = f(mp)
            mm = p.copy(); mm[i] -= eps; mm[j] -= eps; fmm = f(mm)
            H[i, j] = (fpp - fpm - fmp + fmm) / (4 * eps * eps)
    return H


def fit_tpl_mle(dist, min_x=1, two_regime=True, xmax=None):
    xs, cs = _arrays(dist, min_x)
    if len(xs) < 3 or cs.sum() < 50:
        return None
    if xmax is None:
        xmax = int(xs.max())
    support = np.arange(min_x, xmax + 1, dtype=float)
    n = cs.sum()
    out = {"n": int(n), "xmax": xmax}

    f = lambda p: _nll_tpl(p, xs, cs, support)
    best = None
    for start in ((1.0, 0.1), (-2.0, 1.0), (0.0, 0.5), (2.5, 0.0)):
        r = minimize(f, start, method="Nelder-Mead",
                     options={"xatol": 1e-7, "fatol": 1e-7, "maxiter": 4000})
        if best is None or r.fun < best.fun:
            best = r
    beta, lam = best.x
    out.update({"beta": float(beta), "lambda": float(lam), "nll": float(best.fun)})
    try:
        H = _hessian(f, best.x)
        cov = np.linalg.inv(H)
        out["se_beta"] = float(math.sqrt(max(cov[0, 0], 0)))
        out["se_lambda"] = float(math.sqrt(max(cov[1, 1], 0)))
    except Exception:
        out["se_beta"] = out["se_lambda"] = float("nan")
    out["aic_tpl"] = 2 * 2 + 2 * best.fun

    # pure power law
    fpl = lambda p: _nll_tpl((p[0], 0.0), xs, cs, support)
    r = minimize(fpl, (2.0,), method="Nelder-Mead")
    out["beta_pl"] = float(r.x[0]); out["aic_pl"] = 2 * 1 + 2 * r.fun
    # pure exponential (geometric)
    fex = lambda p: _nll_tpl((0.0, p[0]), xs, cs, support)
    r = minimize(fex, (0.5,), method="Nelder-Mead")
    out["lambda_exp"] = float(r.x[0]); out["aic_exp"] = 2 * 1 + 2 * r.fun

    if two_regime and xmax >= 4:
        best2 = None
        for d in range(2, min(xmax - 1, 25) + 1):
            g = lambda p: _nll_two_regime(p, xs, cs, support, d)
            r = minimize(g, (1.0, 0.3), method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-6})
            if best2 is None or r.fun < best2[1]:
                best2 = (d, r.fun, r.x)
        d, nll2, (l1, l2) = best2
        out.update({"tr_break": int(d), "tr_l1": float(l1), "tr_l2": float(l2),
                    "aic_two": 2 * 3 + 2 * nll2})
    aics = {k: out[k] for k in ("aic_tpl", "aic_pl", "aic_exp", "aic_two") if k in out}
    out["best_model"] = min(aics, key=aics.get)[4:]
    return out


def describe(dist, min_count=10):
    xs, cs = _arrays(dist, 0)
    if cs.sum() == 0:
        return {}
    n = cs.sum()
    mean = float((xs * cs).sum() / n)
    mode = int(xs[np.argmax(cs)])
    var = float(((xs - mean) ** 2 * cs).sum() / n)
    cum = np.cumsum(cs) / n
    q99 = int(xs[np.searchsorted(cum, 0.99)])
    q999 = int(xs[min(np.searchsorted(cum, 0.999), len(xs) - 1)])
    m = (xs > mode) & (cs >= min_count)
    lam_tail = float("nan")
    if m.sum() >= 3:
        slope = np.polyfit(xs[m], np.log(cs[m]), 1)[0]
        lam_tail = float(-slope)
    return {"n": int(n), "mean": mean, "mode": mode, "var": var, "q99": q99, "q999": q999,
            "max": int(xs.max()), "lambda_tail": lam_tail}


def fit_all(dist, min_count=10, two_regime=True):
    d = {int(k): int(v) for k, v in dist.items()}
    res = {"desc": describe(d, min_count)}
    res["ols"] = fit_tpl_ols(d, min_count)
    # size-robust variant: drop the sparse far tail (relative frequency < 1e-4), so that
    # the points used do not depend on corpus size
    res["olsp"] = fit_tpl_ols(d, min_count, min_p=1e-4)
    res["mle"] = fit_tpl_mle(d, two_regime=two_regime)
    return res
