import numpy as np
import pandas as pd
from feature_config import common_coverage,validate_weights,allocations_from_weights,fx_decomposition,resolve_window

idx=pd.date_range('2020-01-31',periods=72,freq='ME')
prices=pd.DataFrame({'A':np.arange(72)+100.0,'B':np.r_[np.repeat(np.nan,12),np.arange(60)+50.0]},index=idx)

# Timeline must shorten to the latest inception among selected assets.
rs,re=resolve_window(idx,'10Y')
a0,a1,starts,ends,flags=common_coverage(prices,['A','B'],rs,re)
assert a0==prices['B'].dropna().index.min()
assert any('B: history begins' in x for x in flags)

# Weight and nominal identities.
w=validate_weights(['A','B'],{'A':.6,'B':.4}); assert np.isclose(w.sum(),1)
a=allocations_from_weights(['A','B'],{'A':.6,'B':.4},1_000_000); assert np.isclose(a.sum(),1_000_000)
try:
 validate_weights(['A','B'],{'A':.7,'B':.4}); raise AssertionError('bad weights accepted')
except ValueError: pass

# Exact multiplicative FX decomposition identity.
local=pd.Series([100.,110.],index=[idx[0],idx[-1]])
fx=pd.Series([15.,18.],index=[idx[0],idx[-1]])
d=fx_decomposition(local,fx,idx[0],idx[-1])
assert np.isclose(d['Local appreciation']+d['FX contribution']+d['Interaction'],d['ZAR price return'])
print('feature_config validation: PASS')
