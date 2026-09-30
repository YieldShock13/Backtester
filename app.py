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
 if len(s)<100: raise RuntimeError('Validated GOVI history is incomplete')
 return s

def _normalise_stxgvi_close(close):
 # Yahoo has changed STXGVI.JO quotation units between ZAR and JSE cents (ZAc).
 # Detect only ~100x regime breaks; never smooth genuine market moves.
 s=close.astype(float).copy().dropna()
 ratios=s/s.shift(1)
 breaks=ratios[(ratios>50)&(ratios<150)].index.tolist()+ratios[(ratios>.005)&(ratios<.02)].index.tolist()
 for dt in sorted(set(breaks)):
  i=s.index.get_loc(dt); ratio=s.iloc[i]/s.iloc[i-1]
  if ratio>50: s.iloc[i:]=s.iloc[i:]/100.0
  elif ratio<.02: s.iloc[i:]=s.iloc[i:]*100.0
 med=float(s.tail(min(60,len(s))).median())
 if med>1000: s=s/100.0
 if not (20 < float(s.iloc[-1]) < 200): raise RuntimeError(f'STXGVI normalised close implausible: {s.iloc[-1]:.2f} ZAR')
 return s

@st.cache_data(ttl=3600,show_spinner=False)
def load_stxgvi():
 h=yf.Ticker('STXGVI.JO').history(start='2023-03-01',auto_adjust=False,actions=True)
 if h.empty: raise RuntimeError('Yahoo returned no STXGVI history')
 h=h.copy(); h.index=pd.to_datetime(h.index).tz_localize(None); h=h.sort_index()
 close_raw=pd.to_numeric(h['Close'],errors='coerce'); close=_normalise_stxgvi_close(close_raw)
 div_raw=pd.to_numeric(h.get('Dividends',0.0),errors='coerce').fillna(0.0); splits=pd.to_numeric(h.get('Stock Splits',0.0),errors='coerce').fillna(0.0)
 div=div_raw/100.0
 first_date=pd.Timestamp('2023-04-25')
 if first_date not in div.index or not np.isclose(float(div.loc[first_date]),1.9145,rtol=0,atol=.0001):
  got=float(div.loc[first_date]) if first_date in div.index else np.nan; raise RuntimeError(f'STXGVI distribution conversion failed: 2023-04-25={got} ZAR, expected 1.9145 ZAR')
 for dt,dv in div[div!=0].items():
  p=close.asof(dt)
  if np.isfinite(p) and (dv<=0 or dv/p>.20): raise RuntimeError(f'STXGVI distribution sanity check failed on {dt.date()}: dividend_ZAR={dv}, close_ZAR={p}')
 wealth=(close+div.reindex(close.index,fill_value=0).cumsum()).rename('STXGVI_WEALTH').dropna().resample('ME').last()
 mr=wealth.pct_change(fill_method=None).dropna()
 if (mr.abs()>.20).any():
  dt=mr.abs().idxmax(); raise RuntimeError(f'STXGVI monthly return sanity check failed on {dt.date()}: {mr.loc[dt]:.2%}')
 if len(wealth)<24: raise RuntimeError('STXGVI live history unexpectedly short')
 return wealth,div,splits

@st.cache_data(ttl=3600,show_spinner=False)
def load_yahoo():
 raw=yf.download(list(TICKERS.values()),start=START,auto_adjust=False,actions=False,progress=False,group_by='column')
 if raw.empty: raise RuntimeError('Yahoo Finance returned no data')
 adj=raw['Adj Close'].rename(columns={v:k for k,v in TICKERS.items()})
 for c in ['NEWGOLD','EXXARO']: adj[c]=adj[c]/100.0
 adj['USDZAR']=adj['USDZAR'].ffill(); adj['EURZAR']=adj['EURZAR'].ffill(); z=pd.DataFrame(index=adj.index)
 for c in ['ALSI','NEWGOLD','EXXARO']: z[c]=adj[c]
 for c in ['SP500','BERKSHIRE','MSCI_EM','AGG']: z[c]=adj[c]*adj['USDZAR']
 z['EUROPE']=adj['EUROPE']*adj['EURZAR']; return z

