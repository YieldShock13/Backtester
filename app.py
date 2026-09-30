import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Portfolio Backtester", layout="wide")
START="2012-02-01"; RF=0.07; INITIAL=1_202_000
ALLOC={"ALSI":400_000,"SP500":200_000,"SA_BONDS":200_000,"EUROPE":125_000,"NEWGOLD":45_000,"EXXARO":50_000,"BERKSHIRE":56_000,"MSCI_EM":65_000,"AGG":61_000}
TICKERS={"ALSI":"^J203.JO","SP500":"^GSPC","EUROPE":"^STOXX","NEWGOLD":"GLD.JO","EXXARO":"EXX.JO","BERKSHIRE":"BRK-B","MSCI_EM":"EEM","AGG":"AGG","USDZAR":"ZAR=X","EURZAR":"EURZAR=X"}
ASSETS=list(ALLOC)

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
def load_stxgvi():
 h=yf.Ticker('STXGVI.JO').history(start='2023-03-01',auto_adjust=False,actions=True)
 if h.empty: raise RuntimeError('Yahoo returned no STXGVI history')
 h=h.copy(); h.index=pd.to_datetime(h.index).tz_localize(None); h=h.sort_index()
 close=_normalise_stxgvi_close(pd.to_numeric(h['Close'],errors='coerce'))
 div=pd.to_numeric(h.get('Dividends',0.0),errors='coerce').fillna(0.0)/100.0
 first_date=pd.Timestamp('2023-04-25')
 if first_date not in div.index or not np.isclose(float(div.loc[first_date]),1.9145,rtol=0,atol=.0001):
  got=float(div.loc[first_date]) if first_date in div.index else np.nan
  raise RuntimeError(f'STXGVI distribution conversion failed: 2023-04-25={got} ZAR, expected 1.9145 ZAR')
 for dt,dv in div[div!=0].items():
  p=close.asof(dt)
  if np.isfinite(p) and (dv<=0 or dv/p>.20): raise RuntimeError(f'STXGVI distribution sanity check failed on {dt.date()}: dividend_ZAR={dv}, close_ZAR={p}')
 return close,div

@st.cache_data(ttl=3600,show_spinner=False)
def load_yahoo_components():
 histories={}
 for asset,ticker in TICKERS.items():
  h=yf.Ticker(ticker).history(start=START,auto_adjust=False,actions=True)
  if h.empty: raise RuntimeError(f'Yahoo Finance returned no data for {ticker}')
  h=h.copy(); h.index=pd.to_datetime(h.index).tz_localize(None); h=h.sort_index()
  close=pd.to_numeric(h['Close'],errors='coerce')
  div=pd.to_numeric(h.get('Dividends',0.0),errors='coerce').fillna(0.0)
  if asset in ['NEWGOLD','EXXARO']:
   close=close/100.0; div=div/100.0
  histories[asset]=(close,div)
 usdzar=histories['USDZAR'][0].ffill(); eurzar=histories['EURZAR'][0].ffill()
 prices={}; divcash={}
 for asset in ['ALSI','SP500','EUROPE','NEWGOLD','EXXARO','BERKSHIRE','MSCI_EM','AGG']:
  close,div=histories[asset]
  if asset in ['SP500','BERKSHIRE','MSCI_EM','AGG']: fx=usdzar.reindex(close.index).ffill()
  elif asset=='EUROPE': fx=eurzar.reindex(close.index).ffill()
  else: fx=pd.Series(1.0,index=close.index)
  prices[asset]=(close*fx).rename(asset)
  # Dividend is translated at its actual payment/ex-date FX, then retained as cash.
  divcash[asset]=(div*fx).rename(asset)
 return prices,divcash

