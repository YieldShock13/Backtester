from pathlib import Path
p=Path('app.py'); s=p.read_text()
# 1) portfolio engine: explicit FX hedge cash P&L overlay
old="def portfolio_values(prices,divs,alloc,reinvest,rebalance=False):\n assets=list(alloc); target=pd.Series(alloc,dtype=float)/sum(alloc.values()); units=pd.Series({a:alloc[a]/float(prices[a].iloc[0]) for a in assets}); cash=pd.Series(0.0,index=assets)\n v=pd.DataFrame(index=prices.index,columns=assets,dtype=float); v.iloc[0]=pd.Series(alloc)\n for i in range(1,len(prices)):\n  dt=prices.index[i]; prev=prices.index[i-1]\n  if rebalance and dt.year!=prev.year:\n   total=(units*prices.loc[prev,assets]+cash).sum(); units=(target*total)/prices.loc[prev,assets]; cash[:]=0.0\n  flows=units*divs.loc[dt,assets]\n  if reinvest: units=units+flows/prices.loc[dt,assets]\n  else: cash=cash+flows\n  v.loc[dt,assets]=units*prices.loc[dt,assets]+cash\n v['PORTFOLIO']=v[assets].sum(axis=1); return v\n"
new="def portfolio_values(prices,divs,alloc,reinvest,rebalance=False,hedge_returns=None):\n assets=list(alloc); target=pd.Series(alloc,dtype=float)/sum(alloc.values()); units=pd.Series({a:alloc[a]/float(prices[a].iloc[0]) for a in assets}); cash=pd.Series(0.0,index=assets)\n v=pd.DataFrame(index=prices.index,columns=assets,dtype=float); v.iloc[0]=pd.Series(alloc)\n hedge_returns=hedge_returns if hedge_returns is not None else pd.DataFrame(0.0,index=prices.index,columns=assets)\n hedge_returns=hedge_returns.reindex(index=prices.index,columns=assets,fill_value=0.0).fillna(0.0)\n for i in range(1,len(prices)):\n  dt=prices.index[i]; prev=prices.index[i-1]\n  if rebalance and dt.year!=prev.year:\n   total=(units*prices.loc[prev,assets]+cash).sum(); units=(target*total)/prices.loc[prev,assets]; cash[:]=0.0\n  prev_exposure=units*prices.loc[prev,assets]\n  hedge_pnl=prev_exposure*hedge_returns.loc[dt,assets]\n  flows=units*divs.loc[dt,assets]\n  if reinvest: units=units+flows/prices.loc[dt,assets]\n  else: cash=cash+flows\n  cash=cash+hedge_pnl\n  v.loc[dt,assets]=units*prices.loc[dt,assets]+cash\n v['PORTFOLIO']=v[assets].sum(axis=1); return v\n"
assert old in s; s=s.replace(old,new,1)
# 2) helper functions before macro loader
anchor="@st.cache_data(ttl=3600,show_spinner=False)\ndef load_macro_factors(daily_mode):"
fx=r'''@st.cache_data(ttl=3600,show_spinner=False)
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

'''
s=s.replace(anchor,fx+anchor,1)
# 3) config immediately after asset selection, before weights/data
anchor="st.session_state.selected_assets=ASSETS\nif not ASSETS: st.error('Select at least one asset.'); st.stop()\nst.markdown('**Weights**')"
replacement="""st.session_state.selected_assets=ASSETS
if not ASSETS: st.error('Select at least one asset.'); st.stop()
st.markdown('**FX Hedging**')
fxc1,fxc2=st.columns(2)
with fxc1: FX_HEDGED=st.toggle('FX hedged',value=False)
with fxc2: BASE_CCY=st.selectbox('Portfolio / base currency',['ZAR','USD','EUR','GBP','JPY','CHF','AUD','CAD'],index=0,disabled=not FX_HEDGED)
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
st.markdown('**Weights**')"""
assert anchor in s; s=s.replace(anchor,replacement,1)
# 4) estimate hedge after validated prices, before portfolio construction
old="  if len(bad): raise RuntimeError('Implausible asset return(s): '+', '.join(f'{k}={v:.1%}' for k,v in bad.items()))\n  bh=portfolio_values(prices,divs,ALLOC,REINVEST,False); rb=portfolio_values(prices,divs,ALLOC,REINVEST,True)"
new="  if len(bad): raise RuntimeError('Implausible asset return(s): '+', '.join(f'{k}={v:.1%}' for k,v in bad.items()))\n  fx_hedge_returns=pd.DataFrame(0.0,index=prices.index,columns=ASSETS); fx_hedge_report=pd.DataFrame()\n  if FX_HEDGED and HEDGED_ASSETS:\n   fx_hedge_returns,fx_hedge_report=estimate_fx_hedges(prices,divs,HEDGED_ASSETS,FX_PAIRS,daily_mode)\n  bh=portfolio_values(prices,divs,ALLOC,REINVEST,False,fx_hedge_returns); rb=portfolio_values(prices,divs,ALLOC,REINVEST,True,fx_hedge_returns)"
assert old in s; s=s.replace(old,new,1)
# 5) caption and visible report
old="frequency='daily' if daily_mode else 'month-end'; st.caption(f'Configured window {prices.index[0]:%d %b %Y} to {prices.index[-1]:%d %b %Y} | {frequency} observations | Nominal {INITIAL:,.0f} | RF {RF:.2%} | Dividends '+('reinvested' if REINVEST else 'retained as cash'))"
new="frequency='daily' if daily_mode else 'month-end'; st.caption(f'Configured window {prices.index[0]:%d %b %Y} to {prices.index[-1]:%d %b %Y} | {frequency} observations | Nominal {INITIAL:,.0f} | RF {RF:.2%} | Dividends '+('reinvested' if REINVEST else 'retained as cash')+(' | FX beta hedge active' if FX_HEDGED and HEDGED_ASSETS else ' | FX unhedged'))\nif FX_HEDGED and HEDGED_ASSETS and not fx_hedge_report.empty:\n st.subheader('FX Beta Hedge — In-Sample Estimates'); fxshow=fx_hedge_report.copy(); fxshow['Alpha (periodic)']=fxshow['Alpha (periodic)'].map(lambda x:f'{x:.4%}'); fxshow['FX Beta / Hedge Ratio']=fxshow['FX Beta / Hedge Ratio'].map(lambda x:f'{x:.4f}'); fxshow['R²']=fxshow['R²'].map(lambda x:f'{x:.4f}'); st.dataframe(fxshow,hide_index=True,use_container_width=True)"
assert old in s; s=s.replace(old,new,1)
# 6) LaTeX: insert before macro scenario section if available
needle=" st.header('21. Return attribution by instrument')"
latex=r''' st.header('21. FX beta hedging')
 st.latex(r'r_{i,t}=\alpha_i+\beta_{FX,i}r_{FX,t}+\epsilon_{i,t}')
 st.latex(r'\hat\beta_{FX,i}=\frac{\operatorname{Cov}(r_i,r_{FX})}{\operatorname{Var}(r_{FX})}')
 st.latex(r'h_{i,t}=-\hat\beta_{FX,i}r_{FX,t},\qquad P\&L^{hedge}_{i,t}=V_{i,t-1}^{market}h_{i,t}')
 st.latex(r'V^{hedged}_{i,t}=q_{i,t}P_{i,t}+C_{i,t}+P\&L^{hedge}_{i,t}')
 st.write('The FX beta is estimated in-sample over the currently configured common backtest window and is recalculated whenever the window, selected asset, frequency, or FX pair changes. The hedge is applied as a cash-settled return overlay to the prior-period market exposure; distributions remain explicit and are not replaced by Adjusted Close.')
 st.write(f'Base currency: {BASE_CCY}; FX hedge enabled: {FX_HEDGED}; hedged assets: {HEDGED_ASSETS}.')
 if FX_HEDGED and HEDGED_ASSETS and not fx_hedge_report.empty: st.dataframe(fx_hedge_report,hide_index=True,use_container_width=True)
 st.header('22. Return attribution by instrument')'''
if needle in s: s=s.replace(needle,latex,1)
# renumber final header if present
s=s.replace("st.header('22. Complete configured metric output')","st.header('23. Complete configured metric output')")
# 7) data audit detail
needle="st.header('Potential Validation Concerns')"
if needle in s:
 s=s.replace(needle,"st.header('FX Hedge Audit')\n st.write('FX hedge methodology: raw reconstructed asset total returns are regressed in-sample on the selected FX pair periodic returns. Hedge ratio equals estimated FX beta. Hedge P&L is -beta × FX return × prior-period asset market exposure and settles to sleeve cash. No hedge is inferred for assets the user did not explicitly select. Pair, sample, beta, alpha and R² are disclosed in Show LaTeX.')\n if FX_HEDGED and HEDGED_ASSETS and not fx_hedge_report.empty: st.dataframe(fx_hedge_report,hide_index=True,use_container_width=True)\n st.header('Potential Validation Concerns')",1)
p.write_text(s)
