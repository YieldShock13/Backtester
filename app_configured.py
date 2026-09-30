import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Portfolio Backtester", layout="wide")
START="2012-02-01"
DEFAULT_RF=0.07
DEFAULT_INITIAL=1_202_000
DEFAULT_ALLOC={"ALSI":400_000,"SP500":200_000,"SA_BONDS":200_000,"EUROPE":125_000,"NEWGOLD":45_000,"EXXARO":50_000,"BERKSHIRE":56_000,"MSCI_EM":65_000,"AGG":61_000}
TICKERS={"ALSI":"^J203.JO","SP500":"^GSPC","EUROPE":"^STOXX","NEWGOLD":"GLD.JO","EXXARO":"EXX.JO","BERKSHIRE":"BRK-B","MSCI_EM":"EEM","AGG":"AGG","USDZAR":"ZAR=X","EURZAR":"EURZAR=X"}
ALL_ASSETS=list(DEFAULT_ALLOC)

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
  close=pd.to_numeric(h['Close'],errors='coerce'); div=pd.to_numeric(h.get('Dividends',0.0),errors='coerce').fillna(0.0)
  if asset in ['NEWGOLD','EXXARO']: close=close/100.0; div=div/100.0
  histories[asset]=(close,div)
 usdzar=histories['USDZAR'][0].ffill(); eurzar=histories['EURZAR'][0].ffill(); prices={}; divcash={}; local={}; fx_used={}
 for asset in ['ALSI','SP500','EUROPE','NEWGOLD','EXXARO','BERKSHIRE','MSCI_EM','AGG']:
  close,div=histories[asset]; local[asset]=close
  if asset in ['SP500','BERKSHIRE','MSCI_EM','AGG']: fx=usdzar.reindex(close.index).ffill()
  elif asset=='EUROPE': fx=eurzar.reindex(close.index).ffill()
  else: fx=pd.Series(1.0,index=close.index)
  fx_used[asset]=fx; prices[asset]=(close*fx).rename(asset); divcash[asset]=(div*fx).rename(asset)
 return prices,divcash,local,fx_used

def build_bond_components(govi,stx_close,stx_divs):
 last_govi=govi.index.max(); anchor=float(govi.iloc[-1]); px_anchor=float(stx_close.asof(last_govi))
 if not np.isfinite(px_anchor) or px_anchor<=0: raise RuntimeError('No valid STXGVI price available to anchor continuation')
 units=anchor/px_anchor; daily=stx_close.loc[stx_close.index>last_govi]
 if daily.empty: return govi.rename('SA_BONDS'),pd.Series(0.0,index=govi.index,name='SA_BONDS'),{'last_govi':last_govi,'extension_months':0,'max_extension_return':np.nan}
 post_price=(units*daily).resample('ME').last(); daily_div=units*stx_divs.reindex(daily.index,fill_value=0.0); post_div=daily_div.resample('ME').sum()
 price=pd.concat([govi,post_price]); price=price[~price.index.duplicated(keep='last')].sort_index().rename('SA_BONDS')
 div=pd.Series(0.0,index=price.index,name='SA_BONDS'); div.loc[post_div.index]=post_div.values
 bridge=pd.concat([pd.Series([anchor],index=[last_govi]),post_price]).sort_index(); extret=bridge.pct_change(fill_method=None); extret.loc[post_div.index]=extret.loc[post_div.index]+post_div/bridge.shift(1).reindex(post_div.index); extret=extret.dropna()
 if (extret.abs()>.20).any():
  dt=extret.abs().idxmax(); raise RuntimeError(f'SA-bond continuation sanity check failed on {dt.date()}: {extret.loc[dt]:.2%}')
 return price,div,{'last_govi':last_govi,'extension_months':len(post_price),'max_extension_return':float(extret.abs().max()),'stx_anchor_price':px_anchor,'stx_units_per_index':units}

