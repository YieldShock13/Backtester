from pathlib import Path
p=Path('app.py'); s=p.read_text()
# Remove only global/theme selectors that leak beyond the hero. Preserve the animated hero itself.
repls={
':root{--orca-bg:#06111f;--orca-panel:#0a1929;--orca-line:#16314b;--orca-blue:#43a9ff;--orca-ice:#d9efff;--orca-text:#eaf4ff;--orca-muted:#8fa8bf}\n':'',
'.stApp{background:linear-gradient(180deg,#06111f 0,#081522 24rem,#f7f9fc 24rem,#f7f9fc 100%)}\n':'',
'[data-testid="stHeader"]{background:rgba(5,14,25,.82);backdrop-filter:blur(12px)}\n':'',
'[data-testid="stToolbar"]{color:#d9efff}\n':'',
'/* retain Streamlit usability below the branded shell */\n[data-testid="stMetric"]{border-radius:10px}\n.stButton>button{border-radius:8px}\n':'',
}
for old,new in repls.items():
 assert old in s, f'Expected theme selector not found: {old[:40]}'
 s=s.replace(old,new,1)
# Guardrails: branding stays; global analytics styling is gone.
assert '.orca-hero{' in s and 'ORCA\'S' in s and '@keyframes orcaFloat' in s
for forbidden in ['.stApp{','[data-testid="stHeader"]{','[data-testid="stToolbar"]{','[data-testid="stMetric"]{','.stButton>button{']:
 assert forbidden not in s, forbidden
p.write_text(s)
