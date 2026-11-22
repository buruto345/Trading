"""Hand-calculated statistical fixtures, independent of historical data."""
import json

import numpy as np
import pandas as pd
import pytest

from src.statistics.analysis import (add_calendar_features, analyze, block_bootstrap,
                                     drawdown, run_analysis, summary, wilson)


def fixture_frame():
    outcomes = ["win","loss","unresolved","ambiguous","invalid","win"]
    times = pd.date_range("2024-01-01",periods=6,freq="D",tz="UTC")
    return pd.DataFrame({"symbol":["BTCUSDT"]*6,"direction":["bullish"]*6,
        "confirmation_time":times,"entry_time":times,"exit_time":times,
        "outcome":outcomes,"gross_r":[2.,-1.,np.nan,np.nan,np.nan,2.],
        "net_r":[1.9,-1.1,np.nan,np.nan,np.nan,1.9],"cost_r":[.1]*6,
        "duration_bars":[3,4,288,1,0,2],"mfe_r":[2,.4,1,2,np.nan,2],
        "mae_r":[.3,1,.9,1,np.nan,.2],"entry":[100]*6,"risk":[1]*6,
        "partition":["in_sample"]*4+["validation","out_of_sample"],
        "fvg_size":[1,2,3,4,100,1000]})


def test_win_rate_denominator_and_all_trade_bounds():
    s = summary(fixture_frame())
    assert (s["patterns"],s["trades"],s["resolved"]) == (6,5,3)
    assert (s["wins"],s["losses"],s["unresolved"],s["ambiguous"],s["invalid"]) == (2,1,1,1,1)
    assert s["win_rate"] == pytest.approx(2/3)
    assert s["win_rate_all_trades_lower"] == .4
    assert s["win_rate_all_trades_upper"] == .8
    assert s["unresolved_rate"] == .2


def test_expectancy_profit_factor_and_net_cost():
    s = summary(fixture_frame())
    assert s["gross"]["expectancy_r"] == 1
    assert s["gross"]["profit_factor"] == 4
    assert s["gross"]["gross_profit_r"] == 4
    assert s["gross"]["gross_loss_r"] == 1
    assert s["cost_adjusted"]["expectancy_r"] == pytest.approx(.9)
    assert s["gross"]["std"] == pytest.approx(np.sqrt(3))


def test_wilson_known_reference():
    interval = wilson(50,100)
    assert interval["low"] == pytest.approx(.40383153,abs=1e-7)
    assert interval["high"] == pytest.approx(.59616847,abs=1e-7)
    assert interval["margin_of_error"] == pytest.approx(.09616847,abs=1e-7)


@pytest.mark.parametrize("wins,n",[(0,10),(10,10),(1,1),(0,1)])
def test_wilson_edges(wins,n):
    c = wilson(wins,n)
    assert 0 <= c["low"] <= c["high"] <= 1


def test_empty_wilson_does_not_invent_rate():
    assert wilson(0,0)["low"] is None
    s = summary(pd.DataFrame())
    assert s["win_rate"] is None
    assert s["patterns"] == 0


def test_drawdown_includes_initial_zero():
    d = drawdown(np.array([-1.,2.,-1.,-1.,2.]))
    assert d["equity"] == [-1,1,0,-1,1]
    assert d["drawdown"] == [1,0,1,2,0]
    assert d["maximum"] == 2
    assert d["average"] == .8


def test_censored_observation_breaks_streak():
    s = summary(fixture_frame())
    assert s["max_consecutive_wins"] == 1
    assert s["max_consecutive_losses"] == 1


def test_unknown_outcome_rejected():
    with pytest.raises(ValueError,match="Unsupported outcome"):
        summary(pd.DataFrame({"outcome":["mystery"]}))


def test_zero_losses_pf_explicit_infinite_flag():
    s = summary(fixture_frame().iloc[[0]])
    assert s["gross"]["profit_factor"] is None
    assert s["gross"]["profit_factor_infinite"] is True


def test_bootstrap_is_seeded_and_preserves_counts():
    data = pd.concat([fixture_frame().assign(confirmation_time=lambda x:x.confirmation_time+pd.Timedelta(days=7*i)) for i in range(12)],ignore_index=True)
    a = block_bootstrap(data,reps=50)
    b = block_bootstrap(data,reps=50)
    assert a == b
    assert a["resolved"] == 36
    assert a["calendar_days"] == 83
    assert a["valid_replicates"] == 50
    assert a["ci"]["95"][0] <= a["ci"]["95"][1]


def test_bootstrap_never_resolves_censored_rows():
    df = fixture_frame().iloc[[2,3]]
    b = block_bootstrap(df,reps=10)
    assert b["available"] is False