def build_master():
 prices,divs,local,fx=load_yahoo_components(); g=load_govi_history(); stx,stxdiv=load_stxgvi(); bp,bd,val=build_bond_components(g,stx,stxdiv)
 mp=pd.DataFrame({a:s.resample('ME').last() for a,s in prices.items()}); mp['SA_BONDS']=bp.reindex(mp.index).ffill()
 md=pd.DataFrame({a:s.resample('ME').sum() for a,s in divs.items()}).reindex(mp.index,fill_value=0.0); md['SA_BONDS']=bd.reindex(mp.index,fill_value=0.0)
 ml=pd.DataFrame({a:s.resample('ME').last() for a,s in local.items()}); mf=pd.DataFrame({a:s.resample('ME').last() for a,s in fx.items()})
 return mp.loc[START:],md.reindex(mp.index,fill_value=0.0).loc[START:],ml.loc[START:],mf.loc[START:],g,val

def resolve_dates(index,timeline,custom_start,custom_end):
 end=index.max()
 if timeline=='All': requested=index.min()
 elif timeline=='Custom': requested=pd.Timestamp(custom_start); end=min(pd.Timestamp(custom_end)+pd.offsets.MonthEnd(0),end)
 else:
  offsets={'1W':pd.DateOffset(weeks=1),'1M':pd.DateOffset(months=1),'3M':pd.DateOffset(months=3),'6M':pd.DateOffset(months=6),'1Y':pd.DateOffset(years=1),'3Y':pd.DateOffset(years=3),'5Y':pd.DateOffset(years=5),'10Y':pd.DateOffset(years=10)}
  requested=end-offsets[timeline]
 available=index[index>=requested]
 if len(available)==0: raise RuntimeError('No observations in requested timeline')
 return available[0],end,requested

def portfolio_values(prices,divs,alloc,reinvest,rebalance=False):
 assets=list(alloc); target=pd.Series(alloc,dtype=float)/sum(alloc.values()); units=pd.Series({a:alloc[a]/float(prices[a].iloc[0]) for a in assets}); cash=pd.Series(0.0,index=assets)
 v=pd.DataFrame(index=prices.index,columns=assets,dtype=float); v.iloc[0]=pd.Series(alloc)
 for i in range(1,len(prices)):
  dt=prices.index[i]; prev=prices.index[i-1]
  if rebalance and dt.year!=prev.year:
   total=(units*prices.loc[prev,assets]+cash).sum(); units=(target*total)/prices.loc[prev,assets]; cash[:]=0.0
  flows=units*divs.loc[dt,assets]
  if reinvest:
   units=units+flows/prices.loc[dt,assets]
  else: cash=cash+flows
  v.loc[dt,assets]=units*prices.loc[dt,assets]+cash
 v['PORTFOLIO']=v[assets].sum(axis=1); return v

def line_chart(series_map,title,ytitle):
 f=go.Figure()
 for name,s in series_map.items(): f.add_trace(go.Scatter(x=s.index,y=s.values,mode='lines',name=name))
 f.update_layout(title=title,xaxis_title='Date',yaxis_title=ytitle,hovermode='x unified',legend_title_text=''); st.plotly_chart(f,use_container_width=True)

def stats(v,market_r,rf):
 p=v.PORTFOLIO; r=p.pct_change(fill_method=None).dropna(); yrs=max((p.index[-1]-p.index[0]).days/365.25,1/365.25); cagr=(p.iloc[-1]/p.iloc[0])**(1/yrs)-1; vol=r.std()*np.sqrt(12); rfp=(1+rf)**(1/12)-1; ex=r-rfp; down=ex[ex<0]; dvol=np.sqrt(np.mean(down**2))*np.sqrt(12); dd=p/p.cummax()-1
 d=pd.concat([r.rename('P'),market_r.rename('M')],axis=1).dropna(); x=d.M-rfp; y=d.P-rfp; beta=y.cov(x)/x.var() if x.var()>0 else np.nan; alpha=(1+y.mean()-beta*x.mean())**12-1 if np.isfinite(beta) else np.nan; var=r.quantile(.05)
 return {'Initial Value':p.iloc[0],'Ending Value':p.iloc[-1],'Total Return':p.iloc[-1]/p.iloc[0]-1,'CAGR':cagr,'Annualised Volatility':vol,'Sharpe Ratio':ex.mean()/ex.std()*np.sqrt(12),'Downside Volatility':dvol,'Sortino Ratio':ex.mean()*12/dvol if dvol>0 else np.nan,'Beta vs ALSI':beta,'CAPM Alpha (Annualised)':alpha,'Maximum Drawdown':dd.min(),'Calmar Ratio':cagr/abs(dd.min()) if dd.min()<0 else np.nan,'Monthly VaR 95%':var,'Monthly CVaR 95%':r[r<=var].mean(),'Best Month':r.max(),'Worst Month':r.min(),'Positive Months':(r>0).mean(),'Max DD Date':dd.idxmin()}

