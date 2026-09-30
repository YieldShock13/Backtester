from pathlib import Path
p=Path('app.py'); s=p.read_text()
needle="if not ASSETS: st.error('Select at least one asset.'); st.stop()\nst.markdown('**FX Hedging**')"
repl="""if not ASSETS: st.error('Select at least one asset.'); st.stop()
st.markdown('**Benchmark**')
if 'benchmark_symbol' not in st.session_state: st.session_state.benchmark_symbol=BENCHMARK_TICKER
if 'benchmark_name' not in st.session_state: st.session_state.benchmark_name='FTSE/JSE All Share Index'
benchmark_query=st.text_input('Search benchmark',placeholder='Search by index, ETF, fund or ticker',key='benchmark_search_query')
benchmark_results=search_assets(benchmark_query) if benchmark_query.strip() else []
if benchmark_results:
 benchmark_labels=[f\"{r['name']} — {r['symbol']}\" for r in benchmark_results]
 def _select_benchmark():
  picked=st.session_state.get('benchmark_search_pick')
  if picked is None: return
  row=benchmark_results[picked]; st.session_state.benchmark_symbol=row['symbol']; st.session_state.benchmark_name=row['name']
 st.pills('Benchmark search results',options=range(len(benchmark_results)),format_func=lambda i: benchmark_labels[i],selection_mode='single',key='benchmark_search_pick',on_change=_select_benchmark)
BENCHMARK=st.session_state.benchmark_symbol
st.caption(f\"Selected benchmark: {st.session_state.benchmark_name} — {BENCHMARK}\")
st.markdown('**FX Hedging**')"""
assert needle in s; s=s.replace(needle,repl,1)
old="bench_p,bench_d,_=load_ticker_components((BENCHMARK_TICKER,)); bp=bench_p[BENCHMARK_TICKER].reindex(prices.index).ffill(); bd=bench_d[BENCHMARK_TICKER].reindex(prices.index,fill_value=0.0); market_r=(bp-bp.shift(1)+bd)/bp.shift(1); met=stats(vals,market_r,RF,ppy)"
new="""if BENCHMARK=='GOVI':
 bp=load_govi_history().reindex(prices.index).ffill(); bd=pd.Series(0.0,index=prices.index)
else:
 bench_p,bench_d,_=load_ticker_components((BENCHMARK,)); bp=bench_p[BENCHMARK].reindex(prices.index).ffill(); bd=bench_d[BENCHMARK].reindex(prices.index,fill_value=0.0)
market_r=(bp-bp.shift(1)+bd)/bp.shift(1); met=stats(vals,market_r,RF,ppy)"""
assert old in s; s=s.replace(old,new,1)
s=s.replace("f'{mode} — Beta & Alpha Evolution vs {BENCHMARK_TICKER}'","f'{mode} — Beta & Alpha Evolution vs {BENCHMARK}'",1).replace("f'{mode} — Rolling Beta vs {BENCHMARK_TICKER}'","f'{mode} — Rolling Beta vs {BENCHMARK}'",1)
s=s.replace("def jse_drawdown_events(vals,market_price,threshold=-.10):","def benchmark_drawdown_events(vals,market_price,threshold=-.10):",1)
s=s.replace("def jse_scenario_stats(vals,market_price,rf,ppy):\n events=jse_drawdown_events(vals,market_price,-.10)\n if not events: return {'Scenario':'JSE −10% Drawdown','Historical Events':0}\n er=pd.DataFrame(events,columns=['Start','End','JSE Event Return','Portfolio Event Return'])","def benchmark_scenario_stats(vals,market_price,rf,ppy,benchmark_label):\n events=benchmark_drawdown_events(vals,market_price,-.10)\n label=f'{benchmark_label} −10% Drawdown'\n if not events: return {'Scenario':label,'Historical Events':0}\n er=pd.DataFrame(events,columns=['Start','End','Benchmark Event Return','Portfolio Event Return'])",1)
s=s.replace("'Scenario':'JSE −10% Drawdown'","'Scenario':label",1).replace("'Avg JSE Event Return':er['JSE Event Return'].mean()","'Avg Benchmark Event Return':er['Benchmark Event Return'].mean()",1).replace("'Avg JSE Event Return':e.M.mean()","'Avg Benchmark Event Return':e.M.mean()",1)
oldm="symbols={'Oil':'CL=F','VIX':'^VIX','MOVE':'^MOVE'}"
assert oldm in s; s=s.replace(oldm,"symbols={'Oil':'CL=F','VIX':'^VIX','MOVE':'^MOVE'}",1)
anchor="  out[name]=x.rename(name)\n return pd.DataFrame(out)"
insert="""  out[name]=x.rename(name)
 # ICE BofA US High Yield Index Option-Adjusted Spread (FRED BAMLH0A0HYM2), percent.
 hy=pd.read_csv('https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2')
 hy['DATE']=pd.to_datetime(hy['DATE']); hy['BAMLH0A0HYM2']=pd.to_numeric(hy['BAMLH0A0HYM2'],errors='coerce')
 hx=hy.set_index('DATE')['BAMLH0A0HYM2'].dropna().sort_index()
 if not daily_mode: hx=hx.resample('ME').last()
 out['HY OAS']=hx.rename('HY OAS')
 return pd.DataFrame(out)"""
