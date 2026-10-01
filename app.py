import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Orca's Capital Strategies | Portfolio Backtester", page_icon="🐋", layout="wide")

# Orca's Capital Strategies — visual shell only; analytics and methodology remain unchanged.
st.markdown(r"""
<style>
.orca-hero{position:relative;overflow:hidden;height:225px;margin:-1rem -1rem 1.6rem;border-bottom:1px solid #1c3d5b;background:radial-gradient(circle at 18% 65%,rgba(28,132,219,.20),transparent 28%),linear-gradient(110deg,#030a12,#071829 58%,#06111f);box-shadow:0 18px 45px rgba(0,0,0,.22)}
.orca-brand{position:absolute;left:31%;top:53px;z-index:5;border-left:1px solid rgba(145,198,238,.35);padding-left:34px}
.orca-name{font-family:Georgia,'Times New Roman',serif;font-size:52px;letter-spacing:.14em;color:#f5f9fc;line-height:1;text-shadow:0 0 28px rgba(108,187,255,.10)}
.orca-sub{font-family:Arial,sans-serif;font-size:15px;letter-spacing:.48em;color:#61b7ff;margin-top:17px;white-space:nowrap}
.orca-mark{position:absolute;left:5%;top:18px;width:350px;height:185px;z-index:3;animation:orcaFloat 5s ease-in-out infinite;filter:drop-shadow(0 8px 18px rgba(31,153,255,.28))}
.orca-wave{position:absolute;right:-4%;bottom:18px;width:55%;height:120px;opacity:.52}
.orca-wave path{fill:none;stroke:#3faaff;stroke-width:2;stroke-dasharray:5 11;animation:waveDash 8s linear infinite}
.orca-wave .w2{opacity:.48;animation-duration:12s}.orca-wave .w3{opacity:.25;animation-duration:16s}
.orca-glow{position:absolute;width:8px;height:8px;border-radius:50%;background:#67c1ff;box-shadow:0 0 16px #47b2ff;animation:pulse 2.7s ease-in-out infinite}
.g1{right:24%;top:63px}.g2{right:13%;top:116px;animation-delay:.8s}.g3{right:35%;top:144px;animation-delay:1.5s}
@keyframes orcaFloat{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-8px) rotate(1deg)}}
@keyframes waveDash{to{stroke-dashoffset:-160}}
@keyframes pulse{0%,100%{opacity:.2;transform:scale(.65)}50%{opacity:1;transform:scale(1.2)}}
@media(max-width:900px){.orca-hero{height:190px}.orca-mark{left:0;width:250px}.orca-brand{left:35%;top:48px}.orca-name{font-size:31px}.orca-sub{font-size:10px;letter-spacing:.28em}}
</style>
<div class="orca-hero">
 <svg class="orca-mark" viewBox="0 0 420 220" aria-label="Animated orca logo">
  <defs><linearGradient id="ob" x1="0" x2="1"><stop offset="0" stop-color="#02070c"/><stop offset=".65" stop-color="#101c28"/><stop offset="1" stop-color="#05090d"/></linearGradient><linearGradient id="ow" x1="0" x2="1"><stop stop-color="#d9efff"/><stop offset="1" stop-color="#ffffff"/></linearGradient></defs>
  <path d="M70 146 C92 88 161 50 245 58 C292 62 337 84 371 107 C336 104 311 108 286 126 C249 153 197 171 142 168 C111 166 86 159 70 146Z" fill="url(#ob)" stroke="#6ebfff" stroke-width="1.5"/>
  <path d="M171 68 C155 35 171 17 201 8 C193 35 204 51 222 59Z" fill="#03090f" stroke="#6ebfff" stroke-width="1.2"/>
  <path d="M285 124 C320 138 333 160 328 184 C308 160 283 151 255 149Z" fill="#03090f" stroke="#6ebfff" stroke-width="1.2"/>
  <path d="M73 143 C49 129 26 130 7 144 C27 149 43 157 57 173 C59 158 64 150 73 143Z" fill="#07111b" stroke="#6ebfff" stroke-width="1.2"/>
  <path d="M251 81 C281 78 311 88 337 104 C304 104 283 112 264 127 C248 139 225 149 204 151 C226 135 238 118 241 99 C243 91 246 85 251 81Z" fill="url(#ow)" opacity=".96"/>
  <ellipse cx="285" cy="88" rx="17" ry="8" fill="#eef8ff" transform="rotate(-8 285 88)"/>
  <circle cx="328" cy="91" r="3" fill="#74c7ff"/>
  <path d="M63 172 Q115 148 164 175 T266 174" fill="none" stroke="#42adff" stroke-width="3" opacity=".8"/>
  <path d="M42 184 Q100 158 160 187 T287 183" fill="none" stroke="#8bd3ff" stroke-width="2" opacity=".35"/>
 </svg>
 <div class="orca-brand"><div class="orca-name">ORCA'S</div><div class="orca-sub">CAPITAL STRATEGIES</div></div>
 <svg class="orca-wave" viewBox="0 0 800 150" preserveAspectRatio="none"><path d="M0 86 C120 20 190 135 310 75 S520 35 800 88"/><path class="w2" d="M0 110 C140 42 220 145 350 92 S590 50 800 106"/><path class="w3" d="M0 58 C130 5 250 105 390 55 S630 20 800 62"/></svg>
 <span class="orca-glow g1"></span><span class="orca-glow g2"></span><span class="orca-glow g3"></span>
</div>
""",unsafe_allow_html=True)
START=None
DEFAULT_RF=0.07
DEFAULT_INITIAL=1_202_000
DEFAULT_TICKERS=["^J203.JO","^GSPC","STXGVI.JO","GLD.JO","EXX.JO","BRK-B","EEM","AGG"]
DEFAULT_WEIGHTS={"^J203.JO":0.3328,"^GSPC":0.1664,"STXGVI.JO":0.1664,"GLD.JO":0.0374,"EXX.JO":0.0416,"BRK-B":0.0466,"EEM":0.0541,"AGG":0.0507}
BENCHMARK_TICKER="^J203.JO"
SHORT_WINDOWS={'1W','1M','3M','6M','1Y'}

@st.cache_data(show_spinner=False)
def load_govi_history():
 d=pd.read_csv('govi_monthly.csv'); d['Date']=pd.to_datetime(d['Date'])+pd.offsets.MonthEnd(0)
 s=pd.Series(pd.to_numeric(d['SA_BONDS'],errors='coerce').values,index=d['Date'],name='GOVI').dropna().sort_index()
 if len(s)<100: raise RuntimeError('Validated GOVI history is incomplete')
 return s

@st.cache_data(ttl=3600,show_spinner=False)
def load_ticker_components(tickers):
 prices={}; divs={}; splits={}
 for ticker in tickers:
  h=yf.Ticker(ticker).history(period='max',interval='1d',auto_adjust=False,actions=True,keepna=True)
  if h.empty: raise RuntimeError(f'Market-data source returned no data for ticker {ticker}')
  h=h.copy(); h.index=pd.to_datetime(h.index).tz_localize(None); h=h.sort_index()
  if 'Adj Close' not in h.columns: raise RuntimeError(f'{ticker}: daily Adjusted Close unavailable')
  adj=pd.to_numeric(h['Adj Close'],errors='coerce').dropna()
  if len(adj)<2: raise RuntimeError(f'{ticker}: fewer than two valid daily Adjusted Close observations')
  if (adj<=0).any(): raise RuntimeError(f'{ticker}: daily Adjusted Close contains non-positive values')
  prices[ticker]=adj.rename(ticker)
  divs[ticker]=pd.Series(0.0,index=h.index,dtype=float,name=ticker)
  splits[ticker]=pd.to_numeric(h.get('Stock Splits',pd.Series(0.0,index=h.index)),errors='coerce').fillna(0.0).rename(ticker)
 return prices,divs,splits

@st.cache_data(ttl=3600,show_spinner=False)
def search_assets(query):
 q=(query or '').strip()
 if not q: return []
 out=[]
 if 'govi' in q.lower() or 'south african government' in q.lower():
  out.append({'symbol':'GOVI','name':'South African Government Bond Index (repository series)','source':'Repository'})
 try:
  srch=yf.Search(q,max_results=12,news_count=0,lists_count=0,recommended=0)
  for item in (getattr(srch,'quotes',None) or []):
   symbol=str(item.get('symbol','')).strip()
   if not symbol: continue
   out.append({'symbol':symbol,'name':str(item.get('longname') or item.get('shortname') or symbol),'source':'Market data'})
 except Exception:
  pass
 seen=set(); clean=[]
 for row in out:
  if row['symbol'] not in seen: clean.append(row); seen.add(row['symbol'])
 return clean

@st.cache_data(ttl=3600,show_spinner=False)
def resolve_instrument_names(symbols):
 names={}
 for symbol in symbols:
  if symbol=='GOVI':
   names[symbol]='South African Government Bond Index'
   continue
  try:
   srch=yf.Search(symbol,max_results=8,news_count=0,lists_count=0,recommended=0)
   quotes=getattr(srch,'quotes',None) or []
   exact=next((q for q in quotes if str(q.get('symbol','')).upper()==symbol.upper()),None)
   q=exact or (quotes[0] if quotes else {})
   names[symbol]=str(q.get('longname') or q.get('shortname') or symbol)
  except Exception:
   names[symbol]=symbol
 return names

def _reconstruct_daily_components(close,div,splits,reinvest):
 c=close.astype(float).sort_index()
 d=div.astype(float).sort_index()
 sp=splits.astype(float).sort_index()
 bad=sp[(sp!=0)&((sp<=0)|(~np.isfinite(sp)))]
 if len(bad): raise RuntimeError(f'Invalid stock split on {bad.index[0].date()}: {bad.iloc[0]}')
 if not reinvest:
  return c.rename(c.name),d.rename(d.name)
 # Reinvest on the dividend event date. If Yahoo has an action-only row with no
 # Close, use the first genuine Close on/after that event; no event is discarded.
 event_div=pd.Series(0.0,index=c.index)
 for dt,dv in d[d!=0].items():
  pos=c.index.searchsorted(dt,side='left')
  if pos>=len(c): continue
  event_div.iloc[pos]+=float(dv)
 bad_px=(event_div!=0)&((c<=0)|(~np.isfinite(c)))
 if bad_px.any():
  dt=bad_px[bad_px].index[0]; raise RuntimeError(f'Invalid reinvestment price on {dt.date()}: {c.loc[dt]}')
 units_factor=(1.0+event_div/c).cumprod()
 return (units_factor*c).rename(c.name),pd.Series(0.0,index=c.index,name=d.name)

def build_master(selected,reinvest):
 yahoo=[x for x in selected if x!='GOVI']; yp,yd,ys=load_ticker_components(tuple(yahoo)) if yahoo else ({},{},{})
 if not yahoo: raise RuntimeError('Select at least one daily-history market instrument')
 genuine=pd.concat([yp[x].rename(x) for x in yahoo],axis=1).sort_index()
 first_valid=genuine.apply(lambda c:c.first_valid_index()).dropna(); last_valid=genuine.apply(lambda c:c.last_valid_index()).dropna()
 common_inception=max(first_valid); common_endpoint=min(last_valid)
 master_index=genuine.index[(genuine.index>=common_inception)&(genuine.index<=common_endpoint)]
 raw=genuine.reindex(master_index)
 missing_before=raw.isna()
 mp=raw.interpolate(method='time',limit_area='inside')
 if mp.isna().any().any():
  bad=mp.isna().sum(); bad=bad[bad>0]
  raise RuntimeError('Unable to interpolate adjusted-price observations: '+', '.join(f'{k}={int(v)}' for k,v in bad.items()))
 interpolation_report=pd.DataFrame([
  {'Series':x,'Type':'Portfolio asset','Interpolated Values':int(missing_before[x].sum()),
   'Genuine Values':int((~missing_before[x]).sum())} for x in yahoo
 ])
 md=pd.DataFrame(0.0,index=mp.index,columns=yahoo)
 g=load_govi_history(); val={'last_govi':g.index.max(),'source':'repository GOVI','interpolation_report':interpolation_report}
 if 'GOVI' in selected: raise RuntimeError('Repository GOVI is monthly-only. Select a Yahoo-traded bond/index proxy with daily history instead.')
 return mp,md,g,val,ys

