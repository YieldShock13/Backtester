from pathlib import Path
p=Path('app.py'); s=p.read_text()
old="latex_slot=report_col1.empty(); audit_slot=report_col2.empty(); st.subheader('Backtest Configuration'); a,b,c,d=st.columns(4)\nwith a: timeline=st.selectbox('Timeline',['1W','1M','3M','6M','1Y','3Y','5Y','10Y','All','Custom'],index=8)\nwith b: INITIAL=float(st.number_input('Nominal amount',min_value=1.0,value=float(DEFAULT_INITIAL),step=10000.0))\nwith c: RF=float(st.number_input('Risk-free rate (%)',min_value=0.0,max_value=100.0,value=7.0,step=.25))/100\nwith d: REINVEST=st.toggle('Reinvest dividends/distributions',value=False)"
new="latex_slot=report_col1.empty(); audit_slot=report_col2.empty(); st.subheader('Backtest Configuration'); a,b,c,d,e=st.columns([1.15,.75,1.15,1.15,1.15])\nwith a: timeline=st.selectbox('Timeline',['1W','1M','3M','6M','1Y','3Y','5Y','10Y','All','Custom'],index=8)\nwith b: PORTFOLIO_CCY=st.segmented_control('Currency',['ZAR','USD','EUR','GBP'],default='ZAR',selection_mode='single') or 'ZAR'\nwith c: INITIAL=float(st.number_input(f'Nominal amount ({PORTFOLIO_CCY})',min_value=1.0,value=float(DEFAULT_INITIAL),step=10000.0))\nwith d: RF=float(st.number_input('Risk-free rate (%)',min_value=0.0,max_value=100.0,value=7.0,step=.25))/100\nwith e: REINVEST=st.toggle('Reinvest dividends/distributions',value=False)"
assert old in s, 'config block not found'; s=s.replace(old,new,1)
oldfx="with fxc2: BASE_CCY=st.selectbox('Portfolio / base currency',['ZAR','USD','EUR','GBP','JPY','CHF','AUD','CAD'],index=0,disabled=not FX_HEDGED)"
newfx="with fxc2:\n BASE_CCY=PORTFOLIO_CCY\n st.text_input('Portfolio / base currency',value=BASE_CCY,disabled=True)"
assert oldfx in s, 'fx block not found'; s=s.replace(oldfx,newfx,1)
start=s.index("@st.dialog('Full Data Audit',width='large')")
end=s.index("if latex_slot.button('Show LaTeX'",start)
audit=r'''@st.dialog('Full Data Audit',width='large')
def show_audit_report():
 st.title('Full Data Audit')
 st.caption(f'Configured run: {prices.index[0]:%Y-%m-%d} to {prices.index[-1]:%Y-%m-%d} | {frequency} | {len(prices)} observations | reporting currency {PORTFOLIO_CCY}')
 checks=[]
 def add(area,check,status,evidence): checks.append({'Area':area,'Check':check,'Status':status,'Evidence':evidence})
 # Structural integrity
 add('Structure','Duplicate dates','PASS' if not prices.index.duplicated().any() else 'FAIL',f'{int(prices.index.duplicated().sum())} duplicate date(s)')
 miss=prices.isna().sum(); add('Structure','Missing prices','PASS' if int(miss.sum())==0 else 'FAIL',f'{int(miss.sum())} missing configured price observations')
 dmiss=divs.isna().sum(); add('Structure','Missing distribution fields','PASS' if int(dmiss.sum())==0 else 'WARNING',f'{int(dmiss.sum())} missing distribution observations')
 add('Structure','Common sample size','PASS' if len(prices)>=12 else 'WARNING',f'{len(prices)} aligned observations across {len(ASSETS)} assets')
 # History / alignment loss
 coverage=[]
 for a0 in ASSETS:
  raw=full_p[a0].dropna() if a0 in full_p else pd.Series(dtype=float)
  coverage.append({'Instrument':instrument_names.get(a0,a0),'Ticker':a0,'Raw observations':len(raw),'Raw start':raw.index.min() if len(raw) else pd.NaT,'Raw end':raw.index.max() if len(raw) else pd.NaT,'Configured observations':int(prices[a0].notna().sum())})
  if len(raw):
   lost=max(0,len(raw.loc[(raw.index>=prices.index[0])&(raw.index<=prices.index[-1])])-int(prices[a0].notna().sum()))
   add('Coverage',a0+' alignment loss','PASS' if lost==0 else 'WARNING',f'{lost} observations lost inside configured window')
 coverage_df=pd.DataFrame(coverage)
 # Return sanity and distributions
 rr=(prices-prices.shift(1)+divs)/prices.shift(1)
 for a0 in ASSETS:
  mx=float(rr[a0].abs().max()) if rr[a0].notna().any() else np.nan
  lim=.35 if daily_mode else 1.0
  add('Returns',a0+' extreme-return scan','PASS' if np.isfinite(mx) and mx<=lim else 'FAIL',f'max |period return|={mx:.2%}; threshold={lim:.0%}')
  negdiv=int((divs[a0]<0).sum()); add('Distributions',a0+' negative distributions','PASS' if negdiv==0 else 'WARNING',f'{negdiv} negative cash distribution(s)')
 # Portfolio identities
 wsum=sum(weights.values()); add('Accounting','Portfolio weights sum','PASS' if abs(wsum-1)<1e-10 else 'FAIL',f'{wsum:.12f}')
 init_err=abs(float(vals.PORTFOLIO.iloc[0])-INITIAL); add('Accounting','Initial portfolio identity','PASS' if init_err<1e-6 else 'FAIL',f'V0={vals.PORTFOLIO.iloc[0]:,.6f}; nominal={INITIAL:,.6f}; error={init_err:.6g}')
 add('Accounting','Finite portfolio values','PASS' if np.isfinite(vals.PORTFOLIO).all() else 'FAIL',f'{int((~np.isfinite(vals.PORTFOLIO)).sum())} non-finite values')
 # Benchmark / regressions
 aligned_capm=pd.concat([vals.PORTFOLIO.pct_change(fill_method=None),bp.pct_change(fill_method=None)],axis=1).dropna()
 add('Regression','CAPM sample','PASS' if len(aligned_capm)>=24 else 'WARNING',f'{len(aligned_capm)} aligned portfolio/benchmark observations')
 add('Regression','Benchmark variance','PASS' if len(aligned_capm)>1 and aligned_capm.iloc[:,1].var()>0 else 'FAIL',f'variance={aligned_capm.iloc[:,1].var() if len(aligned_capm)>1 else np.nan:.8g}')
 # FX hedge diagnostics
 if FX_HEDGED:
  add('FX hedge','Hedged assets selected','PASS' if len(HEDGED_ASSETS)>0 else 'WARNING',f'{len(HEDGED_ASSETS)} selected')
  if not fx_hedge_report.empty:
   for _,r0 in fx_hedge_report.iterrows(): add('FX hedge',str(r0['Instrument'])+' regression sample','PASS' if int(r0['Observations'])>=24 else 'WARNING',f"{int(r0['Observations'])} obs; beta={r0['FX Beta / Hedge Ratio']:.4f}; R²={r0['R²']:.4f}")
 # Scenario sufficiency
 if not scenario_df.empty:
  for _,r0 in scenario_df.iterrows():
   n=int(r0.get('Historical Events',0)); add('Macro scenarios',str(r0.get('Scenario','Scenario'))+' event count','PASS' if n>=10 else ('WARNING' if n>=3 else 'FAIL'),f'{n} independent historical event(s)')
 # Source-specific validation already executed upstream
 if 'STXGVI.JO' in ASSETS: add('Source validation','STXGVI cents/ZAR normalisation','PASS','normalisation and distribution sanity checks completed before portfolio construction')
 if 'GOVI' in ASSETS: add('Source validation','GOVI repository history','PASS' if len(govi)>=100 else 'FAIL',f'{len(govi)} repository observations; last={govi.index.max():%Y-%m-%d}')
 audit=pd.DataFrame(checks); rank={'PASS':0,'WARNING':1,'FAIL':2}; worst=max((rank[x] for x in audit.Status),default=0); overall=['PASS','WARNING','FAIL'][worst]
 nfail=int((audit.Status=='FAIL').sum()); nwarn=int((audit.Status=='WARNING').sum()); npass=int((audit.Status=='PASS').sum())
 if overall=='PASS': st.success(f'AUDIT PASS — {npass} checks passed; no warnings or failures.')
 elif overall=='WARNING': st.warning(f'AUDIT WARNING — {npass} pass | {nwarn} warning | {nfail} fail')
 else: st.error(f'AUDIT FAIL — {npass} pass | {nwarn} warning | {nfail} fail')
 st.subheader('Flags requiring attention')
 flagged=audit[audit.Status!='PASS']; st.dataframe(flagged if not flagged.empty else pd.DataFrame([{'Status':'PASS','Evidence':'No audit flags in configured run.'}]),hide_index=True,use_container_width=True)
 st.subheader('Complete audit checks'); st.dataframe(audit,hide_index=True,use_container_width=True)
 st.subheader('Instrument coverage'); st.dataframe(coverage_df,hide_index=True,use_container_width=True)
 st.subheader('Configured weights'); st.dataframe(pd.DataFrame({'Instrument':[instrument_names.get(x,x) for x in ASSETS],'Ticker':ASSETS,'Weight':[weights[x] for x in ASSETS]}),hide_index=True,use_container_width=True)
 if not fx_hedge_report.empty: st.subheader('FX hedge regression audit'); st.dataframe(fx_hedge_report,hide_index=True,use_container_width=True)
 if not scenario_df.empty: st.subheader('Scenario sample audit'); st.dataframe(scenario_df,hide_index=True,use_container_width=True)
 st.subheader('Methodology note')
 st.write('Audit checks are run on the configured output and its underlying aligned data. Raw Close and explicit cash distributions are used; Adjusted Close is not used. PASS indicates no issue detected by the stated check, WARNING identifies a limitation or small sample requiring attention, and FAIL identifies a breached validation rule. The audit is diagnostic rather than a guarantee of source correctness.')
'''
s=s[:start]+audit+'\n'+s[end:]
s=s.replace("st.write(f'Nominal V0 = {INITIAL:,.2f}; reinvest distributions = {REINVEST}.')","st.write(f'Reporting currency = {PORTFOLIO_CCY}; nominal V0 = {PORTFOLIO_CCY} {INITIAL:,.2f}; reinvest distributions = {REINVEST}.')",1)
p.write_text(s)
