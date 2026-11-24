"""Check all saved price/geometry fields and original timestamp normalization."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_ha_validation import OUT,OLD,read,save
from src.ha_validation import reference as ref
from src.data_validation.validator import normalize_timestamp


def main():
    rows=[]
    for symbol in read(OUT/'validation_summary.json')['instruments']:
        f=pd.read_parquet(ROOT/f'data/processed/ha_m1/{symbol}_features.parquet')
        e=pd.read_parquet(OLD/f'{symbol}_observations.parquet');i=e.doji_index.to_numpy();d=e.direction.to_numpy()
        hc=f.ha_close.to_numpy()[i];ad=np.where(d==1,f.ha_low.to_numpy()[i],f.ha_high.to_numpy()[i]);risk=d*(hc-ad);fav=hc+d*risk
        mc=f.close.to_numpy()[i]
        expected=dict(reference=hc,adverse=ad,risk=risk,favorable=fav,doji_market_close=mc,
            reference_minus_market_close=hc-mc,market_close_outside_boundaries=(mc<=np.minimum(ad,fav))|(mc>=np.maximum(ad,fav)))
        g=ref.geometry(f);oldg=pd.read_parquet(ROOT/f'reports/ha_descriptive/{symbol}_geometry.parquet')
        expected.update(body_ratio=g.body_ratio.to_numpy()[i],doji_range=g['range'].to_numpy()[i])
        fields={k:int((e[k].to_numpy()!=a).sum()) for k,a in expected.items()}
        geom={k:int((~np.isclose(g[k],oldg[k],rtol=0,atol=0,equal_nan=True)).sum()) for k in ['body_ratio','range','tolerance']}
        raw=pd.read_parquet(ROOT/f'data/processed/ha_m1/{symbol}_1m.parquet',columns=['timestamp','source_timestamp'])
        times=normalize_timestamp(raw.source_timestamp)
        prefixes=[]
        for n in [1000,10000,50000,len(raw)//2,len(raw)-1]:
            prefix=normalize_timestamp(raw.source_timestamp.iloc[:n])
            prefixes.append(dict(rows=n,mismatches=int(prefix.ne(times.iloc[:n]).sum())))
        rows.append(dict(symbol=symbol,observations=len(e),saved_field_mismatches=fields,geometry_numeric_mismatches=geom,
            normalized_source_timestamp_mismatches=int(times.ne(raw.timestamp).sum()),
            explicit_ms_conversion_mismatches=int(pd.to_datetime(raw.source_timestamp,unit='ms',utc=True).ne(raw.timestamp).sum()),
            normalization_prefixes=prefixes,source_timestamp_min=int(raw.source_timestamp.min()),source_timestamp_max=int(raw.source_timestamp.max())))
    save('supplemental_field_audit.json',rows)
    assert all(not any(r['saved_field_mismatches'].values()) and not any(r['geometry_numeric_mismatches'].values()) and not r['normalized_source_timestamp_mismatches'] and not r['explicit_ms_conversion_mismatches'] and not any(x['mismatches'] for x in r['normalization_prefixes']) for r in rows)
    print('All stored price/geometry fields and 15 normalization prefixes agree.')


if __name__=='__main__':main()
