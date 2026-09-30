from pathlib import Path
p=Path('app.py'); s=p.read_text()

# Optional benchmark control. Portfolio history is never shortened by benchmark inception.
old="""st.markdown('**Benchmark**')
if 'benchmark_symbol' not in st.session_state: st.session_state.benchmark_symbol=BENCHMARK_TICKER
if 'benchmark_name' not in st.session_state: st.session_state.benchmark_name='FTSE/JSE All Share Index'
benchmark_query=st.text_input('Search benchmark',placeholder='Search by index, ETF, fund or ticker',key='benchmark_search_query')
benchmark_results=search_assets(benchmark_query) if benchmark_query.strip() else []
if benchmark_results:
 benchmark_labels=[f\"{r['name']} — {r['symbol']}\" for r in benchmark_results]
 def _select_benchmark():
  picked=st.session_state.get('benchmark_search_pick')
  if picked is None: return
  row=benchmark_results[picked]; st.session_state.benchmark_symbol=row['symbol']; st.session_state.benchmark_name=row['name']
 st.pills('Benchmark search results',options=range(len(benchmark_results)),format_func=lambda i: benchmark_labels[i],selection_mode='single',key='benchmark_search_pick',on_change=_select_benchmark)
BENCHMARK=st.session_state.benchmark_symbol
st.caption(f\"Selected benchmark: {st.session_state.benchmark_name} — {BENCHMARK}\")
"""
new="""st.markdown('**Benchmark (optional)**')
USE_BENCHMARK=st.toggle('Use benchmark',value=True,key='use_benchmark')
if 'benchmark_symbol' not in st.session_state: st.session_state.benchmark_symbol=BENCHMARK_TICKER
if 'benchmark_name' not in st.session_state: st.session_state.benchmark_name='FTSE/JSE All Share Index'
if USE_BENCHMARK:
 benchmark_query=st.text_input('Search benchmark',placeholder='Search by index, ETF, fund or ticker',key='benchmark_search_query')
 benchmark_results=search_assets(benchmark_query) if benchmark_query.strip() else []
 if benchmark_results:
  benchmark_labels=[f\"{r['name']} — {r['symbol']}\" for r in benchmark_results]
  def _select_benchmark():
   picked=st.session_state.get('benchmark_search_pick')
   if picked is None: return
   row=benchmark_results[picked]; st.session_state.benchmark_symbol=row['symbol']; st.session_state.benchmark_name=row['name']
  st.pills('Benchmark search results',options=range(len(benchmark_results)),format_func=lambda i: benchmark_labels[i],selection_mode='single',key='benchmark_search_pick',on_change=_select_benchmark)
 BENCHMARK=st.session_state.benchmark_symbol
 st.caption(f\"Selected benchmark: {st.session_state.benchmark_name} — {BENCHMARK}\")
else:
 BENCHMARK=None
 st.caption('No benchmark selected. Portfolio analytics and standalone VaR remain available; benchmark beta/alpha/CAPM and benchmark stress are omitted.')
"""
if old not in s: raise RuntimeError('benchmark UI anchor not found')
s=s.replace(old,new)

# Benchmark data: restrict missing-count to the benchmark's actual overlap with the portfolio.
old="""  if BENCHMARK=='GOVI': raise RuntimeError('Repository GOVI is monthly-only and cannot be used as a weekly benchmark. Select a daily-history market ticker/proxy.')
  bench_p,bench_d,_=load_ticker_components((BENCHMARK,)); bp_all=bench_p[BENCHMARK].resample('W-FRI').last(); bd_all=bench_d[BENCHMARK].resample('W-FRI').sum(); benchmark_missing_weeks=int(bp_all.reindex(prices.index).isna().sum()); bp=bp_all.reindex(prices.index); bd=bd_all.reindex(prices.index,fill_value=0.0)
"""
new="""  benchmark_missing_weeks=0; benchmark_overlap_start=None; benchmark_overlap_end=None
  if USE_BENCHMARK:
   if BENCHMARK=='GOVI': raise RuntimeError('Repository GOVI is monthly-only and cannot be used as a weekly benchmark. Select a daily-history market ticker/proxy.')
   bench_p,bench_d,_=load_ticker_components((BENCHMARK,)); bp_all=bench_p[BENCHMARK].resample('W-FRI').last(); bd_all=bench_d[BENCHMARK].resample('W-FRI').sum()
   bench_valid=bp_all.dropna(); benchmark_overlap_start=max(prices.index.min(),bench_valid.index.min()); benchmark_overlap_end=min(prices.index.max(),bench_valid.index.max())
   benchmark_portfolio_index=prices.index[(prices.index>=benchmark_overlap_start)&(prices.index<=benchmark_overlap_end)]
   benchmark_missing_weeks=int(bp_all.reindex(benchmark_portfolio_index).isna().sum())
   bp=bp_all.reindex(prices.index); bd=bd_all.reindex(prices.index,fill_value=0.0)
  else:
   bp=pd.Series(np.nan,index=prices.index,dtype=float); bd=pd.Series(0.0,index=prices.index,dtype=float)
"""
if old not in s: raise RuntimeError('benchmark data anchor not found')
s=s.replace(old,new)