def build_bond_components(govi,stx_close,stx_divs):
 last_govi=govi.index.max(); anchor=float(govi.iloc[-1]); px_anchor=float(stx_close.asof(last_govi))
 if not np.isfinite(px_anchor) or px_anchor<=0: raise RuntimeError('No valid STXGVI price available to anchor continuation')
 units=anchor/px_anchor; daily=stx_close.loc[stx_close.index>last_govi]
 if daily.empty:
  return govi.rename('SA_BONDS'),pd.Series(0.0,index=govi.index,name='SA_BONDS'),{'last_govi':last_govi,'extension_months':0,'max_extension_return':np.nan}
 # Price component only. Cash distributions are kept separately and never folded into future return denominators.
 post_price=(units*daily).resample('ME').last()
 daily_div=(units*stx_divs.reindex(daily.index,fill_value=0.0))
 post_div=daily_div.resample('ME').sum()
 price=pd.concat([govi,post_price]); price=price[~price.index.duplicated(keep='last')].sort_index().rename('SA_BONDS')
 div=pd.Series(0.0,index=price.index,name='SA_BONDS'); div.loc[post_div.index]=post_div.values
 # Extension return for validation is period return: price change + only that month's distribution.
 bridge=pd.concat([pd.Series([anchor],index=[last_govi]),post_price]).sort_index()
 extret=bridge.pct_change(fill_method=None)
 extret.loc[post_div.index]=extret.loc[post_div.index]+post_div/bridge.shift(1).reindex(post_div.index)
 extret=extret.dropna()
 if (extret.abs()>.20).any():
  dt=extret.abs().idxmax(); raise RuntimeError(f'SA-bond continuation sanity check failed on {dt.date()}: {extret.loc[dt]:.2%}')
 return price,div,{'last_govi':last_govi,'extension_months':len(post_price),'max_extension_return':float(extret.abs().max()),'stx_anchor_price':px_anchor,'stx_units_per_index':units}

def build_master():
 prices,divs=load_yahoo_components(); g=load_govi_history(); stx,stxdiv=load_stxgvi(); bp,bd,val=build_bond_components(g,stx,stxdiv)
 # Month-end raw/split-normalised prices.
 mp=pd.DataFrame({a:s.resample('ME').last() for a,s in prices.items()})
 mp['SA_BONDS']=bp.reindex(mp.index).ffill()
 # Cash dividends/distributions paid during each month, in ZAR per original unit/index-unit.
 md=pd.DataFrame({a:s.resample('ME').sum() for a,s in divs.items()}).reindex(mp.index,fill_value=0.0)
 md['SA_BONDS']=bd.reindex(mp.index,fill_value=0.0)
 mp=mp[ASSETS].loc[START:].dropna(); md=md[ASSETS].reindex(mp.index,fill_value=0.0)
 if mp.empty: raise RuntimeError('Master dataset is empty')
 if not np.isclose(sum(ALLOC.values()),INITIAL): raise RuntimeError('Allocation does not reconcile to starting capital')
 # Period return identity: (ending price - starting price + distributions DURING period) / starting price.
 pr=(mp-mp.shift(1)+md)/mp.shift(1)
 bad=pr.abs().max(); bad=bad[bad>1.0]
 if len(bad): raise RuntimeError('Implausible monthly asset return(s): '+', '.join(f'{k}={v:.1%}' for k,v in bad.items()))
 return mp,md,pr,g,val

def buy_hold(prices,divs):
 v=pd.DataFrame(index=prices.index,columns=ASSETS,dtype=float); cash=pd.DataFrame(0.0,index=prices.index,columns=ASSETS)
 for a in ASSETS:
  units=ALLOC[a]/float(prices[a].iloc[0])
  asset_cash=(units*divs[a]).cumsum()
  v[a]=units*prices[a]+asset_cash
  cash[a]=asset_cash
 v['PORTFOLIO']=v[ASSETS].sum(axis=1)
 return v,cash

def annual_rebalanced(prices,divs):
 # Cash distributions remain cash permanently. Only invested market value is rebalanced annually.
 target=pd.Series(ALLOC,dtype=float)/INITIAL
 units=pd.Series({a:ALLOC[a]/float(prices[a].iloc[0]) for a in ASSETS},dtype=float)
 cash=pd.Series(0.0,index=ASSETS); v=pd.DataFrame(index=prices.index,columns=ASSETS,dtype=float)
 for i,dt in enumerate(prices.index):
  if i>0 and dt.year!=prices.index[i-1].year:
   invested=pd.Series({a:units[a]*prices.loc[dt,a] for a in ASSETS}); total_invested=invested.sum()
   units=(target*total_invested)/prices.loc[dt,ASSETS]
  cash=cash+units*divs.loc[dt,ASSETS]
  v.loc[dt,ASSETS]=units*prices.loc[dt,ASSETS]+cash
 v['PORTFOLIO']=v[ASSETS].sum(axis=1)
 return v

