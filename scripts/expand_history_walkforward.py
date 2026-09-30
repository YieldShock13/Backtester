from pathlib import Path
p=Path('app.py'); s=p.read_text()

# Maximum available history.
s=s.replace('START="2012-02-01"','START=None')
s=s.replace("h=yf.Ticker(ticker).history(start=START,interval='1d',auto_adjust=False,actions=True)","h=yf.Ticker(ticker).history(period='max',interval='1d',auto_adjust=False,actions=True)")
s=s.replace("return mp.loc[START:],md.reindex(mp.index,fill_value=0.0).loc[START:],g,val,ys","return mp,md.reindex(mp.index,fill_value=0.0),g,val,ys")
s=s.replace("custom_start=st.date_input('Custom start',value=pd.Timestamp(START).date())","custom_start=st.date_input('Custom start',value=pd.Timestamp('1900-01-01').date())")

# Correct the already-deployed weekly alignment implementation. Count missing weeks only
# inside the common investable life of all selected assets; never count pre-inception gaps.
old="asset_weekly=full_p[ASSETS]; raw_week_count=len(asset_weekly); missing_by_asset=asset_weekly.isna().sum().astype(int).to_dict(); common=asset_weekly.dropna(how='any').index; dropped_asset_weeks=raw_week_count-len(common); start,end,requested=resolve_dates(common,timeline,custom_start,custom_end,daily_mode); prices=full_p.loc[(full_p.index>=start)&(full_p.index<=end),ASSETS].dropna(how='any'); divs=full_d.reindex(prices.index,fill_value=0.0)[ASSETS]"
new="asset_weekly=full_p[ASSETS]; first_valid=asset_weekly.apply(lambda c:c.first_valid_index()).dropna(); last_valid=asset_weekly.apply(lambda c:c.last_valid_index()).dropna(); common_inception=max(first_valid); common_endpoint=min(last_valid); comparable=asset_weekly.loc[(asset_weekly.index>=common_inception)&(asset_weekly.index<=common_endpoint)]; raw_week_count=len(comparable); missing_by_asset=comparable.isna().sum().astype(int).to_dict(); common=comparable.dropna(how='any').index; excluded_incomplete_weeks=int(comparable.isna().any(axis=1).sum()); start,end,requested=resolve_dates(common,timeline,custom_start,custom_end,daily_mode); prices=comparable.loc[(comparable.index>=start)&(comparable.index<=end),ASSETS].dropna(how='any'); divs=full_d.reindex(prices.index,fill_value=0.0)[ASSETS]"
if old not in s and 'common_inception=max(first_valid)' not in s:
    raise RuntimeError('Current weekly alignment block not found')
s=s.replace(old,new)

oldflag="if 'dropped_asset_weeks' in globals() and dropped_asset_weeks>0: data_flags.append(f'Weekly alignment excluded {dropped_asset_weeks} asset-weeks from the union calendar because at least one selected asset had no genuine observation in that week. No interpolation or cross-week price fill was used.')"
newflag="if 'excluded_incomplete_weeks' in globals() and excluded_incomplete_weeks>0: data_flags.append(f'Weekly alignment excluded {excluded_incomplete_weeks} incomplete week(s) within the common asset history ({common_inception:%Y-%m-%d} to {common_endpoint:%Y-%m-%d}) because at least one selected asset had no genuine observation that week. Pre-inception/post-history gaps are not counted. No interpolation or cross-week price fill was used.')"
s=s.replace(oldflag,newflag)

# Audit row if not already present.
audit_anchor="if 'STXGVI.JO' in ASSETS: add('Source validation'"
audit="""if 'missing_by_asset' in globals():
  miss_txt=', '.join(f'{k}: {v}' for k,v in missing_by_asset.items() if v) or 'none'
  add('Alignment','Complete-case weekly alignment','PASS' if excluded_incomplete_weeks==0 and benchmark_missing_weeks==0 else 'WARNING',f'Comparable common-history weeks={raw_week_count} ({common_inception:%Y-%m-%d} to {common_endpoint:%Y-%m-%d}); incomplete weeks excluded={excluded_incomplete_weeks}; benchmark-incomplete weeks excluded={benchmark_missing_weeks}; final aligned weeks={len(prices)}; missing weeks by asset={miss_txt}. Pre-inception/post-history weeks are not counted. No interpolation or cross-week forward fill.')
 """
if "add('Alignment','Complete-case weekly alignment'" not in s:
    if audit_anchor not in s: raise RuntimeError('Audit insertion anchor not found')
    s=s.replace(audit_anchor,audit+audit_anchor)

p.write_text(s)
s=p.read_text()
for req in ["period='max'","common_inception=max(first_valid)","excluded_incomplete_weeks","Complete-case weekly alignment","Pre-inception/post-history gaps are not counted","No interpolation or cross-week price fill"]:
    assert req in s, req
assert 'dropped_asset_weeks' not in s
assert 'START="2012-02-01"' not in s
