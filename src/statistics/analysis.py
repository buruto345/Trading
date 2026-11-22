"""Reproducible statistical analysis; no parameter selection or trading advice.

Rates are proportions, not percentages. Unresolved and ambiguous observations are
retained explicitly. Calendar-block resampling keeps simultaneous instruments in
the same sampled day, and exploratory subgroup analysis excludes final OOS data.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import binomtest, norm
from statsmodels.stats.multitest import multipletests

SEED = 20261121
RESOLVED = {"win", "loss", "breakeven", "break_even"}


def clean_json(value: Any) -> Any:
    """Convert non-finite numeric values to null for valid browser JSON."""
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def wilson(wins: int, n: int, confidence: float = .95) -> dict[str, Any]:
    if n == 0:
        return {"confidence": confidence, "low": None, "high": None,
                "margin_of_error": None, "normal_margin_of_error": None}
    z = float(norm.ppf((1 + confidence) / 2))
    p = wins / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n))/den
    half = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return {"confidence": confidence, "low": max(0., center-half),
            "high": min(1., center+half), "margin_of_error": half,
            "normal_margin_of_error": z*np.sqrt(p*(1-p)/n)}


def _numbers(df: pd.DataFrame, column: str) -> np.ndarray:
    if column not in df:
        return np.array([], dtype=float)
    a = pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=float)
    return a[np.isfinite(a)]


def _mean(a: np.ndarray) -> float | None:
    return float(a.mean()) if len(a) else None


def _distribution(a: np.ndarray) -> dict[str, Any]:
    return {"n": len(a), "mean": _mean(a),
            "median": float(np.median(a)) if len(a) else None,
            "std": float(np.std(a, ddof=1)) if len(a) > 1 else None,
            "min": float(a.min()) if len(a) else None,
            "max": float(a.max()) if len(a) else None,
            "percentiles": {str(p): float(np.percentile(a, p)) if len(a) else None
                            for p in [5, 25, 50, 75, 95]}}


def drawdown(outcomes: np.ndarray) -> dict[str, Any]:
    equity = np.r_[0., np.cumsum(outcomes)]
    dd = np.maximum.accumulate(equity)-equity
    return {"maximum": float(dd.max()), "average": float(dd[1:].mean()) if len(outcomes) else 0.,
            "equity": equity[1:].tolist(), "drawdown": dd[1:].tolist()}


def _max_streak(outcomes: list[str], target: str) -> int:
    best = current = 0
    for x in outcomes:
        current = current+1 if x == target else 0
        best = max(best, current)
    return best


def _performance(a: np.ndarray) -> dict[str, Any]:
    positive, negative = a[a > 0], a[a < 0]
    profit, loss = float(positive.sum()), float(-negative.sum())
    dd = drawdown(a)
    return {"gross_profit_r": profit, "gross_loss_r": loss,
            "net_result_r": float(a.sum()), "expectancy_r": _mean(a),
            "profit_factor": profit/loss if loss else None,
            "profit_factor_infinite": bool(profit > 0 and loss == 0),
            "average_winning_outcome_r": _mean(positive),
            "average_losing_outcome_r": _mean(negative),
            "maximum_drawdown_r": dd["maximum"], "average_drawdown_r": dd["average"],
            **_distribution(a)}


def summary(df: pd.DataFrame, bootstrap: bool = False) -> dict[str, Any]:
    """Summarize every input pattern, explicitly separating censoring and invalids."""
    frame = df.copy()
    if "outcome" not in frame:
        frame["outcome"] = pd.Series(dtype=str)
    if "exit_time" in frame:
        frame = frame.sort_values("exit_time", kind="stable", na_position="last")
    counts = frame["outcome"].value_counts().to_dict()
    wins, losses = int(counts.get("win", 0)), int(counts.get("loss", 0))
    breakeven = int(counts.get("breakeven", 0)+counts.get("break_even", 0))
    invalid = int(counts.get("invalid", 0))
    ambiguous, unresolved = int(counts.get("ambiguous", 0)), int(counts.get("unresolved", 0))
    entered = frame["traded"].fillna(False).astype(bool) if "traded" in frame else frame.outcome != "invalid"
    resolved, trades = wins+losses+breakeven, int(entered.sum())
    no_entry = int(((~entered)&(frame.outcome != "invalid")).sum())
    unresolved_trades = int(((frame.outcome == "unresolved")&entered).sum())
    ambiguous_trades = int(((frame.outcome == "ambiguous")&entered).sum())
    unknown = len(frame)-sum(int(counts.get(k, 0)) for k in RESOLVED|{"invalid", "ambiguous", "unresolved"})
    if unknown:
        raise ValueError(f"Unsupported outcome labels: {set(counts)-RESOLVED-{'invalid','ambiguous','unresolved'}}")
    r = frame[frame.outcome.isin(RESOLVED)]
    gross, net = _numbers(r, "gross_r"), _numbers(r, "net_r")
    ordered_outcomes = frame[entered].outcome.tolist()
    result = {"patterns": len(frame), "trades": trades, "resolved": resolved,
              "wins": wins, "losses": losses, "breakeven": breakeven,
              "unresolved": unresolved, "ambiguous": ambiguous, "invalid": invalid,
              "no_entry":no_entry,"unresolved_trades":unresolved_trades,"ambiguous_trades":ambiguous_trades,
              "win_rate": wins/resolved if resolved else None,
              "loss_rate": losses/resolved if resolved else None,
              "unresolved_rate": unresolved_trades/trades if trades else None,
              "ambiguous_rate": ambiguous_trades/trades if trades else None,
              "censored_rate": (ambiguous_trades+unresolved_trades)/trades if trades else None,
              "win_rate_all_trades_lower": wins/trades if trades else None,
              "win_rate_all_trades_upper": (wins+ambiguous_trades+unresolved_trades)/trades if trades else None,
              "break_even_win_rate_gross": 1/3,
              "risk_reward": 2,
              "wilson": {str(round(c*100)): wilson(wins, resolved, c) for c in [.9, .95, .99]},
              "gross": _performance(gross), "cost_adjusted": _performance(net),
              "max_consecutive_wins": _max_streak(ordered_outcomes, "win"),
              "max_consecutive_losses": _max_streak(ordered_outcomes, "loss"),
              "duration_bars": _distribution(_numbers(frame[entered], "duration_bars")),
              "duration_minutes": _distribution(_numbers(frame[entered], "duration_minutes")),
              "mfe_r": _distribution(_numbers(frame[entered], "mfe_r")),
              "mae_r": _distribution(_numbers(frame[entered], "mae_r")),
              "binomial_p_greater_than_one_third": float(binomtest(wins, resolved, 1/3, alternative="greater").pvalue) if resolved else None,
              "denominators": {"win_rate": "wins / resolved (wins + losses + breakeven)",
                               "loss_rate": "losses / resolved", "unresolved_rate": "unresolved entered trades / trades",
                               "ambiguous_rate": "ambiguous entered trades / trades", "censored_rate": "(unresolved entered trades + ambiguous entered trades) / trades",
                               "all_trades_bounds": "wins / trades to (wins + unresolved entered trades + ambiguous entered trades) / trades",
                               "expectancy": "sum(realized R) / finite resolved R records",
                               "trades": "sum(traded=True) when available; otherwise patterns - invalid",
                               "unresolved": "All unresolved pattern rows, including no-entry; unresolved_trades excludes no-entry."}}
    if bootstrap:
        result["bootstrap"] = block_bootstrap(frame)
    return clean_json(result)


def block_bootstrap(df: pd.DataFrame, block_days: int = 7, reps: int = 1000,
                    seed: int = SEED) -> dict[str, Any]:
    """Circular moving calendar-day blocks; pooled symbols resampled together.

    Confidence intervals are percentile bootstrap intervals. ESS is a descriptive
    variance ratio, not a count of proven independent observations. All calendar
    days between first and last available confirmation are retained (including
    zero-event days); circular wrapping avoids endpoint underrepresentation.
    """
    if block_days < 1 or reps < 2:
        raise ValueError("block_days >= 1 and reps >= 2 required")
    if df.empty or "confirmation_time" not in df:
        return {"available": False, "reason": "No timestamped observations"}
    frame = df.copy()
    dates = pd.to_datetime(frame.confirmation_time, utc=True).dt.floor("D")
    frame["day"] = dates
    frame["_n"] = frame.outcome.isin(RESOLVED).astype(int)
    frame["_w"] = (frame.outcome == "win").astype(int)
    frame["_gross"] = pd.to_numeric(frame.get("gross_r", pd.Series(np.nan, index=frame.index)), errors="coerce").where(frame._n == 1)
    frame["_net"] = pd.to_numeric(frame.get("net_r", pd.Series(np.nan, index=frame.index)), errors="coerce").where(frame._n == 1)
    frame["_ng"] = frame._gross.notna().astype(int)
    frame["_nn"] = frame._net.notna().astype(int)
    daily = frame.groupby("day")[["_n", "_w", "_gross", "_net", "_ng", "_nn"]].sum()
    daily = daily.reindex(pd.date_range(dates.min(), dates.max(), freq="D"), fill_value=0.)
    data = daily.to_numpy(dtype=float)
    total = data.sum(axis=0)
    n = int(total[0])
    if n == 0:
        return {"available": False, "reason": "No resolved observations"}
    days = len(data)
    block = min(block_days, days)
    rng = np.random.default_rng(seed)
    draws = np.empty((reps, 3))
    for i in range(reps):
        starts = rng.integers(0, days, size=int(np.ceil(days/block)))
        indices = ((starts[:, None] + np.arange(block)) % days).ravel()[:days]
        sums = data[indices].sum(axis=0)
        draws[i] = [sums[1]/sums[0] if sums[0] else np.nan,
                    sums[2]/sums[4] if sums[4] else np.nan,
                    sums[3]/sums[5] if sums[5] else np.nan]
    p = total[1]/total[0]
    finite_rates = draws[np.isfinite(draws[:, 0]), 0]
    variance = np.var(finite_rates, ddof=1) if len(finite_rates)>1 else np.nan
    ess = min(float(n), max(1., p*(1-p)/variance)) if variance > 0 and 0 < p < 1 else None
    rates_by_day = daily._w.div(daily._n.where(daily._n > 0)).dropna()
    lag1 = rates_by_day.autocorr(lag=1) if len(rates_by_day)>2 and rates_by_day.std()>0 else None
    ci = {}
    for level in [.9, .95, .99]:
        alpha = (1-level)/2
        ci[str(round(level*100))] = [float(np.quantile(finite_rates, alpha)), float(np.quantile(finite_rates, 1-alpha))] if len(finite_rates) else [None, None]
    def expectation_interval(column: int) -> list[float | None]:
        finite = draws[np.isfinite(draws[:, column]), column]
        return np.quantile(finite, [.025,.975]).tolist() if len(finite) else [None,None]
    return clean_json({"available": True, "method": "circular moving calendar-day block bootstrap",
                       "requested_block_days": block_days, "block_days": block, "calendar_days": days,
                       "replicates": reps, "valid_replicates": len(finite_rates), "seed": seed,
                       "resolved": n, "win_rate": p, "ci": ci,
                       "effective_sample_size": ess, "bootstrap_variance": variance,
                       "iid_binomial_variance": p*(1-p)/n,
                       "daily_win_rate_lag1_autocorrelation": lag1,
                       "autocorrelation_note": "Correlation across consecutive active days; inactive days omitted for this diagnostic only.",
                       "gross_expectancy_ci95": expectation_interval(1),
                       "net_expectancy_ci95": expectation_interval(2),
                       "win_rate_distribution": finite_rates.tolist(),
                       "gross_expectancy_distribution": draws[:,1].tolist(),
                       "net_expectancy_distribution": draws[:,2].tolist(),
                       "ess_note": "Heuristic min(n, max(1, p*(1-p)/Var_bootstrap(p))); undefined for p=0/1 or zero bootstrap variance. Not an independence guarantee.",
                       "dependence_test": "Evidence against gross p<=1/3 if bootstrap 95% interval lower endpoint >1/3; descriptive, not an exact null-centered p-value."})


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    t = pd.to_datetime(frame.confirmation_time, utc=True)
    frame["hour"] = t.dt.hour.astype(str).str.zfill(2)
    frame["weekday"] = t.dt.day_of_week.map({0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"})
    frame["month"] = t.dt.strftime("%Y-%m")
    frame["month_of_year"] = t.dt.month.astype(str).str.zfill(2)
    frame["quarter"] = t.dt.year.astype(str)+"-Q"+t.dt.quarter.astype(str)
    frame["year"] = t.dt.year.astype(str)
    asian = t.dt.tz_convert("Asia/Tokyo").dt.hour.between(9,17)
    london = t.dt.tz_convert("Europe/London").dt.hour.between(8,16)
    ny = t.dt.tz_convert("America/New_York").dt.hour.between(8,16)
    frame["session"] = [" + ".join(name for name, present in zip(["Asian","London","New York"], flags) if present) or "Other"
                        for flags in zip(asian,london,ny)]
    return frame


def _groups(df: pd.DataFrame, column: str) -> dict[str, Any]:
    if column not in df:
        return {}
    return {str(key): summary(group) for key,group in df.groupby(column, observed=True, dropna=False, sort=True)}


def _binned_features(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = df.copy()
    edges = {}
    training = frame[frame.partition == "in_sample"] if "partition" in frame else frame.iloc[:0]
    for column in ["fvg_size", "fvg_relative", "fvg_count", "sweep_size", "body_size", "wick_size", "delay_bars", "volatility", "volume"]:
        if column not in frame:
            continue
        finite = _numbers(training,column)
        if len(finite) < 4:
            continue
        cuts = np.unique(np.quantile(finite,[.25,.5,.75]))
        boundaries = np.r_[-np.inf,cuts,np.inf]
        labels = [f"Q{i+1}" for i in range(len(boundaries)-1)]
        frame[column+"_bin"] = pd.cut(pd.to_numeric(frame[column],errors="coerce"), boundaries, labels=labels, include_lowest=True).astype(str)
        edges[column] = {"internal_cuts": cuts.tolist(), "labels": labels,
                         "training_rows": len(finite), "fit_partition": "in_sample",
                         "note": "Pooled instrument thresholds; raw-price features are not directly comparable across instruments."}
    return frame,edges


def analyze(df: pd.DataFrame, bootstrap_reps: int = 1000) -> dict[str, Any]:
    frame = add_calendar_features(df) if len(df) else df.copy()
    if "outcome" not in frame:
        frame["outcome"] = pd.Series(dtype=str)
    frame, bin_edges = _binned_features(frame)
    overall = summary(frame)
    overall["bootstrap"] = block_bootstrap(frame, reps=bootstrap_reps)
    exploratory_frame = frame[frame.partition.isin(["in_sample","validation"])] if "partition" in frame else frame.iloc[:0]
    dimensions = ["symbol","direction","hour","weekday","month","quarter","year","session","regime","daily_bias","daily_bias_alignment"]
    dimensions += [col for col in frame if col.endswith("_bin")]
    exploratory = []
    for col in dimensions:
        if col not in exploratory_frame:
            continue
        for key, group in exploratory_frame.groupby(col,observed=True,dropna=False,sort=True):
            exploratory.append({"dimension":col,"group":str(key),**summary(group)})
    for columns,name in [(["symbol","direction"],"instrument_direction"),(["symbol","session"],"instrument_session"),(["weekday","hour"],"weekday_hour"),(["year","month_of_year"],"year_month")]:
        if all(c in exploratory_frame for c in columns):
            for keys,group in exploratory_frame.groupby(columns,observed=True,dropna=False,sort=True):
                exploratory.append({"dimension":name,"group":" | ".join(map(str,keys)),"keys":list(map(str,keys)),**summary(group)})
    valid = [i for i,row in enumerate(exploratory) if row["binomial_p_greater_than_one_third"] is not None]
    if valid:
        pvals = [exploratory[i]["binomial_p_greater_than_one_third"] for i in valid]
        rejected,adjusted,_,_ = multipletests(pvals,alpha=.05,method="fdr_bh")
        for idx,q,rej in zip(valid,adjusted,rejected):
            exploratory[idx]["bh_q_value"] = float(q)
            exploratory[idx]["bh_reject_05"] = bool(rej)
    partitions = _groups(frame,"partition")
    for name in partitions:
        partitions[name]["bootstrap"] = block_bootstrap(frame[frame.partition == name],reps=bootstrap_reps)
    sensitivity = {}
    for days in [1,7,30]:
        b = overall["bootstrap"] if days == 7 else block_bootstrap(frame,block_days=days,reps=bootstrap_reps)
        sensitivity[str(days)] = {k:v for k,v in b.items() if not k.endswith("distribution")}
    costs = []
    if "entry" in frame and "risk" in frame:
        for bps in [0,5,10,20]:
            adjusted = frame.copy()
            adjusted["cost_r"] = bps/10000*pd.to_numeric(adjusted.entry,errors="coerce")/pd.to_numeric(adjusted.risk,errors="coerce")
            adjusted["net_r"] = pd.to_numeric(adjusted.gross_r,errors="coerce")-adjusted.cost_r
            s = summary(adjusted)
            finite_costs = _numbers(adjusted[adjusted.outcome.isin(RESOLVED)],"cost_r")
            costs.append({"round_trip_bps":bps,"resolved":s["resolved"],"cost_adjusted":s["cost_adjusted"],
                          "mean_cost_r_resolved":_mean(finite_costs),
                          "break_even_rate_constant_2R_minus_1R_approx":(1+float(finite_costs.mean()))/3 if len(finite_costs) else None,
                          "note":"Approximation uses mean cost R and exact +2/-1 gross payoffs; gap losses and outcome-dependent costs break this identity. Funding not included."})
    r = frame[frame.outcome.isin(RESOLVED)].copy()
    if "exit_time" in r:
        r = r.sort_values("exit_time",kind="stable")
    gross = pd.to_numeric(r.get("gross_r",pd.Series(dtype=float)),errors="coerce").fillna(0).to_numpy(dtype=float)
    net = pd.to_numeric(r.get("net_r",pd.Series(dtype=float)),errors="coerce").fillna(0).to_numpy(dtype=float)
    curves = {"timestamps": pd.to_datetime(r.exit_time,utc=True).astype(str).tolist() if "exit_time" in r else [],
              "gross":drawdown(gross),"cost_adjusted":drawdown(net)}
    return clean_json({"overall":overall,"instruments":_groups(frame,"symbol"),"directions":_groups(frame,"direction"),
                       "partitions":partitions,"instrument_direction":_groups(frame.assign(instrument_direction=frame.symbol.astype(str)+" | "+frame.direction.astype(str)),"instrument_direction") if len(frame) else {},
                       "exploratory":exploratory,"bin_edges":bin_edges,"bootstrap_sensitivity":sensitivity,
                       "cost_sensitivity":costs,"curves":curves,
                       "method":{"combined_weighting":"One equally weighted valid hypothetical observation; instruments with more observations receive more weight. R is additive bookkeeping, not a capital-weighted portfolio.",
                                 "win_rate":"W/(W+L+B), with unresolved and ambiguous counts and all-trade bounds shown separately.",
                                 "wilson":"Independent Bernoulli approximation; not dependence-adjusted.",
                                 "binomial_test":"One-sided exact binomial H0 p<=1/3. Nominal +2/-1 gross-payoff threshold; not a test of cost-adjusted profitability, and IID assumption may fail.",
                                 "multiple_testing":f"Benjamini-Hochberg FDR alpha=.05 across {len(valid)} exploratory subgroup binomial tests in one family. Overlapping correlated groups and temporal dependence mean q-values are descriptive, not confirmed discoveries.",
                                 "exploration":"Only in_sample + validation; final out_of_sample excluded from subgroup discovery and bin fitting.",
                                 "sessions":"Exclusive labels of all active sessions: Asian 09:00–18:00 Asia/Tokyo; London 08:00–17:00 Europe/London; New York 08:00–17:00 America/New_York. IANA timezone DST respected. Other if none. Windows apply every calendar day; not exchange opening hours or holiday calendars.",
                                 "time_features":"At pattern confirmation, in UTC unless session explicitly local.",
                                 "drawdown":"Peak cumulative realized R minus current cumulative R, including initial zero. Ordered by exit_time; equal timestamp ties stable. No mark-to-market or portfolio capital constraints.",
                                 "streaks":"Chronological exit-time sequence; ambiguous/unresolved entered trades interrupt streaks; invalid and no-entry observations excluded.",
                                 "excursions":"As supplied by simulator; exit-bar extrema are bounds if intrabar sequence unknown.",
                                 "costs":"Sensitivity assumes total round-trip bps times entry/risk, subtracts from resolved gross R. Funding excluded.",
                                 "assumptions":"No strategy or threshold chosen by observed performance. Historical significance cannot establish future profitability."}})


def run_analysis(df: pd.DataFrame, output_dir: str | Path, bootstrap_reps: int = 1000) -> dict[str, Any]:
    result = analyze(df,bootstrap_reps=bootstrap_reps)
    path = Path(output_dir)
    path.mkdir(parents=True,exist_ok=True)
    (path/"statistical_analysis.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    pd.json_normalize(result["exploratory"]).to_csv(path/"exploratory_subgroups.csv",index=False)
    return result
