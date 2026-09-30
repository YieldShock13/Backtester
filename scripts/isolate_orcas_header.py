from pathlib import Path
import runpy

s=Path('app.py').read_text()
if "st.segmented_control('Currency'" not in s:
    runpy.run_path('scripts/final_currency_audit_patch.py', run_name='__main__')
s=Path('app.py').read_text()
if "Search benchmark" not in s:
    runpy.run_path('scripts/final_benchmark_macro_patch.py', run_name='__main__')

p=Path('app.py'); s=p.read_text()
s=s.replace("'Beta vs ALSI':beta","'Beta vs Benchmark':beta")
s=s.replace("met[\"Beta vs ALSI\"]","met[\"Beta vs Benchmark\"]")
s=s.replace("st.write(f'Benchmark={BENCHMARK_TICKER}; current beta=","st.write(f'Benchmark={BENCHMARK}; current beta=")
s=s.replace("| Nominal {INITIAL:,.0f} | RF", "| Nominal {PORTFOLIO_CCY} {INITIAL:,.0f} | RF")
s=s.replace("hy['DATE']=pd.to_datetime(hy['DATE']); hy['BAMLH0A0HYM2']=pd.to_numeric(hy['BAMLH0A0HYM2'],errors='coerce')\n hx=hy.set_index('DATE')['BAMLH0A0HYM2'].dropna().sort_index()", "date_col='DATE' if 'DATE' in hy.columns else 'observation_date' if 'observation_date' in hy.columns else hy.columns[0]\n hy[date_col]=pd.to_datetime(hy[date_col],errors='coerce'); hy['BAMLH0A0HYM2']=pd.to_numeric(hy['BAMLH0A0HYM2'],errors='coerce')\n hx=hy.dropna(subset=[date_col]).set_index(date_col)['BAMLH0A0HYM2'].dropna().sort_index()")
s=s.replace("h=yf.Ticker(ticker).history(start=START,auto_adjust=False,actions=True)","h=yf.Ticker(ticker).history(start=START,interval='1d',auto_adjust=False,actions=True)")
s=s.replace("mp=pd.DataFrame({x:v.resample('ME').last() for x,v in yp.items()}); md=pd.DataFrame({x:v.resample('ME').sum() for x,v in yd.items()})","mp=pd.DataFrame({x:v.resample('W-FRI').last() for x,v in yp.items()}); md=pd.DataFrame({x:v.resample('W-FRI').sum() for x,v in yd.items()})")
s=s.replace("if 'GOVI' in selected: mp['GOVI']=g.reindex(mp.index).ffill(); md['GOVI']=0.0","if 'GOVI' in selected: raise RuntimeError('Repository GOVI is monthly-only. For the weekly backtest select a Yahoo-traded bond/index proxy with daily history instead.')")
s=s.replace("custom_days=(pd.Timestamp(custom_end)-pd.Timestamp(custom_start)).days if timeline=='Custom' and custom_start and custom_end else None; daily_mode=timeline in SHORT_WINDOWS or (timeline=='Custom' and custom_days is not None and custom_days<=366); ppy=252 if daily_mode else 12","custom_days=(pd.Timestamp(custom_end)-pd.Timestamp(custom_start)).days if timeline=='Custom' and custom_start and custom_end else None; daily_mode=False; ppy=52")
s=s.replace("if daily_mode: full_p,full_d,govi,bond_validation,split_events=build_daily(ASSETS)\n  else: full_p,full_d,govi,bond_validation,split_events=build_master(ASSETS)","full_p,full_d,govi,bond_validation,split_events=build_master(ASSETS)")
s=s.replace("frequency='daily' if daily_mode else 'month-end'","frequency='weekly (Friday-labelled; last available trading close)'")
s=s.replace("roll_n=252 if daily_mode else 12; sharpe_n=756 if daily_mode else 36","roll_n=52; sharpe_n=156")
s=s.replace("if not daily_mode: x=x.resample('ME').last()","if not daily_mode: x=x.resample('W-FRI').last()")
s=s.replace("if not daily_mode: hx=hx.resample('ME').last()","if not daily_mode: hx=hx.resample('W-FRI').last()")
s=s.replace("fx=fp[pair].reindex(prices.index).ffill()","fx=fp[pair].resample('W-FRI').last().reindex(prices.index)")
p.write_text(s)

