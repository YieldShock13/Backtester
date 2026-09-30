from pathlib import Path
p=Path('app.py'); s=p.read_text()

# 1) Negative weights / shorts. Net weights must sum to +100%; gross may exceed 100%.
old="with cols[i%3]: raww[a0]=st.number_input(f'{a0} (%)',0.0,100.0,float(default),.25,key=f'w_{a0}')/100\nif sum(raww.values())<=0: st.error('Weights must be positive.'); st.stop()\nweights={a0:w/sum(raww.values()) for a0,w in raww.items()}; ALLOC={a0:INITIAL*w for a0,w in weights.items()}"
new="with cols[i%3]: raww[a0]=st.number_input(f'{a0} (%)',min_value=-500.0,max_value=500.0,value=float(default),step=.25,key=f'w_{a0}',help='Negative weight = short position.')/100\nnet_weight=sum(raww.values()); gross_weight=sum(abs(w) for w in raww.values())\nif net_weight<=0: st.error('Net portfolio weight must be greater than 0%.'); st.stop()\nweights={a0:w/net_weight for a0,w in raww.items()}; ALLOC={a0:INITIAL*w for a0,w in weights.items()}\nst.caption(f'Net exposure normalised to 100% | Gross exposure {sum(abs(w) for w in weights.values()):.1%}. Negative weights are treated as short positions.')\nst.markdown('**Leverage & Financing**')\nlev1,lev2=st.columns(2)\nwith lev1: LEVERAGE=float(st.number_input('Portfolio leverage (x)',min_value=1.0,max_value=10.0,value=1.0,step=.1,help='1.0x = no additional leverage. Applied to portfolio periodic returns after configured long/short weights.'))\nwith lev2: LEVERAGE_COST=float(st.number_input('Annual leverage / financing cost (%)',min_value=0.0,max_value=100.0,value=0.0,step=.25,help='Annual financing rate charged on additional borrowed capital (leverage − 1).'))/100"
if old not in s: raise RuntimeError('weights block not found')
s=s.replace(old,new)

# 2) Apply leverage to portfolio return path before ALL portfolio-level analytics.
old="mode=st.radio('Backtest mode',['Buy & Hold','Annual Rebalanced'],horizontal=True,index=0); vals=bh if mode=='Buy & Hold' else rb\nmarket_r="
new="""mode=st.radio('Backtest mode',['Buy & Hold','Annual Rebalanced'],horizontal=True,index=0); vals=(bh if mode=='Buy & Hold' else rb).copy()
# Additional leverage is applied to the configured long/short portfolio return. Financing
# cost is charged only on borrowed capital (L-1), converted to an effective weekly rate.
base_portfolio=vals.PORTFOLIO.copy(); base_r=base_portfolio.pct_change(fill_method=None)
weekly_financing=(1+LEVERAGE_COST)**(1/ppy)-1
levered_r=LEVERAGE*base_r-(LEVERAGE-1.0)*weekly_financing
levered_growth=(1+levered_r.fillna(0.0)).cumprod(); vals.loc[:,'PORTFOLIO']=INITIAL*levered_growth
vals.loc[vals.index[0],'PORTFOLIO']=INITIAL
market_r="""
if old not in s: raise RuntimeError('mode/vals anchor not found')
s=s.replace(old,new)

# Make configured-window caption disclose leverage/cost.
old="+(' | FX beta hedge active' if FX_HEDGED and HEDGED_ASSETS else ' | FX unhedged'))"
new="+(' | FX beta hedge active' if FX_HEDGED and HEDGED_ASSETS else ' | FX unhedged')+f' | Leverage {LEVERAGE:.1f}x | Financing cost {LEVERAGE_COST:.2%} p.a.')"
if old not in s: raise RuntimeError('caption anchor not found')
s=s.replace(old,new)

# 3) Pearson / Spearman viewer toggle.
old="st.divider(); st.subheader('Asset Correlation'); corr=asset_r[ASSETS].dropna().corr(); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()) if len(corr)>1 else np.nan; st.metric('Net Inter-Asset Correlation','N/A' if not np.isfinite(net_corr) else f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title='Pearson Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)"
new="""st.divider(); st.subheader('Asset Correlation')
corr_method=st.segmented_control('Correlation measure',['Pearson','Spearman'],default='Pearson',selection_mode='single',key='corr_method') or 'Pearson'
corr=asset_r[ASSETS].dropna().corr(method=corr_method.lower()); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()) if len(corr)>1 else np.nan; st.metric(f'Net Inter-Asset {corr_method} Correlation','N/A' if not np.isfinite(net_corr) else f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title=f'{corr_method} Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)"""
if old not in s: raise RuntimeError('correlation block not found')
s=s.replace(old,new)

# 4) Add leverage methodology to LaTeX if dialog exists.
anchor="st.header('24. Complete configured metric output')"
latex="""st.header('24. Long/short weights and leverage')
 st.latex(r'\\sum_i w_i=1,\\qquad G=\\sum_i|w_i|,\\qquad w_i<0\\;\\Rightarrow\\;\\text{short position}')
 st.latex(r'r^{(L)}_{p,t}=Lr_{p,t}-(L-1)c_w,\\qquad c_w=(1+c_a)^{1/52}-1')
 st.write('Configured weights are normalised to net 100%; negative weights represent short positions and gross exposure may exceed 100%. Additional leverage L scales the configured portfolio periodic return. Financing cost is charged on additional borrowed capital L−1 using the effective weekly equivalent of the annual financing rate. All headline portfolio return/risk metrics use the resulting net-of-financing leveraged portfolio path.')
 st.header('25. Complete configured metric output')"""
if anchor in s: s=s.replace(anchor,latex)

# 5) End disclaimer.
if "Not financial advice. Outputs are subject to revision." not in s:
    s += "\n\nst.divider()\nst.caption('Not financial advice. Outputs are for research/informational purposes only and are subject to revision.')\n"

p.write_text(s)
s=p.read_text()
for req in ["Negative weight = short position","Portfolio leverage (x)","Annual leverage / financing cost (%)","levered_r=LEVERAGE*base_r-(LEVERAGE-1.0)*weekly_financing","Correlation measure',['Pearson','Spearman']","corr(method=corr_method.lower())","Not financial advice. Outputs are for research/informational purposes only and are subject to revision.","Gross exposure","Financing cost {LEVERAGE_COST:.2%} p.a."]:
    assert req in s, req
assert "st.number_input(f'{a0} (%)',0.0,100.0" not in s
