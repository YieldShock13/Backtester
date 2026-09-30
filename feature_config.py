import numpy as np
import pandas as pd

WINDOWS={"1W":pd.DateOffset(weeks=1),"1M":pd.DateOffset(months=1),"3M":pd.DateOffset(months=3),"6M":pd.DateOffset(months=6),"1Y":pd.DateOffset(years=1),"3Y":pd.DateOffset(years=3),"5Y":pd.DateOffset(years=5),"10Y":pd.DateOffset(years=10)}
FOREIGN_FX={"SP500":"USDZAR","BERKSHIRE":"USDZAR","MSCI_EM":"USDZAR","AGG":"USDZAR","EUROPE":"EURZAR"}


def resolve_window(index,label,custom_start=None,custom_end=None):
    idx=pd.DatetimeIndex(index).sort_values()
    if len(idx)==0: raise ValueError("Cannot resolve timeline on empty data")
    available_start,available_end=idx.min(),idx.max()
    requested_end=available_end if custom_end is None else pd.Timestamp(custom_end)
    if label=="All": requested_start=available_start
    elif label=="Custom":
        if custom_start is None: raise ValueError("Custom timeline requires a start date")
        requested_start=pd.Timestamp(custom_start)
    elif label in WINDOWS: requested_start=requested_end-WINDOWS[label]
    else: raise ValueError(f"Unknown timeline: {label}")
    return requested_start,requested_end


def common_coverage(prices,selected_assets,requested_start,requested_end):
    if not selected_assets: raise ValueError("Select at least one asset")
    starts={a:prices[a].dropna().index.min() for a in selected_assets}
    ends={a:prices[a].dropna().index.max() for a in selected_assets}
    actual_start=max(pd.Timestamp(requested_start),max(starts.values()))
    actual_end=min(pd.Timestamp(requested_end),min(ends.values()))
    if actual_start>actual_end: raise ValueError("Selected assets have no overlapping history in the requested timeline")
    flags=[]
    for a in selected_assets:
        if starts[a]>pd.Timestamp(requested_start): flags.append(f"{a}: history begins {starts[a]:%Y-%m-%d}")
        if ends[a]<pd.Timestamp(requested_end): flags.append(f"{a}: history ends {ends[a]:%Y-%m-%d}")
    return actual_start,actual_end,starts,ends,flags


def validate_weights(selected_assets,weights):
    w=pd.Series({a:float(weights[a]) for a in selected_assets},dtype=float)
    if (w<0).any(): raise ValueError("Weights cannot be negative")
    if not np.isclose(w.sum(),1.0,atol=1e-8): raise ValueError(f"Weights must sum to 100%; current sum is {w.sum():.6%}")
    return w


def allocations_from_weights(selected_assets,weights,nominal):
    if float(nominal)<=0: raise ValueError("Nominal amount must be positive")
    w=validate_weights(selected_assets,weights)
    alloc=w*float(nominal)
    if not np.isclose(alloc.sum(),float(nominal),atol=.01): raise RuntimeError("Nominal allocation reconciliation failed")
    return alloc


def fx_decomposition(local_price,fx,start,end):
    p0=float(local_price.asof(pd.Timestamp(start))); p1=float(local_price.asof(pd.Timestamp(end)))
    f0=float(fx.asof(pd.Timestamp(start))); f1=float(fx.asof(pd.Timestamp(end)))
    if min(p0,p1,f0,f1)<=0: raise ValueError("FX decomposition requires positive prices and FX rates")
    local=p1/p0-1; currency=f1/f0-1; interaction=local*currency; zar=(p1*f1)/(p0*f0)-1
    if not np.isclose(local+currency+interaction,zar,atol=1e-12): raise RuntimeError("FX decomposition identity failed")
    return {"Local appreciation":local,"FX contribution":currency,"Interaction":interaction,"ZAR price return":zar}


def latex_workings(rf,nominal,reinvest,weights):
    mode="reinvested" if reinvest else "retained as cash"
    return [
      ("Period total return",r"R_{t_0,t_1}=\frac{P_{t_1}-P_{t_0}+\sum_{t_0<t\le t_1}D_t}{P_{t_0}}"),
      ("Buy-and-hold, cash distributions",r"V_t=N P_t+C_t,\quad C_t=N\sum_{i\le t}D_i"),
      ("Dividend reinvestment",r"N_t=N_{t^-}+\frac{N_{t^-}D_t}{P_t},\quad V_t=N_tP_t"),
      ("FX translation",r"P_t^{ZAR}=P_t^{LC}\times FX_t"),
      ("FX decomposition",r"R^{ZAR}=R^{LC}+R^{FX}+R^{LC}R^{FX}"),
      ("Sharpe",rf"SR=\frac{{\bar r-r_f}}{{\sigma_r}},\quad r_f={rf:.4f}"),
      ("Portfolio",rf"V_0=R\,{nominal:,.2f},\quad D_t\text{{ is {mode}}}"),
      ("Weights",r"\sum_i w_i=1")]


def audit_rows(selected_assets,coverage_starts,coverage_ends,bond_validation,reinvest):
    rows=[]
    for a in selected_assets:
        if a=="SA_BONDS": source="Repository GOVI -> STXGVI.JO splice"; transform="GOVI through validated cutoff; thereafter fixed STXGVI units + cash distributions"
        elif a in ["SP500","BERKSHIRE","MSCI_EM","AGG"]: source="Yahoo Finance + USDZAR"; transform="Raw Close; ZAR translation; cash distributions"
        elif a=="EUROPE": source="Yahoo Finance + EURZAR"; transform="Raw Close; ZAR translation; cash distributions"
        else: source="Yahoo Finance"; transform="Raw Close; JSE cents/Rand normalization where applicable; cash distributions"
        rows.append({"Asset":a,"Source / connection":source,"Available from":coverage_starts[a],"Available to":coverage_ends[a],"Transformation":transform,"Dividend treatment":"Reinvest" if reinvest else "Retain as cash","Inspection requirement":"SA bond splice/proxy requires explicit review" if a=="SA_BONDS" else "Check corporate actions and source completeness"})
    return pd.DataFrame(rows)
