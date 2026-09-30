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
START="2012-02-01"
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

def _normalise_stxgvi_close(close):
 s=close.astype(float).copy().dropna(); ratios=s/s.shift(1)
 breaks=ratios[(ratios>50)&(ratios<150)].index.tolist()+ratios[(ratios>.005)&(ratios<.02)].index.tolist()
 for dt in sorted(set(breaks)):
  i=s.index.get_loc(dt); ratio=s.iloc[i]/s.iloc[i-1]
  if ratio>50: s.iloc[i:]=s.iloc[i:]/100.0
  elif ratio<.02: s.iloc[i:]=s.iloc[i:]*100.0
 if float(s.tail(min(60,len(s))).median())>1000: s=s/100.0
 if not (20<float(s.iloc[-1])<200): raise RuntimeError(f'STXGVI normalised close implausible: {s.iloc[-1]:.2f} ZAR')
 return s

@st.cache_data(ttl=3600,show_spinner=False)
def load_ticker_components(tickers):
 prices={}; divs={}; splits={}
 for ticker in tickers:
  h=yf.Ticker(ticker).history(start=START,auto_adjust=False,actions=True)
  if h.empty: raise RuntimeError(f'Market-data source returned no data for ticker {ticker}')
  h=h.copy(); h.index=pd.to_datetime(h.index).tz_localize(None); h=h.sort_index()
  close=pd.to_numeric(h['Close'],errors='coerce').dropna()
  div=pd.to_numeric(h.get('Dividends',0.0),errors='coerce').fillna(0.0).reindex(close.index,fill_value=0.0)
  if ticker.upper()=='STXGVI.JO':
   close=_normalise_stxgvi_close(close)
   div=div.reindex(close.index,fill_value=0.0)/100.0
   check_date=pd.Timestamp('2023-04-25')
   if check_date in div.index and not np.isclose(float(div.loc[check_date]),1.9145,rtol=0,atol=.0001): raise RuntimeError(f'STXGVI distribution conversion failed: {div.loc[check_date]} ZAR')
   for dt,dv in div[div!=0].items():
    px=close.asof(dt)
    if np.isfinite(px) and (dv<=0 or dv/px>.20): raise RuntimeError(f'STXGVI distribution sanity check failed on {dt.date()}: dividend_ZAR={dv}, close_ZAR={px}')
  sp=pd.to_numeric(h.get('Stock Splits',0.0),errors='coerce').fillna(0.0).reindex(close.index,fill_value=0.0)
  if len(close)<2: raise RuntimeError(f'{ticker}: fewer than two valid Close observations')
  prices[ticker]=close.rename(ticker); divs[ticker]=div.rename(ticker); splits[ticker]=sp.rename(ticker)
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

def build_master(selected):
 yahoo=[x for x in selected if x!='GOVI']; yp,yd,ys=load_ticker_components(tuple(yahoo)) if yahoo else ({},{},{})
 if yahoo:
  mp=pd.DataFrame({x:v.resample('ME').last() for x,v in yp.items()}); md=pd.DataFrame({x:v.resample('ME').sum() for x,v in yd.items()})
 else:
  g0=load_govi_history(); mp=pd.DataFrame(index=g0.index); md=pd.DataFrame(index=g0.index)
 g=load_govi_history(); val={'last_govi':g.index.max(),'source':'repository GOVI'}
 if 'GOVI' in selected: mp['GOVI']=g.reindex(mp.index).ffill(); md['GOVI']=0.0
 return mp.loc[START:],md.reindex(mp.index,fill_value=0.0).loc[START:],g,val,ys

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

