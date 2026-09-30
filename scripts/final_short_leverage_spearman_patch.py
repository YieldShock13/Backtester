from pathlib import Path
p=Path('app.py'); s=p.read_text()

# 1) Negative weights / shorts. Net weights must sum to +100%; gross may exceed 100%.
old="with cols[i%3]: raww[a0]=st.number_input(f'{a0} (%)',0.0,100.0,float(default),.25,key=f'w_{a0}')/100\nif sum(raww.values())<=0: st.error('Weights must be positive.'); st.stop()\nweights={a0:w/sum(raww.values()) for a0,w in raww.items()}; ALLOC={a0:INITIAL*w for a0,w in weights.items()}"
new="with cols[i%3]: raww[a0]=st.number_input(f'{a0} (%)',min_value=-500.0,max_value=500.0,value=float(default),step=.25,key=f'w_{a0}',help='Negative weight = short position.')/100\nnet_weight=sum(raww.values()); gross_weight=sum(abs(w) for w in raww.values())\nif net_weight<=0: st.error('Net portfolio weight must be greater than 0%.'); st.stop()\nweights={a0:w/net_weight for a0,w in raww.items()}; ALLOC={a0:INITIAL*w for a0,w in weights.items()}\nst.caption(f'Net exposure normalised to 100% | Gross exposure {sum(abs(w) for w in weights.values()):.1%}. Negative weights are treated as short positions.')\nst.markdown('**Leverage & Financing**')\nlev1,lev2=st.columns(2)\nwith lev1: LEVERAGE=float(st.number_input('Portfolio leverage (x)',min_value=1.0,max_value=10.0,value=1.0,step=.1,help='1.0x = no additional leverage. Applied to portfolio periodic returns after configured long/short weights.'))\nwith lev2: LEVERAGE_COST=float(st.number_input('Annual leverage / financing cost (%)',min_value=0.0,max_value=100.0,value=0.0,step=.25,help='Annual financing rate charged on additional borrowed capital (leverage − 1).'))/100"
if old in s: s=s.replace(old,new)

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
if old in s: s=s.replace(old,new)

old="+(' | FX beta hedge active' if FX_HEDGED and HEDGED_ASSETS else ' | FX unhedged'))"
new="+(' | FX beta hedge active' if FX_HEDGED and HEDGED_ASSETS else ' | FX unhedged')+f' | Leverage {LEVERAGE:.1f}x | Financing cost {LEVERAGE_COST:.2%} p.a.')"
if old in s: s=s.replace(old,new)

# 3) Pearson / Spearman viewer toggle.
old="st.divider(); st.subheader('Asset Correlation'); corr=asset_r[ASSETS].dropna().corr(); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()) if len(corr)>1 else np.nan; st.metric('Net Inter-Asset Correlation','N/A' if not np.isfinite(net_corr) else f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title='Pearson Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)"
new="""st.divider(); st.subheader('Asset Correlation')
corr_method=st.segmented_control('Correlation measure',['Pearson','Spearman'],default='Pearson',selection_mode='single',key='corr_method') or 'Pearson'
corr=asset_r[ASSETS].dropna().corr(method=corr_method.lower()); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()) if len(corr)>1 else np.nan; st.metric(f'Average Inter-Asset {corr_method} Correlation','N/A' if not np.isfinite(net_corr) else f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title=f'{corr_method} Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)"""
if old in s: s=s.replace(old,new)
# Also correct wording if the correlation feature was already deployed.
s=s.replace("st.metric(f'Net Inter-Asset {corr_method} Correlation'","st.metric(f'Average Inter-Asset {corr_method} Correlation'")

# 4) Add leverage methodology to LaTeX if dialog exists.
anchor="st.header('24. Complete configured metric output')"
latex="""st.header('24. Long/short weights and leverage')
 st.latex(r'\\sum_i w_i=1,\\qquad G=\\sum_i|w_i|,\\qquad w_i<0\\;\\Rightarrow\\;\\text{short position}')
 st.latex(r'r^{(L)}_{p,t}=Lr_{p,t}-(L-1)c_w,\\qquad c_w=(1+c_a)^{1/52}-1')
 st.write('Configured weights are normalised to net 100%; negative weights represent short positions and gross exposure may exceed 100%. Additional leverage L scales the configured portfolio periodic return. Financing cost is charged on additional borrowed capital L−1 using the effective weekly equivalent of the annual financing rate. All headline portfolio return/risk metrics use the resulting net-of-financing leveraged portfolio path.')
 st.header('25. Complete configured metric output')"""
if anchor in s: s=s.replace(anchor,latex)