def build_bond_series(govi,stx):
 last_govi=govi.index.max(); pre=govi.copy(); post=stx.loc[stx.index>last_govi]
 if post.empty: return pre.rename('SA_BONDS'),{'last_govi':last_govi,'extension_months':0,'max_extension_return':np.nan}
 prior=stx.loc[stx.index<=last_govi]
 if prior.empty: raise RuntimeError('No STXGVI observation available to anchor continuation')
 anchor=float(pre.iloc[-1]); stx_anchor=float(prior.iloc[-1]); post=anchor*(post/stx_anchor)
 bridge=pd.concat([pd.Series([anchor],index=[last_govi]),post]); extret=bridge.pct_change(fill_method=None).dropna()
 if (extret.abs()>.20).any():
  dt=extret.abs().idxmax(); raise RuntimeError(f'SA-bond continuation sanity check failed on {dt.date()}: {extret.loc[dt]:.2%}')
 bond=pd.concat([pre,post]); bond=bond[~bond.index.duplicated(keep='last')].sort_index(); bond.name='SA_BONDS'
 return bond,{'last_govi':last_govi,'extension_months':len(post),'max_extension_return':float(extret.abs().max())}

def build_master():
 z=load_yahoo(); g=load_govi_history(); stx,divs,splits=load_stxgvi(); bond,val=build_bond_series(g,stx); m=z.resample('ME').last(); m['SA_BONDS']=bond.reindex(m.index).ffill(); m=m[list(ALLOC)].loc['2012-02-01':].dropna()
 if m.empty: raise RuntimeError('Master dataset is empty')
 if not np.isclose(sum(ALLOC.values()),INITIAL): raise RuntimeError('Allocation does not reconcile to starting capital')
 mr=m.pct_change(fill_method=None).dropna()
 bad=mr.abs().max(); bad=bad[bad>1.0]
 if len(bad): raise RuntimeError('Implausible monthly asset return(s): '+', '.join(f'{k}={v:.1%}' for k,v in bad.items()))
 return m,g,stx,divs,splits,val

def buy_hold(m):
 v=m.div(m.iloc[0]).mul(pd.Series(ALLOC),axis=1); v['PORTFOLIO']=v.sum(axis=1); return v

def annual_rebalanced(m):
 assets=list(ALLOC); target=pd.Series(ALLOC,dtype=float)/INITIAL; r=m[assets].pct_change(fill_method=None).fillna(0); v=pd.DataFrame(index=m.index,columns=assets,dtype=float); v.iloc[0]=pd.Series(ALLOC)
 for i in range(1,len(m)):
  prev=v.iloc[i-1].astype(float)
  if m.index[i].year!=m.index[i-1].year: prev=target*prev.sum()
  v.iloc[i]=prev*(1+r.iloc[i])
 v['PORTFOLIO']=v.sum(axis=1); return v

def capm_stats(v,m):
 rp=v.PORTFOLIO.pct_change(fill_method=None); rm=m.ALSI.pct_change(fill_method=None); d=pd.concat([rp.rename('P'),rm.rename('M')],axis=1).dropna(); mrf=(1+RF)**(1/12)-1; x=d.M-mrf; y=d.P-mrf; b=y.cov(x)/x.var(); a=y.mean()-b*x.mean(); return b,(1+a)**12-1

def metrics(v,m):
 p=v.PORTFOLIO.dropna(); r=p.pct_change(fill_method=None).dropna(); yrs=(p.index[-1]-p.index[0]).days/365.25; cagr=(p.iloc[-1]/p.iloc[0])**(1/yrs)-1; vol=r.std()*np.sqrt(12); ex=r-((1+RF)**(1/12)-1); down=ex[ex<0]; dvol=np.sqrt(np.mean(down**2))*np.sqrt(12); dd=p/p.cummax()-1; var=r.quantile(.05); beta,alpha=capm_stats(v,m)
 return {'Initial Value':p.iloc[0],'Ending Value':p.iloc[-1],'Total Return':p.iloc[-1]/p.iloc[0]-1,'CAGR':cagr,'Annualised Volatility':vol,'Sharpe Ratio (RF 7%)':ex.mean()/ex.std()*np.sqrt(12),'Downside Volatility':dvol,'Sortino Ratio':ex.mean()*12/dvol,'Beta vs ALSI':beta,'CAPM Alpha (Annualised)':alpha,'Maximum Drawdown':dd.min(),'Calmar Ratio':cagr/abs(dd.min()),'Monthly VaR 95%':var,'Monthly CVaR 95%':r[r<=var].mean(),'Best Month':r.max(),'Worst Month':r.min(),'Positive Months':(r>0).mean(),'Max DD Date':dd.idxmin()}

