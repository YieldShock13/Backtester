import numpy as np, pandas as pd, yfinance as yf
TICKERS=['^J203.JO','^GSPC','STXGVI.JO','GLD.JO','EXX.JO','BRK-B','EEM','AGG']
def get(t):
 h=yf.Ticker(t).history(period='max',interval='1d',auto_adjust=False,actions=True,keepna=True)
 h=h.copy(); h.index=pd.to_datetime(h.index).tz_localize(None); h=h.sort_index()
 c=pd.to_numeric(h['Close'],errors='coerce').dropna(); d=pd.to_numeric(h.get('Dividends',0),errors='coerce').fillna(0.0)
 ed=pd.Series(0.0,index=c.index)
 for dt,dv in d[d!=0].items():
  p=c.index.searchsorted(dt,side='left')
  if p<len(c): ed.iloc[p]+=float(dv)
 r=(c+ed)/c.shift(1)-1
 lvl=pd.Series(index=c.index,dtype=float,name=t); lvl.iloc[0]=100.0; lvl.iloc[1:]=100*(1+r.iloc[1:]).cumprod().to_numpy()
 return h,c,ed,r,lvl
levels={}; raw={}
for t in TICKERS:
 h,c,d,r,lvl=get(t); levels[t]=lvl; raw[t]=(h,c,d,r)
 print('TICKER',t,'n',len(c),'start',c.index.min().date(),'end',c.index.max().date(),'div_events',int((d!=0).sum()),'max_abs_daily_TR',float(r.abs().max()),'date',r.abs().idxmax().date())
 assert np.isfinite(lvl.dropna()).all() and (lvl.dropna()>0).all()
 for dt in d[d!=0].index:
  i=c.index.get_loc(dt)
  if i>0:
   expected=(c.iloc[i]-c.iloc[i-1]+d.loc[dt])/c.iloc[i-1]
   assert np.isclose(r.loc[dt],expected,rtol=0,atol=1e-12)
L=pd.concat(levels,axis=1).sort_index(); start=max(L[t].first_valid_index() for t in TICKERS); end=min(L[t].last_valid_index() for t in TICKERS); L=L.loc[start:end]
common=L.dropna(how='any'); weekly=common.groupby(common.index.to_period('W-FRI')).tail(1)
assert not weekly.empty and weekly.notna().all().all()
for per,g in common.groupby(common.index.to_period('W-FRI')):
 chosen=weekly[weekly.index.to_period('W-FRI')==per]; assert len(chosen)==1 and chosen.index[0]==g.index.max()
print('WEEKLY_COMMON n',len(weekly),'start',weekly.index.min().date(),'end',weekly.index.max().date())
print('LAST_10_COMMON_DATES',','.join(str(x.date()) for x in weekly.index[-10:]))
for t in TICKERS:
 h,c,d,r=raw[t]; events=d[d!=0]
 if len(events):
  dt=events.index[-1]; per=dt.to_period('W-FRI'); w=weekly[weekly.index.to_period('W-FRI')==per]
  print('LAST_DIV',t,dt.date(),float(events.loc[dt]),'week_common',str(w.index[0].date()) if len(w) else 'NONE','event_TR',float(r.loc[dt]))
print('VALIDATION_PASS')

# trigger validation
