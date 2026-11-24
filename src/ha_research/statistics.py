"""Outcome reporting interface, gated on explicit externally established definitions."""
import pandas as pd
from scipy.stats import binomtest
from src.statistics.analysis import wilson

UNRESOLVED = [
    'minimum_pullback_candles', 'minimum_impulse_candles', 'pullback_color_continuity',
    'maximum_doji_body_ratio', 'doji_wick_ratio', 'intermediate_characteristics',
    'maximum_intermediate_candles', 'entry_price', 'stop_loss', 'outcome_labeling',
    'maximum_observation_period', 'ambiguous_intrabar_handling',
]


def require_definitions(definitions):
    missing = [key for key in UNRESOLVED if not definitions.get(key)]
    if missing:
        raise ValueError('Unresolved definitions: ' + ', '.join(missing))


def outcome_report(observations, definitions, independence_evidence=None):
    """No outcome generation. Call only with documented, auditable historical labels.

    A supplied independence rationale is an assertion requiring external review,
    never evidence inferred from unique IDs or non-overlapping timestamps.
    """
    require_definitions(definitions)
    required = {'observation_id', 'symbol', 'period', 'partition', 'outcome'}
    if not required.issubset(observations.columns):
        raise ValueError('Missing outcome columns: ' + str(required - set(observations.columns)))
    if observations[list(required)].isna().any().any():
        raise ValueError('Outcome fields cannot be null')
    if observations.observation_id.duplicated().any():
        raise ValueError('Duplicate observation_id')
    if not observations.outcome.isin(['win', 'loss', 'ambiguous', 'unresolved']).all():
        raise ValueError('Unsupported outcome label')
    if not observations.partition.isin(['in_sample', 'validation', 'out_of_sample']).all():
        raise ValueError('Unsupported partition')

    def describe(df):
        wins, losses = int(df.outcome.eq('win').sum()), int(df.outcome.eq('loss').sum())
        n = wins + losses
        unresolved = len(df) - n
        return dict(sample_size=len(df), resolved=n, wins=wins, losses=losses,
                    ambiguous=int(df.outcome.eq('ambiguous').sum()),
                    unresolved=int(df.outcome.eq('unresolved').sum()),
                    observed_proportion=wins / n if n else None,
                    independent_observations=n if independence_evidence else None,
                    independence_status='externally asserted' if independence_evidence else 'not established',
                    wilson95_iid_reference=wilson(wins, n),
                    iid_interval_caution='Not dependence-robust; not a confirmatory CI without independent trials.',
                    p_equal_075_iid=float(binomtest(wins, n, .75).pvalue) if n and independence_evidence else None,
                    all_observations_bounds=[wins / len(df), (wins + unresolved) / len(df)] if len(df) else [None, None])

    groups = []
    for keys, group in observations.groupby(['symbol', 'period', 'partition'], sort=True):
        groups.append(dict(zip(['symbol', 'period', 'partition'], keys)) | describe(group))
    return dict(overall=describe(observations), groups=groups, definitions=definitions,
                independence_evidence=independence_evidence,
                cautions=['Selection bias and missing data can change the observation population.',
                          'Use causal features and purge outcomes crossing split boundaries.',
                          'Multiple experiments require a frozen testing family and correction.',
                          'Do not optimize on OOS; retrospective reused OOS is not independent validation.',
                          'Cross-market and serial dependence require a prespecified block/cluster analysis.'])