def annual_returns(v):
 r=v.PORTFOLIO.pct_change(fill_method=None).dropna(); a=(1+r).groupby(r.index.year).prod()-1; o=pd.DataFrame({'Year':a.index.astype(int),'Annual Return':a.values,'Period':'Full Year'}); o.loc[o.Year==v.index[0].year,'Period']='Partial Year'; o.loc[o.Year==v.index[-1].year,'Period']='Partial Year'; return o

def annual_asset_returns(m):
 r=m[list(ALLOC)].pct_change(fill_method=None); a=(1+r).groupby(r.index.year).prod(min_count=1)-1
 # The first observation is the backtest base, so the first row is the return from that base through year-end.
 a.index=a.index.astype(int); a.index.name='Year'; a=a.reset_index()
 a.insert(1,'Period','Full Year'); a.loc[a.Year==m.index[0].year,'Period']='Partial Year'; a.loc[a.Year==m.index[-1].year,'Period']='Partial Year'
 return a

def line_chart(series_map,title,ytitle):
 f=go.Figure()
 for name,s in series_map.items(): f.add_trace(go.Scatter(x=s.index,y=s.values,mode='lines',name=name))
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

st.title('Portfolio Backtester'); st.caption('Live Yahoo Finance | SA bonds: SARB GOVI through Feb-2026, then Satrix GOVI ETF continuation with Yahoo ZAR/ZAc regime normalisation + explicit cash distributions | Starting capital R1,202,000 | RF 7%')
try:
 with st.spinner('Updating and validating market data…'): master,govi,stxgvi,stx_divs,stx_splits,bond_validation=build_master(); bh=buy_hold(master); rb=annual_rebalanced(master)