def period_returns(prices,divs):
 return (prices-prices.shift(1)+divs)/prices.shift(1)

def validate_accounting(prices,divs,asset_r,bh,rb):
 if not np.isclose(bh.PORTFOLIO.iloc[0],INITIAL) or not np.isclose(rb.PORTFOLIO.iloc[0],INITIAL): raise RuntimeError('Portfolio start-value reconciliation failed')
 for name,v in [('Buy & Hold',bh),('Annual Rebalanced',rb)]:
  if not np.allclose(v[ASSETS].sum(axis=1),v.PORTFOLIO,rtol=0,atol=.01): raise RuntimeError(f'{name} sleeve reconciliation failed')
 # Explicitly verify the return formula independently of any synthetic wealth series.
 check=(prices/prices.shift(1)-1)+(divs/prices.shift(1))
 err=(asset_r-check).abs().max().max()
 if not np.isfinite(err) or err>1e-10: raise RuntimeError(f'Asset period-return identity failed: max error {err}')
 # No prior dividend may enter a later period denominator.
 for a in ASSETS:
  nz=divs[a][divs[a]!=0]
  if len(nz):
   dt=nz.index[0]; prev=prices.index[prices.index.get_loc(dt)-1] if prices.index.get_loc(dt)>0 else None
   if prev is not None:
    expected=(prices.loc[dt,a]-prices.loc[prev,a]+divs.loc[dt,a])/prices.loc[prev,a]
    if not np.isclose(asset_r.loc[dt,a],expected,rtol=0,atol=1e-12): raise RuntimeError(f'Dividend period-return validation failed for {a} on {dt.date()}')
 return True

def capm_stats(v,market_r):
 rp=v.PORTFOLIO.pct_change(fill_method=None); d=pd.concat([rp.rename('P'),market_r.rename('M')],axis=1).dropna(); mrf=(1+RF)**(1/12)-1; x=d.M-mrf; y=d.P-mrf; b=y.cov(x)/x.var(); a=y.mean()-b*x.mean(); return b,(1+a)**12-1

def metrics(v,market_r):
 p=v.PORTFOLIO.dropna(); r=p.pct_change(fill_method=None).dropna(); yrs=(p.index[-1]-p.index[0]).days/365.25; cagr=(p.iloc[-1]/p.iloc[0])**(1/yrs)-1; vol=r.std()*np.sqrt(12); ex=r-((1+RF)**(1/12)-1); down=ex[ex<0]; dvol=np.sqrt(np.mean(down**2))*np.sqrt(12); dd=p/p.cummax()-1; var=r.quantile(.05); beta,alpha=capm_stats(v,market_r)
 return {'Initial Value':p.iloc[0],'Ending Value':p.iloc[-1],'Total Return':p.iloc[-1]/p.iloc[0]-1,'CAGR':cagr,'Annualised Volatility':vol,'Sharpe Ratio (RF 7%)':ex.mean()/ex.std()*np.sqrt(12),'Downside Volatility':dvol,'Sortino Ratio':ex.mean()*12/dvol,'Beta vs ALSI':beta,'CAPM Alpha (Annualised)':alpha,'Maximum Drawdown':dd.min(),'Calmar Ratio':cagr/abs(dd.min()),'Monthly VaR 95%':var,'Monthly CVaR 95%':r[r<=var].mean(),'Best Month':r.max(),'Worst Month':r.min(),'Positive Months':(r>0).mean(),'Max DD Date':dd.idxmin()}

def annual_returns(v):
 r=v.PORTFOLIO.pct_change(fill_method=None).dropna(); a=(1+r).groupby(r.index.year).prod()-1; o=pd.DataFrame({'Year':a.index.astype(int),'Annual Return':a.values,'Period':'Full Year'}); o.loc[o.Year==v.index[0].year,'Period']='Partial Year'; o.loc[o.Year==v.index[-1].year,'Period']='Partial Year'; return o

def annual_asset_returns(asset_r,prices):
 a=(1+asset_r).groupby(asset_r.index.year).prod(min_count=1)-1; a.index=a.index.astype(int); a.index.name='Year'; a=a.reset_index(); a.insert(1,'Period','Full Year'); a.loc[a.Year==prices.index[0].year,'Period']='Partial Year'; a.loc[a.Year==prices.index[-1].year,'Period']='Partial Year'; return a