def build_daily(selected):
 if 'GOVI' in selected: raise RuntimeError('GOVI is monthly-only. For daily analysis select an instrument with daily observations, such as STXGVI.JO.')
 yp,yd,ys=load_ticker_components(tuple(selected)); dp=pd.concat(yp.values(),axis=1); dd=pd.concat(yd.values(),axis=1).reindex(dp.index,fill_value=0.0); g=load_govi_history(); val={'last_govi':g.index.max(),'source':'repository GOVI'}
 return dp,dd,g,val,ys

def resolve_dates(index,timeline,custom_start,custom_end,daily=False):
 end=index.max()
 if timeline=='All': requested=index.min()
 elif timeline=='Custom': requested=pd.Timestamp(custom_start); end=min(pd.Timestamp(custom_end),end)
 else:
  offsets={'1W':pd.DateOffset(weeks=1),'1M':pd.DateOffset(months=1),'3M':pd.DateOffset(months=3),'6M':pd.DateOffset(months=6),'1Y':pd.DateOffset(years=1),'3Y':pd.DateOffset(years=3),'5Y':pd.DateOffset(years=5),'10Y':pd.DateOffset(years=10)}; requested=end-offsets[timeline]
 available=index[(index>=requested)&(index<=end)]
 if len(available)==0: raise RuntimeError('No observations in requested timeline')
 return available[0],available[-1],requested

