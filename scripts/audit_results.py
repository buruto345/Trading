"""Independent Polars/NumPy reconciliation of stored final results."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import polars as pl
import numpy as np


def audit(root=ROOT):
    output=Path(root)/'reports/results'
    frame=pl.read_parquet(output/'simulations.parquet')
    analysis=json.loads((output/'statistical_analysis.json').read_text(encoding='utf-8'))
    def check(frame,stats):
        assert frame.height==stats['patterns']
        assert frame['pattern_id'].n_unique()==frame.height
        for outcome,metric in [('win','wins'),('loss','losses'),('ambiguous','ambiguous'),('unresolved','unresolved'),('invalid','invalid')]:
            assert frame.filter(pl.col('outcome')==outcome).height==stats[metric]
        resolved=frame.filter(pl.col('outcome').is_in(['win','loss']))
        assert resolved.height==stats['resolved']
        if resolved.height:
            assert abs(resolved.filter(pl.col('outcome')=='win').height/resolved.height-stats['win_rate'])<1e-12
            for column,key in [('gross_r','gross'),('net_r','cost_adjusted')]:
                assert np.isclose(resolved[column].sum(),stats[key]['net_result_r'])
                assert np.isclose(resolved[column].mean(),stats[key]['expectancy_r'])
        assert frame['traded'].sum()==stats['trades']
    check(frame,analysis['overall'])
    for symbol,s in analysis['instruments'].items():check(frame.filter(pl.col('symbol')==symbol),s)
    for partition,s in analysis['partitions'].items():check(frame.filter(pl.col('partition')==partition),s)
    development=frame.filter(pl.col('partition')!='out_of_sample')
    exploratory_symbol= [x for x in analysis['exploratory'] if x['dimension']=='symbol']
    assert sum(x['patterns'] for x in exploratory_symbol)==development.height
    assert all(x['fit_partition']=='in_sample' for x in analysis['bin_edges'].values())
    result={'status':'passed','library':'Polars independent of pandas aggregation','total_rows':frame.height,'checks':['Overall, instrument and partition counts match Parquet','Win rate numerator/denominator reconstructed','Gross/net sum and expectancy reconstructed','Actual entries counted via traded','Exploratory totals exclude OOS','All quantile edges fitted only in_sample']}
    (output/'independent_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':print(json.dumps(audit(),indent=2))