oldflag="if 'benchmark_missing_weeks' in globals() and benchmark_missing_weeks>0: data_flags.append(f'Benchmark data unavailable for {benchmark_missing_weeks} portfolio week(s). These dates are excluded only from benchmark-dependent analytics (beta, alpha, CAPM and benchmark stress); portfolio history, portfolio returns, CAGR, volatility, drawdown and standalone VaR are unchanged.')"
newflag="""if USE_BENCHMARK and benchmark_missing_weeks>0: data_flags.append(f'Benchmark has {benchmark_missing_weeks} missing week(s) inside its overlap with the portfolio ({benchmark_overlap_start:%Y-%m-%d} to {benchmark_overlap_end:%Y-%m-%d}). Only those benchmark-dependent observations are dropped; portfolio history and portfolio-level analytics are unchanged.')
if USE_BENCHMARK and benchmark_overlap_start>prices.index.min(): st.caption(f'Portfolio history begins {prices.index.min():%Y-%m-%d}. Benchmark-dependent analytics begin at the nearest available benchmark overlap date, {benchmark_overlap_start:%Y-%m-%d}; earlier portfolio observations remain in all portfolio-level calculations.')"""
if oldflag not in s: raise RuntimeError('benchmark flag anchor not found')
s=s.replace(oldflag,newflag)

old="""market_r=(bp-bp.shift(1)+bd)/bp.shift(1)
# Separate benchmark-analysis sample: missing benchmark weeks are excluded ONLY
# from benchmark-dependent calculations. Portfolio values/returns are untouched.
portfolio_r_for_benchmark=vals.PORTFOLIO.pct_change(fill_method=None)
benchmark_analysis=pd.concat([portfolio_r_for_benchmark.rename('Portfolio'),market_r.rename('Benchmark')],axis=1).dropna()
benchmark_return_aligned=benchmark_analysis['Benchmark']
met=stats(vals,benchmark_return_aligned,RF,ppy)"""
new="""market_r=(bp-bp.shift(1)+bd)/bp.shift(1) if USE_BENCHMARK else pd.Series(np.nan,index=prices.index,dtype=float)
portfolio_r_for_benchmark=vals.PORTFOLIO.pct_change(fill_method=None)
benchmark_analysis=pd.concat([portfolio_r_for_benchmark.rename('Portfolio'),market_r.rename('Benchmark')],axis=1).dropna() if USE_BENCHMARK else pd.DataFrame(columns=['Portfolio','Benchmark'])
benchmark_return_aligned=benchmark_analysis['Benchmark'] if USE_BENCHMARK else pd.Series(dtype=float)
met=stats(vals,benchmark_return_aligned,RF,ppy)"""
if old not in s: raise RuntimeError('benchmark analysis anchor not found')
s=s.replace(old,new)

# Benchmark-dependent visual analytics are conditional.
old="""st.divider(); st.subheader(f'{mode} — Beta & Alpha Evolution vs {BENCHMARK}'); roll_beta,roll_alpha,capm_window=rolling_capm(vals,market_r,RF,ppy); line_chart({f'{capm_window}-period Rolling Beta':roll_beta},f'{mode} — Rolling Beta vs {BENCHMARK}','Beta'); line_chart({f'{capm_window}-period Rolling Alpha':roll_alpha*100},f'{mode} — Rolling Annualised CAPM Alpha','Alpha (%)'); cb,ncb=conditional_beta(vals,bp)
"""
new="""if USE_BENCHMARK:
 st.divider(); st.subheader(f'{mode} — Beta & Alpha Evolution vs {BENCHMARK}'); roll_beta,roll_alpha,capm_window=rolling_capm(vals,market_r,RF,ppy); line_chart({f'{capm_window}-period Rolling Beta':roll_beta},f'{mode} — Rolling Beta vs {BENCHMARK}','Beta'); line_chart({f'{capm_window}-period Rolling Alpha':roll_alpha*100},f'{mode} — Rolling Annualised CAPM Alpha','Alpha (%)'); cb,ncb=conditional_beta(vals,bp)
else: cb,ncb=np.nan,0
"""
if old not in s: raise RuntimeError('beta section anchor not found')
s=s.replace(old,new)