def metric_table(m):
 pct={'Total Return','CAGR','Annualised Volatility','Downside Volatility','CAPM Alpha (Annualised)','Maximum Drawdown','Monthly VaR 95%','Monthly CVaR 95%','Best Month','Worst Month','Positive Months'}; rows=[]
 for k,v in m.items():
  x=pd.Timestamp(v).strftime('%Y-%m') if k=='Max DD Date' else f'R{v:,.0f}' if k in ['Initial Value','Ending Value'] else f'{v:.2%}' if k in pct else f'{v:.3f}'; rows.append((k,x))
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

def rolling_capm(v,market_r,rf,window=36):
 rp=v.PORTFOLIO.pct_change(fill_method=None); d=pd.concat([rp.rename('P'),market_r.rename('M')],axis=1).dropna(); rfp=(1+rf)**(1/12)-1; x=d.M-rfp; y=d.P-rfp; b=y.rolling(window).cov(x)/x.rolling(window).var(); a=y.rolling(window).mean()-b*x.rolling(window).mean(); return b,(1+a)**12-1

def fx_attribution(local,fx,zar_price,divs,assets):
 rows=[]
 for a in assets:
  if a not in ['SP500','BERKSHIRE','MSCI_EM','AGG','EUROPE']: continue
  d=pd.concat([local[a].rename('L'),fx[a].rename('F'),zar_price[a].rename('Z')],axis=1).dropna()
  if len(d)<2: continue
  l=d.L.iloc[-1]/d.L.iloc[0]-1; f=d.F.iloc[-1]/d.F.iloc[0]-1; interaction=l*f; cash=divs[a].sum()/d.Z.iloc[0]; total=l+f+interaction+cash
  rows.append({'Asset':a,'Total ZAR Return':total,'Underlying contribution % of total':l/total if total else np.nan,'FX contribution % of total':f/total if total else np.nan,'FX interaction % of total':interaction/total if total else np.nan,'Cash distribution % of total':cash/total if total else np.nan})
 return pd.DataFrame(rows)

st.title('Portfolio Backtester')
st.subheader('Backtest Configuration')
a,b,c,d=st.columns(4)
with a: timeline=st.selectbox('Timeline',['1W','1M','3M','6M','1Y','3Y','5Y','10Y','All','Custom'],index=8)
with b: INITIAL=float(st.number_input('Nominal amount (ZAR)',min_value=1.0,value=float(DEFAULT_INITIAL),step=10000.0))
with c: RF=float(st.number_input('Risk-free rate (%)',min_value=0.0,max_value=100.0,value=7.0,step=.25))/100
with d: REINVEST=st.toggle('Reinvest dividends/distributions',value=False)
custom_start=custom_end=None
if timeline=='Custom':
 x,y=st.columns(2)
 with x: custom_start=st.date_input('Custom start',value=pd.Timestamp(START).date())
 with y: custom_end=st.date_input('Custom end',value=pd.Timestamp.today().date())
ASSETS=st.multiselect('Assets',ALL_ASSETS,default=ALL_ASSETS)
if not ASSETS: st.error('Select at least one asset.'); st.stop()
st.markdown('**Weights**')
cols=st.columns(3); raww={}
for i,a0 in enumerate(ASSETS):
 with cols[i%3]: raww[a0]=st.number_input(f'{a0} (%)',0.0,100.0,float(DEFAULT_ALLOC[a0]/DEFAULT_INITIAL*100),.25)/100
