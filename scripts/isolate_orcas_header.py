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
# FRED CSV currently exposes its observation date as 'observation_date', not always 'DATE'.
s=s.replace("hy['DATE']=pd.to_datetime(hy['DATE']); hy['BAMLH0A0HYM2']=pd.to_numeric(hy['BAMLH0A0HYM2'],errors='coerce')\n hx=hy.set_index('DATE')['BAMLH0A0HYM2'].dropna().sort_index()", "date_col='DATE' if 'DATE' in hy.columns else 'observation_date' if 'observation_date' in hy.columns else hy.columns[0]\n hy[date_col]=pd.to_datetime(hy[date_col],errors='coerce'); hy['BAMLH0A0HYM2']=pd.to_numeric(hy['BAMLH0A0HYM2'],errors='coerce')\n hx=hy.dropna(subset=[date_col]).set_index(date_col)['BAMLH0A0HYM2'].dropna().sort_index()")
p.write_text(s)

s=p.read_text()
assert '.orca-hero{' in s and "ORCA'S" in s
for forbidden in ['.stApp{','[data-testid="stHeader"]{','[data-testid="stToolbar"]{','[data-testid="stMetric"]{','.stButton>button{']:
    assert forbidden not in s, forbidden
for required in ["st.segmented_control('Currency'","Complete audit checks","Search benchmark","Oil +3σ Shock","US HY OAS +2σ Widening","benchmark_scenario_stats","Beta vs Benchmark","Benchmark={BENCHMARK}","Pearson Correlation Matrix","Show LaTeX","observation_date"]:
    assert required in s, required