assert anchor in s; s=s.replace(anchor,insert,1)
start=s.index("sc1,sc2,sc3,sc4=st.columns(4)")
end=s.index("scenario_df=pd.DataFrame(scenario_rows)",start)
newui="""bench_label=st.session_state.get('benchmark_name',BENCHMARK)
sc1,sc2,sc3,sc4,sc5=st.columns(5)
with sc1: use_bench=st.toggle(f'{BENCHMARK} −10% Drawdown',value=True,key='macro_benchmark')
with sc2: use_oil=st.toggle('Oil +3σ Shock',value=False,key='macro_oil')
with sc3: use_vix=st.toggle('VIX +2σ Shock',value=False,key='macro_vix')
with sc4: use_move=st.toggle('MOVE +1.5σ Shock',value=False,key='macro_move')
with sc5: use_hyoas=st.toggle('US HY OAS +2σ Widening',value=False,key='macro_hyoas')
scenario_rows=[]; macro_factor_meta=[]
if use_bench:
 scenario_rows.append(benchmark_scenario_stats(vals,bp,RF,ppy,BENCHMARK))
 macro_factor_meta.append({'Scenario':f'{BENCHMARK} −10% Drawdown','Factor':BENCHMARK,'Event':'previous peak → first crossing of −10% drawdown','Threshold':'≤ −10%'})
if use_oil or use_vix or use_move or use_hyoas:
 try:
  mf=load_macro_factors(daily_mode).reindex(prices.index).ffill()
  for name,use,zcut,label,transform in [('Oil',use_oil,3.0,'Oil +3σ Shock','pct'),('VIX',use_vix,2.0,'VIX +2σ Shock','pct'),('MOVE',use_move,1.5,'MOVE +1.5σ Shock','pct'),('HY OAS',use_hyoas,2.0,'US HY OAS +2σ Widening','diff')]:
   if not use: continue
   chg=mf[name].diff() if transform=='diff' else mf[name].pct_change(fill_method=None)
   mu=chg.mean(); sig=chg.std(); threshold=mu+zcut*sig
   scenario_rows.append(one_period_shock_stats(vals,bp,chg,threshold,RF,ppy,label))
   macro_factor_meta.append({'Scenario':label,'Factor':name,'Event':'single configured observation interval','Transformation':'percentage-point change' if transform=='diff' else 'percentage change','Mean':mu,'Std Dev':sig,'Threshold':threshold})
 except Exception as e:
  st.warning(f'Macro factor data unavailable for selected scenario(s): {e}')
"""
s=s[:start]+newui+s[end:]
s=s.replace("'Avg JSE Event Return'","'Avg Benchmark Event Return'")
for req in ["PORTFOLIO_CCY=st.segmented_control","Complete audit checks","Pearson Correlation Matrix","Show LaTeX","FX Beta Hedge","ORCA'S","Oil +3σ Shock","US HY OAS +2σ Widening","benchmark_scenario_stats"]: assert req in s,req
p.write_text(s)