def line_chart(series_map,title,ytitle):
 f=go.Figure()
 for name,s in series_map.items(): f.add_trace(go.Scatter(x=s.index,y=s.values,mode='lines',name=name))
 f.update_layout(title=title,xaxis_title='Date',yaxis_title=ytitle,hovermode='x unified',legend_title_text=''); st.plotly_chart(f,use_container_width=True)

def metric_table(m):
 pct={'Total Return','CAGR','Annualised Volatility','Downside Volatility','CAPM Alpha (Annualised)','Maximum Drawdown','Monthly VaR 95%','Monthly CVaR 95%','Best Month','Worst Month','Positive Months'}; rows=[]
 for k,v in m.items():
  x=pd.Timestamp(v).strftime('%Y-%m') if k=='Max DD Date' else f'R{v:,.0f}' if k in ['Initial Value','Ending Value'] else f'{v:.2%}' if k in pct else f'{v:.3f}'; rows.append((k,x))
 return pd.DataFrame(rows,columns=['Metric','Value'])

def rolling_capm(v,market_r,window=36):
 rp=v.PORTFOLIO.pct_change(fill_method=None); d=pd.concat([rp.rename('P'),market_r.rename('M')],axis=1).dropna(); mrf=(1+RF)**(1/12)-1; x=d.M-mrf; y=d.P-mrf; b=y.rolling(window).cov(x)/x.rolling(window).var(); a=y.rolling(window).mean()-b*x.rolling(window).mean(); return b,(1+a)**12-1

def conditional_beta(v,market_r,market_price):
 rp=v.PORTFOLIO.pct_change(fill_method=None); dd=market_price/market_price.cummax()-1; d=pd.concat([rp.rename('P'),market_r.rename('M'),dd.rename('DD')],axis=1).dropna(); s=d[d.DD<=-.10]; mrf=(1+RF)**(1/12)-1
 if len(s)<2:return np.nan,len(s),s
 return (s.P-mrf).cov(s.M-mrf)/(s.M-mrf).var(),len(s),s

st.title('Portfolio Backtester')
st.caption('Raw Yahoo Close only | Cash dividends retained, never reinvested | Yahoo Close already split-normalised | Period returns include only distributions paid in that period | SA bonds: GOVI through Feb-2026, then STXGVI fixed units + cash distributions | Starting capital R1,202,000 | RF 7%')
try:
 with st.spinner('Updating and validating market data…'):
  prices,divs,asset_r,govi,bond_validation=build_master(); bh,bh_cash=buy_hold(prices,divs); rb=annual_rebalanced(prices,divs); validate_accounting(prices,divs,asset_r,bh,rb)
