import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Portfolio Backtester", layout="wide")
START="2012-02-01"; RF=0.07; INITIAL=1_202_000
ALLOC={"ALSI":400_000,"SP500":200_000,"SA_BONDS":200_000,"EUROPE":125_000,"NEWGOLD":45_000,"EXXARO":50_000,"BERKSHIRE":56_000,"MSCI_EM":65_000,"AGG":61_000}
TICKERS={"ALSI":"^J203.JO","SP500":"^GSPC","EUROPE":"^STOXX","NEWGOLD":"GLD.JO","EXXARO":"EXX.JO","BERKSHIRE":"BRK-B","MSCI_EM":"EEM","AGG":"AGG","USDZAR":"ZAR=X","EURZAR":"EURZAR=X"}

@st.cache_data(show_spinner=False)
def load_govi_history():
 d=pd.read_csv('govi_monthly.csv'); d['Date']=pd.to_datetime(d['Date'])+pd.offsets.MonthEnd(0); s=pd.Series(pd.to_numeric(d['SA_BONDS'],errors='coerce').values,index=d['Date'],name='GOVI').dropna().sort_index()
 if len(s)<100:return (_ for _ in ()).throw(RuntimeError('Validated GOVI history is incomplete'))
 return s

@st.cache_data(ttl=3600,show_spinner=False)
def load_stxgvi():
 # Yahoo historical Close is already split-normalised. Adj Close is NOT used.
 # We therefore add explicit cash distributions to Close, but do not apply the
 # Stock Splits action a second time. Split events are retained and sanity-checked.
 h=yf.Ticker('STXGVI.JO').history(start='2023-03-01',auto_adjust=False,actions=True)
 if h.empty:return (_ for _ in ()).throw(RuntimeError('Yahoo returned no STXGVI history'))
 h=h.copy(); h.index=pd.to_datetime(h.index).tz_localize(None); h=h.sort_index()
 close=pd.to_numeric(h['Close'],errors='coerce')
 div=pd.to_numeric(h.get('Dividends',0.0),errors='coerce').fillna(0.0)
 splits=pd.to_numeric(h.get('Stock Splits',0.0),errors='coerce').fillna(0.0)
 if close.dropna().empty:return (_ for _ in ()).throw(RuntimeError('STXGVI Close is empty'))
 # Guard against unit corruption: STXGVI trades in JSE cents and distributions
 # are reported in cents per security. A distribution cannot plausibly exceed 20% of price.
 for dt,dv in div[div!=0].items():
  p=close.asof(dt)
  if np.isfinite(p) and (dv<=0 or dv/p>.20):
   raise RuntimeError(f'STXGVI distribution unit check failed on {dt.date()}: dividend={dv}, close={p}')
 # Since Yahoo Close history is split-normalised, a split action must NOT create a
 # mechanical price discontinuity in the Close series. Reject suspicious data instead.
 for dt,sr in splits[splits!=0].items():
  loc=close.index.get_indexer([dt])[0]
  if loc>0 and np.isfinite(close.iloc[loc-1]) and np.isfinite(close.iloc[loc]):
   jump=close.iloc[loc]/close.iloc[loc-1]
   if abs(jump-1)>0.35:
    raise RuntimeError(f'STXGVI split-normalisation check failed on {dt.date()}: split={sr}, close ratio={jump:.3f}')
 # Non-reinvested holder wealth: one split-normalised unit plus accumulated cash distributions.
 # This matches the requested economic treatment: distributions retained as cash.
 wealth=(close+div.cumsum()).rename('STXGVI_WEALTH').dropna()
 w=wealth.resample('ME').last()
 if len(w)<24:return (_ for _ in ()).throw(RuntimeError('STXGVI live history unexpectedly short'))
 return w,div[div!=0],splits[splits!=0]

