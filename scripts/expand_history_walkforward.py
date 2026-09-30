from pathlib import Path
p=Path('app.py'); s=p.read_text()

# No arbitrary 2012 history cap: request the maximum source history and let the common
# aligned weekly index determine the earliest feasible portfolio start.
s=s.replace('START="2012-02-01"','START=None')
s=s.replace("h=yf.Ticker(ticker).history(start=START,interval='1d',auto_adjust=False,actions=True)","h=yf.Ticker(ticker).history(period='max',interval='1d',auto_adjust=False,actions=True)")
s=s.replace("return mp.loc[START:],md.reindex(mp.index,fill_value=0.0).loc[START:],g,val,ys","return mp,md.reindex(mp.index,fill_value=0.0),g,val,ys")
s=s.replace("custom_start=st.date_input('Custom start',value=pd.Timestamp(START).date())","custom_start=st.date_input('Custom start',value=pd.Timestamp('1900-01-01').date())")

# Walk-forward helpers: 52-week estimation window, strictly one-step-ahead validation.
anchor="title_col, report_col1, report_col2=st.columns([8,1,1])"
helpers=r'''def walk_forward_validation(vals,market_r,rf,ppy=52,window=52,var_method='Historical',var_level=.95):
 rp=vals.PORTFOLIO.pct_change(fill_method=None).rename('Portfolio')
 d=pd.concat([rp,market_r.rename('Benchmark')],axis=1).dropna()
 rfp=(1+rf)**(1/ppy)-1; rows=[]; z95=-1.6448536269514722
 for i in range(window,len(d)):
  train=d.iloc[i-window:i]; test=d.iloc[i]; x=train.Benchmark-rfp; y=train.Portfolio-rfp
  beta=y.cov(x)/x.var() if x.var()>0 else np.nan; alpha=y.mean()-beta*x.mean() if np.isfinite(beta) else np.nan
  capm_pred=rfp+alpha+beta*(test.Benchmark-rfp) if np.isfinite(beta) else np.nan
  tr=train.Portfolio.dropna()
  if var_method=='Historical': q=float(tr.quantile(1-var_level)); sigma=np.nan
  elif var_method=='Parametric':
   mu=float(tr.mean()); sigma=float(tr.std(ddof=1)); q=mu+z95*sigma
  else:
   try:
    from arch import arch_model
    fit=arch_model(tr.values*100,mean='Constant',vol='GARCH',p=1,q=1,dist='normal',rescale=False).fit(disp='off',show_warning=False)
    fc=fit.forecast(horizon=1,reindex=False); mu=float(fit.params.get('mu',tr.mean()*100))/100; sigma=float(np.sqrt(fc.variance.values[-1,0]))/100; q=mu+z95*sigma
   except Exception:
    q=np.nan; sigma=np.nan
  rows.append({'Date':d.index[i],'Actual Return':float(test.Portfolio),'Benchmark Return':float(test.Benchmark),'CAPM Forecast':capm_pred,'CAPM Alpha':alpha,'CAPM Beta':beta,'VaR 95%':q,'VaR Breach':bool(test.Portfolio<q) if np.isfinite(q) else False,'Forecast Sigma':sigma})
 out=pd.DataFrame(rows).set_index('Date') if rows else pd.DataFrame()
 return out

def walk_forward_summary(wf,var_method):
 if wf.empty: return pd.DataFrame()
 valid=wf.dropna(subset=['Actual Return','CAPM Forecast']); rmse=float(np.sqrt(((valid['Actual Return']-valid['CAPM Forecast'])**2).mean())) if len(valid) else np.nan
 mae=float((valid['Actual Return']-valid['CAPM Forecast']).abs().mean()) if len(valid) else np.nan
 v=wf.dropna(subset=['VaR 95%']); breaches=int(v['VaR Breach'].sum()) if len(v) else 0; rate=breaches/len(v) if len(v) else np.nan
 return pd.DataFrame([{'Estimation Window':'52 weeks','OOS Weeks':len(wf),'CAPM Forecast RMSE':rmse,'CAPM Forecast MAE':mae,'Mean OOS Beta':wf['CAPM Beta'].mean(),'VaR Method':var_method,'VaR Confidence':'95%','VaR Breaches':breaches,'VaR Breach Rate':rate,'Expected Breach Rate':.05}])

'''
if 'def walk_forward_validation(' not in s: s=s.replace(anchor,helpers+anchor)

