from pathlib import Path
import runpy

# Apply the existing currency/audit patch idempotently only when not already present.
s = Path('app.py').read_text()
if "st.segmented_control('Currency'" not in s:
    runpy.run_path('scripts/final_currency_audit_patch.py', run_name='__main__')

# Final benchmark and macro-risk extension.
runpy.run_path('scripts/final_benchmark_macro_patch.py', run_name='__main__')

s = Path('app.py').read_text()
assert '.orca-hero{' in s and "ORCA'S" in s and '@keyframes orcaFloat' in s
for forbidden in ['.stApp{','[data-testid="stHeader"]{','[data-testid="stToolbar"]{','[data-testid="stMetric"]{','.stButton>button{']:
    assert forbidden not in s, forbidden
for required in ["st.segmented_control('Currency'","Complete audit checks","Search benchmark","Oil +3σ Shock","US HY OAS +2σ Widening","benchmark_scenario_stats","Pearson Correlation Matrix","Show LaTeX"]:
    assert required in s, required