@st.cache_data(ttl=3600,show_spinner=False)
def load_yahoo():
 raw=yf.download(list(TICKERS.values()),start=START,auto_adjust=False,actions=False,progress=False,group_by='column')
 if raw.empty:return (_ for _ in ()).throw(RuntimeError('Yahoo Finance returned no data'))
 adj=raw['Adj Close'].rename(columns={v:k for k,v in TICKERS.items()})
 for c in ['NEWGOLD','EXXARO']:adj[c]=adj[c]/100.0
 adj['USDZAR']=adj['USDZAR'].ffill(); adj['EURZAR']=adj['EURZAR'].ffill(); z=pd.DataFrame(index=adj.index)
 for c in ['ALSI','NEWGOLD','EXXARO']:z[c]=adj[c]
 for c in ['SP500','BERKSHIRE','MSCI_EM','AGG']:z[c]=adj[c]*adj['USDZAR']
 z['EUROPE']=adj['EUROPE']*adj['EURZAR']; return z

def _period_return(s,start,end):
 x=s.loc[pd.Timestamp(start):pd.Timestamp(end)].dropna()
 if len(x)<2:return np.nan
 return float(x.iloc[-1]/x.iloc[0]-1)

def build_bond_series(govi,stx):
 # Validate STXGVI against independent published Satrix MDD fund returns.
 # Sep-2024 MDD: 1y fund 25.54%; Sep-2025 MDD: 1y fund 14.02%.
 # Month-end wealth observations should reproduce these closely; 1.0% absolute tolerance
 # allows month-end/trading-day boundary differences but not a bad reconstruction.
 checks=[]
 for label,start,end,target in [
  ('1Y to Sep-2024','2023-09-30','2024-09-30',0.2554),
  ('1Y to Sep-2025','2024-09-30','2025-09-30',0.1402),
 ]:
  actual=_period_return(stx,start,end)
  if not np.isfinite(actual):raise RuntimeError(f'STXGVI official-return validation missing data: {label}')
  err=actual-target; checks.append((label,actual,target,err))
  if abs(err)>.01:raise RuntimeError(f'STXGVI official-return validation failed ({label}): reconstructed={actual:.2%}, official={target:.2%}, error={err:.2%}')
 # Secondary overlap diagnostic against GOVI. Do not compare a non-reinvested cash-holder
 # series to a total-return benchmark as if they were identical; require directionally sane tracking.
 gr=govi.pct_change(fill_method=None); sr=stx.pct_change(fill_method=None); ov=pd.concat([gr.rename('GOVI'),sr.rename('STXGVI')],axis=1).loc['2023-04-01':].dropna()
 if len(ov)<24:raise RuntimeError('Insufficient GOVI/STXGVI overlap for validation')
 corr=float(ov.corr().iloc[0,1]); te=float((ov.STXGVI-ov.GOVI).std()*np.sqrt(12)); bias=float((ov.STXGVI-ov.GOVI).mean()*12)
 if corr<.75 or te>.10 or abs(bias)>.06:raise RuntimeError(f'STXGVI/GOVI overlap validation failed: r={corr:.3f}, TE={te:.2%}, bias={bias:.2%}')
 pre=govi.loc[:'2023-02-28']; anchor=float(pre.iloc[-1]); post=stx.loc['2023-03-01':]; post=anchor*(post/post.iloc[0]); bond=pd.concat([pre,post]); bond=bond[~bond.index.duplicated(keep='last')].sort_index(); bond.name='SA_BONDS'
 return bond,{'corr':corr,'te':te,'bias':bias,'n':len(ov),'start':ov.index.min(),'end':ov.index.max(),'official_checks':checks}

def build_master():
 z=load_yahoo(); g=load_govi_history(); stx,divs,splits=load_stxgvi(); bond,val=build_bond_series(g,stx); m=z.resample('ME').last(); m['SA_BONDS']=bond.reindex(m.index).ffill(); m=m[list(ALLOC)].loc['2012-02-01':].dropna(); return m,g,stx,divs,splits,val