needle="else: st.info('Select at least one macro risk scenario.')\n\n@st.dialog('Complete Quantitative Workings',width='large')"
section=r'''else: st.info('Select at least one macro risk scenario.')

st.divider(); st.subheader('Walk-Forward Validator — 52-Week Estimation Window')
st.caption('Strict one-step-ahead validation: each CAPM and VaR estimate uses only the preceding 52 weekly observations; the following week is held out for validation.')
wf_method=st.segmented_control('VaR model',['Historical','Parametric','GARCH(1,1)'],default='Historical',selection_mode='single',key='wf_var_method') or 'Historical'
wf=walk_forward_validation(vals,market_r,RF,ppy,52,wf_method,.95)
wf_summary=walk_forward_summary(wf,wf_method)
if wf.empty:
 st.warning('Walk-forward validation requires at least 53 aligned weekly portfolio/benchmark observations.')
else:
 show_sum=wf_summary.copy()
 for c0 in ['CAPM Forecast RMSE','CAPM Forecast MAE','VaR Breach Rate','Expected Breach Rate']:
  if c0 in show_sum: show_sum[c0]=show_sum[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
 if 'Mean OOS Beta' in show_sum: show_sum['Mean OOS Beta']=show_sum['Mean OOS Beta'].map(lambda x:f'{x:.3f}' if pd.notna(x) else 'N/A')
 st.dataframe(show_sum,hide_index=True,use_container_width=True)
 line_chart({'Actual Weekly Return':wf['Actual Return']*100,'CAPM One-Step Forecast':wf['CAPM Forecast']*100},'Walk-Forward CAPM — Actual vs One-Step-Ahead Forecast','Return (%)')
 line_chart({'52-Week CAPM Beta':wf['CAPM Beta']},'Walk-Forward CAPM — Estimated Beta','Beta')
 line_chart({'Actual Weekly Return':wf['Actual Return']*100,'95% VaR Threshold':wf['VaR 95%']*100},f'Walk-Forward {wf_method} VaR — One-Step-Ahead Validation','Return (%)')
 wf_table=wf.reset_index()[['Date','Actual Return','CAPM Forecast','CAPM Alpha','CAPM Beta','VaR 95%','VaR Breach']].copy()
 for c0 in ['Actual Return','CAPM Forecast','CAPM Alpha','VaR 95%']: wf_table[c0]=wf_table[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
 wf_table['CAPM Beta']=wf_table['CAPM Beta'].map(lambda x:f'{x:.3f}' if pd.notna(x) else 'N/A')
 st.dataframe(wf_table,hide_index=True,use_container_width=True)

@st.dialog('Complete Quantitative Workings',width='large')'''
if "Walk-Forward Validator — 52-Week Estimation Window" not in s:
 if needle not in s: raise RuntimeError('Walk-forward insertion anchor not found')
 s=s.replace(needle,section)

latex_anchor="st.header('23. Complete configured metric output')"
latex=r'''st.header('23. Walk-forward CAPM and VaR validation')
 st.latex(r'\\hat\\beta_t=\\frac{Cov(r_p-r_f,r_m-r_f)_{t-52:t-1}}{Var(r_m-r_f)_{t-52:t-1}},\\qquad \\hat r_{p,t}=r_f+\\hat\\alpha_t+\\hat\\beta_t(r_{m,t}-r_f)')
 st.latex(r'VaR^{hist}_{.95,t}=Q_{.05}(r_{p,t-52:t-1})')
 st.latex(r'VaR^{param}_{.95,t}=\\hat\\mu_t+z_{.05}\\hat\\sigma_t,\\qquad z_{.05}=-1.64485')
 st.latex(r'\\sigma_t^2=\\omega+\\alpha\\epsilon_{t-1}^2+\\beta\\sigma_{t-1}^2,\\qquad VaR^{GARCH}_{.95,t}=\\hat\\mu_t+z_{.05}\\hat\\sigma_t')
 st.write('Every estimate is fit only on the preceding 52 weekly observations and evaluated on the next held-out week. Historical VaR is empirical; Parametric VaR assumes normal weekly returns; GARCH uses a GARCH(1,1) conditional variance with normal innovations. The displayed breach rate is compared with the nominal 5% rate.')
 st.header('24. Complete configured metric output')'''
if "23. Walk-forward CAPM and VaR validation" not in s: s=s.replace(latex_anchor,latex)

audit_anchor="if 'STXGVI.JO' in ASSETS: add('Source validation'"
audit=r'''if 'wf' in globals():
  add('Walk-forward','52-week OOS sample','PASS' if len(wf)>=52 else ('WARNING' if len(wf)>0 else 'FAIL'),f'{len(wf)} held-out weekly validation observations')
  if not wf.empty:
   nv=int(wf['VaR 95%'].notna().sum()); add('Walk-forward','VaR estimates available','PASS' if nv==len(wf) else 'WARNING',f'{nv}/{len(wf)} one-step VaR estimates available using {wf_method}')
   nb=int(wf['CAPM Forecast'].notna().sum()); add('Walk-forward','CAPM estimates available','PASS' if nb==len(wf) else 'WARNING',f'{nb}/{len(wf)} one-step CAPM forecasts available')
 '''
if "add('Walk-forward','52-week OOS sample'" not in s: s=s.replace(audit_anchor,audit+audit_anchor)