def portfolio_values(prices,divs,alloc,reinvest,rebalance=False,hedge_returns=None):
 assets=list(alloc); target=pd.Series(alloc,dtype=float)/sum(alloc.values()); units=pd.Series({a:alloc[a]/float(prices[a].iloc[0]) for a in assets}); cash=pd.Series(0.0,index=assets)
 v=pd.DataFrame(index=prices.index,columns=assets,dtype=float); v.iloc[0]=pd.Series(alloc)
 hedge_returns=hedge_returns if hedge_returns is not None else pd.DataFrame(0.0,index=prices.index,columns=assets)
 hedge_returns=hedge_returns.reindex(index=prices.index,columns=assets,fill_value=0.0).fillna(0.0)
 for i in range(1,len(prices)):
  dt=prices.index[i]; prev=prices.index[i-1]
  if rebalance and dt.year!=prev.year:
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
 d=pd.concat([r.rename('P'),market_r.rename('M')],axis=1).dropna(); x=d.M-rfp; y=d.P-rfp; beta=y.cov(x)/x.var() if x.var()>0 else np.nan; alpha=(1+y.mean()-beta*x.mean())**ppy-1 if np.isfinite(beta) else np.nan; var=r.quantile(.05)
 return {'Initial Value':p.iloc[0],'Ending Value':p.iloc[-1],'Total Return':p.iloc[-1]/p.iloc[0]-1,'CAGR':cagr,'Annualised Volatility':vol,'Sharpe Ratio':ex.mean()/ex.std()*np.sqrt(ppy) if ex.std()>0 else np.nan,'Downside Volatility':dvol,'Sortino Ratio':ex.mean()*ppy/dvol if dvol>0 else np.nan,'Beta vs ALSI':beta,'CAPM Alpha (Annualised)':alpha,'Maximum Drawdown':dd.min(),'Calmar Ratio':cagr/abs(dd.min()) if dd.min()<0 else np.nan,'Period VaR 95%':var,'Period CVaR 95%':r[r<=var].mean(),'Best Period':r.max(),'Worst Period':r.min(),'Positive Periods':(r>0).mean(),'Max DD Date':dd.idxmin()}

def metric_table(m):
 pct={'Total Return','CAGR','Annualised Volatility','Downside Volatility','CAPM Alpha (Annualised)','Maximum Drawdown','Period VaR 95%','Period CVaR 95%','Best Period','Worst Period','Positive Periods'}; rows=[]
 for k,v in m.items():
  x=pd.Timestamp(v).strftime('%Y-%m-%d') if k=='Max DD Date' else f'R{v:,.0f}' if k in ['Initial Value','Ending Value'] else f'{v:.2%}' if k in pct else f'{v:.3f}'; rows.append((k,x))
 return pd.DataFrame(rows,columns=['Metric','Value'])

def annual_returns(v):
 rows=[]
 for y in sorted(v.index.year.unique()):
  idx=v.index[v.index.year==y]; prior=v.index[v.index<idx[0]]; start=prior[-1] if len(prior) else idx[0]; end=idx[-1]; rows.append((y,v.loc[end,'PORTFOLIO']/v.loc[start,'PORTFOLIO']-1,'Partial Year' if y in [v.index[0].year,v.index[-1].year] else 'Full Year'))
 return pd.DataFrame(rows,columns=['Year','Annual Total Return','Period'])

def annual_asset_returns(prices,divs,assets):
 rows=[]
 for y in sorted(prices.index.year.unique()):
  idx=prices.index[prices.index.year==y]; prior=prices.index[prices.index<idx[0]]; start=prior[-1] if len(prior) else idx[0]; end=idx[-1]; row={'Year':y,'Period':'Partial Year' if y in [prices.index[0].year,prices.index[-1].year] else 'Full Year'}
  for a in assets: row[a]=(prices.loc[end,a]-prices.loc[start,a]+divs.loc[(divs.index>start)&(divs.index<=end),a].sum())/prices.loc[start,a]
  rows.append(row)
 return pd.DataFrame(rows)

def rolling_capm(v,market_r,rf,ppy):
 window=36 if ppy==12 else 252; rp=v.PORTFOLIO.pct_change(fill_method=None); d=pd.concat([rp.rename('P'),market_r.rename('M')],axis=1).dropna(); rfp=(1+rf)**(1/ppy)-1; x=d.M-rfp; y=d.P-rfp; b=y.rolling(window).cov(x)/x.rolling(window).var(); a=y.rolling(window).mean()-b*x.rolling(window).mean(); return b,(1+a)**ppy-1,window

def conditional_beta(v,market_price,threshold=-.10):
 rp=v.PORTFOLIO.pct_change(fill_method=None); rm=market_price.pct_change(fill_method=None); dd=market_price/market_price.cummax()-1; d=pd.concat([rp.rename('P'),rm.rename('M'),dd.rename('DD')],axis=1).dropna(); d=d[d.DD<=threshold]
 return d.P.cov(d.M)/d.M.var() if len(d)>=2 and d.M.var()>0 else np.nan,len(d)


@st.cache_data(ttl=3600,show_spinner=False)
def load_fx_pair(pair_symbol,daily_mode):
 h=yf.Ticker(pair_symbol).history(start=START,auto_adjust=False,actions=False)
 if h.empty: raise RuntimeError(f'FX source returned no data for {pair_symbol}')
 x=pd.to_numeric(h['Close'],errors='coerce').dropna(); x.index=pd.to_datetime(x.index).tz_localize(None); x=x.sort_index()
 if not daily_mode: x=x.resample('ME').last()
 return x.rename(pair_symbol)