def buy_hold(m):
 v=m.div(m.iloc[0]).mul(pd.Series(ALLOC),axis=1); v['PORTFOLIO']=v.sum(axis=1); return v

def annual_rebalanced(m):
 assets=list(ALLOC); target=pd.Series(ALLOC,dtype=float)/INITIAL; r=m[assets].pct_change(fill_method=None).fillna(0); v=pd.DataFrame(index=m.index,columns=assets,dtype=float); v.iloc[0]=pd.Series(ALLOC)
 for i in range(1,len(m)):
  prev=v.iloc[i-1].astype(float)
  if m.index[i].year!=m.index[i-1].year:prev=target*prev.sum()
  v.iloc[i]=prev*(1+r.iloc[i])
 v['PORTFOLIO']=v.sum(axis=1); return v

def capm_stats(v,m):
 rp=v.PORTFOLIO.pct_change(fill_method=None); rm=m.ALSI.pct_change(fill_method=None); d=pd.concat([rp.rename('P'),rm.rename('M')],axis=1).dropna(); mrf=(1+RF)**(1/12)-1; x=d.M-mrf; y=d.P-mrf; b=y.cov(x)/x.var(); a=y.mean()-b*x.mean(); return b,(1+a)**12-1

def metrics(v,m):
 p=v.PORTFOLIO.dropna(); r=p.pct_change(fill_method=None).dropna(); yrs=(p.index[-1]-p.index[0]).days/365.25; cagr=(p.iloc[-1]/p.iloc[0])**(1/yrs)-1; vol=r.std()*np.sqrt(12); ex=r-((1+RF)**(1/12)-1); down=ex[ex<0]; dvol=np.sqrt(np.mean(down**2))*np.sqrt(12); dd=p/p.cummax()-1; var=r.quantile(.05); beta,alpha=capm_stats(v,m)
 return {'Initial Value':p.iloc[0],'Ending Value':p.iloc[-1],'Total Return':p.iloc[-1]/p.iloc[0]-1,'CAGR':cagr,'Annualised Volatility':vol,'Sharpe Ratio (RF 7%)':ex.mean()/ex.std()*np.sqrt(12),'Downside Volatility':dvol,'Sortino Ratio':ex.mean()*12/dvol,'Beta vs ALSI':beta,'CAPM Alpha (Annualised)':alpha,'Maximum Drawdown':dd.min(),'Calmar Ratio':cagr/abs(dd.min()),'Monthly VaR 95%':var,'Monthly CVaR 95%':r[r<=var].mean(),'Best Month':r.max(),'Worst Month':r.min(),'Positive Months':(r>0).mean(),'Max DD Date':dd.idxmin()}

def annual_returns(v):
 r=v.PORTFOLIO.pct_change(fill_method=None).dropna(); a=(1+r).groupby(r.index.year).prod()-1; o=pd.DataFrame({'Year':a.index.astype(int),'Annual Return':a.values,'Period':'Full Year'}); o.loc[o.Year==v.index[0].year,'Period']='Partial Year'; o.loc[o.Year==v.index[-1].year,'Period']='Partial Year'; return o

def line_chart(series_map,title,ytitle):
 f=go.Figure()
 for name,s in series_map.items():f.add_trace(go.Scatter(x=s.index,y=s.values,mode='lines',name=name))
 f.update_layout(title=title,xaxis_title='Date',yaxis_title=ytitle,hovermode='x unified',legend_title_text=''); st.plotly_chart(f,use_container_width=True)

def metric_table(m):
 pct={'Total Return','CAGR','Annualised Volatility','Downside Volatility','CAPM Alpha (Annualised)','Maximum Drawdown','Monthly VaR 95%','Monthly CVaR 95%','Best Month','Worst Month','Positive Months'}; rows=[]
 for k,v in m.items():
  x=pd.Timestamp(v).strftime('%Y-%m') if k=='Max DD Date' else f'R{v:,.0f}' if k in ['Initial Value','Ending Value'] else f'{v:.2%}' if k in pct else f'{v:.3f}'; rows.append((k,x))
 return pd.DataFrame(rows,columns=['Metric','Value'])

