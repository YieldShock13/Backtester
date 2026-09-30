from pathlib import Path
import py_compile
p=Path('app.py'); s=p.read_text()
old="""st.divider(); st.subheader('Asset Correlation')
corr_method=st.segmented_control('Correlation measure',['Pearson','Spearman'],default='Pearson',selection_mode='single',key='corr_method') or 'Pearson'
corr=asset_r[ASSETS].dropna().corr(method=corr_method.lower()); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()) if len(corr)>1 else np.nan; st.metric(f'Average Inter-Asset {corr_method} Correlation','N/A' if not np.isfinite(net_corr) else f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title=f'{corr_method} Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)"""
new="""st.divider(); st.subheader('Asset Correlation')
corr_left,corr_right=st.columns([4,1])
with corr_left:
 corr_method=st.segmented_control('Correlation measure',['Pearson','Spearman'],default='Pearson',selection_mode='single',key='corr_method') or 'Pearson'
with corr_right:
 corr_latex=st.button('LaTeX / Diagnostics',key='corr_latex_btn',use_container_width=True)
# Diagnostics are descriptive guidance, not an automatic model-selection rule.
# Pearson measures linear association; Spearman measures monotonic rank association.
from scipy.stats import spearmanr
corr_sample=asset_r[ASSETS].dropna()
pair_diag=[]
for ii,a in enumerate(ASSETS):
 for b in ASSETS[ii+1:]:
  xy=corr_sample[[a,b]].dropna(); n=len(xy)
  if n<8: continue
  x=xy[a].to_numpy(float); y=xy[b].to_numpy(float)
  pr=float(np.corrcoef(x,y)[0,1]); sr=float(spearmanr(x,y,nan_policy='omit').statistic)
  # Linear fit and residual diagnostics: R^2 describes linear fit; curvature-gain compares
  # a quadratic fit with the linear fit. Large Pearson-vs-Spearman divergence is also flagged.
  coef1=np.polyfit(x,y,1); y1=np.polyval(coef1,x); ss=float(np.sum((y-y.mean())**2)); r2_lin=(1-float(np.sum((y-y1)**2))/ss) if ss>0 else np.nan
  r2_quad=np.nan
  if n>=12 and np.unique(x).size>=3 and ss>0:
   coef2=np.polyfit(x,y,2); y2=np.polyval(coef2,x); r2_quad=1-float(np.sum((y-y2)**2))/ss
  curvature_gain=(r2_quad-r2_lin) if np.isfinite(r2_quad) and np.isfinite(r2_lin) else np.nan
  nonlinear_flag=bool((np.isfinite(curvature_gain) and curvature_gain>=0.05) or abs(sr-pr)>=0.10)
  pair_diag.append({'Pair':f'{a} / {b}','N':n,'Pearson':pr,'Spearman':sr,'Linear R²':r2_lin,'Quadratic ΔR²':curvature_gain,'Non-linearity flag':'Yes' if nonlinear_flag else 'No'})
if pair_diag:
 corr_diag=pd.DataFrame(pair_diag); nonlinear_share=float((corr_diag['Non-linearity flag']=='Yes').mean())
 corr_guidance=('Spearman may be more informative: several pairs show material non-linearity / rank-vs-linear divergence.' if nonlinear_share>=0.25 else 'Pearson is reasonable for linear association; Spearman remains useful as a robustness comparison.')
else:
 corr_diag=pd.DataFrame(); nonlinear_share=np.nan; corr_guidance='Insufficient paired observations for diagnostics.'
if corr_latex:
 @st.dialog('Correlation Diagnostics & LaTeX',width='large')
 def _corr_diag_dialog():
  st.latex(r'\\rho_P(X,Y)=\\frac{\\operatorname{Cov}(X,Y)}{\\sigma_X\\sigma_Y}')
  st.latex(r'\\rho_S(X,Y)=\\rho_P(\\operatorname{rank}(X),\\operatorname{rank}(Y))')
  st.latex(r'R^2_{lin}=1-\\frac{\\sum_t(y_t-\\hat y^{lin}_t)^2}{\\sum_t(y_t-\\bar y)^2},\\qquad \\Delta R^2=R^2_{quad}-R^2_{lin}')
  st.write('Pearson measures linear association. Spearman measures monotonic association after ranking observations. The diagnostics below do not mechanically choose a coefficient; they flag cases where a simple linear description may be inadequate.')
  st.info(corr_guidance)
  if not corr_diag.empty: st.dataframe(corr_diag,hide_index=True,use_container_width=True,column_config={'Pearson':st.column_config.NumberColumn(format='%.3f'),'Spearman':st.column_config.NumberColumn(format='%.3f'),'Linear R²':st.column_config.NumberColumn(format='%.3f'),'Quadratic ΔR²':st.column_config.NumberColumn(format='%.3f')})
  st.caption('Diagnostic flag: quadratic fit improves R² by at least 0.05 and/or |Spearman − Pearson| ≥ 0.10. This is a diagnostic convention, not a formal universal test or automatic selection rule.')
 _corr_diag_dialog()
corr=corr_sample.corr(method=corr_method.lower()); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()) if len(corr)>1 else np.nan; st.metric(f'Average Inter-Asset {corr_method} Correlation','N/A' if not np.isfinite(net_corr) else f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title=f'{corr_method} Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)"""
if old not in s: raise RuntimeError('correlation block not found')
s=s.replace(old,new)
p.write_text(s)
py_compile.compile(str(p),doraise=True)
s=p.read_text()
for x in ["LaTeX / Diagnostics","Correlation Diagnostics & LaTeX","spearmanr","Quadratic ΔR²","Non-linearity flag","Pearson measures linear association","Spearman measures monotonic association","not a formal universal test or automatic selection rule"]: assert x in s,x
print('PASS: correlation diagnostics added and app compiles')
