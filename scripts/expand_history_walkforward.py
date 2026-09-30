from pathlib import Path
p=Path('app.py'); s=p.read_text()

# Build weekly observations from the latest genuine DAILY date shared by every
# selected asset in each week. This avoids throwing away a week merely because
# different exchanges had different final trading days. No interpolation/fill.
old="""def build_master(selected):
 yahoo=[x for x in selected if x!='GOVI']; yp,yd,ys=load_ticker_components(tuple(yahoo)) if yahoo else ({},{},{})
 if yahoo:
  mp=pd.DataFrame({x:v.resample('W-FRI').last() for x,v in yp.items()}); md=pd.DataFrame({x:v.resample('W-FRI').sum() for x,v in yd.items()})
 else:
  g0=load_govi_history(); mp=pd.DataFrame(index=g0.index); md=pd.DataFrame(index=g0.index)
 g=load_govi_history(); val={'last_govi':g.index.max(),'source':'repository GOVI'}
 if 'GOVI' in selected: raise RuntimeError('Repository GOVI is monthly-only. For the weekly backtest select a Yahoo-traded bond/index proxy with daily history instead.')
 return mp,md.reindex(mp.index,fill_value=0.0),g,val,ys
"""
new="""def build_master(selected):
 yahoo=[x for x in selected if x!='GOVI']; yp,yd,ys=load_ticker_components(tuple(yahoo)) if yahoo else ({},{},{})
 if yahoo:
  daily_px=pd.concat([yp[x].rename(x) for x in yahoo],axis=1)
  mutual_daily=daily_px.dropna(how='any')
  # For each Friday-labelled week, select the latest actual calendar date on which
  # ALL selected assets have a genuine Close. Values remain genuine daily closes.
  mp=mutual_daily.groupby(mutual_daily.index.to_period('W-FRI')).tail(1).copy()
  mp.index=mp.index.to_period('W-FRI').end_time.normalize()
  mp=mp[~mp.index.duplicated(keep='last')].sort_index()
  # Cash distributions remain actual flows and are summed over their calendar week.
  md=pd.DataFrame({x:yd[x].resample('W-FRI').sum() for x in yahoo}).reindex(mp.index,fill_value=0.0)
 else:
  g0=load_govi_history(); mp=pd.DataFrame(index=g0.index); md=pd.DataFrame(index=g0.index)
 g=load_govi_history(); val={'last_govi':g.index.max(),'source':'repository GOVI'}
 if 'GOVI' in selected: raise RuntimeError('Repository GOVI is monthly-only. For the weekly backtest select a Yahoo-traded bond/index proxy with daily history instead.')
 return mp,md.reindex(mp.index,fill_value=0.0),g,val,ys
"""
if old not in s:
    raise RuntimeError('build_master anchor not found')
s=s.replace(old,new)

# The resulting weekly matrix is already synchronized across selected assets.
# Keep the complete-case guard for genuinely unrecoverable weeks and audit them,
# but do not elevate a tiny number of excluded weeks into the prominent DATA FLAGS banner.
oldflag="if 'excluded_incomplete_weeks' in globals() and excluded_incomplete_weeks>0: data_flags.append(f'Weekly alignment excluded {excluded_incomplete_weeks} incomplete week(s) within the common asset history ({common_inception:%Y-%m-%d} to {common_endpoint:%Y-%m-%d}) because at least one selected asset had no genuine observation that week. Pre-inception/post-history gaps are not counted. No interpolation or cross-week price fill was used.')"
s=s.replace(oldflag,"# Weekly alignment exclusions are documented in Data Audit; they are not promoted to DATA FLAGS unless they prevent the backtest.")

# Make the audit language describe the recovery rule accurately.
old_a="f'Comparable common-history weeks={raw_week_count} ({common_inception:%Y-%m-%d} to {common_endpoint:%Y-%m-%d}); incomplete weeks excluded={excluded_incomplete_weeks}; benchmark-incomplete weeks excluded={benchmark_missing_weeks}; final aligned weeks={len(prices)}; missing weeks by asset={miss_txt}. Pre-inception/post-history weeks are not counted. No interpolation or cross-week forward fill.'"
new_a="f'Weekly observations use the latest genuine daily date shared by all selected assets within each Friday-labelled week. Comparable weeks={raw_week_count} ({common_inception:%Y-%m-%d} to {common_endpoint:%Y-%m-%d}); unrecoverable asset weeks excluded={excluded_incomplete_weeks}; benchmark-incomplete weeks excluded={benchmark_missing_weeks}; final aligned weeks={len(prices)}. No interpolation or cross-week forward fill.'"
s=s.replace(old_a,new_a)

p.write_text(s)
s=p.read_text()
for req in ["mutual_daily=daily_px.dropna(how='any')","groupby(mutual_daily.index.to_period('W-FRI')).tail(1)","latest genuine daily date shared by all selected assets","No interpolation or cross-week forward fill"]:
    assert req in s, req
