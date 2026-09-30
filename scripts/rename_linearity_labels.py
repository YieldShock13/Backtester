from pathlib import Path
import py_compile
p=Path('app.py')
s=p.read_text()
replacements={
    "st.button('LaTeX / Diagnostics'":"st.button('Linearity Test: Show LaTeX'",
    "@st.dialog('Correlation Diagnostics & LaTeX'":"@st.dialog('Linearity Test — Methodology & Results'",
    "Pearson measures linear association. Spearman measures monotonic association after ranking observations. The diagnostics below do not mechanically choose a coefficient; they flag cases where a simple linear description may be inadequate.":"This linearity test examines whether each asset-pair return relationship is sufficiently linear for Pearson correlation, or whether a monotonic rank relationship may make Spearman correlation more informative. The results are guidance rather than an automatic model-selection rule.",
    "Diagnostic flag: quadratic fit improves R² by at least 0.05 and/or |Spearman − Pearson| ≥ 0.10. This is a diagnostic convention, not a formal universal test or automatic selection rule.":"Linearity flag: quadratic fit improves R² by at least 0.05 and/or |Spearman − Pearson| ≥ 0.10. This is a diagnostic convention, not a formal universal test or automatic selection rule."
}
for old,new in replacements.items():
    if old in s: s=s.replace(old,new)
p.write_text(s)
py_compile.compile(str(p),doraise=True)
s=p.read_text()
for required in ["Linearity Test: Show LaTeX","Linearity Test — Methodology & Results","This linearity test examines whether each asset-pair return relationship","Linearity flag:"]:
    assert required in s, required
assert "st.button('LaTeX / Diagnostics'" not in s
assert "@st.dialog('Correlation Diagnostics & LaTeX'" not in s
print('PASS: linearity test labels are explicit and app compiles')