except Exception as e: st.error(f'Data update/validation failed: {e}'); st.exception(e); st.stop()
market_r=asset_r['ALSI']; bhm,rbm=metrics(bh,market_r),metrics(rb,market_r)
st.success(f"Data loaded through {prices.index[-1]:%d %b %Y} | GOVI authoritative through {bond_validation['last_govi']:%d %b %Y} | STXGVI extension months: {bond_validation['extension_months']} | max extension move: {bond_validation['max_extension_return']:.2%} | accounting identities: PASS")
mode=st.radio('Backtest mode',['Buy & Hold','Annual Rebalanced'],horizontal=True,index=0); vals=bh if mode=='Buy & Hold' else rb; met=bhm if mode=='Buy & Hold' else rbm
c1,c2,c3,c4=st.columns(4); c1.metric(f'{mode} Value',f"R{met['Ending Value']:,.0f}"); c2.metric(f'{mode} CAGR',f"{met['CAGR']:.2%}"); c3.metric('Sharpe (7% RF)',f"{met['Sharpe Ratio (RF 7%)']:.3f}"); c4.metric('Max Drawdown',f"{met['Maximum Drawdown']:.2%}")
st.subheader(f'{mode} Analytics'); st.dataframe(metric_table(met),hide_index=True,use_container_width=True)
p=vals.PORTFOLIO; r=p.pct_change(fill_method=None).dropna(); growth=p/p.iloc[0]*100; dd=(p/p.cummax()-1)*100; roll_ret=((1+r).rolling(12).apply(np.prod,raw=True)-1)*100; roll_vol=r.rolling(12).std()*np.sqrt(12)*100; ex=r-((1+RF)**(1/12)-1); roll_sr=ex.rolling(36).mean()/ex.rolling(36).std()*np.sqrt(12)
line_chart({mode:p},f'{mode} — Portfolio Value','ZAR'); line_chart({mode:growth},f'{mode} — Growth of R100','Value'); line_chart({'Drawdown':dd},f'{mode} — Portfolio Drawdown','%'); bar=go.Figure(go.Bar(x=r.index,y=r.values*100)); bar.update_layout(title=f'{mode} — Monthly Portfolio Returns',yaxis_title='Return (%)'); st.plotly_chart(bar,use_container_width=True); line_chart({'12M Return':roll_ret},f'{mode} — Rolling 12-Month Return','%'); line_chart({'12M Volatility':roll_vol},f'{mode} — Rolling 12-Month Annualised Volatility','%'); line_chart({'36M Sharpe':roll_sr},f'{mode} — Rolling 36-Month Sharpe Ratio — RF 7%','Sharpe'); line_chart({c:vals[c] for c in ASSETS},f'{mode} — Portfolio Sleeve Values','ZAR')
st.subheader(f'{mode} Annual Returns'); ar=annual_returns(vals); ar['Annual Return']=ar['Annual Return'].map(lambda x:f'{x:.2%}'); st.dataframe(ar,hide_index=True,use_container_width=True)
st.subheader('Annual Return by Asset'); aar=annual_asset_returns(asset_r,prices)
for c in ASSETS: aar[c]=aar[c].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
st.dataframe(aar,hide_index=True,use_container_width=True)
weights=vals[ASSETS].div(vals.PORTFOLIO,axis=0); wt=pd.DataFrame({'Asset':ASSETS,'Initial Weight':[ALLOC[a]/INITIAL for a in ASSETS],'Ending Weight':weights.iloc[-1].values}); wt['Initial Weight']=wt['Initial Weight'].map(lambda x:f'{x:.2%}'); wt['Ending Weight']=wt['Ending Weight'].map(lambda x:f'{x:.2%}'); st.subheader(f'{mode} Portfolio Weights'); st.dataframe(wt,hide_index=True,use_container_width=True)
st.divider(); st.subheader('Buy & Hold vs Annual Rebalancing'); line_chart({'Buy & Hold':bh.PORTFOLIO,'Annual Rebalanced':rb.PORTFOLIO},'Portfolio Value Comparison','ZAR'); st.dataframe(pd.DataFrame({'Buy & Hold':metric_table(bhm).set_index('Metric').Value,'Annual Rebalanced':metric_table(rbm).set_index('Metric').Value}),use_container_width=True)
with st.expander('Methodology & data'):
 st.write('Raw Close is used, never Adjusted Close. Yahoo Close is already split-normalised, so reported split events are not applied again. Foreign prices and dividends are translated into ZAR. Dividends/distributions remain cash and are never reinvested. Buy & Hold keeps original asset units fixed. Annual Rebalanced changes only invested asset units at calendar-year boundaries; accumulated dividend cash is not used to buy assets.')
 st.write('Asset-period return is calculated directly as (ending price − starting price + cash distributions paid during the period) / starting price. Prior-period cash distributions never enter a later return denominator. SA bonds use repository GOVI through February 2026; thereafter fixed STXGVI units extend the price component and STXGVI distributions are tracked separately as cash.')
st.divider(); st.subheader('Asset Correlation'); corr=asset_r[ASSETS].dropna().corr(); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()); st.metric('Net Inter-Asset Correlation',f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title='Pearson Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)
st.divider(); st.subheader(f'{mode} — Beta & Alpha Evolution vs ALSI'); roll_beta,roll_alpha=rolling_capm(vals,market_r); line_chart({'36M Rolling Beta':roll_beta},f'{mode} — 36-Month Rolling Beta vs ALSI','Beta'); line_chart({'36M Rolling Alpha':roll_alpha*100},f'{mode} — 36-Month Rolling Annualised CAPM Alpha','Alpha (%)'); cb,nobs,stress=conditional_beta(vals,market_r,prices['ALSI']); st.metric('Conditional Beta — ALSI Drawdown ≥10%', 'N/A' if not np.isfinite(cb) else f'{cb:.3f}'); st.caption(f'Conditional beta estimated using {nobs} monthly observations where ALSI was at least 10% below its prior peak.')