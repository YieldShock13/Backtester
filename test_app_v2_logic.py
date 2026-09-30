import numpy as np
import pandas as pd
from feature_config import common_coverage, validate_weights, allocations_from_weights, fx_decomposition


def test_cash_dividend_not_reinvested_identity():
    p0,p1,d=100.0,90.0,10.0
    units=1000.0/p0
    ending=units*p1+units*d
    assert np.isclose(ending,1000.0)
    assert np.isclose((p1-p0+d)/p0,0.0)


def test_reinvestment_differs_after_post_dividend_price_move():
    units=10.0; div=5.0; ex_price=100.0; final_price=90.0
    cash_value=units*final_price+units*div
    reinvested_units=units+(units*div/ex_price)
    reinvested_value=reinvested_units*final_price
    assert cash_value>reinvested_value


def test_weights_and_nominal_reconcile():
    assets=['A','B']; w={'A':.4,'B':.6}
    out=allocations_from_weights(assets,w,1_202_000)
    assert np.isclose(out.sum(),1_202_000)
    assert np.isclose(validate_weights(assets,w).sum(),1.0)


def test_common_history_shortens_and_flags():
    idx=pd.date_range('2020-01-31',periods=24,freq='ME')
    p=pd.DataFrame({'A':range(24),'B':[np.nan]*6+list(range(18))},index=idx)
    s,e,starts,ends,flags=common_coverage(p,['A','B'],pd.Timestamp('2020-01-31'),idx[-1])
    assert s==idx[6]
    assert any('B: history begins' in x for x in flags)


def test_fx_decomposition_exact():
    idx=pd.to_datetime(['2020-01-01','2021-01-01'])
    p=pd.Series([100.,110.],index=idx); f=pd.Series([15.,16.5],index=idx)
    d=fx_decomposition(p,f,idx[0],idx[1])
    assert np.isclose(d['Local appreciation'],.10)
    assert np.isclose(d['FX contribution'],.10)
    assert np.isclose(d['Interaction'],.01)
    assert np.isclose(d['ZAR price return'],.21)