# 5) Compact footer + expandable comprehensive disclaimer.
old_disclaimer="st.divider()\nst.caption('Not financial advice. Outputs are for research/informational purposes only and are subject to revision.')"
full_disclaimer="""st.divider()
st.caption('Not financial advice. For research, analytical, educational and informational purposes only. Historical, simulated and modelled outputs may be inaccurate and are not indicative of future results. Subject to revision. See Full Disclaimer below.')
with st.expander('Full Disclaimer', expanded=False):
    st.markdown('''
**Important Disclaimer**

This tool and all information, calculations, analytics, backtests, estimates, scenarios, charts, statistics and other outputs generated by it are provided solely for general informational, analytical, educational and research purposes. Nothing contained in or produced by this tool constitutes, or should be construed as, financial, investment, trading, legal, tax, accounting or other professional advice, nor as a recommendation, solicitation, offer or endorsement to buy, sell, hold, short, hedge or otherwise transact in any security, financial instrument, investment product, asset class or strategy.

Outputs are generated using historical and/or third-party data, user-selected assumptions and quantitative models. Although reasonable efforts may be made to maintain the integrity of calculations and underlying data, no representation or warranty, express or implied, is made as to the accuracy, completeness, reliability, timeliness, availability or fitness for any particular purpose of the data, methodology or outputs. Data may contain errors, omissions, revisions, survivorship effects, corporate-action issues, differing market calendars, stale observations or other limitations.

Backtested, simulated and hypothetical results have inherent limitations and do not represent actual trading unless expressly stated otherwise. Historical performance is not a guarantee or reliable indication of future results. Modelled relationships, correlations, betas, alphas, risk measures, scenario analyses, Value-at-Risk estimates and other statistical estimates may change materially over time and may not persist under future market conditions.

Results may not reflect all transaction costs, taxes, fees, bid-ask spreads, market impact, liquidity constraints, borrowing constraints, short-selling costs, stock-borrow availability, financing costs, margin requirements, collateral requirements, currency effects or other factors that would affect an actual investment portfolio, except where expressly incorporated into the selected configuration. Leverage and short positions can materially magnify both gains and losses and may result in losses exceeding the capital initially allocated to a position or strategy.

Any scenario, stress test or historical event analysis is an analytical representation based on the methodology and data described by the tool. It is not a forecast, prediction or representation of how a portfolio or financial instrument will necessarily perform during any future market event. Risk measures are estimates rather than guarantees of maximum loss.

Users are responsible for independently verifying all information and for assessing the suitability, appropriateness and risks of any investment, transaction or strategy having regard to their own objectives, financial circumstances, risk tolerance and legal or regulatory requirements. No investment or trading decision should be made solely in reliance on this tool or its outputs. Where appropriate, users should obtain advice from suitably qualified and authorised professional advisers.

The tool, its underlying methodologies, assumptions, data sources, calculations, functionality and outputs may be corrected, modified, updated, replaced or revised at any time without notice. Outputs should therefore be treated as provisional analytical information and may differ between runs or following data or methodology revisions.

To the fullest extent permitted by applicable law, the developers, owners, operators and contributors accept no liability for any direct, indirect, incidental, consequential or other loss, damage, cost or expense arising from or connected with access to, use of, inability to use, or reliance upon this tool, its data or any output generated by it.

Use of this tool does not create an adviser-client, fiduciary, agency or other professional relationship between the user and the developers, owners, operators or contributors.

**By using this tool, the user acknowledges the limitations described above and accepts responsibility for independently evaluating any information or output before relying upon it.**
''')"""
if old_disclaimer in s:
    s=s.replace(old_disclaimer,full_disclaimer)
elif "with st.expander('Full Disclaimer'" not in s:
    s += "\n\n"+full_disclaimer+"\n"

p.write_text(s)
s=p.read_text()
for req in ["Negative weight = short position","Portfolio leverage (x)","Annual leverage / financing cost (%)","levered_r=LEVERAGE*base_r-(LEVERAGE-1.0)*weekly_financing","Correlation measure","['Pearson','Spearman']","corr(method=corr_method.lower())","Average Inter-Asset {corr_method} Correlation","with st.expander('Full Disclaimer'","Nothing contained in or produced by this tool constitutes","Backtested, simulated and hypothetical results have inherent limitations","Leverage and short positions can materially magnify","Use of this tool does not create an adviser-client","Gross exposure","Financing cost {LEVERAGE_COST:.2%} p.a."]:
    assert req in s, req
assert "st.number_input(f'{a0} (%)',0.0,100.0" not in s