if sum(raww.values())<=0: st.error('Weights must be positive.'); st.stop()
weights={a0:w/sum(raww.values()) for a0,w in raww.items()}; ALLOC={a0:INITIAL*w for a0,w in weights.items()}
if not np.isclose(sum(ALLOC.values()),INITIAL,atol=.01): st.error('Allocation reconciliation failed.'); st.stop()

try:
 with st.spinner('Updating, configuring and validating market data…'):
  full_p,full_d,full_l,full_fx,govi,bond_validation=build_master(); common=full_p[ASSETS].dropna().index; start,end,requested=resolve_dates(common,timeline,custom_start,custom_end); prices=full_p.loc[(full_p.index>=start)&(full_p.index<=end),ASSETS].dropna(); divs=full_d.reindex(prices.index,fill_value=0.0)[ASSETS]
  if len(prices)<2: raise RuntimeError('Selected timeline has fewer than two common month-end observations')
  asset_r=(prices-prices.shift(1)+divs)/prices.shift(1); bad=asset_r.abs().max(); bad=bad[bad>1.0]
  if len(bad): raise RuntimeError('Implausible monthly asset return(s): '+', '.join(f'{k}={v:.1%}' for k,v in bad.items()))
  bh=portfolio_values(prices,divs,ALLOC,REINVEST,False); rb=portfolio_values(prices,divs,ALLOC,REINVEST,True)
  for name,v in [('Buy & Hold',bh),('Annual Rebalanced',rb)]:
   if not np.isclose(v.PORTFOLIO.iloc[0],INITIAL,atol=.01): raise RuntimeError(f'{name} start-value reconciliation failed')
   if not np.allclose(v[ASSETS].sum(axis=1),v.PORTFOLIO,atol=.01,rtol=0): raise RuntimeError(f'{name} sleeve reconciliation failed')
except Exception as e: st.error(f'Data update/validation failed: {e}'); st.exception(e); st.stop()

if start>requested: st.warning(f'Requested start {requested:%Y-%m-%d} unavailable for the selected common asset set. Backtest starts at first common validated observation: {start:%Y-%m-%d}.')
st.caption(f'Configured window {prices.index[0]:%d %b %Y} to {prices.index[-1]:%d %b %Y} | Nominal R{INITIAL:,.0f} | RF {RF:.2%} | Dividends '+('reinvested' if REINVEST else 'retained as cash'))
st.success(f"Data validation PASS | GOVI authoritative through {bond_validation['last_govi']:%d %b %Y} | STXGVI extension months: {bond_validation['extension_months']} | accounting identities: PASS")

