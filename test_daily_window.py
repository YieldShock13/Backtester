import numpy as np
import pandas as pd
from daily_window import use_daily_window, build_daily_components, align_daily_window, periods_per_year, validate_period_return_identity


def hist(close,div=None,idx=None):
    idx=pd.date_range('2026-03-02',periods=len(close),freq='D') if idx is None else pd.DatetimeIndex(idx)
    return pd.DataFrame({'Close':close,'Dividends':np.zeros(len(close)) if div is None else div},index=idx)


def test_frequency_policy():
    assert use_daily_window('1W',None,None)
    assert use_daily_window('6M',None,None)
    assert not use_daily_window('1Y',None,None)
    assert use_daily_window('Custom','2026-01-01','2026-03-01')
    assert not use_daily_window('Custom','2025-01-01','2026-03-01')
    assert periods_per_year('daily')==252 and periods_per_year('monthly')==12


def test_raw_close_fx_and_cash_dividend_are_separate():
    idx=pd.date_range('2026-03-02',periods=3,freq='D')
    histories={
      'USDZAR':hist([15,16,17],idx=idx),'EURZAR':hist([18,18,18],idx=idx),
      'SP500':hist([100,101,102],[0,2,0],idx),'STXGVI':hist([8500,8600,8700],[0,300,0],idx)
    }
    p,d,notes=build_daily_components(histories,['SP500','SA_BONDS'],pd.Timestamp('2026-03-01'))
    assert np.isclose(p.loc[idx[1],'SP500'],101*16)
    assert np.isclose(d.loc[idx[1],'SP500'],2*16)
    assert np.isclose(p.loc[idx[1],'SA_BONDS'],8600)
    assert np.isclose(d.loc[idx[1],'SA_BONDS'],3.0)
    validate_period_return_identity(p,d)


def test_no_price_interpolation_and_window_is_flagged():
    idx=pd.to_datetime(['2026-03-02','2026-03-03','2026-03-04','2026-03-05'])
    p=pd.DataFrame({'A':[100,101,102,103],'B':[np.nan,200,201,202]},index=idx)
    d=pd.DataFrame(0.0,index=idx,columns=['A','B'])
    pw,dw,s,e,starts,ends,flags=align_daily_window(p,d,['A','B'],pd.Timestamp('2026-03-02'),pd.Timestamp('2026-03-05'))
    assert s==pd.Timestamp('2026-03-03')
    assert list(pw.index)==list(idx[1:])
    assert any('B: daily history begins 2026-03-03' in x for x in flags)


def test_sa_bonds_daily_is_cut_at_govi_boundary_not_interpolated():
    idx=pd.date_range('2026-02-27',periods=5,freq='D')
    histories={'USDZAR':hist([15]*5,idx=idx),'EURZAR':hist([18]*5,idx=idx),'STXGVI':hist([8500,8510,8520,8530,8540],idx=idx)}
    p,d,_=build_daily_components(histories,['SA_BONDS'],pd.Timestamp('2026-02-28'))
    assert p['SA_BONDS'].dropna().index.min()==pd.Timestamp('2026-03-01')