def estimate_fx_hedges(prices,divs,hedged_assets,fx_pairs,daily_mode):
 hedge=pd.DataFrame(0.0,index=prices.index,columns=prices.columns); rows=[]
 asset_total=(prices-prices.shift(1)+divs)/prices.shift(1)
 for asset in hedged_assets:
  pair=fx_pairs[asset]; fx=load_fx_pair(pair,daily_mode).reindex(prices.index).ffill(); fr=fx.pct_change(fill_method=None)
  d=pd.concat([asset_total[asset].rename('asset'),fr.rename('fx')],axis=1).dropna()
  if len(d)<12: raise RuntimeError(f'{asset}: fewer than 12 aligned observations for FX beta estimation against {pair}')
  var=float(d.fx.var()); beta=float(d.asset.cov(d.fx)/var) if var>0 else np.nan
  if not np.isfinite(beta): raise RuntimeError(f'{asset}: FX beta could not be estimated against {pair}')
  alpha=float(d.asset.mean()-beta*d.fx.mean()); fitted=alpha+beta*d.fx; ssr=float(((d.asset-fitted)**2).sum()); sst=float(((d.asset-d.asset.mean())**2).sum()); r2=1-ssr/sst if sst>0 else np.nan
  hedge.loc[:,asset]=(-beta*fr).reindex(prices.index).fillna(0.0)
  rows.append({'Instrument':asset,'FX Pair':pair,'Observations':len(d),'Alpha (periodic)':alpha,'FX Beta / Hedge Ratio':beta,'R²':r2,'Sample Start':d.index.min(),'Sample End':d.index.max()})
 return hedge,pd.DataFrame(rows)

@st.cache_data(ttl=3600,show_spinner=False)
def load_macro_factors(daily_mode):
 symbols={'Oil':'CL=F','VIX':'^VIX','MOVE':'^MOVE'}
 yp,_,_=load_ticker_components(tuple(symbols.values()))
 out={}
 for name,sym in symbols.items():
  x=yp[sym].astype(float).sort_index()
  if not daily_mode: x=x.resample('ME').last()
  out[name]=x.rename(name)
 return pd.DataFrame(out)

def _conditional_capm(period_returns,market_returns,rf,ppy):
 d=pd.concat([period_returns.rename('P'),market_returns.rename('M')],axis=1).dropna(); n=len(d)
 if n<2 or d.M.var()<=0: return np.nan,np.nan,n
 rfp=(1+rf)**(1/ppy)-1; x=d.M-rfp; y=d.P-rfp; beta=y.cov(x)/x.var(); alpha=y.mean()-beta*x.mean()
 return beta,alpha,n

def jse_drawdown_events(vals,market_price,threshold=-.10):
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

def jse_scenario_stats(vals,market_price,rf,ppy):
 events=jse_drawdown_events(vals,market_price,-.10)
 if not events: return {'Scenario':'JSE −10% Drawdown','Historical Events':0}
 er=pd.DataFrame(events,columns=['Start','End','JSE Event Return','Portfolio Event Return'])
 # Conditional CAPM uses all underlying periodic observations contained inside the independent event windows.
 rp=vals.PORTFOLIO.pct_change(fill_method=None); rm=market_price.pct_change(fill_method=None); idx=pd.Index([])
 for st,en,_,_ in events: idx=idx.union(rp.index[(rp.index>st)&(rp.index<=en)])
 beta,alpha,n=_conditional_capm(rp.reindex(idx),rm.reindex(idx),rf,ppy)
 return {'Scenario':'JSE −10% Drawdown','Historical Events':len(er),'Avg Portfolio Event Return':er['Portfolio Event Return'].mean(),'Median Portfolio Event Return':er['Portfolio Event Return'].median(),'Avg JSE Event Return':er['JSE Event Return'].mean(),'Worst Portfolio Event':er['Portfolio Event Return'].min(),'Best Portfolio Event':er['Portfolio Event Return'].max(),'Positive Portfolio Events':(er['Portfolio Event Return']>0).mean(),'Conditional Beta':beta,'Conditional Alpha (periodic)':alpha,'CAPM Period Obs':n}

