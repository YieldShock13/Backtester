from pathlib import Path
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
if old not in s:
 raise RuntimeError('portfolio_values block not found')
s=s.replace(old,new)
old="""  bh=portfolio_values(prices,divs,ALLOC,REINVEST,False,fx_hedge_returns); rb=portfolio_values(prices,divs,ALLOC,REINVEST,True,fx_hedge_returns)
"""
new="""  bh=portfolio_values(prices,divs,ALLOC,REINVEST,None,fx_hedge_returns)
"""
if old not in s:
 raise RuntimeError('portfolio build block not found')
s=s.replace(old,new)
old="""mode=st.radio('Backtest mode',['Buy & Hold','Annual Rebalanced'],horizontal=True,index=0); vals=(bh if mode=='Buy & Hold' else rb).copy()
"""
new="""mode=st.selectbox('Backtest mode',['Buy & Hold','Rebalanced'],index=0,key='backtest_mode')
if mode=='Rebalanced':
 rebalance_frequency=st.selectbox('Rebalancing frequency',['Annual','Semi-Annual','Quarterly','Monthly','Weekly'],index=0,key='rebalance_frequency',help='Portfolio is reset to the configured target weights at the first available weekly observation of each selected rebalance period.')
 vals=portfolio_values(prices,divs,ALLOC,REINVEST,rebalance_frequency,fx_hedge_returns).copy()
 mode_label=f'{rebalance_frequency} Rebalanced'
else:
 rebalance_frequency=None; vals=bh.copy(); mode_label='Buy & Hold'
"""
if old not in s:
 raise RuntimeError('backtest mode block not found')
s=s.replace(old,new)
# User-facing headings/labels should show the selected rebalance frequency.
s=s.replace("f'{mode} Value'","f'{mode_label} Value'").replace("f'{mode} CAGR'","f'{mode_label} CAGR'")
s=s.replace("f'{mode} Analytics'","f'{mode_label} Analytics'").replace("f'{mode} Annual Total Returns'","f'{mode_label} Annual Total Returns'")
s=s.replace("f'{mode} Portfolio Weights'","f'{mode_label} Portfolio Weights'")
s=s.replace("{mode} —", "{mode_label} —")
s=s.replace("{mode}:p", "{mode_label}:p").replace("{mode:growth", "{mode_label}:growth")
# Keep report metadata explicit.
s=s.replace("| mode={mode}')", "| mode={mode_label}')")
p.write_text(s)
s=p.read_text()
for x in ["st.selectbox('Backtest mode',['Buy & Hold','Rebalanced']","st.selectbox('Rebalancing frequency',['Annual','Semi-Annual','Quarterly','Monthly','Weekly']","freq=='Weekly'","freq=='Monthly'","freq=='Quarterly'","freq=='Semi-Annual'","freq=='Annual'","mode_label=f'{rebalance_frequency} Rebalanced'"]:
 assert x in s,x
print('PASS: configurable rebalance frequency added')