s=Path('app.py').read_text()
if "USE_BENCHMARK=st.toggle('Use benchmark'" not in s or "benchmark_overlap_start=max(prices.index.min(),bench_valid.index.min())" not in s:
    runpy.run_path('scripts/expand_history_walkforward.py', run_name='__main__')

s=Path('app.py').read_text()
if ("Portfolio leverage (x)" not in s or "Correlation measure" not in s or "Negative weight = short position" not in s or "with st.expander('Full Disclaimer'" not in s or "Average Inter-Asset {corr_method} Correlation" not in s):
    runpy.run_path('scripts/final_short_leverage_spearman_patch.py', run_name='__main__')

s=Path('app.py').read_text()
if "st.selectbox('Rebalancing frequency',['Annual','Semi-Annual','Quarterly','Monthly','Weekly']" not in s:
    runpy.run_path('scripts/rebalancing_frequency_patch.py', run_name='__main__')

s=Path('app.py').read_text()
if "Correlation Diagnostics & LaTeX" not in s:
    runpy.run_path('scripts/correlation_diagnostics_patch.py', run_name='__main__')

s=p.read_text()
assert '.orca-hero{' in s and "ORCA'S" in s
for forbidden in ['.stApp{','[data-testid="stHeader"]{','[data-testid="stToolbar"]{','[data-testid="stMetric"]{','.stButton>button{']:
    assert forbidden not in s, forbidden
for required in ["st.segmented_control('Currency'","Complete audit checks","Benchmark (optional)","USE_BENCHMARK=st.toggle('Use benchmark'","Oil +3σ Shock","US HY OAS +2σ Widening","Beta vs Benchmark","Show LaTeX","observation_date","interval='1d'","ppy=52","roll_n=52; sharpe_n=156","period='max'","Walk-Forward Validator — 52-Week Estimation Window","GARCH(1,1)","mutual_daily=daily_px.dropna(how='any')","benchmark_overlap_start=max(prices.index.min(),bench_valid.index.min())","Only those benchmark-dependent observations are dropped","Portfolio history begins","walk_forward_validation(vals,market_r if USE_BENCHMARK else None","Negative weight = short position","Portfolio leverage (x)","Annual leverage / financing cost (%)","Correlation measure","['Pearson','Spearman']","corr(method=corr_method.lower())","Average Inter-Asset {corr_method} Correlation","levered_r=LEVERAGE*base_r-(LEVERAGE-1.0)*weekly_financing","with st.expander('Full Disclaimer'","Nothing contained in or produced by this tool constitutes","st.selectbox('Backtest mode',['Buy & Hold','Rebalanced']","st.selectbox('Rebalancing frequency',['Annual','Semi-Annual','Quarterly','Monthly','Weekly']","mode_label=f'{rebalance_frequency} Rebalanced'","LaTeX / Diagnostics","Correlation Diagnostics & LaTeX","Quadratic ΔR²","Non-linearity flag","not a formal universal test or automatic selection rule"]:
    assert required in s, required
assert "auto_adjust=False,actions=True" in s
assert "['Adj Close']" not in s and '[\"Adj Close\"]' not in s
assert 'START="2012-02-01"' not in s
assert 'dropped_asset_weeks' not in s
assert "aligned_index=prices.index.intersection" not in s
assert "benchmark_missing_weeks=int(bp_all.reindex(prices.index).isna().sum())" not in s
assert "st.number_input(f'{a0} (%)',0.0,100.0" not in s