def one_period_shock_stats(vals,market_price,factor_change,threshold,rf,ppy,label):
 rp=vals.PORTFOLIO.pct_change(fill_method=None); rm=market_price.pct_change(fill_method=None)
 d=pd.concat([rp.rename('P'),rm.rename('M'),factor_change.rename('F')],axis=1).dropna(); e=d[d.F>=threshold]
 beta,alpha,n=_conditional_capm(e.P,e.M,rf,ppy)
 return {'Scenario':label,'Historical Events':len(e),'Avg Portfolio Event Return':e.P.mean() if len(e) else np.nan,'Median Portfolio Event Return':e.P.median() if len(e) else np.nan,'Avg JSE Event Return':e.M.mean() if len(e) else np.nan,'Avg Factor Shock':e.F.mean() if len(e) else np.nan,'Worst Portfolio Event':e.P.min() if len(e) else np.nan,'Best Portfolio Event':e.P.max() if len(e) else np.nan,'Positive Portfolio Events':(e.P>0).mean() if len(e) else np.nan,'Conditional Beta':beta,'Conditional Alpha (periodic)':alpha,'CAPM Period Obs':n}

title_col, report_col1, report_col2=st.columns([8,1,1])
with title_col: st.title('Portfolio Backtester')
latex_slot=report_col1.empty(); audit_slot=report_col2.empty(); st.subheader('Backtest Configuration'); a,b,c,d,e=st.columns([1.15,.75,1.15,1.15,1.15])
with a: timeline=st.selectbox('Timeline',['1W','1M','3M','6M','1Y','3Y','5Y','10Y','All','Custom'],index=8)
with b: PORTFOLIO_CCY=st.segmented_control('Currency',['ZAR','USD','EUR','GBP'],default='ZAR',selection_mode='single') or 'ZAR'
with c: INITIAL=float(st.number_input(f'Nominal amount ({PORTFOLIO_CCY})',min_value=1.0,value=float(DEFAULT_INITIAL),step=10000.0))
with d: RF=float(st.number_input('Risk-free rate (%)',min_value=0.0,max_value=100.0,value=7.0,step=.25))/100
with e: REINVEST=st.toggle('Reinvest dividends/distributions',value=False)
custom_start=custom_end=None
if timeline=='Custom':
 x,y=st.columns(2)
 with x: custom_start=st.date_input('Custom start',value=pd.Timestamp(START).date())
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
st.markdown('**FX Hedging**')
fxc1,fxc2=st.columns(2)
with fxc1: FX_HEDGED=st.toggle('FX hedged',value=False)
with fxc2:
 BASE_CCY=PORTFOLIO_CCY
 st.text_input('Portfolio / base currency',value=BASE_CCY,disabled=True)
HEDGED_ASSETS=[]; FX_PAIRS={}
if FX_HEDGED:
 HEDGED_ASSETS=st.multiselect('Assets to FX hedge',options=ASSETS,default=[],help='Only assets already selected in the portfolio can be hedged.')
 foreign_ccys=[x for x in ['USD','EUR','GBP','JPY','CHF','AUD','CAD','ZAR'] if x!=BASE_CCY]
 if HEDGED_ASSETS:
  st.caption('Select the FX pair used to estimate each asset’s in-sample currency beta. Pair direction is foreign currency per base-currency quote convention as supplied by the market-data series.')
  fxcols=st.columns(3)
  for i,a_fx in enumerate(HEDGED_ASSETS):
   opts=[f'{ccy}{BASE_CCY}=X' for ccy in foreign_ccys]
   default_i=opts.index(f'USD{BASE_CCY}=X') if f'USD{BASE_CCY}=X' in opts else 0
   with fxcols[i%3]: FX_PAIRS[a_fx]=st.selectbox(f'{a_fx} FX pair',opts,index=default_i,key=f'fxpair_{a_fx}_{BASE_CCY}')
st.markdown('**Weights**'); cols=st.columns(3); raww={}; default_sum=sum(DEFAULT_WEIGHTS.get(x,0.0) for x in ASSETS)
for i,a0 in enumerate(ASSETS):
 default=(DEFAULT_WEIGHTS.get(a0,0.0)/default_sum*100) if default_sum>0 else 100/len(ASSETS)
 with cols[i%3]: raww[a0]=st.number_input(f'{a0} (%)',0.0,100.0,float(default),.25,key=f'w_{a0}')/100