# Complete-case weekly alignment. A Friday label represents the last genuine observation
# inside that calendar week. We never interpolate or carry a price across an empty week.
old="common=full_p[ASSETS].dropna().index; start,end,requested=resolve_dates(common,timeline,custom_start,custom_end,daily_mode); prices=full_p.loc[(full_p.index>=start)&(full_p.index<=end),ASSETS].dropna(); divs=full_d.reindex(prices.index,fill_value=0.0)[ASSETS]"
new="asset_weekly=full_p[ASSETS]; raw_week_count=len(asset_weekly); missing_by_asset=asset_weekly.isna().sum().astype(int).to_dict(); common=asset_weekly.dropna(how='any').index; dropped_asset_weeks=raw_week_count-len(common); start,end,requested=resolve_dates(common,timeline,custom_start,custom_end,daily_mode); prices=full_p.loc[(full_p.index>=start)&(full_p.index<=end),ASSETS].dropna(how='any'); divs=full_d.reindex(prices.index,fill_value=0.0)[ASSETS]"
s=s.replace(old,new)

# Load benchmark before portfolio construction and intersect it with the exact same weekly
# index. Missing benchmark weeks are removed rather than forward-filled.
old2="if len(prices)<2: raise RuntimeError('Selected timeline has fewer than two common observations')\n  asset_r="
new2="""if BENCHMARK=='GOVI': raise RuntimeError('Repository GOVI is monthly-only and cannot be used as a weekly benchmark. Select a daily-history market ticker/proxy.')
  bench_p,bench_d,_=load_ticker_components((BENCHMARK,)); bp_all=bench_p[BENCHMARK].resample('W-FRI').last(); bd_all=bench_d[BENCHMARK].resample('W-FRI').sum(); benchmark_missing_weeks=int(bp_all.reindex(prices.index).isna().sum()); aligned_index=prices.index.intersection(bp_all.dropna().index); prices=prices.reindex(aligned_index).dropna(how='any'); divs=divs.reindex(prices.index,fill_value=0.0); bp=bp_all.reindex(prices.index); bd=bd_all.reindex(prices.index,fill_value=0.0)
  if len(prices)<2: raise RuntimeError('Selected timeline has fewer than two complete-case weekly observations across assets and benchmark')
  asset_r="""
s=s.replace(old2,new2)

# Remove the later duplicate benchmark loader; bp/bd are already aligned before portfolio construction.
old3="if BENCHMARK=='GOVI':\n bp=load_govi_history().reindex(prices.index).ffill(); bd=pd.Series(0.0,index=prices.index)\nelse:\n bench_p,bench_d,_=load_ticker_components((BENCHMARK,)); bp=bench_p[BENCHMARK].resample('W-FRI').last().reindex(prices.index); bd=bench_d[BENCHMARK].resample('W-FRI').sum().reindex(prices.index,fill_value=0.0)\nmarket_r="
s=s.replace(old3,"market_r=")

# FX: no cross-week forward fill. Regression uses only weeks with genuine aligned FX observations.
s=s.replace("fx=load_fx_pair(pair,daily_mode).reindex(prices.index).ffill(); fr=fx.pct_change(fill_method=None)","fx=load_fx_pair(pair,daily_mode).reindex(prices.index); fr=fx.pct_change(fill_method=None)")
s=s.replace("fx=fp[pair].resample('W-FRI').last().reindex(prices.index)","fx=fp[pair].resample('W-FRI').last().reindex(prices.index)")

# Surface weekly alignment in flags/audit.
flag_anchor="data_flags=[]"
flag_text="""data_flags=[]
if 'dropped_asset_weeks' in globals() and dropped_asset_weeks>0: data_flags.append(f'Weekly alignment excluded {dropped_asset_weeks} asset-weeks from the union calendar because at least one selected asset had no genuine observation in that week. No interpolation or cross-week price fill was used.')
if 'benchmark_missing_weeks' in globals() and benchmark_missing_weeks>0: data_flags.append(f'Weekly alignment excluded {benchmark_missing_weeks} additional week(s) with no genuine benchmark observation.')"""
s=s.replace(flag_anchor,flag_text)

audit_insert="""if 'missing_by_asset' in globals():
  miss_txt=', '.join(f'{k}: {v}' for k,v in missing_by_asset.items() if v) or 'none'
  add('Alignment','Complete-case weekly alignment','PASS' if dropped_asset_weeks==0 and benchmark_missing_weeks==0 else 'WARNING',f'Raw weekly union={raw_week_count}; asset-incomplete weeks excluded={dropped_asset_weeks}; benchmark-incomplete weeks excluded={benchmark_missing_weeks}; final aligned weeks={len(prices)}; missing by asset={miss_txt}. No interpolation or cross-week forward fill.')
 """
if "add('Alignment','Complete-case weekly alignment'" not in s: s=s.replace(audit_anchor,audit_insert+audit_anchor)

p.write_text(s)
s=p.read_text()
for req in ["period='max'","Walk-Forward Validator — 52-Week Estimation Window","GARCH(1,1)","52-week OOS sample","VaR^{hist}","CAPM One-Step Forecast","Complete-case weekly alignment","dropna(how='any')","aligned_index=prices.index.intersection","No interpolation or cross-week forward fill"]: assert req in s, req
assert 'START="2012-02-01"' not in s
assert ".loc[START:]" not in s
