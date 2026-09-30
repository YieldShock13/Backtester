from pathlib import Path
import py_compile

p=Path("app.py")
s=p.read_text()
old=""" for asset in hedged_assets:
  pair=fx_pairs[asset]; fx=load_fx_pair(pair,daily_mode).reindex(prices.index); fr=fx.pct_change(fill_method=None)
  d=pd.concat([asset_total[asset].rename('asset'),fr.rename('fx')],axis=1).dropna()
  if len(d)<12: raise RuntimeError(f'{asset}: fewer than 12 aligned observations for FX beta estimation against {pair}')
"""
new=""" for asset in hedged_assets:
  pair=fx_pairs[asset]
  fx_raw=load_fx_pair(pair,daily_mode).dropna().sort_index()
  # Align by portfolio week, not exact timestamp. Each portfolio observation receives
  # the last genuine FX close from the same W-FRI week only; never carry across weeks.
  fx_week=fx_raw.copy()
  fx_week.index=fx_week.index.to_period('W-FRI').end_time.normalize()
  fx_week=fx_week.groupby(level=0).last()
  portfolio_week=pd.DatetimeIndex(prices.index).to_period('W-FRI').end_time.normalize()
  fx=pd.Series(fx_week.reindex(portfolio_week).to_numpy(),index=prices.index,name=pair)
  fr=fx.pct_change(fill_method=None)
  d=pd.concat([asset_total[asset].rename('asset'),fr.rename('fx')],axis=1).dropna()
  if len(d)<12: raise RuntimeError(f'{asset}: fewer than 12 same-week aligned observations for FX beta estimation against {pair}')
"""
if old not in s:
    raise RuntimeError("FX hedge block not found")
s=s.replace(old,new)
p.write_text(s)
py_compile.compile(str(p),doraise=True)
s=p.read_text()
for x in ["Align by portfolio week, not exact timestamp","to_period('W-FRI')","never carry across weeks","same-week aligned observations"]:
    assert x in s,x
print("PASS: FX hedge uses genuine same-week FX observations and app compiles")
