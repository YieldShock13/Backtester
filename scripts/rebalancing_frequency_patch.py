from pathlib import Path
import py_compile
p=Path('app.py')
s=p.read_text()
old="""def portfolio_values(prices,divs,alloc,reinvest,rebalance=False,hedge_returns=None):
 assets=list(alloc); target=pd.Series(alloc,dtype=float)/sum(alloc.values()); units=pd.Series({a:alloc[a]/float(prices[a].iloc[0]) for a in assets}); cash=pd.Series(0.0,index=assets)
 v=pd.DataFrame(index=prices.index,columns=assets,dtype=float); v.iloc[0]=pd.Series(alloc)
 hedge_returns=hedge_returns if hedge_returns is not None else pd.DataFrame(0.0,index=prices.index,columns=assets)
 hedge_returns=hedge_returns.reindex(index=prices.index,columns=assets,fill_value=0.0).fillna(0.0)
 for i in range(1,len(prices)):
  dt=prices.index[i]; prev=prices.index[i-1]
  if rebalance and dt.year!=prev.year:
   total=(units*prices.loc[prev,assets]+cash).sum(); units=(target*total)/prices.loc[prev,assets]; cash[:]=0.0
"""
new="""def portfolio_values(prices,divs,alloc,reinvest,rebalance_frequency=None,hedge_returns=None):
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
"""
if old not in s: raise RuntimeError('portfolio_values block not found')
s=s.replace(old,new)
old="  bh=portfolio_values(prices,divs,ALLOC,REINVEST,False,fx_hedge_returns); rb=portfolio_values(prices,divs,ALLOC,REINVEST,True,fx_hedge_returns)\n"
new="  bh=portfolio_values(prices,divs,ALLOC,REINVEST,None,fx_hedge_returns)\n"
if old not in s: raise RuntimeError('portfolio build block not found')
s=s.replace(old,new)
old="mode=st.radio('Backtest mode',['Buy & Hold','Annual Rebalanced'],horizontal=True,index=0); vals=(bh if mode=='Buy & Hold' else rb).copy()\n"
new="""mode=st.selectbox('Backtest mode',['Buy & Hold','Rebalanced'],index=0,key='backtest_mode')
if mode=='Rebalanced':
 rebalance_frequency=st.selectbox('Rebalancing frequency',['Annual','Semi-Annual','Quarterly','Monthly','Weekly'],index=0,key='rebalance_frequency',help='Portfolio is reset to the configured target weights at the first available weekly observation of each selected rebalance period.')
 vals=portfolio_values(prices,divs,ALLOC,REINVEST,rebalance_frequency,fx_hedge_returns).copy()
 mode_label=f'{rebalance_frequency} Rebalanced'
else:
 rebalance_frequency=None; vals=bh.copy(); mode_label='Buy & Hold'
"""
if old not in s: raise RuntimeError('backtest mode block not found')
s=s.replace(old,new)
# Replace only user-facing f-string labels; do not rewrite dictionary syntax.
for a,b in [
 ("f'{mode} Value'","f'{mode_label} Value'"),
 ("f'{mode} CAGR'","f'{mode_label} CAGR'"),
 ("f'{mode} Analytics'","f'{mode_label} Analytics'"),
 ("f'{mode} Annual Total Returns'","f'{mode_label} Annual Total Returns'"),
 ("f'{mode} Portfolio Weights'","f'{mode_label} Portfolio Weights'"),
 ("f'{mode} — Portfolio Value'","f'{mode_label} — Portfolio Value'"),
 ("f'{mode} — Growth of 100'","f'{mode_label} — Growth of 100'"),
 ("f'{mode} — Portfolio Drawdown'","f'{mode_label} — Portfolio Drawdown'"),
 ("f'{mode} — Rolling 1-Year Total Return'","f'{mode_label} — Rolling 1-Year Total Return'"),
 ("f'{mode} — Rolling 1-Year Annualised Volatility'","f'{mode_label} — Rolling 1-Year Annualised Volatility'"),
 ("f'{mode} — Rolling 3-Year Sharpe Ratio'","f'{mode_label} — Rolling 3-Year Sharpe Ratio'"),
 ("f'{mode} — Portfolio Sleeve Values'","f'{mode_label} — Portfolio Sleeve Values'"),
 ("f'{mode} — Beta & Alpha Evolution vs {BENCHMARK}'","f'{mode_label} — Beta & Alpha Evolution vs {BENCHMARK}'"),
 ("| mode={mode}')","| mode={mode_label}')")]:
 s=s.replace(a,b)
# Legend dictionaries need valid string keys.
s=s.replace("line_chart({mode:p},", "line_chart({mode_label:p},")
s=s.replace("line_chart({mode:growth},", "line_chart({mode_label:growth},")
p.write_text(s)
# Fail inside the patch itself before the workflow can ever reach commit if generated code is invalid.
py_compile.compile(str(p),doraise=True)
s=p.read_text()
for x in ["st.selectbox('Backtest mode',['Buy & Hold','Rebalanced']","st.selectbox('Rebalancing frequency',['Annual','Semi-Annual','Quarterly','Monthly','Weekly']","freq=='Weekly'","freq=='Monthly'","freq=='Quarterly'","freq=='Semi-Annual'","freq=='Annual'","mode_label=f'{rebalance_frequency} Rebalanced'","line_chart({mode_label:p}","line_chart({mode_label:growth}"]:
 assert x in s,x
print('PASS: configurable rebalance frequency added and generated app compiles')