def portfolio_values(prices,divs,alloc,reinvest,rebalance_frequency=None,hedge_returns=None):
 assets=list(alloc); target=pd.Series(alloc,dtype=float)/sum(alloc.values()); units=pd.Series({a:alloc[a]/float(prices[a].iloc[0]) for a in assets}); cash=pd.Series(0.0,index=assets)
 v=pd.DataFrame(index=prices.index,columns=assets,dtype=float); v.iloc[0]=pd.Series(alloc)
 hedge_returns=hedge_returns if hedge_returns is not None else pd.DataFrame(0.0,index=prices.index,columns=assets)
 hedge_returns=hedge_returns.reindex(index=prices.index,columns=assets,fill_value=0.0).fillna(0.0)
 def _rebalance_due(prev,dt,freq):
  if not freq: return False
  if freq=='Weekly': return True
  if freq=='Monthly': return (dt.year,dt.month)!=(prev.year,prev.month)
  if freq=='Quarterly': return (dt.year,(dt.month-1)//3)!=(prev.year,(prev.month-1)//3)
  if freq=='Semi-Annual': return (dt.year,(dt.month-1)//6)!=(prev.year,(prev.month-1)//6)
  if freq=='Annual': return dt.year!=prev.year
  return False
 for i in range(1,len(prices)):
  dt=prices.index[i]; prev=prices.index[i-1]
  if _rebalance_due(prev,dt,rebalance_frequency):
   total=(units*prices.loc[prev,assets]+cash).sum(); units=(target*total)/prices.loc[prev,assets]; cash[:]=0.0
  prev_exposure=units*prices.loc[prev,assets]
  hedge_pnl=prev_exposure*hedge_returns.loc[dt,assets]
  flows=units*divs.loc[dt,assets]
  if reinvest: units=units+flows/prices.loc[dt,assets]
  else: cash=cash+flows
  cash=cash+hedge_pnl
  v.loc[dt,assets]=units*prices.loc[dt,assets]+cash
 v['PORTFOLIO']=v[assets].sum(axis=1); return v

def line_chart(series_map,title,ytitle):
 f=go.Figure()
 for name,s in series_map.items(): f.add_trace(go.Scatter(x=s.index,y=s.values,mode='lines',name=name))
 f.update_layout(title=title,xaxis_title='Date',yaxis_title=ytitle,hovermode='x unified',legend_title_text=''); st.plotly_chart(f,use_container_width=True)

def stats(v,market_r,rf,ppy):
 p=v.PORTFOLIO; r=p.pct_change(fill_method=None).dropna(); yrs=max((p.index[-1]-p.index[0]).days/365.25,1/365.25); cagr=(p.iloc[-1]/p.iloc[0])**(1/yrs)-1; vol=r.std()*np.sqrt(ppy); rfp=(1+rf)**(1/ppy)-1; ex=r-rfp; down=ex[ex<0]; dvol=np.sqrt(np.mean(down**2))*np.sqrt(ppy); dd=p/p.cummax()-1
 d=pd.concat([r.rename('P'),market_r.rename('M')],axis=1).dropna(); x=d.M-rfp; y=d.P-rfp; beta=y.cov(x)/x.var() if x.var()>0 else np.nan; alpha=(1+y.mean()-beta*x.mean())**ppy-1 if np.isfinite(beta) else np.nan
 # Parametric 95% annual VaR from daily returns: annualise mean by 252 and
 # volatility by sqrt(252), then take the 5% normal quantile.
 mu_ann=float(r.mean())*ppy; sigma_ann=float(r.std(ddof=1))*np.sqrt(ppy); z05=-1.6448536269514722
 annual_var=mu_ann+z05*sigma_ann
 return {'Backtest Range':f'{p.index[0]:%Y-%m-%d} to {p.index[-1]:%Y-%m-%d}','Initial Value':p.iloc[0],'Ending Value':p.iloc[-1],'Total Return':p.iloc[-1]/p.iloc[0]-1,'CAGR':cagr,'Annualised Volatility':vol,'Sharpe Ratio':ex.mean()/ex.std()*np.sqrt(ppy) if ex.std()>0 else np.nan,'Downside Volatility':dvol,'Sortino Ratio':ex.mean()*ppy/dvol if dvol>0 else np.nan,'Beta vs Benchmark':beta,'CAPM Alpha (Annualised)':alpha,'Maximum Drawdown':dd.min(),'Calmar Ratio':cagr/abs(dd.min()) if dd.min()<0 else np.nan,'Annual Parametric VaR 95%':annual_var,'Best Daily Return':r.max(),'Worst Daily Return':r.min(),'Positive Trading Days':(r>0).mean(),'Max DD Date':dd.idxmin()}

def metric_table(m):
 pct={'Total Return','CAGR','Annualised Volatility','Downside Volatility','CAPM Alpha (Annualised)','Maximum Drawdown','Annual Parametric VaR 95%','Best Daily Return','Worst Daily Return','Positive Trading Days'}; rows=[]
 for k,v in m.items():
  x=v if k=='Backtest Range' else pd.Timestamp(v).strftime('%Y-%m-%d') if k=='Max DD Date' else f'R{v:,.0f}' if k in ['Initial Value','Ending Value'] else f'{v:.2%}' if k in pct else f'{v:.3f}'; rows.append((k,x))
 return pd.DataFrame(rows,columns=['Metric','Value'])

def annual_returns(v):
 rows=[]
 for y in sorted(v.index.year.unique()):
  idx=v.index[v.index.year==y]; prior=v.index[v.index<idx[0]]; start=prior[-1] if len(prior) else idx[0]; end=idx[-1]; rows.append((y,v.loc[end,'PORTFOLIO']/v.loc[start,'PORTFOLIO']-1,'Partial Year' if y in [v.index[0].year,v.index[-1].year] else 'Full Year'))
 return pd.DataFrame(rows,columns=['Year','Annual Total Return','Period'])

def annual_asset_returns(prices,divs,assets):
 # Standard total return: compound each synchronized period's price change plus
 # dividend distribution. This is independent of the portfolio reinvest toggle.
 tr=(prices-prices.shift(1)+divs)/prices.shift(1)
 rows=[]
 for y in sorted(prices.index.year.unique()):
  idx=prices.index[prices.index.year==y]
  row={'Year':y,'Period':'Partial Year' if y in [prices.index[0].year,prices.index[-1].year] else 'Full Year'}
  for asset in assets:
   r=tr.loc[idx,asset].dropna()
   row[asset]=(1.0+r).prod()-1.0 if len(r) else np.nan
  rows.append(row)
 return pd.DataFrame(rows)

def rolling_capm(v,market_r,rf,ppy):
 window=36 if ppy==12 else 252; rp=v.PORTFOLIO.pct_change(fill_method=None); d=pd.concat([rp.rename('P'),market_r.rename('M')],axis=1).dropna(); rfp=(1+rf)**(1/ppy)-1; x=d.M-rfp; y=d.P-rfp; b=y.rolling(window).cov(x)/x.rolling(window).var(); a=y.rolling(window).mean()-b*x.rolling(window).mean(); return b,(1+a)**ppy-1,window

def conditional_beta(v,market_price,threshold=-.10):
 rp=v.PORTFOLIO.pct_change(fill_method=None); rm=market_price.pct_change(fill_method=None); dd=market_price/market_price.cummax()-1; d=pd.concat([rp.rename('P'),rm.rename('M'),dd.rename('DD')],axis=1).dropna(); d=d[d.DD<=threshold]
 return d.P.cov(d.M)/d.M.var() if len(d)>=2 and d.M.var()>0 else np.nan,len(d)


@st.cache_data(ttl=3600,show_spinner=False)
def load_fx_pair(source_ccy,base_ccy,daily_mode):
 if source_ccy==base_ccy: return None,None
 direct=f'{source_ccy}{base_ccy}=X'
 inverse=f'{base_ccy}{source_ccy}=X'
 for symbol,invert in [(direct,False),(inverse,True)]:
  try:
   h=yf.Ticker(symbol).history(period='max',interval='1d',auto_adjust=False,actions=False)
   if h.empty: continue
   x=pd.to_numeric(h['Close'],errors='coerce').dropna(); x.index=pd.to_datetime(x.index).tz_localize(None); x=x.sort_index()
   if invert: x=1.0/x
   if not daily_mode: x=x.resample('W-FRI').last()
   return x.rename(f'{source_ccy}/{base_ccy}'),symbol
  except Exception:
   continue
 raise RuntimeError(f'FX source returned no usable data for {source_ccy}/{base_ccy}')

def translate_currency(prices,divs,adjusted_assets,source_ccys,base_ccy,daily_mode):
 out_p=prices.copy(); out_d=divs.copy(); rows=[]
 for asset in adjusted_assets:
  source=source_ccys[asset]
  if source==base_ccy: continue
  fx_raw,symbol=load_fx_pair(source,base_ccy,daily_mode)
  if daily_mode:
   fx0=fx_raw.reindex(prices.index)
   missing_before=int(fx0.isna().sum())
   fx=fx0.interpolate(method='time',limit_area='inside')
  else:
   fx_week=fx_raw.copy(); fx_week.index=fx_week.index.to_period('W-FRI').end_time.normalize(); fx_week=fx_week.groupby(level=0).last()
   portfolio_week=pd.DatetimeIndex(prices.index).to_period('W-FRI').end_time.normalize()
   fx=pd.Series(fx_week.reindex(portfolio_week).to_numpy(),index=prices.index,name=f'{source}/{base_ccy}')
  missing=int(fx.isna().sum())
  if missing: raise RuntimeError(f'{asset}: {missing} portfolio observation(s) have no same-period {source}/{base_ccy} FX rate')
  out_p.loc[:,asset]=prices[asset].astype(float)*fx.astype(float)
  out_d.loc[:,asset]=divs[asset].astype(float)*fx.astype(float)
  rows.append({'Instrument':asset,'Source Currency':source,'Base Currency':base_ccy,'FX Series Used':symbol,'Observations':int(fx.notna().sum()),'Interpolated Values':missing_before if daily_mode else 0,'Sample Start':fx.index.min(),'Sample End':fx.index.max()})
 return out_p,out_d,pd.DataFrame(rows)

@st.cache_data(ttl=3600,show_spinner=False)
def load_macro_factors(daily_mode):
 symbols={'Oil':'CL=F','VIX':'^VIX','MOVE':'^MOVE'}
 yp,_,_=load_ticker_components(tuple(symbols.values()))
 out={}
 for name,sym in symbols.items():
  x=yp[sym].astype(float).sort_index()
  if not daily_mode: x=x.resample('W-FRI').last()
  out[name]=x.rename(name)
 # ICE BofA US High Yield Index Option-Adjusted Spread (FRED BAMLH0A0HYM2), percent.
 hy=pd.read_csv('https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2')
 date_col='DATE' if 'DATE' in hy.columns else 'observation_date' if 'observation_date' in hy.columns else hy.columns[0]
 hy[date_col]=pd.to_datetime(hy[date_col],errors='coerce'); hy['BAMLH0A0HYM2']=pd.to_numeric(hy['BAMLH0A0HYM2'],errors='coerce')
 hx=hy.dropna(subset=[date_col]).set_index(date_col)['BAMLH0A0HYM2'].dropna().sort_index()
 if not daily_mode: hx=hx.resample('W-FRI').last()
 out['HY OAS']=hx.rename('HY OAS')
 return pd.DataFrame(out)

def _conditional_capm(period_returns,market_returns,rf,ppy):
 d=pd.concat([period_returns.rename('P'),market_returns.rename('M')],axis=1).dropna(); n=len(d)
 if n<2 or d.M.var()<=0: return np.nan,np.nan,n
 rfp=(1+rf)**(1/ppy)-1; x=d.M-rfp; y=d.P-rfp; beta=y.cov(x)/x.var(); alpha=y.mean()-beta*x.mean()
 return beta,alpha,n

def benchmark_drawdown_events(vals,market_price,threshold=-.10):
 # Independent peak-to-first-threshold-crossing historical episodes. A new event cannot begin until a new high is established.
 p=market_price.dropna().sort_index(); events=[]; peak_date=p.index[0]; peak=float(p.iloc[0]); armed=True
 for dt,px in p.iloc[1:].items():
  px=float(px)
  if px>=peak:
   peak=px; peak_date=dt; armed=True; continue
  dd=px/peak-1
  if armed and dd<=threshold:
   if peak_date in vals.index and dt in vals.index:
    events.append((peak_date,dt,float(dd),float(vals.loc[dt,'PORTFOLIO']/vals.loc[peak_date,'PORTFOLIO']-1)))
   armed=False
 return events

def benchmark_scenario_stats(vals,market_price,rf,ppy,benchmark_label):
 events=benchmark_drawdown_events(vals,market_price,-.10)
 label=f'{benchmark_label} −10% Drawdown'
 if not events: return {'Scenario':label,'Historical Events':0}
 er=pd.DataFrame(events,columns=['Start','End','Benchmark Event Return','Portfolio Event Return'])
 # Conditional CAPM uses all underlying periodic observations contained inside the independent event windows.
 rp=vals.PORTFOLIO.pct_change(fill_method=None); rm=market_price.pct_change(fill_method=None); idx=pd.Index([])
 for st,en,_,_ in events: idx=idx.union(rp.index[(rp.index>st)&(rp.index<=en)])
 beta,alpha,n=_conditional_capm(rp.reindex(idx),rm.reindex(idx),rf,ppy)
 return {'Scenario':label,'Historical Events':len(er),'Avg Portfolio Event Return':er['Portfolio Event Return'].mean(),'Median Portfolio Event Return':er['Portfolio Event Return'].median(),'Avg Benchmark Event Return':er['Benchmark Event Return'].mean(),'Worst Portfolio Event':er['Portfolio Event Return'].min(),'Best Portfolio Event':er['Portfolio Event Return'].max(),'Positive Portfolio Events':(er['Portfolio Event Return']>0).mean(),'Conditional Beta':beta,'Conditional Alpha (periodic)':alpha,'CAPM Period Obs':n}

def one_period_shock_stats(vals,market_price,factor_change,threshold,rf,ppy,label):
 rp=vals.PORTFOLIO.pct_change(fill_method=None); rm=market_price.pct_change(fill_method=None)
 d=pd.concat([rp.rename('P'),rm.rename('M'),factor_change.rename('F')],axis=1).dropna(); e=d[d.F>=threshold]
 beta,alpha,n=_conditional_capm(e.P,e.M,rf,ppy)
 return {'Scenario':label,'Historical Events':len(e),'Avg Portfolio Event Return':e.P.mean() if len(e) else np.nan,'Median Portfolio Event Return':e.P.median() if len(e) else np.nan,'Avg Benchmark Event Return':e.M.mean() if len(e) else np.nan,'Avg Factor Shock':e.F.mean() if len(e) else np.nan,'Worst Portfolio Event':e.P.min() if len(e) else np.nan,'Best Portfolio Event':e.P.max() if len(e) else np.nan,'Positive Portfolio Events':(e.P>0).mean() if len(e) else np.nan,'Conditional Beta':beta,'Conditional Alpha (periodic)':alpha,'CAPM Period Obs':n}

def walk_forward_validation(vals,market_r,rf,ppy=52,window=52,var_method='Historical',var_level=.95):
 rp=vals.PORTFOLIO.pct_change(fill_method=None).dropna().rename('Portfolio')
 mr=market_r.rename('Benchmark') if market_r is not None else pd.Series(dtype=float,name='Benchmark')
 rfp=(1+rf)**(1/ppy)-1; rows=[]; z95=-1.6448536269514722
 for i in range(window,len(rp)):
  train_p=rp.iloc[i-window:i]; test_p=rp.iloc[i]; dt=rp.index[i]; tr=train_p.dropna(); beta=alpha=capm_pred=np.nan; test_b=np.nan
  if len(mr):
   hist=pd.concat([train_p,mr.reindex(train_p.index)],axis=1).dropna()
   if len(hist)>=window:
    x=hist.Benchmark-rfp; y=hist.Portfolio-rfp; beta=y.cov(x)/x.var() if x.var()>0 else np.nan; alpha=y.mean()-beta*x.mean() if np.isfinite(beta) else np.nan; test_b=mr.reindex([dt]).iloc[0]
    capm_pred=rfp+alpha+beta*(test_b-rfp) if np.isfinite(beta) and pd.notna(test_b) else np.nan
  if var_method=='Historical': q=float(tr.quantile(1-var_level)); sigma=np.nan
  elif var_method=='Parametric':
   mu=float(tr.mean()); sigma=float(tr.std(ddof=1)); q=mu+z95*sigma
  else:
   # GARCH(1,1), normal innovations; fit only to the trailing 52 weeks, forecast t+1.
   try:
    from arch import arch_model
    fit=arch_model(tr.values*100,mean='Constant',vol='GARCH',p=1,q=1,dist='normal',rescale=False).fit(disp='off',show_warning=False)
    fc=fit.forecast(horizon=1,reindex=False); mu=float(fit.params.get('mu',tr.mean()*100))/100; sigma=float(np.sqrt(fc.variance.values[-1,0]))/100; q=mu+z95*sigma
   except Exception:
    q=np.nan; sigma=np.nan
  rows.append({'Date':dt,'Actual Return':float(test_p),'Benchmark Return':float(test_b) if pd.notna(test_b) else np.nan,'CAPM Forecast':capm_pred,'CAPM Alpha':alpha,'CAPM Beta':beta,'VaR 95%':q,'VaR Breach':bool(test_p<q) if np.isfinite(q) else False,'Forecast Sigma':sigma})
 out=pd.DataFrame(rows).set_index('Date') if rows else pd.DataFrame()
 return out

def walk_forward_summary(wf,var_method):
 if wf.empty: return pd.DataFrame()
 valid=wf.dropna(subset=['Actual Return','CAPM Forecast']); rmse=float(np.sqrt(((valid['Actual Return']-valid['CAPM Forecast'])**2).mean())) if len(valid) else np.nan
 mae=float((valid['Actual Return']-valid['CAPM Forecast']).abs().mean()) if len(valid) else np.nan
 v=wf.dropna(subset=['VaR 95%']); breaches=int(v['VaR Breach'].sum()) if len(v) else 0; rate=breaches/len(v) if len(v) else np.nan
 return pd.DataFrame([{'Estimation Window':'252 days','OOS Weeks':len(wf),'CAPM Forecast RMSE':rmse,'CAPM Forecast MAE':mae,'Mean OOS Beta':wf['CAPM Beta'].mean(),'VaR Method':var_method,'VaR Confidence':'95%','VaR Breaches':breaches,'VaR Breach Rate':rate,'Expected Breach Rate':.05}])

title_col, report_col1, report_col2=st.columns([8,1,1])
with title_col: st.title('Portfolio Backtester')
latex_slot=report_col1.empty(); audit_slot=report_col2.empty(); st.subheader('Backtest Configuration'); a,b,c,d,e=st.columns([1.15,.75,1.15,1.15,1.15])
with a: timeline=st.selectbox('Timeline',['1W','1M','3M','6M','1Y','3Y','5Y','10Y','All','Custom'],index=8)
with b: PORTFOLIO_CCY=st.segmented_control('Currency',['ZAR','USD','EUR','GBP'],default='ZAR',selection_mode='single') or 'ZAR'
with c: INITIAL=float(st.number_input(f'Nominal amount ({PORTFOLIO_CCY})',min_value=1.0,value=float(DEFAULT_INITIAL),step=10000.0))
with d: RF=float(st.number_input('Risk-free rate (%)',min_value=0.0,max_value=100.0,value=7.0,step=.25))/100
with e:
 REINVEST=True
 st.toggle('Adjusted-return series (distributions embedded)',value=True,disabled=True,help='Adjusted prices already embed distributions; they are not added separately.')
custom_start=custom_end=None
if timeline=='Custom':
 x,y=st.columns(2)
 with x: custom_start=st.date_input('Custom start',value=pd.Timestamp('1900-01-01').date())
 with y: custom_end=st.date_input('Custom end',value=pd.Timestamp.today().date())
if 'selected_assets' not in st.session_state: st.session_state.selected_assets=DEFAULT_TICKERS.copy()
st.markdown('**Assets**')
search_query=st.text_input('Search asset',placeholder='Search by company, fund, index or ticker')
results=search_assets(search_query) if search_query.strip() else []
if 'asset_names' not in st.session_state: st.session_state.asset_names={}
if results:
 labels=[f"{r['name']} — {r['symbol']}" for r in results]
 def _select_search_asset():
  picked=st.session_state.get('asset_search_pick')
  if picked is None: return
  row=results[picked]; symbol=row['symbol']
  st.session_state.asset_names[symbol]=row['name']
  current=list(st.session_state.get('selected_assets_widget',st.session_state.selected_assets))
  if symbol not in current: current.append(symbol)
  st.session_state.selected_assets=current.copy()
  st.session_state.selected_assets_widget=current
 picked=st.pills('Search results',options=range(len(results)),format_func=lambda i: labels[i],selection_mode='single',key='asset_search_pick',on_change=_select_search_asset)
ASSETS=st.multiselect('Selected assets',options=list(dict.fromkeys(st.session_state.selected_assets+DEFAULT_TICKERS+['GOVI'])),default=st.session_state.selected_assets,key='selected_assets_widget')
st.session_state.selected_assets=ASSETS
if not ASSETS: st.error('Select at least one asset.'); st.stop()
st.markdown('**Benchmark (optional)**')
USE_BENCHMARK=st.toggle('Use benchmark',value=True,key='use_benchmark')
if 'benchmark_symbol' not in st.session_state: st.session_state.benchmark_symbol=BENCHMARK_TICKER
if 'benchmark_name' not in st.session_state: st.session_state.benchmark_name='FTSE/JSE All Share Index'
if USE_BENCHMARK:
 benchmark_query=st.text_input('Search benchmark',placeholder='Search by index, ETF, fund or ticker',key='benchmark_search_query')
 benchmark_results=search_assets(benchmark_query) if benchmark_query.strip() else []
 if benchmark_results:
  benchmark_labels=[f"{r['name']} — {r['symbol']}" for r in benchmark_results]
  def _select_benchmark():
   picked=st.session_state.get('benchmark_search_pick')
   if picked is None: return
   row=benchmark_results[picked]; st.session_state.benchmark_symbol=row['symbol']; st.session_state.benchmark_name=row['name']
  st.pills('Benchmark search results',options=range(len(benchmark_results)),format_func=lambda i: benchmark_labels[i],selection_mode='single',key='benchmark_search_pick',on_change=_select_benchmark)
 BENCHMARK=st.session_state.benchmark_symbol
 st.caption(f"Selected benchmark: {st.session_state.benchmark_name} — {BENCHMARK}")
else:
 BENCHMARK=None
 st.caption('No benchmark selected. Portfolio analytics and standalone VaR remain available; benchmark beta/alpha/CAPM and benchmark stress are omitted.')
st.markdown('**Currency Exposure**')
fxc1,fxc2=st.columns(2)
with fxc1: FX_ADJUST=st.toggle('Adjust foreign assets to portfolio currency',value=False)
with fxc2:
 BASE_CCY=PORTFOLIO_CCY
 st.text_input('Portfolio / base currency',value=BASE_CCY,disabled=True)
FX_ADJUSTED_ASSETS=[]; SOURCE_CCYS={}
if FX_ADJUST:
 FX_ADJUSTED_ASSETS=st.multiselect('Assets to currency-adjust',options=ASSETS,default=[],help='Choose from the assets currently loaded into the portfolio. Unselected assets are left unchanged.')
 foreign_ccys=[x for x in ['USD','EUR','GBP','JPY','CHF','AUD','CAD','ZAR'] if x!=BASE_CCY]
 if FX_ADJUSTED_ASSETS:
  st.caption('Select the source currency in which each selected Yahoo asset return is measured. The app translates that asset into the portfolio/base currency before the backtest.')
  fxcols=st.columns(3)
  for i,a_fx in enumerate(FX_ADJUSTED_ASSETS):
   default_i=foreign_ccys.index('USD') if 'USD' in foreign_ccys else 0
   with fxcols[i%3]: SOURCE_CCYS[a_fx]=st.selectbox(f'{a_fx} source currency',foreign_ccys,index=default_i,key=f'fxccy_{a_fx}_{BASE_CCY}')
BENCHMARK_FX_ADJUST=False; BENCHMARK_SOURCE_CCY=None
if USE_BENCHMARK:
 BENCHMARK_FX_ADJUST=st.toggle('Currency-adjust benchmark to portfolio currency',value=False,help='Optional. Use when the selected benchmark is quoted in a currency different from the portfolio/base currency.')
 if BENCHMARK_FX_ADJUST:
  benchmark_ccys=[x for x in ['USD','EUR','GBP','JPY','CHF','AUD','CAD','ZAR'] if x!=BASE_CCY]
  benchmark_default=benchmark_ccys.index('USD') if 'USD' in benchmark_ccys else 0
  BENCHMARK_SOURCE_CCY=st.selectbox('Benchmark source currency',benchmark_ccys,index=benchmark_default,key=f'benchmark_fxccy_{BENCHMARK}_{BASE_CCY}')
st.markdown('**Weights**'); cols=st.columns(3); raww={}; default_sum=sum(DEFAULT_WEIGHTS.get(x,0.0) for x in ASSETS)
for i,a0 in enumerate(ASSETS):
 default=(DEFAULT_WEIGHTS.get(a0,0.0)/default_sum*100) if default_sum>0 else 100/len(ASSETS)
 with cols[i%3]: raww[a0]=st.number_input(f'{a0} (%)',min_value=-500.0,max_value=500.0,value=float(default),step=.25,key=f'w_{a0}',help='Negative weight = short position.')/100
net_weight=sum(raww.values()); gross_weight=sum(abs(w) for w in raww.values())
if net_weight<=0: st.error('Net portfolio weight must be greater than 0%.'); st.stop()
weights={a0:w/net_weight for a0,w in raww.items()}; ALLOC={a0:INITIAL*w for a0,w in weights.items()}
st.caption(f'Net exposure normalised to 100% | Gross exposure {sum(abs(w) for w in weights.values()):.1%}. Negative weights are treated as short positions.')
st.markdown('**Leverage & Financing**')
lev1,lev2=st.columns(2)
with lev1: LEVERAGE=float(st.number_input('Portfolio leverage (x)',min_value=1.0,max_value=10.0,value=1.0,step=.1,help='1.0x = no additional leverage. Applied to portfolio periodic returns after configured long/short weights.'))
with lev2: LEVERAGE_COST=float(st.number_input('Annual leverage / financing cost (%)',min_value=0.0,max_value=100.0,value=0.0,step=.25,help='Annual financing rate charged on additional borrowed capital (leverage − 1).'))/100
custom_days=(pd.Timestamp(custom_end)-pd.Timestamp(custom_start)).days if timeline=='Custom' and custom_start and custom_end else None; daily_mode=True; ppy=252
try:
 with st.spinner('Updating, configuring and validating market data…'):
  full_p,full_d,govi,bond_validation,split_events=build_master(ASSETS,REINVEST)
  interpolation_report=bond_validation.get('interpolation_report',pd.DataFrame()).copy()
  common_inception=full_p.index.min(); common_endpoint=full_p.index.max(); raw_week_count=len(full_p)
  missing_by_asset={a:int(interpolation_report.loc[interpolation_report.Series==a,'Interpolated Values'].sum()) if not interpolation_report.empty else 0 for a in ASSETS}
  excluded_incomplete_weeks=0
  start,end,requested=resolve_dates(full_p.index,timeline,custom_start,custom_end,daily_mode)
  prices=full_p.loc[(full_p.index>=start)&(full_p.index<=end),ASSETS].copy(); divs=pd.DataFrame(0.0,index=prices.index,columns=ASSETS)
  benchmark_missing_weeks=0; benchmark_overlap_start=None; benchmark_overlap_end=None
  if USE_BENCHMARK:
   if BENCHMARK=='GOVI': raise RuntimeError('Repository GOVI is monthly-only and cannot be used as a daily benchmark. Select a daily-history market ticker/proxy.')
   bench_p,bench_d,_=load_ticker_components((BENCHMARK,)); bp_raw=bench_p[BENCHMARK].sort_index()
   bench_valid=bp_raw.dropna(); benchmark_overlap_start=max(prices.index.min(),bench_valid.index.min()); benchmark_overlap_end=min(prices.index.max(),bench_valid.index.max())
   benchmark_portfolio_index=prices.index[(prices.index>=benchmark_overlap_start)&(prices.index<=benchmark_overlap_end)]
   bp_on_master=bp_raw.reindex(benchmark_portfolio_index)
   benchmark_missing_weeks=int(bp_on_master.isna().sum())
   bp_interp=bp_on_master.interpolate(method='time',limit_area='inside')
   bp=pd.Series(np.nan,index=prices.index,dtype=float,name=BENCHMARK); bp.loc[benchmark_portfolio_index]=bp_interp
   bd=pd.Series(0.0,index=prices.index,dtype=float)
   interpolation_report=pd.concat([interpolation_report,pd.DataFrame([{'Series':BENCHMARK,'Type':'Benchmark','Interpolated Values':benchmark_missing_weeks,'Genuine Values':int(bp_on_master.notna().sum())}])],ignore_index=True)
  else:
   bp=pd.Series(np.nan,index=prices.index,dtype=float); bd=pd.Series(0.0,index=prices.index,dtype=float)
  if len(prices)<2: raise RuntimeError('Selected timeline has fewer than two synchronized portfolio observations')
  benchmark_fx_report=pd.DataFrame()
  if USE_BENCHMARK and BENCHMARK_FX_ADJUST:
   bp_frame=pd.DataFrame({BENCHMARK:bp},index=prices.index); bd_frame=pd.DataFrame({BENCHMARK:bd},index=prices.index)
   bp_frame,bd_frame,benchmark_fx_report=translate_currency(bp_frame,bd_frame,[BENCHMARK],{BENCHMARK:BENCHMARK_SOURCE_CCY},BASE_CCY,daily_mode)
   bp=bp_frame[BENCHMARK]; bd=bd_frame[BENCHMARK]
  fx_translation_report=pd.DataFrame()
  if FX_ADJUST and FX_ADJUSTED_ASSETS:
   prices,divs,fx_translation_report=translate_currency(prices,divs,FX_ADJUSTED_ASSETS,SOURCE_CCYS,BASE_CCY,daily_mode)
  # All downstream asset-return analytics must use the same currency-adjusted
  # prices and distributions as the portfolio engine.
  asset_r=(prices-prices.shift(1)+divs)/prices.shift(1); bad=asset_r.abs().max(); bad=bad[bad>(.35 if daily_mode else 1.0)]
  if len(bad): raise RuntimeError('Implausible asset return(s): '+', '.join(f'{k}={v:.1%}' for k,v in bad.items()))
  bh=portfolio_values(prices,divs,ALLOC,REINVEST,None)
except Exception as e: st.error(f'Data update/validation failed: {e}'); st.exception(e); st.stop()
data_flags=[]
# Weekly alignment exclusions are documented in Data Audit; they are not promoted to DATA FLAGS unless they prevent the backtest.
if USE_BENCHMARK and benchmark_missing_weeks>0: data_flags.append(f'Benchmark had {benchmark_missing_weeks} missing daily level(s) inside its overlap with the portfolio; these levels were time-interpolated and recorded in Data Audit.')
if USE_BENCHMARK and benchmark_overlap_start>prices.index.min(): st.caption(f'Portfolio history begins {prices.index.min():%Y-%m-%d}. Benchmark-dependent analytics begin at the nearest available benchmark overlap date, {benchmark_overlap_start:%Y-%m-%d}; earlier portfolio observations remain in all portfolio-level calculations.')
if start>requested: data_flags.append(f'Requested start {requested:%Y-%m-%d} unavailable for the selected common asset set; backtest starts at {start:%Y-%m-%d}.')
frequency='daily Adjusted Close (missing aligned levels interpolated)'; st.caption(f'Configured window {prices.index[0]:%d %b %Y} to {prices.index[-1]:%d %b %Y} | {frequency} | Nominal {PORTFOLIO_CCY} {INITIAL:,.0f} | RF {RF:.2%} | Adjusted returns (distributions embedded)'+(f' | FX translated to {BASE_CCY}: {len(FX_ADJUSTED_ASSETS)} asset(s)' if FX_ADJUST and FX_ADJUSTED_ASSETS else ' | FX translation off')+f' | Leverage {LEVERAGE:.1f}x | Financing cost {LEVERAGE_COST:.2%} p.a.')
if FX_ADJUST and FX_ADJUSTED_ASSETS and not fx_translation_report.empty:
 st.subheader('Currency Translation'); st.dataframe(fx_translation_report,hide_index=True,use_container_width=True)
if USE_BENCHMARK and BENCHMARK_FX_ADJUST and not benchmark_fx_report.empty:
 st.subheader('Benchmark Currency Translation'); st.dataframe(benchmark_fx_report,hide_index=True,use_container_width=True)
if data_flags: st.warning('DATA FLAGS — '+' | '.join(data_flags))
mode=st.selectbox('Backtest mode',['Buy & Hold','Rebalanced'],index=0,key='backtest_mode')
if mode=='Rebalanced':
 rebalance_frequency=st.selectbox('Rebalancing frequency',['Annual','Semi-Annual','Quarterly','Monthly','Weekly'],index=0,key='rebalance_frequency',help='Portfolio is reset to the configured target weights at the first available daily observation of each selected rebalance period.')
 vals=portfolio_values(prices,divs,ALLOC,REINVEST,rebalance_frequency).copy()
 mode_label=f'{rebalance_frequency} Rebalanced'
else:
 rebalance_frequency=None; vals=bh.copy(); mode_label='Buy & Hold'
# Additional leverage is applied to the configured long/short portfolio return. Financing
# cost is charged only on borrowed capital (L-1), converted to an effective daily rate.
base_portfolio=vals.PORTFOLIO.copy(); base_r=base_portfolio.pct_change(fill_method=None)
period_financing=(1+LEVERAGE_COST)**(1/ppy)-1
levered_r=LEVERAGE*base_r-(LEVERAGE-1.0)*period_financing
levered_growth=(1+levered_r.fillna(0.0)).cumprod(); vals.loc[:,'PORTFOLIO']=INITIAL*levered_growth
vals.loc[vals.index[0],'PORTFOLIO']=INITIAL
market_r=(bp-bp.shift(1)+bd)/bp.shift(1) if USE_BENCHMARK else pd.Series(np.nan,index=prices.index,dtype=float)
portfolio_r_for_benchmark=vals.PORTFOLIO.pct_change(fill_method=None)
benchmark_analysis=pd.concat([portfolio_r_for_benchmark.rename('Portfolio'),market_r.rename('Benchmark')],axis=1).dropna() if USE_BENCHMARK else pd.DataFrame(columns=['Portfolio','Benchmark'])
benchmark_return_aligned=benchmark_analysis['Benchmark'] if USE_BENCHMARK else pd.Series(dtype=float)
met=stats(vals,benchmark_return_aligned,RF,ppy)
c1,c2,c3,c4=st.columns(4); c1.metric(f'{mode_label} Value',f"{met['Ending Value']:,.0f}"); c2.metric(f'{mode_label} CAGR',f"{met['CAGR']:.2%}"); c3.metric(f'Sharpe ({RF:.2%} RF)',f"{met['Sharpe Ratio']:.3f}"); c4.metric('Max Drawdown',f"{met['Maximum Drawdown']:.2%}")
st.subheader(f'{mode_label} Analytics'); st.dataframe(metric_table(met),hide_index=True,use_container_width=True)
p=vals.PORTFOLIO; r=p.pct_change(fill_method=None).dropna(); growth=p/p.iloc[0]*100; dd=(p/p.cummax()-1)*100; roll_n=252; sharpe_n=756; roll_ret=((1+r).rolling(roll_n).apply(np.prod,raw=True)-1)*100; roll_vol=r.rolling(roll_n).std()*np.sqrt(ppy)*100; ex=r-((1+RF)**(1/ppy)-1); roll_sr=ex.rolling(sharpe_n).mean()/ex.rolling(sharpe_n).std()*np.sqrt(ppy)
line_chart({mode_label:p},f'{mode_label} — Portfolio Value','Value'); line_chart({mode_label:growth},f'{mode_label} — Growth of 100','Value'); line_chart({'Drawdown':dd},f'{mode_label} — Portfolio Drawdown','%'); line_chart({'Rolling 1Y Total Return':roll_ret},f'{mode_label} — Rolling 1-Year Total Return','%'); line_chart({'Rolling 1Y Volatility':roll_vol},f'{mode_label} — Rolling 1-Year Annualised Volatility','%'); line_chart({'Rolling 3Y Sharpe':roll_sr},f'{mode_label} — Rolling 3-Year Sharpe Ratio','Sharpe'); line_chart({c0:vals[c0] for c0 in ASSETS},f'{mode_label} — Portfolio Sleeve Values','Value')
st.subheader(f'{mode_label} Annual Total Returns'); ar=annual_returns(vals); ar['Annual Total Return']=ar['Annual Total Return'].map(lambda x:f'{x:.2%}'); st.dataframe(ar,hide_index=True,use_container_width=True)
st.subheader('Annual Total Return by Ticker'); aar=annual_asset_returns(prices,divs,ASSETS)
for c0 in ASSETS: aar[c0]=aar[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
st.dataframe(aar,hide_index=True,use_container_width=True)
st.subheader('Return Attribution by Instrument — Capital Gain vs Income'); attr=[]
instrument_names=resolve_instrument_names(tuple(ASSETS)); instrument_names.update(st.session_state.get('asset_names',{}))
for a0 in ASSETS:
 p0=float(prices[a0].iloc[0]); p1=float(prices[a0].iloc[-1]); cap=(p1-p0)/p0; inc=float(divs[a0].iloc[1:].sum())/p0; total=cap+inc; attr.append({'Instrument':instrument_names.get(a0,a0),'Ticker / Series':a0,'Total Return':total,'Capital Gain':cap,'Income / Distributions':inc,'Capital Gain % of Total':cap/total if not np.isclose(total,0) else np.nan,'Income % of Total':inc/total if not np.isclose(total,0) else np.nan})
at=pd.DataFrame(attr)
for c0 in ['Total Return','Capital Gain','Income / Distributions','Capital Gain % of Total','Income % of Total']: at[c0]=at[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
st.dataframe(at,hide_index=True,use_container_width=True)
weights_end=vals[ASSETS].div(vals.PORTFOLIO,axis=0); wt=pd.DataFrame({'Ticker':ASSETS,'Initial Weight':[weights[a0] for a0 in ASSETS],'Ending Weight':weights_end.iloc[-1].values}); wt['Initial Weight']=wt['Initial Weight'].map(lambda x:f'{x:.2%}'); wt['Ending Weight']=wt['Ending Weight'].map(lambda x:f'{x:.2%}'); st.subheader(f'{mode_label} Portfolio Weights'); st.dataframe(wt,hide_index=True,use_container_width=True)
st.divider(); st.subheader('Asset Correlation')
corr_left,corr_right=st.columns([4,1])
with corr_left:
 corr_method=st.segmented_control('Correlation measure',['Pearson','Spearman'],default='Pearson',selection_mode='single',key='corr_method') or 'Pearson'
with corr_right:
 corr_latex=st.button('Linearity Test: Show LaTeX',key='corr_latex_btn',use_container_width=True)
# Diagnostics are descriptive guidance, not an automatic model-selection rule.
# Pearson measures linear association; Spearman measures monotonic rank association.
from scipy.stats import spearmanr
corr_sample=asset_r[ASSETS].dropna()
pair_diag=[]
for ii,a in enumerate(ASSETS):
 for b in ASSETS[ii+1:]:
  xy=corr_sample[[a,b]].dropna(); n=len(xy)
  if n<8: continue
  x=xy[a].to_numpy(float); y=xy[b].to_numpy(float)
  pr=float(np.corrcoef(x,y)[0,1]); sr=float(spearmanr(x,y,nan_policy='omit').statistic)
  # Linear fit and residual diagnostics: R^2 describes linear fit; curvature-gain compares
  # a quadratic fit with the linear fit. Large Pearson-vs-Spearman divergence is also flagged.
  coef1=np.polyfit(x,y,1); y1=np.polyval(coef1,x); ss=float(np.sum((y-y.mean())**2)); r2_lin=(1-float(np.sum((y-y1)**2))/ss) if ss>0 else np.nan
  r2_quad=np.nan
  if n>=12 and np.unique(x).size>=3 and ss>0:
   coef2=np.polyfit(x,y,2); y2=np.polyval(coef2,x); r2_quad=1-float(np.sum((y-y2)**2))/ss
  curvature_gain=(r2_quad-r2_lin) if np.isfinite(r2_quad) and np.isfinite(r2_lin) else np.nan
  nonlinear_flag=bool((np.isfinite(curvature_gain) and curvature_gain>=0.05) or abs(sr-pr)>=0.10)
  pair_diag.append({'Pair':f'{a} / {b}','N':n,'Pearson':pr,'Spearman':sr,'Linear R²':r2_lin,'Quadratic ΔR²':curvature_gain,'Non-linearity flag':'Yes' if nonlinear_flag else 'No'})
if pair_diag:
 corr_diag=pd.DataFrame(pair_diag); nonlinear_share=float((corr_diag['Non-linearity flag']=='Yes').mean())
 corr_guidance=('Spearman may be more informative: several pairs show material non-linearity / rank-vs-linear divergence.' if nonlinear_share>=0.25 else 'Pearson is reasonable for linear association; Spearman remains useful as a robustness comparison.')
else:
 corr_diag=pd.DataFrame(); nonlinear_share=np.nan; corr_guidance='Insufficient paired observations for diagnostics.'
if corr_latex:
 @st.dialog('Linearity Test — Methodology & Results',width='large')
 def _corr_diag_dialog():
  st.latex(r'\rho_P(X,Y)=\frac{\operatorname{Cov}(X,Y)}{\sigma_X\sigma_Y}')
  st.latex(r'\rho_S(X,Y)=\rho_P(\operatorname{rank}(X),\operatorname{rank}(Y))')
  st.latex(r'R^2_{lin}=1-\frac{\sum_t(y_t-\hat y^{lin}_t)^2}{\sum_t(y_t-\bar y)^2},\qquad \Delta R^2=R^2_{quad}-R^2_{lin}')
  st.write('This linearity test examines whether each asset-pair return relationship is sufficiently linear for Pearson correlation, or whether a monotonic rank relationship may make Spearman correlation more informative. The results are guidance rather than an automatic model-selection rule.')
  st.info(corr_guidance)
  if not corr_diag.empty: st.dataframe(corr_diag,hide_index=True,use_container_width=True,column_config={'Pearson':st.column_config.NumberColumn(format='%.3f'),'Spearman':st.column_config.NumberColumn(format='%.3f'),'Linear R²':st.column_config.NumberColumn(format='%.3f'),'Quadratic ΔR²':st.column_config.NumberColumn(format='%.3f')})
  st.caption('Linearity flag: quadratic fit improves R² by at least 0.05 and/or |Spearman − Pearson| ≥ 0.10. This is a diagnostic convention, not a formal universal test or automatic selection rule.')
 _corr_diag_dialog()
corr=corr_sample.corr(method=corr_method.lower()); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()) if len(corr)>1 else np.nan; st.metric(f'Average Inter-Asset {corr_method} Correlation','N/A' if not np.isfinite(net_corr) else f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title=f'{corr_method} Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)
if USE_BENCHMARK:
 st.divider(); st.subheader(f'{mode_label} — Beta & Alpha Evolution vs {BENCHMARK}'); roll_beta,roll_alpha,capm_window=rolling_capm(vals,market_r,RF,ppy); line_chart({f'{capm_window}-period Rolling Beta':roll_beta},f'{mode} — Rolling Beta vs {BENCHMARK}','Beta'); line_chart({f'{capm_window}-period Rolling Alpha':roll_alpha*100},f'{mode} — Rolling Annualised CAPM Alpha','Alpha (%)'); cb,ncb=conditional_beta(vals,bp)
else: cb,ncb=np.nan,0

st.divider(); st.subheader('Macro Risk & Historical Scenario Analysis')
st.caption('Historical event analysis: portfolio performance is measured over the same realised market interval as each stress event. Results are event returns, not annualised hypothetical forecasts.')
bench_label=st.session_state.get('benchmark_name',BENCHMARK)
sc1,sc2,sc3,sc4,sc5=st.columns(5)
with sc1: use_bench=st.toggle(f'Benchmark −10% Drawdown ({bench_label} — {BENCHMARK})',value=True,key='macro_benchmark',disabled=not USE_BENCHMARK) if USE_BENCHMARK else False
with sc2: use_oil=st.toggle('Oil +3σ Shock',value=False,key='macro_oil')
with sc3: use_vix=st.toggle('VIX +2σ Shock',value=False,key='macro_vix')
with sc4: use_move=st.toggle('MOVE +1.5σ Shock',value=False,key='macro_move')
with sc5: use_hyoas=st.toggle('US HY OAS +2σ Widening',value=False,key='macro_hyoas')
scenario_rows=[]; macro_factor_meta=[]
if use_bench:
 scenario_rows.append(benchmark_scenario_stats(vals,bp,RF,ppy,BENCHMARK))
 macro_factor_meta.append({'Scenario':f'Benchmark −10% Drawdown ({bench_label} — {BENCHMARK})','Factor':f'{bench_label} — {BENCHMARK}','Event':'previous peak → first crossing of −10% drawdown','Threshold':'≤ −10%'})
if use_oil or use_vix or use_move or use_hyoas:
 try:
  mf=load_macro_factors(daily_mode).reindex(prices.index).interpolate(method='time',limit_area='inside')
  for name,use,zcut,label,transform in [('Oil',use_oil,3.0,'Oil +3σ Shock','pct'),('VIX',use_vix,2.0,'VIX +2σ Shock','pct'),('MOVE',use_move,1.5,'MOVE +1.5σ Shock','pct'),('HY OAS',use_hyoas,2.0,'US HY OAS +2σ Widening','diff')]:
   if not use: continue
   chg=mf[name].diff() if transform=='diff' else mf[name].pct_change(fill_method=None)
   mu=chg.mean(); sig=chg.std(); threshold=mu+zcut*sig
   scenario_rows.append(one_period_shock_stats(vals,bp,chg,threshold,RF,ppy,label) if USE_BENCHMARK else one_period_shock_stats(vals,pd.Series(np.nan,index=vals.index),chg,threshold,RF,ppy,label))
   macro_factor_meta.append({'Scenario':label,'Factor':name,'Event':'single configured observation interval','Transformation':'percentage-point change' if transform=='diff' else 'percentage change','Mean':mu,'Std Dev':sig,'Threshold':threshold})
 except Exception as e:
  st.warning(f'Macro factor data unavailable for selected scenario(s): {e}')
scenario_df=pd.DataFrame(scenario_rows); macro_factor_meta_df=pd.DataFrame(macro_factor_meta)
if not scenario_df.empty:
 display_scen=scenario_df.copy()
 for c0 in ['Avg Portfolio Event Return','Median Portfolio Event Return','Avg Benchmark Event Return','Avg Factor Shock','Worst Portfolio Event','Best Portfolio Event','Positive Portfolio Events','Conditional Alpha (periodic)']:
  if c0 in display_scen: display_scen[c0]=display_scen[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
 if 'Conditional Beta' in display_scen: display_scen['Conditional Beta']=display_scen['Conditional Beta'].map(lambda x:f'{x:.3f}' if pd.notna(x) else 'N/A')
 st.dataframe(display_scen,hide_index=True,use_container_width=True)
else: st.info('Select at least one macro risk scenario.')

st.divider(); st.subheader('Walk-Forward Validator — 252-Day Estimation Window')
st.caption('Strict one-step-ahead validation: each CAPM and VaR estimate uses only the preceding 252 daily observations; the following day is held out for validation.')
wf_method=st.segmented_control('VaR model',['Historical','Parametric','GARCH(1,1)'],default='Historical',selection_mode='single',key='wf_var_method') or 'Historical'
wf=walk_forward_validation(vals,market_r if USE_BENCHMARK else None,RF,ppy,252,wf_method,.95)
wf_summary=walk_forward_summary(wf,wf_method)
if wf.empty:
 st.warning('Walk-forward validation requires at least 253 daily portfolio observations.')
else:
 show_sum=wf_summary.copy()
 for c0 in ['CAPM Forecast RMSE','CAPM Forecast MAE','VaR Breach Rate','Expected Breach Rate']:
  if c0 in show_sum: show_sum[c0]=show_sum[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
 if 'Mean OOS Beta' in show_sum: show_sum['Mean OOS Beta']=show_sum['Mean OOS Beta'].map(lambda x:f'{x:.3f}' if pd.notna(x) else 'N/A')
 st.dataframe(show_sum,hide_index=True,use_container_width=True)
 line_chart({'Actual Weekly Return':wf['Actual Return']*100,'CAPM One-Step Forecast':wf['CAPM Forecast']*100},'Walk-Forward CAPM — Actual vs One-Step-Ahead Forecast','Return (%)')
 line_chart({'52-Week CAPM Beta':wf['CAPM Beta']},'Walk-Forward CAPM — Estimated Beta','Beta')
 line_chart({'Actual Weekly Return':wf['Actual Return']*100,'95% VaR Threshold':wf['VaR 95%']*100},f'Walk-Forward {wf_method} VaR — One-Step-Ahead Validation','Return (%)')
 wf_table=wf.reset_index()[['Date','Actual Return','CAPM Forecast','CAPM Alpha','CAPM Beta','VaR 95%','VaR Breach']].copy()
 for c0 in ['Actual Return','CAPM Forecast','CAPM Alpha','VaR 95%']: wf_table[c0]=wf_table[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
 wf_table['CAPM Beta']=wf_table['CAPM Beta'].map(lambda x:f'{x:.3f}' if pd.notna(x) else 'N/A')
 st.dataframe(wf_table,hide_index=True,use_container_width=True)

@st.dialog('Complete Quantitative Workings',width='large')
def show_latex_report():
 st.title('Complete Quantitative Workings')
 st.caption(f'Configured run: {prices.index[0]:%Y-%m-%d} to {prices.index[-1]:%Y-%m-%d} | frequency={frequency} | N={ppy} | RF={RF:.4%} | observations={len(prices)} | mode={mode_label}')
 st.header('1. Data state, units and reconstructed returns')
 st.latex(r'P_{i,t}=\text{raw close price},\quad D_{i,t}=\text{cash distribution per unit},\quad S_{i,t}=\text{split event}')
 st.latex(r'r_{i,t}=\frac{P_{i,t}-P_{i,t-1}+D_{i,t}}{P_{i,t-1}}')
 st.latex(r'R^{cap}_i=\frac{P_{i,T}-P_{i,0}}{P_{i,0}},\quad R^{inc}_i=\frac{\sum_{t=1}^{T}D_{i,t}}{P_{i,0}},\quad R^{tot}_i=R^{cap}_i+R^{inc}_i')
 st.latex(r'\omega^{cap}_i=R^{cap}_i/R^{tot}_i,\quad \omega^{inc}_i=R^{inc}_i/R^{tot}_i')
 st.write('Daily Yahoo Adjusted Close is used directly for every Yahoo ticker. Distributions and split effects are embedded in Adjusted Close and are not added again downstream. No ticker-specific normalisation or manual corporate-action reconstruction is applied.')
 st.dataframe(pd.DataFrame({'Instrument':[instrument_names.get(i,i) for i in ASSETS],'Ticker / Series':ASSETS,'Initial Price':[prices[i].iloc[0] for i in ASSETS],'Final Price':[prices[i].iloc[-1] for i in ASSETS],'Cash Distributions':[divs[i].iloc[1:].sum() for i in ASSETS]}),hide_index=True,use_container_width=True)
 st.header('2. Portfolio initialisation and accounting identity')
 st.latex(r'A_{i,0}=w_iV_0,\qquad q_{i,0}=\frac{A_{i,0}}{P_{i,0}},\qquad \sum_iw_i=1')
 st.latex(r'I_{i,t}=q_{i,t-1}D_{i,t}')
 st.latex(r'q_{i,t}=q_{i,t-1}+\frac{I_{i,t}}{P_{i,t}}\quad\text{(reinvestment)}')
 st.latex(r'C_{i,t}=C_{i,t-1}+I_{i,t}\quad\text{(income retained as cash)}')
 st.latex(r'V_{i,t}=q_{i,t}P_{i,t}+C_{i,t},\qquad V_t=\sum_iV_{i,t}')
 st.write(f'Reporting currency = {PORTFOLIO_CCY}; nominal V0 = {PORTFOLIO_CCY} {INITIAL:,.2f}; reinvest distributions = {REINVEST}.')
 st.header('3. Annual rebalancing')
 st.latex(r'w_i^*=\frac{A_{i,0}}{V_0},\qquad q_{i,t^+}=\frac{w_i^*V_{t^-}}{P_{i,t^-}},\qquad C_{i,t^+}=0')
 st.write('Rebalancing is applied at the first observation of a new calendar year when Annual Rebalanced mode is selected.')
 st.header('4. Portfolio and annual total return')
 st.latex(r'r_{p,t}=\frac{V_t}{V_{t-1}}-1,\qquad R_{p,0:T}=\frac{V_T}{V_0}-1')
 st.latex(r'R_{p,y}=\frac{V_{y,end}}{V_{y,start}}-1')
 st.latex(r'R_{i,y}=\frac{P_{i,end}-P_{i,start}+\sum_{t\in y}D_{i,t}}{P_{i,start}}')
 st.header('5. CAGR and elapsed-time convention')
 st.latex(r'Y=\frac{T_{end}-T_{start}}{365.25},\qquad CAGR=\left(\frac{V_T}{V_0}\right)^{1/Y}-1')
 st.write(f'Current CAGR = {met["CAGR"]:.6%}; elapsed observations = {len(prices)}.')
 st.header('6. Volatility and risk-free transformation')
 st.latex(r'N=252\ \text{(daily)}')
 st.latex(r'\sigma_{ann}=s(r_p)\sqrt{N}')
 st.latex(r'r_{f}=\left(1+R_f\right)^{1/N}-1,\qquad e_t=r_{p,t}-r_f')
 st.write(f'Current N={ppy}; annual RF={RF:.6%}; periodic RF={(1+RF)**(1/ppy)-1:.8%}; annualised volatility={met["Annualised Volatility"]:.6%}.')
 st.header('7. Sharpe ratio')
 st.latex(r'Sharpe=\frac{\bar e}{s(e)}\sqrt{N}')
 st.write(f'Current Sharpe = {met["Sharpe Ratio"]:.6f}.')
 st.header('8. Downside deviation and Sortino')
 st.latex(r'\mathcal D=\{t:e_t<0\},\qquad \sigma_{down}=\sqrt{\frac{1}{|\mathcal D|}\sum_{t\in\mathcal D}e_t^2}\sqrt N')
 st.latex(r'Sortino=\frac{\bar e\,N}{\sigma_{down}}')
 st.write(f'Downside volatility={met["Downside Volatility"]:.6%}; Sortino={met["Sortino Ratio"]:.6f}.')
 st.header('9. Drawdown, maximum drawdown and Calmar')
 st.latex(r'H_t=\max_{s\le t}V_s,\qquad DD_t=\frac{V_t}{H_t}-1,\qquad MDD=\min_tDD_t')
 st.latex(r'Calmar=\frac{CAGR}{|MDD|}')
 st.write(f'MDD={met["Maximum Drawdown"]:.6%}; MDD date={met["Max DD Date"]:%Y-%m-%d}; Calmar={met["Calmar Ratio"]:.6f}.')
 st.header('10. Historical VaR and CVaR / Expected Shortfall')
 st.latex(r'VaR_{95}=Q_{0.05}(r_p)')
 st.latex(r'CVaR_{95}=E[r_p\mid r_p\le VaR_{95}]')
 st.write(f'VaR95={met["Period VaR 95%"]:.6%}; CVaR95={met["Period CVaR 95%"]:.6%}.')
 st.header('11. Empirical return diagnostics')
 st.latex(r'r_{best}=\max_t r_{p,t},\quad r_{worst}=\min_t r_{p,t},\quad p_+=\frac{\sum_t\mathbf 1(r_{p,t}>0)}{T}')
 st.write(f'Best={met["Best Period"]:.6%}; worst={met["Worst Period"]:.6%}; positive periods={met["Positive Periods"]:.6%}.')
 st.header('12. Rolling one-year total return')
 st.latex(r'R^{(L)}_{p,t}=\prod_{j=0}^{L-1}(1+r_{p,t-j})-1')
 st.write(f'L={roll_n} observations.')
 st.header('13. Rolling annualised volatility')
 st.latex(r'\sigma^{(L)}_{p,t}=s(r_{p,t-L+1:t})\sqrt N')
 st.header('14. Rolling three-year Sharpe')
 st.latex(r'Sharpe^{(W)}_t=\frac{\overline e_{t-W+1:t}}{s(e_{t-W+1:t})}\sqrt N')
 st.write(f'W={sharpe_n} observations.')
 st.header('15. Portfolio sleeve weights and drift')
 st.latex(r'w_{i,t}=\frac{V_{i,t}}{V_t},\qquad \Delta w_{i,t}=w_{i,t}-w_{i,0}')
 st.dataframe(wt,hide_index=True,use_container_width=True)
 st.header('16. Pearson covariance and correlation matrix')
 st.latex(r'Cov_{ij}=\frac{1}{T-1}\sum_{t=1}^{T}(r_{i,t}-\bar r_i)(r_{j,t}-\bar r_j)')
 st.latex(r'\rho_{ij}=\frac{Cov_{ij}}{s_i s_j}')
 st.latex(r'\bar\rho=\frac{2}{K(K-1)}\sum_{i<j}\rho_{ij}')
 st.write('The page heatmap is the Pearson matrix computed from the same reconstructed periodic asset returns.')
 st.dataframe(corr,use_container_width=True)
 st.write('Net inter-asset correlation = '+('N/A' if not np.isfinite(net_corr) else f'{net_corr:.6f}'))
 st.header('17. CAPM beta')
 st.latex(r'x_t=r_{m,t}-r_f,\qquad y_t=r_{p,t}-r_f,\qquad \beta=\frac{Cov(y,x)}{Var(x)}')
 st.write(f'Benchmark={BENCHMARK}; current beta={met["Beta vs Benchmark"]:.6f}.')
 st.header('18. CAPM alpha')
 st.latex(r'\alpha_{period}=\bar y-\beta\bar x')
 st.latex(r'\alpha_{ann}=(1+\alpha_{period})^N-1')
 st.write(f'Current annualised alpha={met["CAPM Alpha (Annualised)"]:.6%}.')
 st.header('19. Rolling beta and rolling alpha')
 st.latex(r'\beta_t^{(W)}=\frac{Cov(y,x)_{t-W+1:t}}{Var(x)_{t-W+1:t}}')
 st.latex(r'\alpha_{t,period}^{(W)}=\bar y^{(W)}_t-\beta_t^{(W)}\bar x^{(W)}_t,\qquad \alpha_{t,ann}^{(W)}=(1+\alpha_{t,period}^{(W)})^N-1')
 st.write(f'Rolling CAPM window={capm_window} observations.')
 st.header('20. Conditional beta in benchmark stress')
 st.latex(r'DD^m_t=\frac{P^m_t}{\max_{s\le t}P^m_s}-1')
 st.latex(r'\mathcal S=\{t:DD^m_t\le-10\%\},\qquad \beta_{cond}=\frac{Cov(r_p,r_m\mid t\in\mathcal S)}{Var(r_m\mid t\in\mathcal S)}')
 st.write(f'Conditional beta='+('N/A' if not np.isfinite(cb) else f'{cb:.6f}')+f'; stress observations={ncb}.')
 st.header('21. Currency translation')
 st.latex(r'1+r^{base}_{i,t}=(1+r^{local}_{i,t})(1+r^{FX}_{local/base,t})')
 st.latex(r'P^{base}_{i,t}=P^{local}_{i,t}X_{local/base,t},\qquad D^{base}_{i,t}=D^{local}_{i,t}X_{local/base,t}')
 st.write('For each user-selected asset, raw Yahoo Close and explicit cash distributions are translated from the user-selected source currency into the configured portfolio/base currency before portfolio construction. Assets not selected for currency adjustment are left unchanged.')
 st.write(f'Base currency: {BASE_CCY}; currency adjustment enabled: {FX_ADJUST}; adjusted assets: {FX_ADJUSTED_ASSETS}. Benchmark currency adjustment enabled: {BENCHMARK_FX_ADJUST if USE_BENCHMARK else False}.')
 if FX_ADJUST and FX_ADJUSTED_ASSETS and not fx_translation_report.empty: st.dataframe(fx_translation_report,hide_index=True,use_container_width=True)
 if USE_BENCHMARK and BENCHMARK_FX_ADJUST and not benchmark_fx_report.empty: st.dataframe(benchmark_fx_report,hide_index=True,use_container_width=True)
 st.header('22. Return attribution by instrument')
 st.latex(r'R_i^{tot}=R_i^{cap}+R_i^{inc},\qquad 1=\frac{R_i^{cap}}{R_i^{tot}}+\frac{R_i^{inc}}{R_i^{tot}}')
 st.dataframe(at,hide_index=True,use_container_width=True)
 st.header('22. Macro risk and conditional performance')
 st.latex(r'\Delta F_t=F_t/F_{t-1}-1,\qquad z_t=\frac{\Delta F_t-\overline{\Delta F}}{s(\Delta F)}')
 st.latex(r'\mathcal S_{Oil}=\{t:z^{Oil}_t\ge2\},\quad \mathcal S_{VIX}=\{t:z^{VIX}_t\ge2\},\quad \mathcal S_{MOVE}=\{t:z^{MOVE}_t\ge1.5\}')
 st.latex(r'\mathcal S_{B}=\{t:DD^{B}_t\le-10\%\}')
 st.write(f'Here B is the configured benchmark: {bench_label} — {BENCHMARK}.')
 st.latex(r'R_{p|S}=\prod_{t\in\mathcal S}(1+r_{p,t})-1,\qquad \bar r_{p|S}=\frac{1}{|\mathcal S|}\sum_{t\in\mathcal S}r_{p,t}')
 st.latex(r'\sigma_{p|S}=s(r_p\mid t\in\mathcal S)\sqrt N')
 st.latex(r'\beta_{S}=\frac{Cov(r_p-r_f,r_m-r_f\mid t\in\mathcal S)}{Var(r_m-r_f\mid t\in\mathcal S)}')
 st.latex(r'\alpha_{S,period}=\overline{(r_p-r_f)}_{S}-\beta_S\overline{(r_m-r_f)}_{S},\qquad \alpha_{S,ann}=(1+\alpha_{S,period})^N-1')
 st.latex(r'HitRate_S=\frac{\#\{t\in\mathcal S:r_{p,t}>0\}}{|\mathcal S|}')
 st.write('σ thresholds use the sample mean and sample standard deviation of factor percentage changes inside the configured backtest window. The scenario output therefore describes realised historical conditional performance; it is not a hypothetical instantaneous price shock.')
 if not macro_factor_meta_df.empty: st.dataframe(macro_factor_meta_df,hide_index=True,use_container_width=True)
 if not scenario_df.empty: st.dataframe(display_scen,hide_index=True,use_container_width=True)
 st.header('23. Walk-forward CAPM and VaR validation')
 st.latex(r'\\hat\\beta_t=\\frac{Cov(r_p-r_f,r_m-r_f)_{t-52:t-1}}{Var(r_m-r_f)_{t-52:t-1}},\\qquad \\hat r_{p,t}=r_f+\\hat\\alpha_t+\\hat\\beta_t(r_{m,t}-r_f)')
 st.latex(r'VaR^{hist}_{.95,t}=Q_{.05}(r_{p,t-52:t-1})')
 st.latex(r'VaR^{param}_{.95,t}=\\hat\\mu_t+z_{.05}\\hat\\sigma_t,\\qquad z_{.05}=-1.64485')
 st.latex(r'\\sigma_t^2=\\omega+\\alpha\\epsilon_{t-1}^2+\\beta\\sigma_{t-1}^2,\\qquad VaR^{GARCH}_{.95,t}=\\hat\\mu_t+z_{.05}\\hat\\sigma_t')
 st.write('Every estimate is fit only on the preceding 252 daily observations and evaluated on the next held-out day. Historical VaR is empirical; Parametric VaR assumes normal daily returns; GARCH uses a GARCH(1,1) conditional variance with normal innovations. The displayed breach rate is compared with the nominal 5% rate.')
 st.header('24. Long/short weights and leverage')
 st.latex(r'\sum_i w_i=1,\qquad G=\sum_i|w_i|,\qquad w_i<0\;\Rightarrow\;\text{short position}')
 st.latex(r'r^{(L)}_{p,t}=Lr_{p,t}-(L-1)c_w,\qquad c_w=(1+c_a)^{1/52}-1')
 st.write('Configured weights are normalised to net 100%; negative weights represent short positions and gross exposure may exceed 100%. Additional leverage L scales the configured portfolio periodic return. Financing cost is charged on additional borrowed capital L−1 using the effective daily equivalent of the annual financing rate. All headline portfolio return/risk metrics use the resulting net-of-financing leveraged portfolio path.')
 st.header('25. Complete configured metric output')
 st.dataframe(metric_table(met),hide_index=True,use_container_width=True)

@st.dialog('Full Data Audit',width='large')
def show_audit_report():
 st.title('Full Data Audit')
 st.caption(f'Configured run: {prices.index[0]:%Y-%m-%d} to {prices.index[-1]:%Y-%m-%d} | {frequency} | {len(prices)} observations | reporting currency {PORTFOLIO_CCY}')
 checks=[]
 def add(area,check,status,evidence): checks.append({'Area':area,'Check':check,'Status':status,'Evidence':evidence})
 add('Structure','Duplicate dates','PASS' if not prices.index.duplicated().any() else 'FAIL',f'{int(prices.index.duplicated().sum())} duplicate date(s)')
 miss=prices.isna().sum(); add('Structure','Missing prices','PASS' if int(miss.sum())==0 else 'FAIL',f'{int(miss.sum())} missing configured price observations')
 dmiss=divs.isna().sum(); add('Structure','Missing distribution fields','PASS' if int(dmiss.sum())==0 else 'WARNING',f'{int(dmiss.sum())} missing distribution observations')
 add('Structure','Common sample size','PASS' if len(prices)>=12 else 'WARNING',f'{len(prices)} aligned daily observations across {len(ASSETS)} assets')
 if 'interpolation_report' in globals() and not interpolation_report.empty:
  total_interp=int(interpolation_report['Interpolated Values'].sum())
  add('Interpolation','Interpolated levels','PASS' if total_interp==0 else 'WARNING',f'{total_interp} total level observation(s) interpolated across portfolio assets and benchmark. Interpolation is performed on levels between genuine endpoints; it does not change the full-series net/terminal return between those endpoints, although daily path-dependent statistics can be affected.')
 coverage=[]
 for a0 in ASSETS:
  raw=full_p[a0].dropna() if a0 in full_p else pd.Series(dtype=float)
  coverage.append({'Instrument':instrument_names.get(a0,a0),'Ticker':a0,'Raw observations':len(raw),'Raw start':raw.index.min() if len(raw) else pd.NaT,'Raw end':raw.index.max() if len(raw) else pd.NaT,'Configured observations':int(prices[a0].notna().sum())})
  if len(raw):
   lost=max(0,len(raw.loc[(raw.index>=prices.index[0])&(raw.index<=prices.index[-1])])-int(prices[a0].notna().sum()))
   add('Coverage',a0+' alignment loss','PASS' if lost==0 else 'WARNING',f'{lost} observations lost inside configured window')
 coverage_df=pd.DataFrame(coverage)
 rr=(prices-prices.shift(1)+divs)/prices.shift(1)
 for a0 in ASSETS:
  mx=float(rr[a0].abs().max()) if rr[a0].notna().any() else np.nan; lim=.35 if daily_mode else 1.0
  add('Returns',a0+' extreme-return scan','PASS' if np.isfinite(mx) and mx<=lim else 'FAIL',f'max |period return|={mx:.2%}; threshold={lim:.0%}')
  negdiv=int((divs[a0]<0).sum()); add('Distributions',a0+' negative distributions','PASS' if negdiv==0 else 'WARNING',f'{negdiv} negative cash distribution(s)')
 wsum=sum(weights.values()); add('Accounting','Portfolio weights sum','PASS' if abs(wsum-1)<1e-10 else 'FAIL',f'{wsum:.12f}')
 init_err=abs(float(vals.PORTFOLIO.iloc[0])-INITIAL); add('Accounting','Initial portfolio identity','PASS' if init_err<1e-6 else 'FAIL',f'V0={vals.PORTFOLIO.iloc[0]:,.6f}; nominal={INITIAL:,.6f}; error={init_err:.6g}')
 add('Accounting','Finite portfolio values','PASS' if np.isfinite(vals.PORTFOLIO).all() else 'FAIL',f'{int((~np.isfinite(vals.PORTFOLIO)).sum())} non-finite values')
 aligned_capm=pd.concat([vals.PORTFOLIO.pct_change(fill_method=None),bp.pct_change(fill_method=None)],axis=1).dropna()
 add('Regression','CAPM sample','PASS' if len(aligned_capm)>=24 else 'WARNING',f'{len(aligned_capm)} aligned portfolio/benchmark observations')
 add('Regression','Benchmark variance','PASS' if len(aligned_capm)>1 and aligned_capm.iloc[:,1].var()>0 else 'FAIL',f'variance={aligned_capm.iloc[:,1].var() if len(aligned_capm)>1 else np.nan:.8g}')
 if FX_ADJUST:
  add('FX translation','Assets selected','PASS' if len(FX_ADJUSTED_ASSETS)>0 else 'WARNING',f'{len(FX_ADJUSTED_ASSETS)} selected')
  if not fx_translation_report.empty:
   for _,r0 in fx_translation_report.iterrows(): add('FX translation',str(r0['Instrument'])+' currency conversion','PASS',f"{r0['Source Currency']} → {r0['Base Currency']}; {int(r0['Observations'])} aligned observations; source={r0['FX Series Used']}")
 if USE_BENCHMARK and BENCHMARK_FX_ADJUST:
  if not benchmark_fx_report.empty:
   for _,r0 in benchmark_fx_report.iterrows(): add('Benchmark FX translation',str(r0['Instrument'])+' currency conversion','PASS',f"{r0['Source Currency']} → {r0['Base Currency']}; {int(r0['Observations'])} aligned observations; source={r0['FX Series Used']}")
  else: add('Benchmark FX translation','Benchmark conversion','FAIL','Benchmark currency adjustment enabled but no translation audit row was produced')
 if not scenario_df.empty:
  for _,r0 in scenario_df.iterrows():
   n=int(r0.get('Historical Events',0)); add('Macro scenarios',str(r0.get('Scenario','Scenario'))+' event count','PASS' if n>=10 else ('WARNING' if n>=3 else 'FAIL'),f'{n} independent historical event(s)')
 if 'wf' in globals():
  add('Walk-forward','252-day OOS sample','PASS' if len(wf)>=252 else ('WARNING' if len(wf)>0 else 'FAIL'),f'{len(wf)} held-out daily validation observations')
  if not wf.empty:
   nv=int(wf['VaR 95%'].notna().sum()); add('Walk-forward','VaR estimates available','PASS' if nv==len(wf) else 'WARNING',f'{nv}/{len(wf)} one-step VaR estimates available using {wf_method}')
   nb=int(wf['CAPM Forecast'].notna().sum()); add('Walk-forward','CAPM estimates available','PASS' if nb==len(wf) else 'WARNING',f'{nb}/{len(wf)} one-step CAPM forecasts available')
 if 'missing_by_asset' in globals():
  miss_txt=', '.join(f'{k}: {v}' for k,v in missing_by_asset.items() if v) or 'none'
  add('Alignment','Daily alignment','PASS',f'Daily adjusted-price observations are aligned on the portfolio master calendar. Missing internal asset/benchmark levels are time-interpolated between genuine observations and retained in the audit. Portfolio observations retained={len(prices)}; benchmark interpolations={benchmark_missing_weeks}.')
 for a0 in ASSETS:
  if a0 in split_events:
   nsplit=int((split_events[a0]!=0).sum())
   add('Corporate actions',a0+' split handling','PASS',f'{nsplit} split event(s) identified; Yahoo Close is already split-adjusted, so split ratios are not applied a second time')
 add('Corporate actions','Adjusted-return treatment','PASS','Daily Yahoo Adjusted Close is used as the return series. Cash distributions and split effects are embedded and are not added again downstream.')
 if 'STXGVI.JO' in ASSETS: add('Source validation','STXGVI cents/ZAR normalisation','PASS','normalisation and distribution sanity checks completed before portfolio construction')
 if 'GOVI' in ASSETS: add('Source validation','GOVI repository history','PASS' if len(govi)>=100 else 'FAIL',f'{len(govi)} repository observations; last={govi.index.max():%Y-%m-%d}')
 audit=pd.DataFrame(checks); rank={'PASS':0,'WARNING':1,'FAIL':2}; worst=max((rank[x] for x in audit.Status),default=0); overall=['PASS','WARNING','FAIL'][worst]
 nfail=int((audit.Status=='FAIL').sum()); nwarn=int((audit.Status=='WARNING').sum()); npass=int((audit.Status=='PASS').sum())
 if overall=='PASS': st.success(f'AUDIT PASS — {npass} checks passed; no warnings or failures.')
 elif overall=='WARNING': st.warning(f'AUDIT WARNING — {npass} pass | {nwarn} warning | {nfail} fail')
 else: st.error(f'AUDIT FAIL — {npass} pass | {nwarn} warning | {nfail} fail')
 st.subheader('Flags requiring attention'); flagged=audit[audit.Status!='PASS']; st.dataframe(flagged if not flagged.empty else pd.DataFrame([{'Status':'PASS','Evidence':'No audit flags in configured run.'}]),hide_index=True,use_container_width=True)
 st.subheader('Complete audit checks'); st.dataframe(audit,hide_index=True,use_container_width=True)
 st.subheader('Instrument coverage'); st.dataframe(coverage_df,hide_index=True,use_container_width=True)
 if 'interpolation_report' in globals() and not interpolation_report.empty:
  st.subheader('Interpolation audit')
  st.dataframe(interpolation_report,hide_index=True,use_container_width=True)
  st.caption('Interpolation is applied to missing price/level observations between genuine surrounding observations. It does not alter the full-series net/terminal return between genuine endpoints; it may affect daily path-dependent statistics such as volatility, correlation, beta and VaR.')
 st.subheader('Configured weights'); st.dataframe(pd.DataFrame({'Instrument':[instrument_names.get(x,x) for x in ASSETS],'Ticker':ASSETS,'Weight':[weights[x] for x in ASSETS]}),hide_index=True,use_container_width=True)
 if not fx_translation_report.empty: st.subheader('FX translation audit'); st.dataframe(fx_translation_report,hide_index=True,use_container_width=True)
 if USE_BENCHMARK and BENCHMARK_FX_ADJUST and not benchmark_fx_report.empty: st.subheader('Benchmark FX translation audit'); st.dataframe(benchmark_fx_report,hide_index=True,use_container_width=True)
 if not scenario_df.empty: st.subheader('Scenario sample audit'); st.dataframe(scenario_df,hide_index=True,use_container_width=True)
 st.subheader('Methodology note'); st.write('Audit checks are run on the configured output and its underlying aligned data. Daily Yahoo Adjusted Close is used directly for asset and benchmark returns. Distributions are not added again downstream. No ticker-specific price rule is used. Missing internal aligned levels are time-interpolated between genuine observations and explicitly counted above. Distributions are embedded in adjusted prices and are not added separately. PASS indicates no issue detected by the stated check, WARNING identifies a limitation or small sample requiring attention, and FAIL identifies a breached validation rule. The audit is diagnostic rather than a guarantee of source correctness.')

if latex_slot.button('Show LaTeX',use_container_width=True): show_latex_report()
if audit_slot.button('Data Audit',use_container_width=True): show_audit_report()


st.divider()
st.caption('Not financial advice. For research, analytical, educational and informational purposes only. Historical, simulated and modelled outputs may be inaccurate and are not indicative of future results. Subject to revision. See Full Disclaimer below.')
with st.expander('Full Disclaimer', expanded=False):
    st.markdown('''
**Important Disclaimer**

This tool and all information, calculations, analytics, backtests, estimates, scenarios, charts, statistics and other outputs generated by it are provided solely for general informational, analytical, educational and research purposes. Nothing contained in or produced by this tool constitutes, or should be construed as, financial, investment, trading, legal, tax, accounting or other professional advice, nor as a recommendation, solicitation, offer or endorsement to buy, sell, hold, short, hedge or otherwise transact in any security, financial instrument, investment product, asset class or strategy.

Outputs are generated using historical and/or third-party data, user-selected assumptions and quantitative models. Although reasonable efforts may be made to maintain the integrity of calculations and underlying data, no representation or warranty, express or implied, is made as to the accuracy, completeness, reliability, timeliness, availability or fitness for any particular purpose of the data, methodology or outputs. Data may contain errors, omissions, revisions, survivorship effects, corporate-action issues, differing market calendars, stale observations or other limitations.

Backtested, simulated and hypothetical results have inherent limitations and do not represent actual trading unless expressly stated otherwise. Historical performance is not a guarantee or reliable indication of future results. Modelled relationships, correlations, betas, alphas, risk measures, scenario analyses, Value-at-Risk estimates and other statistical estimates may change materially over time and may not persist under future market conditions.

Results may not reflect all transaction costs, taxes, fees, bid-ask spreads, market impact, liquidity constraints, borrowing constraints, short-selling costs, stock-borrow availability, financing costs, margin requirements, collateral requirements, currency effects or other factors that would affect an actual investment portfolio, except where expressly incorporated into the selected configuration. Leverage and short positions can materially magnify both gains and losses and may result in losses exceeding the capital initially allocated to a position or strategy.

Any scenario, stress test or historical event analysis is an analytical representation based on the methodology and data described by the tool. It is not a forecast, prediction or representation of how a portfolio or financial instrument will necessarily perform during any future market event. Risk measures are estimates rather than guarantees of maximum loss.

Users are responsible for independently verifying all information and for assessing the suitability, appropriateness and risks of any investment, transaction or strategy having regard to their own objectives, financial circumstances, risk tolerance and legal or regulatory requirements. No investment or trading decision should be made solely in reliance on this tool or its outputs. Where appropriate, users should obtain advice from suitably qualified and authorised professional advisers.

The tool, its underlying methodologies, assumptions, data sources, calculations, functionality and outputs may be corrected, modified, updated, replaced or revised at any time without notice. Outputs should therefore be treated as provisional analytical information and may differ between runs or following data or methodology revisions.

To the fullest extent permitted by applicable law, the developers, owners, operators and contributors accept no liability for any direct, indirect, incidental, consequential or other loss, damage, cost or expense arising from or connected with access to, use of, inability to use, or reliance upon this tool, its data or any output generated by it.

Use of this tool does not create an adviser-client, fiduciary, agency or other professional relationship between the user and the developers, owners, operators or contributors.

**By using this tool, the user acknowledges the limitations described above and accepts responsibility for independently evaluating any information or output before relying upon it.**
''')