except Exception as e: st.error(f'Data update/validation failed: {e}'); st.exception(e); st.stop()
bhm,rbm=metrics(bh,master),metrics(rb,master); st.success(f"Data loaded through {master.index[-1]:%d %b %Y} | GOVI authoritative through {bond_validation['last_govi']:%d %b %Y} | STXGVI extension months: {bond_validation['extension_months']} | max extension move: {bond_validation['max_extension_return']:.2%}")
mode=st.radio('Backtest mode',['Buy & Hold','Annual Rebalanced'],horizontal=True,index=0); vals=bh if mode=='Buy & Hold' else rb; met=bhm if mode=='Buy & Hold' else rbm
c1,c2,c3,c4=st.columns(4); c1.metric(f'{mode} Value',f"R{met['Ending Value']:,.0f}"); c2.metric(f'{mode} CAGR',f"{met['CAGR']:.2%}"); c3.metric('Sharpe (7% RF)',f"{met['Sharpe Ratio (RF 7%)']:.3f}"); c4.metric('Max Drawdown',f"{met['Maximum Drawdown']:.2%}")
st.subheader(f'{mode} Analytics'); st.dataframe(metric_table(met),hide_index=True,use_container_width=True)
p=vals.PORTFOLIO; r=p.pct_change(fill_method=None).dropna(); growth=p/p.iloc[0]*100; dd=(p/p.cummax()-1)*100; roll_ret=((1+r).rolling(12).apply(np.prod,raw=True)-1)*100; roll_vol=r.rolling(12).std()*np.sqrt(12)*100; ex=r-((1+RF)**(1/12)-1); roll_sr=ex.rolling(36).mean()/ex.rolling(36).std()*np.sqrt(12)
line_chart({mode:p},f'{mode} — Portfolio Value','ZAR'); line_chart({mode:growth},f'{mode} — Growth of R100','Value'); line_chart({'Drawdown':dd},f'{mode} — Portfolio Drawdown','%'); bar=go.Figure(go.Bar(x=r.index,y=r.values*100)); bar.update_layout(title=f'{mode} — Monthly Portfolio Returns',yaxis_title='Return (%)'); st.plotly_chart(bar,use_container_width=True); line_chart({'12M Return':roll_ret},f'{mode} — Rolling 12-Month Return','%'); line_chart({'12M Volatility':roll_vol},f'{mode} — Rolling 12-Month Annualised Volatility','%'); line_chart({'36M Sharpe':roll_sr},f'{mode} — Rolling 36-Month Sharpe Ratio — RF 7%','Sharpe'); line_chart({c:vals[c] for c in ALLOC},f'{mode} — Portfolio Sleeve Values','ZAR')
st.subheader(f'{mode} Annual Returns'); ar=annual_returns(vals); ar['Annual Return']=ar['Annual Return'].map(lambda x:f'{x:.2%}'); st.dataframe(ar,hide_index=True,use_container_width=True)
st.subheader('Annual Return by Asset'); aar=annual_asset_returns(master); 
for c in ALLOC: aar[c]=aar[c].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
st.dataframe(aar,hide_index=True,use_container_width=True)
weights=vals[list(ALLOC)].div(vals.PORTFOLIO,axis=0); wt=pd.DataFrame({'Asset':list(ALLOC),'Initial Weight':[ALLOC[a]/INITIAL for a in ALLOC],'Ending Weight':weights.iloc[-1].values}); wt['Initial Weight']=wt['Initial Weight'].map(lambda x:f'{x:.2%}'); wt['Ending Weight']=wt['Ending Weight'].map(lambda x:f'{x:.2%}'); st.subheader(f'{mode} Portfolio Weights'); st.dataframe(wt,hide_index=True,use_container_width=True)
st.divider(); st.subheader('Buy & Hold vs Annual Rebalancing'); line_chart({'Buy & Hold':bh.PORTFOLIO,'Annual Rebalanced':rb.PORTFOLIO},'Portfolio Value Comparison','ZAR'); st.dataframe(pd.DataFrame({'Buy & Hold':metric_table(bhm).set_index('Metric').Value,'Annual Rebalanced':metric_table(rbm).set_index('Metric').Value}),use_container_width=True)
with st.expander('Methodology & data'):
 st.write('Buy & Hold permits weights to drift. Annual Rebalanced resets to original target weights at the start of each calendar year. Foreign sleeves are translated into ZAR. SA equity uses FTSE/JSE All Share (^J203.JO).')
 st.write('SA bonds use repository GOVI through February 2026. Later months use STXGVI. Yahoo has supplied STXGVI prices in both ZAR and JSE cents; the loader detects only ~100x quotation-unit regime breaks and converts them to a continuous ZAR price before adding cash distributions. Monthly continuation moves above 20% are rejected rather than allowed into the backtest.')
st.divider(); st.subheader('Asset Correlation'); asset_returns=master[list(ALLOC)].pct_change(fill_method=None).dropna(); corr=asset_returns.corr(); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()); st.metric('Net Inter-Asset Correlation',f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title='Pearson Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)
st.divider(); st.subheader(f'{mode} — Beta & Alpha Evolution vs ALSI'); roll_beta,roll_alpha=rolling_capm(vals,master); line_chart({'36M Rolling Beta':roll_beta},f'{mode} — 36-Month Rolling Beta vs ALSI','Beta'); line_chart({'36M Rolling Alpha':roll_alpha*100},f'{mode} — 36-Month Rolling Annualised CAPM Alpha','Alpha (%)'); cb,nobs,stress=conditional_beta(vals,master); st.metric('Conditional Beta — ALSI Drawdown ≥10%', 'N/A' if not np.isfinite(cb) else f'{cb:.3f}'); st.caption(f'Conditional beta estimated using {nobs} monthly observations where ALSI was at least 10% below its prior peak.')