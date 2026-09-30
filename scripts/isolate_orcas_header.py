from pathlib import Path
import runpy

# Preserve the header-only Orca branding and apply the validated final UI/audit patch.
# Updating this file intentionally triggers the existing deployment workflow.
runpy.run_path('scripts/final_currency_audit_patch.py', run_name='__main__')

s = Path('app.py').read_text()
assert '.orca-hero{' in s and "ORCA'S" in s and '@keyframes orcaFloat' in s
for forbidden in ['.stApp{','[data-testid="stHeader"]{','[data-testid="stToolbar"]{','[data-testid="stMetric"]{','.stButton>button{']:
    assert forbidden not in s, forbidden
assert "st.segmented_control('Currency'" in s
assert "PORTFOLIO_CCY" in s
assert "Full Data Audit" in s
assert "Flags requiring attention" in s
assert "Complete audit checks" in s