if sum(raww.values())<=0: st.error('Weights must be positive.'); st.stop()
weights={a0:w/sum(raww.values()) for a0,w in raww.items()}; ALLOC={a0:INITIAL*w for a0,w in weights.items()}
custom_days=(pd.Timestamp(custom_end)-pd.Timestamp(custom_start)).days if timeline=='Custom' and custom_start and custom_end else None; daily_mode=timeline in SHORT_WINDOWS or (timeline=='Custom' and custom_days is not None and custom_days<=366); ppy=252 if daily_mode else 12
try:
 with st.spinner('Updating, configuring and validating market data…'):
  if daily_mode: full_p,full_d,govi,bond_validation,split_events=build_daily(ASSETS)
  else: full_p,full_d,govi,bond_validation,split_events=build_master(ASSETS)
  common=full_p[ASSETS].dropna().index; start,end,requested=resolve_dates(common,timeline,custom_start,custom_end,daily_mode); prices=full_p.loc[(full_p.index>=start)&(full_p.index<=end),ASSETS].dropna(); divs=full_d.reindex(prices.index,fill_value=0.0)[ASSETS]
  if len(prices)<2: raise RuntimeError('Selected timeline has fewer than two common observations')
  asset_r=(prices-prices.shift(1)+divs)/prices.shift(1); bad=asset_r.abs().max(); bad=bad[bad>(.35 if daily_mode else 1.0)]
  if len(bad): raise RuntimeError('Implausible asset return(s): '+', '.join(f'{k}={v:.1%}' for k,v in bad.items()))
  fx_hedge_returns=pd.DataFrame(0.0,index=prices.index,columns=ASSETS); fx_hedge_report=pd.DataFrame()
  if FX_HEDGED and HEDGED_ASSETS:
   fx_hedge_returns,fx_hedge_report=estimate_fx_hedges(prices,divs,HEDGED_ASSETS,FX_PAIRS,daily_mode)
  bh=portfolio_values(prices,divs,ALLOC,REINVEST,False,fx_hedge_returns); rb=portfolio_values(prices,divs,ALLOC,REINVEST,True,fx_hedge_returns)
except Exception as e: st.error(f'Data update/validation failed: {e}'); st.exception(e); st.stop()
data_flags=[]
if start>requested: data_flags.append(f'Requested start {requested:%Y-%m-%d} unavailable for the selected common asset set; backtest starts at {start:%Y-%m-%d}.')
frequency='daily' if daily_mode else 'month-end'; st.caption(f'Configured window {prices.index[0]:%d %b %Y} to {prices.index[-1]:%d %b %Y} | {frequency} observations | Nominal {INITIAL:,.0f} | RF {RF:.2%} | Dividends '+('reinvested' if REINVEST else 'retained as cash')+(' | FX beta hedge active' if FX_HEDGED and HEDGED_ASSETS else ' | FX unhedged'))
if FX_HEDGED and HEDGED_ASSETS and not fx_hedge_report.empty:
 st.subheader('FX Beta Hedge — In-Sample Estimates'); fxshow=fx_hedge_report.copy(); fxshow['Alpha (periodic)']=fxshow['Alpha (periodic)'].map(lambda x:f'{x:.4%}'); fxshow['FX Beta / Hedge Ratio']=fxshow['FX Beta / Hedge Ratio'].map(lambda x:f'{x:.4f}'); fxshow['R²']=fxshow['R²'].map(lambda x:f'{x:.4f}'); st.dataframe(fxshow,hide_index=True,use_container_width=True)
