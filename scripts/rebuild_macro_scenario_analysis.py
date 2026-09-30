from pathlib import Path
p=Path('app.py'); s=p.read_text()
# Replace old conditional-observation stats with event-based historical scenario helpers.
a=s.index('def macro_scenario_stats(')
b=s.index('\ntitle_col, report_col1',a)
new=r'''def _conditional_capm(period_returns,market_returns,rf,ppy):
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
'''
s=s[:a]+new+s[b:]
# Replace macro UI/calculation block only.
a=s.index("st.divider(); st.subheader('Macro Risk & Conditional Performance')")
b=s.index("\n@st.dialog('Complete Quantitative Workings'",a)
new=r'''st.divider(); st.subheader('Macro Risk & Historical Scenario Analysis')
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
'''
s=s[:a]+new+s[b:]
# Update LaTeX terminology/equations without disturbing other sections.
s=s.replace("st.header('Macro scenario methodology')","st.header('Macro historical scenario methodology')")
s=s.replace("Historical conditional regimes", "Historical event scenarios")
p.write_text(s)
