import numpy as np
import pandas as pd

SHORT_LABELS={"1W","1M","3M","6M"}
USD_ASSETS={"SP500","BERKSHIRE","MSCI_EM","AGG"}
EUR_ASSETS={"EUROPE"}
JSE_CENTS={"NEWGOLD","EXXARO"}


def use_daily_window(label,start,end):
    if label in SHORT_LABELS:
        return True
    if label=="Custom" and start is not None and end is not None:
        return (pd.Timestamp(end)-pd.Timestamp(start)).days<=183
    return False


def normalise_history(frame,asset):
    if frame is None or frame.empty:
        raise ValueError(f"{asset}: empty source history")
    h=frame.copy().sort_index()
    h.index=pd.to_datetime(h.index).tz_localize(None) if getattr(h.index,"tz",None) is not None else pd.to_datetime(h.index)
    close=pd.to_numeric(h["Close"],errors="coerce")
    div=pd.to_numeric(h["Dividends"],errors="coerce").fillna(0.0) if "Dividends" in h else pd.Series(0.0,index=h.index)
    if asset in JSE_CENTS:
        close=close/100.0; div=div/100.0
    return close.dropna(),div


def build_daily_components(histories,selected,last_govi):
    # Raw Close only. Yahoo Close is treated as split-normalised; no second split adjustment.
    # Dividends remain separate cash flows. FX is translated on each observation/dividend date.
    usd_close,_=normalise_history(histories["USDZAR"],"USDZAR")
    eur_close,_=normalise_history(histories["EURZAR"],"EURZAR")
    prices={}; divs={}; notes={}
    for asset in selected:
        source="STXGVI" if asset=="SA_BONDS" else asset
        close,div=normalise_history(histories[source],source)
        if asset=="SA_BONDS":
            close=close.loc[close.index>pd.Timestamp(last_govi)]
            div=div.reindex(close.index,fill_value=0.0)/100.0
            notes[asset]=f"Daily SA bond history uses STXGVI only after GOVI cutoff {pd.Timestamp(last_govi):%Y-%m-%d}; earlier GOVI is monthly and is not interpolated."
        elif asset in USD_ASSETS:
            fx=usd_close.reindex(close.index).ffill()
            close=close*fx; div=div*fx
            notes[asset]="Raw local-currency Close translated with observed USD/ZAR; dividends translated separately."
        elif asset in EUR_ASSETS:
            fx=eur_close.reindex(close.index).ffill()
            close=close*fx; div=div*fx
            notes[asset]="Raw local-currency Close translated with observed EUR/ZAR; dividends translated separately."
        else:
            notes[asset]="Raw Close in ZAR; dividends kept separate from price."
        prices[asset]=close.rename(asset); divs[asset]=div.reindex(close.index,fill_value=0.0).rename(asset)
    p=pd.concat(prices,axis=1).sort_index()
    d=pd.concat(divs,axis=1).reindex(p.index).fillna(0.0)
    return p,d,notes


def common_observed_window(prices,selected,requested_start,requested_end):
    starts={}; ends={}; flags=[]
    for a in selected:
        s=prices[a].dropna()
        if s.empty: raise ValueError(f"{a}: no daily observations")
        starts[a]=s.index.min(); ends[a]=s.index.max()
    start=max(pd.Timestamp(requested_start),max(starts.values()))
    end=min(pd.Timestamp(requested_end),min(ends.values()))
    if start>end: raise ValueError("Selected assets have no overlapping observed daily history")
    # Align to actual common trading observations, never interpolate an asset price.
    x=prices.loc[(prices.index>=start)&(prices.index<=end),selected].dropna(how="any")
    if len(x)<2: raise ValueError("Fewer than two common observed daily prices in requested window")
    actual_start=x.index[0]; actual_end=x.index[-1]
    for a in selected:
        if starts[a]>pd.Timestamp(requested_start): flags.append(f"{a}: daily history begins {starts[a]:%Y-%m-%d}")
        if ends[a]<pd.Timestamp(requested_end): flags.append(f"{a}: daily history ends {ends[a]:%Y-%m-%d}")
    if actual_start>pd.Timestamp(requested_start): flags.append(f"common first observed trading date is {actual_start:%Y-%m-%d}")
    if actual_end<pd.Timestamp(requested_end): flags.append(f"common last observed trading date is {actual_end:%Y-%m-%d}")
    return x,daily_dividends_on_price_index(prices,selected,actual_start,actual_end),actual_start,actual_end,starts,ends,flags


def daily_dividends_on_price_index(prices,selected,start,end):
    # Placeholder is intentionally rejected if called without the source dividend frame.
    raise RuntimeError("Use align_daily_window(prices, dividends, ...) so dividend cash cannot be silently lost")


def align_daily_window(prices,dividends,selected,requested_start,requested_end):
    starts={}; ends={}; flags=[]
    for a in selected:
        s=prices[a].dropna()
        if s.empty: raise ValueError(f"{a}: no daily observations")
        starts[a]=s.index.min(); ends[a]=s.index.max()
    start=max(pd.Timestamp(requested_start),max(starts.values())); end=min(pd.Timestamp(requested_end),min(ends.values()))
    if start>end: raise ValueError("Selected assets have no overlapping observed daily history")
    p=prices.loc[(prices.index>=start)&(prices.index<=end),selected].dropna(how="any")
    if len(p)<2: raise ValueError("Fewer than two common observed daily prices in requested window")
    actual_start=p.index[0]; actual_end=p.index[-1]
    d=dividends.reindex(p.index)[selected].fillna(0.0)
    for a in selected:
        if starts[a]>pd.Timestamp(requested_start): flags.append(f"{a}: daily history begins {starts[a]:%Y-%m-%d}")
        if ends[a]<pd.Timestamp(requested_end): flags.append(f"{a}: daily history ends {ends[a]:%Y-%m-%d}")
    if actual_start>pd.Timestamp(requested_start): flags.append(f"common first observed trading date is {actual_start:%Y-%m-%d}")
    if actual_end<pd.Timestamp(requested_end): flags.append(f"common last observed trading date is {actual_end:%Y-%m-%d}")
    return p,d,actual_start,actual_end,starts,ends,flags


def periods_per_year(frequency):
    return 252 if frequency=="daily" else 12


def validate_period_return_identity(prices,dividends):
    r=(prices-prices.shift(1)+dividends)/prices.shift(1)
    reconstructed=(prices/prices.shift(1)-1)+(dividends/prices.shift(1))
    err=(r-reconstructed).abs().max().max()
    if np.isfinite(err) and err>1e-12: raise RuntimeError(f"Period-return identity failed: {err}")
    return True
