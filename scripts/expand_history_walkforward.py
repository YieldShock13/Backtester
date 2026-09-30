from pathlib import Path
p=Path('app.py'); s=p.read_text()

# Portfolio observations remain authoritative. Benchmark availability must never
# remove an otherwise valid portfolio week. Benchmark-dependent analytics get a
# separate inner-aligned return sample below.
old="""  bench_p,bench_d,_=load_ticker_components((BENCHMARK,)); bp_all=bench_p[BENCHMARK].resample('W-FRI').last(); bd_all=bench_d[BENCHMARK].resample('W-FRI').sum(); benchmark_missing_weeks=int(bp_all.reindex(prices.index).isna().sum()); aligned_index=prices.index.intersection(bp_all.dropna().index); prices=prices.reindex(aligned_index).dropna(how='any'); divs=divs.reindex(prices.index,fill_value=0.0); bp=bp_all.reindex(prices.index); bd=bd_all.reindex(prices.index,fill_value=0.0)
  if len(prices)<2: raise RuntimeError('Selected timeline has fewer than two complete-case weekly observations across assets and benchmark')
"""
new="""  bench_p,bench_d,_=load_ticker_components((BENCHMARK,)); bp_all=bench_p[BENCHMARK].resample('W-FRI').last(); bd_all=bench_d[BENCHMARK].resample('W-FRI').sum(); benchmark_missing_weeks=int(bp_all.reindex(prices.index).isna().sum()); bp=bp_all.reindex(prices.index); bd=bd_all.reindex(prices.index,fill_value=0.0)
  if len(prices)<2: raise RuntimeError('Selected timeline has fewer than two synchronized portfolio observations')
"""
if old not in s: raise RuntimeError('Benchmark-removal block not found')
s=s.replace(old,new)

old="market_r=(bp-bp.shift(1)+bd)/bp.shift(1); met=stats(vals,market_r,RF,ppy)"
new="""market_r=(bp-bp.shift(1)+bd)/bp.shift(1)
# Separate benchmark-analysis sample: missing benchmark weeks are excluded ONLY
# from benchmark-dependent calculations. Portfolio values/returns are untouched.
portfolio_r_for_benchmark=vals.PORTFOLIO.pct_change(fill_method=None)
benchmark_analysis=pd.concat([portfolio_r_for_benchmark.rename('Portfolio'),market_r.rename('Benchmark')],axis=1).dropna()
benchmark_return_aligned=benchmark_analysis['Benchmark']
met=stats(vals,benchmark_return_aligned,RF,ppy)"""
if old not in s: raise RuntimeError('market_r stats anchor not found')
s=s.replace(old,new)

oldflag="if 'benchmark_missing_weeks' in globals() and benchmark_missing_weeks>0: data_flags.append(f'Weekly alignment excluded {benchmark_missing_weeks} additional week(s) with no genuine benchmark observation.')"
newflag="if 'benchmark_missing_weeks' in globals() and benchmark_missing_weeks>0: data_flags.append(f'Benchmark data unavailable for {benchmark_missing_weeks} portfolio week(s). These dates are excluded only from benchmark-dependent analytics (beta, alpha, CAPM and benchmark stress); portfolio history, portfolio returns, CAGR, volatility, drawdown and standalone VaR are unchanged.')"
if oldflag not in s: raise RuntimeError('Benchmark flag anchor not found')
s=s.replace(oldflag,newflag)

# Walk-forward CAPM uses the benchmark-aligned sample naturally; standalone VaR
# remains based on the full portfolio return series inside the validator function.
s=s.replace("wf=walk_forward_validation(vals,market_r,RF,ppy,52,wf_method,.95)","wf=walk_forward_validation(vals,market_r,RF,ppy,52,wf_method,.95)")

# Make Data Audit explicit about scope.
old_a="benchmark-incomplete weeks excluded={benchmark_missing_weeks}; final aligned weeks={len(prices)}. No interpolation or cross-week forward fill."
new_a="benchmark-missing portfolio weeks={benchmark_missing_weeks}; portfolio weeks retained={len(prices)}. Benchmark-missing dates are dropped only from benchmark-dependent analytics; portfolio-level history and standalone risk/return calculations are unchanged. No interpolation or cross-week forward fill."
s=s.replace(old_a,new_a)

p.write_text(s)
s=p.read_text()
for req in ["Benchmark data unavailable for {benchmark_missing_weeks} portfolio week(s)","excluded only from benchmark-dependent analytics","portfolio history, portfolio returns, CAGR, volatility, drawdown and standalone VaR are unchanged","benchmark_analysis=pd.concat","portfolio_r_for_benchmark=vals.PORTFOLIO.pct_change(fill_method=None)","portfolio weeks retained={len(prices)}"]:
    assert req in s, req
assert "aligned_index=prices.index.intersection(bp_all.dropna().index)" not in s
assert "prices=prices.reindex(aligned_index)" not in s