s=s.replace("with sc1: use_bench=st.toggle(f'Benchmark −10% Drawdown ({bench_label} — {BENCHMARK})',value=True,key='macro_benchmark')","with sc1: use_bench=st.toggle(f'Benchmark −10% Drawdown ({bench_label} — {BENCHMARK})',value=True,key='macro_benchmark',disabled=not USE_BENCHMARK) if USE_BENCHMARK else False")
s=s.replace("scenario_rows.append(one_period_shock_stats(vals,bp,chg,threshold,RF,ppy,label))","scenario_rows.append(one_period_shock_stats(vals,bp,chg,threshold,RF,ppy,label) if USE_BENCHMARK else one_period_shock_stats(vals,pd.Series(np.nan,index=vals.index),chg,threshold,RF,ppy,label))")

# Walk-forward validator: VaR always runs on full portfolio history; CAPM is optional.
old="""def walk_forward_validation(vals,market_r,rf,ppy=52,window=52,var_method='Historical',var_level=.95):
 rp=vals.PORTFOLIO.pct_change(fill_method=None).rename('Portfolio')
 d=pd.concat([rp,market_r.rename('Benchmark')],axis=1).dropna()
 rfp=(1+rf)**(1/ppy)-1; rows=[]; z95=-1.6448536269514722
 for i in range(window,len(d)):
  train=d.iloc[i-window:i]; test=d.iloc[i]; x=train.Benchmark-rfp; y=train.Portfolio-rfp
  beta=y.cov(x)/x.var() if x.var()>0 else np.nan; alpha=y.mean()-beta*x.mean() if np.isfinite(beta) else np.nan
  capm_pred=rfp+alpha+beta*(test.Benchmark-rfp) if np.isfinite(beta) else np.nan
  tr=train.Portfolio.dropna()
"""
new="""def walk_forward_validation(vals,market_r,rf,ppy=52,window=52,var_method='Historical',var_level=.95):
 rp=vals.PORTFOLIO.pct_change(fill_method=None).dropna().rename('Portfolio')
 mr=market_r.rename('Benchmark') if market_r is not None else pd.Series(dtype=float,name='Benchmark')
 rfp=(1+rf)**(1/ppy)-1; rows=[]; z95=-1.6448536269514722
 for i in range(window,len(rp)):
  train_p=rp.iloc[i-window:i]; test_p=rp.iloc[i]; dt=rp.index[i]; tr=train_p.dropna(); beta=alpha=capm_pred=np.nan; test_b=np.nan
  if len(mr):
   hist=pd.concat([train_p,mr.reindex(train_p.index)],axis=1).dropna()
   if len(hist)>=window:
    x=hist.Benchmark-rfp; y=hist.Portfolio-rfp; beta=y.cov(x)/x.var() if x.var()>0 else np.nan; alpha=y.mean()-beta*x.mean() if np.isfinite(beta) else np.nan; test_b=mr.reindex([dt]).iloc[0]
    capm_pred=rfp+alpha+beta*(test_b-rfp) if np.isfinite(beta) and pd.notna(test_b) else np.nan
"""
if old not in s: raise RuntimeError('walk-forward function anchor not found')
s=s.replace(old,new)
s=s.replace("rows.append({'Date':d.index[i],'Actual Return':float(test.Portfolio),'Benchmark Return':float(test.Benchmark),'CAPM Forecast':capm_pred,'CAPM Alpha':alpha,'CAPM Beta':beta,'VaR 95%':q,'VaR Breach':bool(test.Portfolio<q) if np.isfinite(q) else False,'Forecast Sigma':sigma})","rows.append({'Date':dt,'Actual Return':float(test_p),'Benchmark Return':float(test_b) if pd.notna(test_b) else np.nan,'CAPM Forecast':capm_pred,'CAPM Alpha':alpha,'CAPM Beta':beta,'VaR 95%':q,'VaR Breach':bool(test_p<q) if np.isfinite(q) else False,'Forecast Sigma':sigma})")
s=s.replace("wf=walk_forward_validation(vals,market_r,RF,ppy,52,wf_method,.95)","wf=walk_forward_validation(vals,market_r if USE_BENCHMARK else None,RF,ppy,52,wf_method,.95)")
s=s.replace("st.warning('Walk-forward validation requires at least 53 aligned weekly portfolio/benchmark observations.')","st.warning('Walk-forward validation requires at least 53 weekly portfolio observations.')")

p.write_text(s)
s=p.read_text()
for req in ["Benchmark (optional)","USE_BENCHMARK=st.toggle('Use benchmark'","benchmark_overlap_start=max(prices.index.min(),bench_valid.index.min())","Only those benchmark-dependent observations are dropped","Portfolio history begins","if USE_BENCHMARK:","walk_forward_validation(vals,market_r if USE_BENCHMARK else None","len(rp)"]:
 assert req in s, req
assert "benchmark_missing_weeks=int(bp_all.reindex(prices.index).isna().sum())" not in s
assert "aligned_index=prices.index.intersection" not in s