def test_sessions_dst_local_definitions():
    df = pd.DataFrame({"confirmation_time":pd.to_datetime(["2024-01-15T08:30Z","2024-07-15T07:30Z","2024-01-15T13:30Z","2024-07-15T12:30Z"],utc=True)})
    s = add_calendar_features(df).session.tolist()
    assert "London" in s[0] and "London" in s[1]
    assert "New York" in s[2] and "New York" in s[3]
    assert "Asian" in s[0]


def test_exploration_excludes_final_oos_and_cuts_fit_training():
    data = fixture_frame()
    analysis = analyze(data,bootstrap_reps=20)
    symbol = [g for g in analysis["exploratory"] if g["dimension"]=="symbol"]
    assert symbol[0]["patterns"] == 5
    assert symbol[0]["wins"] == 1
    assert analysis["overall"]["wins"] == 2
    assert analysis["bin_edges"]["fvg_size"]["internal_cuts"] == [1.75,2.5,3.25]
    assert analysis["partitions"]["out_of_sample"]["wins"] == 1


def test_multiple_testing_q_values_bounded():
    analysis = analyze(fixture_frame(),bootstrap_reps=20)
    groups = [g for g in analysis["exploratory"] if "bh_q_value" in g]
    assert groups
    assert all(0 <= g["bh_q_value"] <= 1 for g in groups)
    assert all(g["bh_q_value"]+1e-15 >= g["binomial_p_greater_than_one_third"] for g in groups)


def test_cost_sensitivity_hand_calculation():
    analysis = analyze(fixture_frame(),bootstrap_reps=20)
    costs = {row["round_trip_bps"]:row for row in analysis["cost_sensitivity"]}
    assert costs[0]["cost_adjusted"]["expectancy_r"] == 1
    assert costs[10]["cost_adjusted"]["expectancy_r"] == pytest.approx(.9)
    assert costs[20]["cost_adjusted"]["expectancy_r"] == pytest.approx(.8)


def test_json_results_reconcile_and_are_strict_json(tmp_path):
    results = run_analysis(fixture_frame(),tmp_path,bootstrap_reps=20)
    stored = json.loads((tmp_path/"statistical_analysis.json").read_text(encoding="utf-8"))
    assert stored["overall"]["patterns"] == 6
    assert sum(g["patterns"] for g in stored["partitions"].values()) == 6
    assert stored == results
    assert (tmp_path/"exploratory_subgroups.csv").exists()
    json.dumps(results,allow_nan=False)


def test_breakeven_counted_in_resolved_denominator():
    frame = fixture_frame().iloc[:2].copy()
    frame.loc[frame.index[1],"outcome"] = "breakeven"
    frame.loc[frame.index[1],["gross_r","net_r"]] = [0,-.1]
    s = summary(frame)
    assert s["win_rate"] == .5
    assert s["breakeven"] == 1


def test_partition_bootstrap_independence():
    result = analyze(fixture_frame(),bootstrap_reps=20)
    assert result["partitions"]["out_of_sample"]["bootstrap"]["resolved"] == 1
    assert result["partitions"]["in_sample"]["bootstrap"]["resolved"] == 2


def test_unentered_boundary_patterns_do_not_count_as_trades():
    frame = fixture_frame()
    frame["traded"] = [True,True,False,True,False,True]
    s = summary(frame)
    assert s["patterns"] == 6
    assert s["trades"] == 4
    assert s["unresolved"] == 1
    assert s["unresolved_trades"] == 0
    assert s["no_entry"] == 1
    assert s["unresolved_rate"] == 0
    assert s["win_rate_all_trades_upper"] == .75


def test_empty_analysis():
    s = analyze(pd.DataFrame(),bootstrap_reps=20)
    assert s["overall"]["patterns"] == 0
    assert s["overall"]["win_rate"] is None


def test_calendar_blocks_keep_simultaneous_instruments_together():
    t = pd.date_range("2020-01-01",periods=100,freq="D",tz="UTC")
    outcomes = ["win"]*50+["loss"]*50
    one = pd.DataFrame({"confirmation_time":t,"symbol":"BTCUSDT","outcome":outcomes,
                        "gross_r":[2.]*50+[-1.]*50,"net_r":[1.9]*50+[-1.1]*50})
    two = pd.concat([one,one.assign(symbol="ZECUSDT")],ignore_index=True)
    a = block_bootstrap(one,reps=200)
    b = block_bootstrap(two,reps=200)
    assert a["win_rate_distribution"] == b["win_rate_distribution"]
    assert b["resolved"] == 2*a["resolved"]
    assert a["effective_sample_size"] == pytest.approx(b["effective_sample_size"])
    assert a["bootstrap_variance"] > a["iid_binomial_variance"]
    assert a["effective_sample_size"] < a["resolved"]

