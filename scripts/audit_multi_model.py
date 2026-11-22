"""Independent SQL reconciliation and baseline integrity check."""
from pathlib import Path
import json,sys
import duckdb
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_multi_model import digest
OUT=ROOT/'reports/multi_model'

def main():
    p=pd.read_parquet(OUT/'patterns.parquet');s=pd.read_parquet(OUT/'simulations.parquet')
    db=duckdb.connect();db.register('observations',s)
    counts=db.execute("SELECT track,model,count(*) patterns,count(*) FILTER(WHERE outcome='win') wins,count(*) FILTER(WHERE outcome='loss') losses,avg(gross_r) gross,avg(net_r) net FROM observations GROUP BY track,model ORDER BY track,model").fetchdf()
    totals=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
    for row in counts.itertuples():
        target=next(x for x in totals if x['track']==row.track and x['model']==row.model)
        assert row.patterns==target['patterns'] and row.wins==target['wins'] and row.losses==target['losses']
        assert np.isclose(row.gross,target['gross']['expectancy_r'])
        assert np.isclose(row.net,target['cost_adjusted']['expectancy_r'])
        assert target['resolved']+target['unresolved']+target['ambiguous']+target['invalid']==target['patterns']
    preservation=json.loads((OUT/'preservation_before.json').read_text(encoding='utf-8'))
    assert all(digest(ROOT/path)==h for path,h in preservation.items())
    assert len(s)==2*len(p) and not p.pattern_id.duplicated().any()
    assert p.loc[p.model.isin([1,2,4]),'revisit_idx'].gt(p.loc[p.model.isin([1,2,4]),'formation_idx']).all()
    for symbol,g in p.groupby('symbol'):
        candles=pd.read_parquet(ROOT/f'data/processed/{symbol}_5m.parquet')
        candles=candles[candles.timestamp<pd.Timestamp('2026-11-21T00:00Z')]
        if symbol=='XAUUSDT':candles=candles[candles.timestamp>=pd.Timestamp('2026-01-05T00:00Z')]
        candles=candles.reset_index(drop=True)
        for row in g.itertuples():
            details=getattr(row,'fvg_details',None)
            if isinstance(details,str):
                for gap in json.loads(details):
                    timestamp=candles.timestamp.iloc[int(gap['formation_idx'])]+pd.Timedelta(minutes=5)
                    assert timestamp==pd.Timestamp(gap['formation_time'])
                    assert timestamp<=row.confirmation_time
    counts.to_csv(OUT/'independent_sql.csv',index=False)
    result={'status':'passed','sql_groups':len(counts),'patterns':len(p),'simulations':len(s),'protected_files_unchanged':len(preservation)}
    (OUT/'independent_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)
if __name__=='__main__':main()
