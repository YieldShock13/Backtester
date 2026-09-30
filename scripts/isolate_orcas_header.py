from pathlib import Path
import runpy

s=Path('app.py').read_text()
if "st.segmented_control('Currency'" not in s: runpy.run_path('scripts/final_currency_audit_patch.py',run_name='__main__')
s=Path('app.py').read_text()
if "Search benchmark" not in s: runpy.run_path('scripts/final_benchmark_macro_patch.py',run_name='__main__')
p=Path('app.py'); s=p.read_text()
s=s.replace("'Beta vs ALSI':beta","'Beta vs Benchmark':beta").replace("met[\"Beta vs ALSI\"]","met[\"Beta vs Benchmark\"]").replace("st.write(f'Benchmark={BENCHMARK_TICKER}; current beta=","st.write(f'Benchmark={BENCHMARK}; current beta=").replace("| Nominal {INITIAL:,.0f} | RF","| Nominal {PORTFOLIO_CCY} {INITIAL:,.0f} | RF")
s=s.replace("h=yf.Ticker(ticker).history(start=START,auto_adjust=False,actions=True)","h=yf.Ticker(ticker).history(start=START,interval='1d',auto_adjust=False,actions=True)")
s=s.replace("frequency='daily' if daily_mode else 'month-end'","frequency='weekly (Friday-labelled; last available trading close)'").replace("roll_n=252 if daily_mode else 12; sharpe_n=756 if daily_mode else 36","roll_n=52; sharpe_n=156")
p.write_text(s)
s=p.read_text()
if "USE_BENCHMARK=st.toggle('Use benchmark'" not in s or "benchmark_overlap_start=max(prices.index.min(),bench_valid.index.min())" not in s: runpy.run_path('scripts/expand_history_walkforward.py',run_name='__main__')
s=Path('app.py').read_text()
if ("Portfolio leverage (x)" not in s or "Correlation measure" not in s or "Negative weight = short position" not in s or "with st.expander('Full Disclaimer'" not in s): runpy.run_path('scripts/final_short_leverage_spearman_patch.py',run_name='__main__')
s=Path('app.py').read_text()
if "st.selectbox('Rebalancing frequency',['Annual','Semi-Annual','Quarterly','Monthly','Weekly']" not in s: runpy.run_path('scripts/rebalancing_frequency_patch.py',run_name='__main__')
s=Path('app.py').read_text()
if "LaTeX / Diagnostics" not in s and "Linearity Test: Show LaTeX" not in s: runpy.run_path('scripts/correlation_diagnostics_patch.py',run_name='__main__')
s=Path('app.py').read_text()
if "Align by portfolio week, not exact timestamp" not in s: runpy.run_path('scripts/fix_fx_weekly_alignment.py',run_name='__main__')
# Always apply the final naming pass so an already-deployed diagnostics block is renamed.
runpy.run_path('scripts/rename_linearity_labels.py',run_name='__main__')
s=p.read_text()
for required in ["ORCA'S","Benchmark (optional)","Negative weight = short position","Portfolio leverage (x)","Correlation measure","['Pearson','Spearman']","Average Inter-Asset {corr_method} Correlation","with st.expander('Full Disclaimer'","st.selectbox('Rebalancing frequency',['Annual','Semi-Annual','Quarterly','Monthly','Weekly']","Linearity Test: Show LaTeX","Linearity Test — Methodology & Results","This linearity test examines whether each asset-pair return relationship","Linearity flag:","Align by portfolio week, not exact timestamp","same-week aligned observations"]:
 assert required in s,required
assert "st.button('LaTeX / Diagnostics'" not in s
assert "@st.dialog('Correlation Diagnostics & LaTeX'" not in s
assert 'START="2012-02-01"' not in s