mode=st.radio('Backtest mode',['Buy & Hold','Annual Rebalanced'],horizontal=True,index=0); vals=bh if mode=='Buy & Hold' else rb
market_r=asset_r['ALSI'] if 'ALSI' in asset_r else pd.Series(index=asset_r.index,dtype=float); met=stats(vals,market_r,RF) if 'ALSI' in ASSETS else stats(vals,vals.PORTFOLIO.pct_change(fill_method=None),RF)
c1,c2,c3,c4=st.columns(4); c1.metric(f'{mode} Value',f"R{met['Ending Value']:,.0f}"); c2.metric(f'{mode} CAGR',f"{met['CAGR']:.2%}"); c3.metric(f'Sharpe ({RF:.2%} RF)',f"{met['Sharpe Ratio']:.3f}"); c4.metric('Max Drawdown',f"{met['Maximum Drawdown']:.2%}")
st.subheader(f'{mode} Analytics'); st.dataframe(metric_table(met),hide_index=True,use_container_width=True)
p=vals.PORTFOLIO; r=p.pct_change(fill_method=None).dropna(); growth=p/p.iloc[0]*100; dd=(p/p.cummax()-1)*100; roll_ret=((1+r).rolling(12).apply(np.prod,raw=True)-1)*100; roll_vol=r.rolling(12).std()*np.sqrt(12)*100; ex=r-((1+RF)**(1/12)-1); roll_sr=ex.rolling(36).mean()/ex.rolling(36).std()*np.sqrt(12)
line_chart({mode:p},f'{mode} — Portfolio Value','ZAR'); line_chart({mode:growth},f'{mode} — Growth of R100','Value'); line_chart({'Drawdown':dd},f'{mode} — Portfolio Drawdown','%'); bar=go.Figure(go.Bar(x=r.index,y=r.values*100)); bar.update_layout(title=f'{mode} — Monthly Portfolio Total Returns',yaxis_title='Total Return (%)'); st.plotly_chart(bar,use_container_width=True); line_chart({'12M Total Return':roll_ret},f'{mode} — Rolling 12-Month Total Return','%'); line_chart({'12M Volatility':roll_vol},f'{mode} — Rolling 12-Month Annualised Volatility','%'); line_chart({'36M Sharpe':roll_sr},f'{mode} — Rolling 36-Month Sharpe Ratio','Sharpe'); line_chart({c0:vals[c0] for c0 in ASSETS},f'{mode} — Portfolio Sleeve Values','ZAR')
st.subheader(f'{mode} Annual Total Returns'); ar=annual_returns(vals); ar['Annual Total Return']=ar['Annual Total Return'].map(lambda x:f'{x:.2%}'); st.dataframe(ar,hide_index=True,use_container_width=True)
st.subheader('Annual Total Return by Asset Class'); aar=annual_asset_returns(prices,divs,ASSETS)
for c0 in ASSETS: aar[c0]=aar[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
st.dataframe(aar,hide_index=True,use_container_width=True)
weights_end=vals[ASSETS].div(vals.PORTFOLIO,axis=0); wt=pd.DataFrame({'Asset':ASSETS,'Initial Weight':[weights[a0] for a0 in ASSETS],'Ending Weight':weights_end.iloc[-1].values}); wt['Initial Weight']=wt['Initial Weight'].map(lambda x:f'{x:.2%}'); wt['Ending Weight']=wt['Ending Weight'].map(lambda x:f'{x:.2%}'); st.subheader(f'{mode} Portfolio Weights'); st.dataframe(wt,hide_index=True,use_container_width=True)
st.divider(); st.subheader('Buy & Hold vs Annual Rebalancing'); line_chart({'Buy & Hold':bh.PORTFOLIO,'Annual Rebalanced':rb.PORTFOLIO},'Portfolio Value Comparison','ZAR'); bhm=stats(bh,market_r if 'ALSI' in ASSETS else bh.PORTFOLIO.pct_change(),RF); rbm=stats(rb,market_r if 'ALSI' in ASSETS else rb.PORTFOLIO.pct_change(),RF); st.dataframe(pd.DataFrame({'Buy & Hold':metric_table(bhm).set_index('Metric').Value,'Annual Rebalanced':metric_table(rbm).set_index('Metric').Value}),use_container_width=True)
st.divider(); st.subheader('Asset Correlation'); corr=asset_r[ASSETS].dropna().corr(); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); stacked=corr.where(mask).stack(); net_corr=float(stacked.mean()) if len(stacked) else np.nan; st.metric('Net Inter-Asset Correlation','N/A' if not np.isfinite(net_corr) else f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title='Pearson Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)
if 'ALSI' in ASSETS:
 st.divider(); st.subheader(f'{mode} — Beta & Alpha Evolution vs ALSI'); roll_beta,roll_alpha=rolling_capm(vals,market_r,RF); line_chart({'36M Rolling Beta':roll_beta},f'{mode} — 36-Month Rolling Beta vs ALSI','Beta'); line_chart({'36M Rolling Alpha':roll_alpha*100},f'{mode} — 36-Month Rolling Annualised CAPM Alpha','Alpha (%)')

st.divider(); st.subheader('Macro Tracker — FX Attribution to Total Return')
fxa=fx_attribution(full_l.reindex(prices.index),full_fx.reindex(prices.index),prices,divs,ASSETS)
if len(fxa):
 for c0 in fxa.columns[1:]: fxa[c0]=fxa[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
 st.dataframe(fxa,hide_index=True,use_container_width=True); st.caption('Attribution shares reconcile underlying appreciation + FX translation + interaction + cash distributions to each foreign asset’s total ZAR return. FX contribution is therefore shown as a percentage of total return, not merely as the standalone FX return.')
else: st.caption('No foreign-currency assets selected.')

st.divider()
with st.expander('Show workings in LaTeX',expanded=False):
 st.header('Full Calculation Workings')
 st.latex(r'P^{ZAR}_{a,t}=P^{local}_{a,t}\times FX_t')
 st.latex(r'D^{ZAR}_{a,t}=D^{local}_{a,t}\times FX_t')
 st.latex(r'r_{a,t}=\frac{P_{a,t}-P_{a,t-1}+D_{a,t}}{P_{a,t-1}}')
 st.latex(r'n_{a,0}=\frac{w_a V_0}{P_{a,0}}')
 st.latex(r'V^{cash}_{a,t}=n_{a,t}P_{a,t}+C_{a,t},\quad C_{a,t}=C_{a,t-1}+n_{a,t}D_{a,t}')
 st.latex(r'n^{reinv}_{a,t}=n_{a,t-1}+\frac{n_{a,t-1}D_{a,t}}{P_{a,t}}')
 st.latex(r'V_t=\sum_a V_{a,t}')
 st.latex(r'R=\frac{V_T}{V_0}-1,\qquad CAGR=\left(\frac{V_T}{V_0}\right)^{1/Y}-1')
 st.latex(r'\sigma_{ann}=\sigma_m\sqrt{12},\qquad r_{f,m}=(1+r_f)^{1/12}-1')
 st.latex(r'Sharpe=\frac{\overline{r_p-r_{f,m}}}{\sigma(r_p-r_{f,m})}\sqrt{12}')
 st.latex(r'DD_t=\frac{V_t}{\max_{s\le t}V_s}-1,\qquad MDD=\min_t DD_t')
 st.latex(r'\beta=\frac{Cov(r_p-r_f,r_m-r_f)}{Var(r_m-r_f)},\qquad \alpha_m=\overline{r_p-r_f}-\beta\overline{r_m-r_f}')
 st.latex(r'1+R_{ZAR}=(1+R_{local})(1+R_{FX})')
 st.latex(r'R_{ZAR}=R_{local}+R_{FX}+R_{local}R_{FX}+R_{cash}')
 st.latex(r'FX\ attribution\ \%=\frac{R_{FX}}{R_{ZAR}},\quad Underlying\ attribution\ \%=\frac{R_{local}}{R_{ZAR}}')
 st.markdown('The displayed FX attribution also reports the interaction and cash-distribution shares so the components reconcile to 100% of total ZAR return.')

with st.expander('Data Audit Report',expanded=False):
 st.write('**Data connections** — Yahoo Finance raw Close/actions for market assets and FX; repository GOVI monthly series for SA government bonds; STXGVI continuation after the authoritative GOVI cutoff.')
 st.write('**Corporate actions** — Adjusted Close is not used. Yahoo Close is treated as already split-normalised; split events are therefore not applied again. Cash dividends/distributions are explicit and follow the selected reinvestment setting.')
 st.write(f"**SA bond interpolation / instrument change** — GOVI is authoritative through {bond_validation['last_govi']:%d %b %Y}; thereafter the series is extended using fixed STXGVI units plus explicit STXGVI cash distributions. This is an instrument continuation, not hidden price interpolation.")
 st.write('**Common coverage** — all tests use the same selected assets and same common configured date window. If the requested history predates common availability, the backtest is shortened and explicitly flagged above.')
 st.write('**Validation concerns requiring deeper inspection** — Yahoo source revisions/corporate-action corrections; ETF distribution unit conventions; instrument-proxy basis around the GOVI/STXGVI splice; and any period return exceeding the hard monthly sanity threshold.')
 st.write('**Accounting checks** — starting nominal reconciles; sleeve values sum to portfolio value; monthly total-return identity is checked; implausible monthly asset moves stop the run rather than being bypassed.')