def rolling_capm(v,m,window=36):
 rp=v.PORTFOLIO.pct_change(fill_method=None); rm=m.ALSI.pct_change(fill_method=None); d=pd.concat([rp.rename('P'),rm.rename('M')],axis=1).dropna(); mrf=(1+RF)**(1/12)-1; x=d.M-mrf; y=d.P-mrf; b=y.rolling(window).cov(x)/x.rolling(window).var(); a=y.rolling(window).mean()-b*x.rolling(window).mean(); return b,(1+a)**12-1

def conditional_beta(v,m):
 rp=v.PORTFOLIO.pct_change(fill_method=None); rm=m.ALSI.pct_change(fill_method=None); dd=m.ALSI/m.ALSI.cummax()-1; d=pd.concat([rp.rename('P'),rm.rename('M'),dd.rename('DD')],axis=1).dropna(); s=d[d.DD<=-.10]; mrf=(1+RF)**(1/12)-1
 if len(s)<2:return np.nan,len(s),s
 return (s.P-mrf).cov(s.M-mrf)/(s.M-mrf).var(),len(s),s

st.title('Portfolio Backtester'); st.caption('Live Yahoo Finance | SA bonds: SARB GOVI through Feb-2023, then Satrix GOVI ETF reconstructed from split-normalised Close + explicit cash distributions | Starting capital R1,202,000 | RF 7%')
try:
 with st.spinner('Updating and validating market data…'):master,govi,stxgvi,stx_divs,stx_splits,bond_validation=build_master(); bh=buy_hold(master); rb=annual_rebalanced(master)