if data_flags: st.warning('DATA FLAGS — '+' | '.join(data_flags))
mode=st.radio('Backtest mode',['Buy & Hold','Annual Rebalanced'],horizontal=True,index=0); vals=bh if mode=='Buy & Hold' else rb
bench_p,bench_d,_=load_ticker_components((BENCHMARK_TICKER,)); bp=bench_p[BENCHMARK_TICKER].reindex(prices.index).ffill(); bd=bench_d[BENCHMARK_TICKER].reindex(prices.index,fill_value=0.0); market_r=(bp-bp.shift(1)+bd)/bp.shift(1); met=stats(vals,market_r,RF,ppy)
c1,c2,c3,c4=st.columns(4); c1.metric(f'{mode} Value',f"{met['Ending Value']:,.0f}"); c2.metric(f'{mode} CAGR',f"{met['CAGR']:.2%}"); c3.metric(f'Sharpe ({RF:.2%} RF)',f"{met['Sharpe Ratio']:.3f}"); c4.metric('Max Drawdown',f"{met['Maximum Drawdown']:.2%}")
st.subheader(f'{mode} Analytics'); st.dataframe(metric_table(met),hide_index=True,use_container_width=True)
p=vals.PORTFOLIO; r=p.pct_change(fill_method=None).dropna(); growth=p/p.iloc[0]*100; dd=(p/p.cummax()-1)*100; roll_n=252 if daily_mode else 12; sharpe_n=756 if daily_mode else 36; roll_ret=((1+r).rolling(roll_n).apply(np.prod,raw=True)-1)*100; roll_vol=r.rolling(roll_n).std()*np.sqrt(ppy)*100; ex=r-((1+RF)**(1/ppy)-1); roll_sr=ex.rolling(sharpe_n).mean()/ex.rolling(sharpe_n).std()*np.sqrt(ppy)
line_chart({mode:p},f'{mode} — Portfolio Value','Value'); line_chart({mode:growth},f'{mode} — Growth of 100','Value'); line_chart({'Drawdown':dd},f'{mode} — Portfolio Drawdown','%'); line_chart({'Rolling 1Y Total Return':roll_ret},f'{mode} — Rolling 1-Year Total Return','%'); line_chart({'Rolling 1Y Volatility':roll_vol},f'{mode} — Rolling 1-Year Annualised Volatility','%'); line_chart({'Rolling 3Y Sharpe':roll_sr},f'{mode} — Rolling 3-Year Sharpe Ratio','Sharpe'); line_chart({c0:vals[c0] for c0 in ASSETS},f'{mode} — Portfolio Sleeve Values','Value')
st.subheader(f'{mode} Annual Total Returns'); ar=annual_returns(vals); ar['Annual Total Return']=ar['Annual Total Return'].map(lambda x:f'{x:.2%}'); st.dataframe(ar,hide_index=True,use_container_width=True)
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
weights_end=vals[ASSETS].div(vals.PORTFOLIO,axis=0); wt=pd.DataFrame({'Ticker':ASSETS,'Initial Weight':[weights[a0] for a0 in ASSETS],'Ending Weight':weights_end.iloc[-1].values}); wt['Initial Weight']=wt['Initial Weight'].map(lambda x:f'{x:.2%}'); wt['Ending Weight']=wt['Ending Weight'].map(lambda x:f'{x:.2%}'); st.subheader(f'{mode} Portfolio Weights'); st.dataframe(wt,hide_index=True,use_container_width=True)
st.divider(); st.subheader('Asset Correlation'); corr=asset_r[ASSETS].dropna().corr(); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()) if len(corr)>1 else np.nan; st.metric('Net Inter-Asset Correlation','N/A' if not np.isfinite(net_corr) else f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title='Pearson Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)
st.divider(); st.subheader(f'{mode} — Beta & Alpha Evolution vs {BENCHMARK_TICKER}'); roll_beta,roll_alpha,capm_window=rolling_capm(vals,market_r,RF,ppy); line_chart({f'{capm_window}-period Rolling Beta':roll_beta},f'{mode} — Rolling Beta vs {BENCHMARK_TICKER}','Beta'); line_chart({f'{capm_window}-period Rolling Alpha':roll_alpha*100},f'{mode} — Rolling Annualised CAPM Alpha','Alpha (%)'); cb,ncb=conditional_beta(vals,bp)

st.divider(); st.subheader('Macro Risk & Historical Scenario Analysis')
st.caption('Historical event analysis: portfolio performance is measured over the same realised market interval as each stress event. Results are event returns, not annualised hypothetical forecasts.')
sc1,sc2,sc3,sc4=st.columns(4)
with sc1: use_jse=st.toggle('JSE −10% Drawdown',value=True,key='macro_jse')
with sc2: use_oil=st.toggle('Oil +2σ Shock',value=False,key='macro_oil')
with sc3: use_vix=st.toggle('VIX +2σ Shock',value=False,key='macro_vix')
with sc4: use_move=st.toggle('MOVE +1.5σ Shock',value=False,key='macro_move')
scenario_rows=[]; macro_factor_meta=[]
if use_jse:
 scenario_rows.append(jse_scenario_stats(vals,bp,RF,ppy))
 macro_factor_meta.append({'Scenario':'JSE −10% Drawdown','Factor':BENCHMARK_TICKER,'Event':'previous peak → first crossing of −10% drawdown','Threshold':'≤ −10%'})
if use_oil or use_vix or use_move:
 try:
  mf=load_macro_factors(daily_mode).reindex(prices.index).ffill()
  for name,use,zcut,label in [('Oil',use_oil,2.0,'Oil +2σ Shock'),('VIX',use_vix,2.0,'VIX +2σ Shock'),('MOVE',use_move,1.5,'MOVE +1.5σ Shock')]:
   if not use: continue
   chg=mf[name].pct_change(fill_method=None); mu=chg.mean(); sig=chg.std(); threshold=mu+zcut*sig
   scenario_rows.append(one_period_shock_stats(vals,bp,chg,threshold,RF,ppy,label))
   macro_factor_meta.append({'Scenario':label,'Factor':name,'Event':'single configured observation interval','Transformation':'percentage change','Mean':mu,'Std Dev':sig,'Threshold':threshold})
 except Exception as e:
  st.warning(f'Macro factor data unavailable for selected scenario(s): {e}')
scenario_df=pd.DataFrame(scenario_rows); macro_factor_meta_df=pd.DataFrame(macro_factor_meta)
if not scenario_df.empty:
 display_scen=scenario_df.copy()
 for c0 in ['Avg Portfolio Event Return','Median Portfolio Event Return','Avg JSE Event Return','Avg Factor Shock','Worst Portfolio Event','Best Portfolio Event','Positive Portfolio Events','Conditional Alpha (periodic)']:
  if c0 in display_scen: display_scen[c0]=display_scen[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
 if 'Conditional Beta' in display_scen: display_scen['Conditional Beta']=display_scen['Conditional Beta'].map(lambda x:f'{x:.3f}' if pd.notna(x) else 'N/A')
 st.dataframe(display_scen,hide_index=True,use_container_width=True)
else: st.info('Select at least one macro risk scenario.')

@st.dialog('Complete Quantitative Workings',width='large')
def show_latex_report():
 st.title('Complete Quantitative Workings')
 st.caption(f'Configured run: {prices.index[0]:%Y-%m-%d} to {prices.index[-1]:%Y-%m-%d} | frequency={frequency} | N={ppy} | RF={RF:.4%} | observations={len(prices)} | mode={mode}')
 st.header('1. Data state, units and reconstructed returns')
 st.latex(r'P_{i,t}=\text{raw close price},\quad D_{i,t}=\text{cash distribution per unit},\quad S_{i,t}=\text{split event}')
 st.latex(r'r_{i,t}=\frac{P_{i,t}-P_{i,t-1}+D_{i,t}}{P_{i,t-1}}')
 st.latex(r'R^{cap}_i=\frac{P_{i,T}-P_{i,0}}{P_{i,0}},\quad R^{inc}_i=\frac{\sum_{t=1}^{T}D_{i,t}}{P_{i,0}},\quad R^{tot}_i=R^{cap}_i+R^{inc}_i')
 st.latex(r'\omega^{cap}_i=R^{cap}_i/R^{tot}_i,\quad \omega^{inc}_i=R^{inc}_i/R^{tot}_i')
 st.write('Adjusted Close is not used. Distributions are explicit. Split events are captured explicitly. STXGVI uses the validated cents/ZAR normalisation before reconstruction. No automatic FX overlay is applied.')
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
 st.latex(r'N=252\ \text{(daily)}\quad\text{or}\quad N=12\ \text{(month-end)}')
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
 st.write(f'Benchmark={BENCHMARK_TICKER}; current beta={met["Beta vs ALSI"]:.6f}.')
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
 st.header('21. FX beta hedging')
 st.latex(r'r_{i,t}=\alpha_i+\beta_{FX,i}r_{FX,t}+\epsilon_{i,t}')
 st.latex(r'\hat\beta_{FX,i}=\frac{\operatorname{Cov}(r_i,r_{FX})}{\operatorname{Var}(r_{FX})}')
 st.latex(r'h_{i,t}=-\hat\beta_{FX,i}r_{FX,t},\qquad P\&L^{hedge}_{i,t}=V_{i,t-1}^{market}h_{i,t}')
 st.latex(r'V^{hedged}_{i,t}=q_{i,t}P_{i,t}+C_{i,t}+P\&L^{hedge}_{i,t}')
 st.write('The FX beta is estimated in-sample over the currently configured common backtest window and is recalculated whenever the window, selected asset, frequency, or FX pair changes. The hedge is applied as a cash-settled return overlay to the prior-period market exposure; distributions remain explicit and are not replaced by Adjusted Close.')
 st.write(f'Base currency: {BASE_CCY}; FX hedge enabled: {FX_HEDGED}; hedged assets: {HEDGED_ASSETS}.')
 if FX_HEDGED and HEDGED_ASSETS and not fx_hedge_report.empty: st.dataframe(fx_hedge_report,hide_index=True,use_container_width=True)
 st.header('22. Return attribution by instrument')
 st.latex(r'R_i^{tot}=R_i^{cap}+R_i^{inc},\qquad 1=\frac{R_i^{cap}}{R_i^{tot}}+\frac{R_i^{inc}}{R_i^{tot}}')
 st.dataframe(at,hide_index=True,use_container_width=True)
 st.header('22. Macro risk and conditional performance')
 st.latex(r'\Delta F_t=F_t/F_{t-1}-1,\qquad z_t=\frac{\Delta F_t-\overline{\Delta F}}{s(\Delta F)}')
 st.latex(r'\mathcal S_{Oil}=\{t:z^{Oil}_t\ge2\},\quad \mathcal S_{VIX}=\{t:z^{VIX}_t\ge2\},\quad \mathcal S_{MOVE}=\{t:z^{MOVE}_t\ge1.5\}')
 st.latex(r'\mathcal S_{JSE}=\{t:DD^{JSE}_t\le-10\%\}')
 st.latex(r'R_{p|S}=\prod_{t\in\mathcal S}(1+r_{p,t})-1,\qquad \bar r_{p|S}=\frac{1}{|\mathcal S|}\sum_{t\in\mathcal S}r_{p,t}')
 st.latex(r'\sigma_{p|S}=s(r_p\mid t\in\mathcal S)\sqrt N')
 st.latex(r'\beta_{S}=\frac{Cov(r_p-r_f,r_m-r_f\mid t\in\mathcal S)}{Var(r_m-r_f\mid t\in\mathcal S)}')
 st.latex(r'\alpha_{S,period}=\overline{(r_p-r_f)}_{S}-\beta_S\overline{(r_m-r_f)}_{S},\qquad \alpha_{S,ann}=(1+\alpha_{S,period})^N-1')
 st.latex(r'HitRate_S=\frac{\#\{t\in\mathcal S:r_{p,t}>0\}}{|\mathcal S|}')
 st.write('σ thresholds use the sample mean and sample standard deviation of factor percentage changes inside the configured backtest window. The scenario output therefore describes realised historical conditional performance; it is not a hypothetical instantaneous price shock.')
 if not macro_factor_meta_df.empty: st.dataframe(macro_factor_meta_df,hide_index=True,use_container_width=True)
 if not scenario_df.empty: st.dataframe(display_scen,hide_index=True,use_container_width=True)
 st.header('23. Complete configured metric output')
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
 add('Structure','Common sample size','PASS' if len(prices)>=12 else 'WARNING',f'{len(prices)} aligned observations across {len(ASSETS)} assets')
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
 if FX_HEDGED:
  add('FX hedge','Hedged assets selected','PASS' if len(HEDGED_ASSETS)>0 else 'WARNING',f'{len(HEDGED_ASSETS)} selected')
  if not fx_hedge_report.empty:
   for _,r0 in fx_hedge_report.iterrows(): add('FX hedge',str(r0['Instrument'])+' regression sample','PASS' if int(r0['Observations'])>=24 else 'WARNING',f"{int(r0['Observations'])} obs; beta={r0['FX Beta / Hedge Ratio']:.4f}; R²={r0['R²']:.4f}")
 if not scenario_df.empty:
  for _,r0 in scenario_df.iterrows():
   n=int(r0.get('Historical Events',0)); add('Macro scenarios',str(r0.get('Scenario','Scenario'))+' event count','PASS' if n>=10 else ('WARNING' if n>=3 else 'FAIL'),f'{n} independent historical event(s)')
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
 st.subheader('Configured weights'); st.dataframe(pd.DataFrame({'Instrument':[instrument_names.get(x,x) for x in ASSETS],'Ticker':ASSETS,'Weight':[weights[x] for x in ASSETS]}),hide_index=True,use_container_width=True)
 if not fx_hedge_report.empty: st.subheader('FX hedge regression audit'); st.dataframe(fx_hedge_report,hide_index=True,use_container_width=True)
 if not scenario_df.empty: st.subheader('Scenario sample audit'); st.dataframe(scenario_df,hide_index=True,use_container_width=True)
 st.subheader('Methodology note'); st.write('Audit checks are run on the configured output and its underlying aligned data. Raw Close and explicit cash distributions are used; Adjusted Close is not used. PASS indicates no issue detected by the stated check, WARNING identifies a limitation or small sample requiring attention, and FAIL identifies a breached validation rule. The audit is diagnostic rather than a guarantee of source correctness.')

if latex_slot.button('Show LaTeX',use_container_width=True): show_latex_report()
if audit_slot.button('Data Audit',use_container_width=True): show_audit_report()