except Exception as e:st.error(f'Data update/validation failed: {e}'); st.exception(e); st.stop()
bhm,rbm=metrics(bh,master),metrics(rb,master); st.success(f"Data loaded through {master.index[-1]:%d %b %Y} | SA-bond continuation validated vs official Satrix returns | GOVI overlap r={bond_validation['corr']:.3f}")
mode=st.radio('Backtest mode',['Buy & Hold','Annual Rebalanced'],horizontal=True,index=0); vals=bh if mode=='Buy & Hold' else rb; met=bhm if mode=='Buy & Hold' else rbm
c1,c2,c3,c4=st.columns(4); c1.metric(f'{mode} Value',f"R{met['Ending Value']:,.0f}"); c2.metric(f'{mode} CAGR',f"{met['CAGR']:.2%}"); c3.metric('Sharpe (7% RF)',f"{met['Sharpe Ratio (RF 7%)']:.3f}"); c4.metric('Max Drawdown',f"{met['Maximum Drawdown']:.2%}")
st.subheader(f'{mode} Analytics'); st.dataframe(metric_table(met),hide_index=True,use_container_width=True)
p=vals.PORTFOLIO; r=p.pct_change(fill_method=None).dropna(); growth=p/p.iloc[0]*100; dd=(p/p.cummax()-1)*100; roll_ret=((1+r).rolling(12).apply(np.prod,raw=True)-1)*100; roll_vol=r.rolling(12).std()*np.sqrt(12)*100; ex=r-((1+RF)**(1/12)-1); roll_sr=ex.rolling(36).mean()/ex.rolling(36).std()*np.sqrt(12)
line_chart({mode:p},f'{mode} — Portfolio Value','ZAR'); line_chart({mode:growth},f'{mode} — Growth of R100','Value'); line_chart({'Drawdown':dd},f'{mode} — Portfolio Drawdown','%'); bar=go.Figure(go.Bar(x=r.index,y=r.values*100)); bar.update_layout(title=f'{mode} — Monthly Portfolio Returns',yaxis_title='Return (%)'); st.plotly_chart(bar,use_container_width=True); line_chart({'12M Return':roll_ret},f'{mode} — Rolling 12-Month Return','%'); line_chart({'12M Volatility':roll_vol},f'{mode} — Rolling 12-Month Annualised Volatility','%'); line_chart({'36M Sharpe':roll_sr},f'{mode} — Rolling 36-Month Sharpe Ratio — RF 7%','Sharpe'); line_chart({c:vals[c] for c in ALLOC},f'{mode} — Portfolio Sleeve Values','ZAR')
st.subheader(f'{mode} Annual Returns'); ar=annual_returns(vals); ar['Annual Return']=ar['Annual Return'].map(lambda x:f'{x:.2%}'); st.dataframe(ar,hide_index=True,use_container_width=True)
weights=vals[list(ALLOC)].div(vals.PORTFOLIO,axis=0); wt=pd.DataFrame({'Asset':list(ALLOC),'Initial Weight':[ALLOC[a]/INITIAL for a in ALLOC],'Ending Weight':weights.iloc[-1].values}); wt['Initial Weight']=wt['Initial Weight'].map(lambda x:f'{x:.2%}'); wt['Ending Weight']=wt['Ending Weight'].map(lambda x:f'{x:.2%}'); st.subheader(f'{mode} Portfolio Weights'); st.dataframe(wt,hide_index=True,use_container_width=True)
st.divider(); st.subheader('Buy & Hold vs Annual Rebalancing'); line_chart({'Buy & Hold':bh.PORTFOLIO,'Annual Rebalanced':rb.PORTFOLIO},'Portfolio Value Comparison','ZAR'); st.dataframe(pd.DataFrame({'Buy & Hold':metric_table(bhm).set_index('Metric').Value,'Annual Rebalanced':metric_table(rbm).set_index('Metric').Value}),use_container_width=True)
with st.expander('Methodology & data'):
 st.write('Buy & Hold permits weights to drift. Annual Rebalanced resets to original target weights at the start of each calendar year. Foreign sleeves are translated into ZAR. SA equity uses FTSE/JSE All Share (^J203.JO).')
 st.write('SA bonds use SARB GOVI through February 2023. From March 2023 the sleeve uses Satrix GOVI ETF (STXGVI). Yahoo historical Close is already split-normalised, so split actions are NOT applied a second time. Yahoo Adjusted Close is not used. Explicit cash distributions are accumulated as cash and are not reinvested. Split events are retained and sanity-checked for discontinuities.')
 for label,actual,target,err in bond_validation['official_checks']:st.write(f'{label}: reconstructed {actual:.2%}; official Satrix MDD {target:.2%}; error {err:.2%}.')
 st.write(f"GOVI overlap {bond_validation['start']:%b %Y}–{bond_validation['end']:%b %Y}: n={bond_validation['n']}; r={bond_validation['corr']:.3f}; TE={bond_validation['te']:.2%} p.a.; bias={bond_validation['bias']:.2%} p.a.; Yahoo split events={len(stx_splits)}.")
st.divider(); st.subheader('Asset Correlation'); asset_returns=master[list(ALLOC)].pct_change(fill_method=None).dropna(); corr=asset_returns.corr(); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()); st.metric('Net Inter-Asset Correlation',f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title='Pearson Correlation Matrix — Monthly ZAR Asset Returns',height=650); st.plotly_chart(heat,use_container_width=True)
st.divider(); st.subheader(f'{mode} — Beta & Alpha Through Time'); roll_beta,roll_alpha=rolling_capm(vals,master); line_chart({'36M Rolling Beta':roll_beta},f'{mode} — 36-Month Rolling Beta vs ALSI','Beta'); line_chart({'36M Rolling Alpha':roll_alpha*100},f'{mode} — 36-Month Rolling CAPM Alpha — RF 7%','Annualised Alpha (%)'); cb,nstress,stress=conditional_beta(vals,master); st.metric('Conditional Beta — ALSI Drawdown ≥10%',f'{cb:.3f}' if np.isfinite(cb) else 'N/A'); st.caption(f'Estimated using {nstress} monthly observations where the ALSI was at least 10% below its previous high.')