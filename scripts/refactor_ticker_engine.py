from pathlib import Path
p=Path('app.py'); s=p.read_text()
a=s.index('DEFAULT_ALLOC='); b=s.index('\nSHORT_WINDOWS=',a)
s=s[:a]+'''DEFAULT_TICKERS=["^J203.JO","^GSPC","STXGVI.JO","GLD.JO","EXX.JO","BRK-B","EEM","AGG"]
DEFAULT_WEIGHTS={"^J203.JO":0.3328,"^GSPC":0.1664,"STXGVI.JO":0.1664,"GLD.JO":0.0374,"EXX.JO":0.0416,"BRK-B":0.0466,"EEM":0.0541,"AGG":0.0507}
BENCHMARK_TICKER="^J203.JO"
'''+s[b:]
a=s.index('@st.cache_data(ttl=3600,show_spinner=False)\ndef load_yahoo_components():'); b=s.index('\ndef build_bond_components',a)
s=s[:a]+'''@st.cache_data(ttl=3600,show_spinner=False)
def load_ticker_components(tickers):
 prices={}; divs={}; splits={}; metadata={}
 for ticker in tickers:
  obj=yf.Ticker(ticker); h=obj.history(start=START,auto_adjust=False,actions=True)
  if h.empty: raise RuntimeError(f'Yahoo Finance returned no data for exact ticker {ticker}')
  h=h.copy(); h.index=pd.to_datetime(h.index).tz_localize(None); h=h.sort_index()
  close=pd.to_numeric(h['Close'],errors='coerce').dropna(); div=pd.to_numeric(h.get('Dividends',0.0),errors='coerce').fillna(0.0).reindex(close.index,fill_value=0.0); sp=pd.to_numeric(h.get('Stock Splits',0.0),errors='coerce').fillna(0.0).reindex(close.index,fill_value=0.0)
  if len(close)<2: raise RuntimeError(f'{ticker}: fewer than two valid Close observations')
  prices[ticker]=close.rename(ticker); divs[ticker]=div.rename(ticker); splits[ticker]=sp.rename(ticker)
  try: metadata[ticker]=obj.history_metadata or {}
  except Exception: metadata[ticker]={}
 return prices,divs,splits,metadata
'''+s[b:]
a=s.index('\ndef build_master():'); b=s.index('\ndef resolve_dates',a)
s=s[:a]+'''
def build_master(selected):
 yahoo=[x for x in selected if x!='GOVI']; yp,yd,ys,meta=load_ticker_components(tuple(yahoo)) if yahoo else ({},{},{},{})
 if yahoo:
  mp=pd.DataFrame({x:v.resample('ME').last() for x,v in yp.items()}); md=pd.DataFrame({x:v.resample('ME').sum() for x,v in yd.items()})
 else:
  g0=load_govi_history(); mp=pd.DataFrame(index=g0.index); md=pd.DataFrame(index=g0.index)
 g=load_govi_history(); val={'last_govi':g.index.max(),'source':'repository GOVI'}
 if 'GOVI' in selected: mp['GOVI']=g.reindex(mp.index).ffill(); md['GOVI']=0.0
 return mp.loc[START:],md.reindex(mp.index,fill_value=0.0).loc[START:],g,val,meta,ys

def build_daily(selected):
 if 'GOVI' in selected: raise RuntimeError('GOVI is monthly-only. For daily analysis use an explicit investable Yahoo ticker such as STXGVI.JO.')
 yp,yd,ys,meta=load_ticker_components(tuple(selected)); dp=pd.concat(yp.values(),axis=1); dd=pd.concat(yd.values(),axis=1).reindex(dp.index,fill_value=0.0); g=load_govi_history(); val={'last_govi':g.index.max(),'source':'repository GOVI'}
 return dp,dd,g,val,meta,ys
'''+s[b:]
a=s.index('\ndef fx_attribution('); b=s.index('\ntitle_col,',a); s=s[:a]+s[b:]
old="ASSETS=st.multiselect('Assets',ALL_ASSETS,default=ALL_ASSETS)\nif not ASSETS: st.error('Select at least one asset.'); st.stop()\nst.markdown('**Weights**'); cols=st.columns(3); raww={}\nfor i,a0 in enumerate(ASSETS):\n with cols[i%3]: raww[a0]=st.number_input(f'{a0} (%)',0.0,100.0,float(DEFAULT_ALLOC[a0]/DEFAULT_INITIAL*100),.25)/100"
new="ticker_text=st.text_input('Exact Yahoo Finance tickers (comma-separated; GOVI is the repository series)',value=','.join(DEFAULT_TICKERS),help='Any Yahoo Finance ticker may be entered using its exact symbol. Example: STXGVI.JO. No automatic FX overlay is applied.')\nASSETS=list(dict.fromkeys([x.strip().upper() for x in ticker_text.split(',') if x.strip()]))\nif not ASSETS: st.error('Enter at least one exact ticker.'); st.stop()\nst.markdown('**Weights**'); cols=st.columns(3); raww={}\ndefault_sum=sum(DEFAULT_WEIGHTS.get(x,0.0) for x in ASSETS)\nfor i,a0 in enumerate(ASSETS):\n default=(DEFAULT_WEIGHTS.get(a0,0.0)/default_sum*100) if default_sum>0 else 100/len(ASSETS)\n with cols[i%3]: raww[a0]=st.number_input(f'{a0} (%)',0.0,100.0,float(default),.25,key=f'w_{a0}')/100"
assert old in s; s=s.replace(old,new)
old="if daily_mode: full_p,full_d,full_l,full_fx,govi,bond_validation=build_daily(ASSETS)\n  else: full_p,full_d,full_l,full_fx,govi,bond_validation=build_master()"
new="if daily_mode: full_p,full_d,govi,bond_validation,source_meta,split_events=build_daily(ASSETS)\n  else: full_p,full_d,govi,bond_validation,source_meta,split_events=build_master(ASSETS)"
assert old in s; s=s.replace(old,new)
s=s.replace("if 'SA_BONDS' in ASSETS and prices.index[-1] > bond_validation['last_govi']:\n data_flags.append(f'SA_BONDS uses STXGVI continuation after GOVI cutoff {bond_validation[\"last_govi\"]:%d %b %Y}.')","if 'GOVI' in ASSETS:\n data_flags.append(f'GOVI is a repository monthly total-return index series through {bond_validation[\"last_govi\"]:%d %b %Y}; it is not a Yahoo ticker.')")
old="market_r=asset_r['ALSI'] if 'ALSI' in asset_r else pd.Series(index=asset_r.index,dtype=float); met=stats(vals,market_r,RF,ppy) if 'ALSI' in ASSETS else stats(vals,vals.PORTFOLIO.pct_change(fill_method=None),RF,ppy)"
new="bench_p,bench_d,_,_=load_ticker_components((BENCHMARK_TICKER,)); bp=bench_p[BENCHMARK_TICKER].reindex(prices.index).ffill(); bd=bench_d[BENCHMARK_TICKER].reindex(prices.index,fill_value=0.0); market_r=(bp-bp.shift(1)+bd)/bp.shift(1); met=stats(vals,market_r,RF,ppy)"
assert old in s; s=s.replace(old,new)
s=s.replace("bhm=stats(bh,market_r if 'ALSI' in ASSETS else bh.PORTFOLIO.pct_change(),RF,ppy); rbm=stats(rb,market_r if 'ALSI' in ASSETS else rb.PORTFOLIO.pct_change(),RF,ppy)","bhm=stats(bh,market_r,RF,ppy); rbm=stats(rb,market_r,RF,ppy)")
old="if 'ALSI' in ASSETS:\n st.divider(); st.subheader(f'{mode} — Beta & Alpha Evolution vs ALSI'); roll_beta,roll_alpha,capm_window=rolling_capm(vals,market_r,RF,ppy); line_chart({f'{capm_window}-period Rolling Beta':roll_beta},f'{mode} — Rolling Beta vs ALSI','Beta'); line_chart({f'{capm_window}-period Rolling Alpha':roll_alpha*100},f'{mode} — Rolling Annualised CAPM Alpha','Alpha (%)'); cb,ncb=conditional_beta(vals,prices['ALSI']); st.metric('Conditional Beta — ALSI drawdown ≥10%', 'N/A' if not np.isfinite(cb) else f'{cb:.3f}', help=f'Calculated from {ncb} configured observations where ALSI was at least 10% below its running peak.')"
new="st.divider(); st.subheader(f'{mode} — Beta & Alpha Evolution vs {BENCHMARK_TICKER}'); roll_beta,roll_alpha,capm_window=rolling_capm(vals,market_r,RF,ppy); line_chart({f'{capm_window}-period Rolling Beta':roll_beta},f'{mode} — Rolling Beta vs {BENCHMARK_TICKER}','Beta'); line_chart({f'{capm_window}-period Rolling Alpha':roll_alpha*100},f'{mode} — Rolling Annualised CAPM Alpha','Alpha (%)'); cb,ncb=conditional_beta(vals,bp); st.metric(f'Conditional Beta — {BENCHMARK_TICKER} drawdown ≥10%', 'N/A' if not np.isfinite(cb) else f'{cb:.3f}', help=f'Calculated from {ncb} configured observations where {BENCHMARK_TICKER} was at least 10% below its running peak.')"
assert old in s; s=s.replace(old,new)
marker="st.dataframe(aar,hide_index=True,use_container_width=True)"
attr="""st.dataframe(aar,hide_index=True,use_container_width=True)
st.subheader('Return Attribution by Ticker — Capital Gain vs Income')
attr=[]
for a0 in ASSETS:
 p0=float(prices[a0].iloc[0]); p1=float(prices[a0].iloc[-1]); cap=(p1-p0)/p0; inc=float(divs[a0].iloc[1:].sum())/p0; total=cap+inc
 attr.append({'Ticker':a0,'Total Return':total,'Capital Gain':cap,'Income / Distributions':inc,'Capital Gain % of Total':cap/total if not np.isclose(total,0) else np.nan,'Income % of Total':inc/total if not np.isclose(total,0) else np.nan})
at=pd.DataFrame(attr)
for c0 in ['Total Return','Capital Gain','Income / Distributions','Capital Gain % of Total','Income % of Total']: at[c0]=at[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
st.dataframe(at,hide_index=True,use_container_width=True)
st.caption('Holding-period identity: total return = capital gain + explicit cash income/distributions. Attribution percentages are each component as a proportion of that ticker’s total return.')"""
s=s.replace(marker,attr,1)
a=s.index("\nst.divider(); st.subheader('Macro Tracker — FX Attribution to Total Return')"); b=s.index("\n@st.dialog('Full Calculation Workings'",a); s=s[:a]+s[b:]
# Replace the first report subsection through Portfolio construction.
a=s.index(" st.header('Data & total-return construction')",s.index("def show_latex_report")); b=s.index(" st.header('Portfolio construction')",a)
s=s[:a]+""" st.header('Data & total-return construction')
 st.write('Each Yahoo instrument uses the exact user-entered ticker with history(auto_adjust=False, actions=True). Close is the price series; Dividends is explicit cash income; Stock Splits is captured for audit. Adjusted Close is never used. No FX overlay is applied.')
 st.latex(r'r_{a,t}=\\frac{P_{a,t}-P_{a,t-1}+D_{a,t}}{P_{a,t-1}}')
 st.latex(r'R^{hold}_{a}=\\frac{P_{a,T}-P_{a,0}+\\sum_{t=1}^{T}D_{a,t}}{P_{a,0}}')
 st.latex(r'R^{hold}_{a}=R^{capital}_{a}+R^{income}_{a}')
 st.latex(r'CapitalShare_a=R^{capital}_a/R^{hold}_a,\\quad IncomeShare_a=R^{income}_a/R^{hold}_a')
"""+s[b:]
# Remove FX report subsection if still present.
if " st.header('FX attribution')" in s:
 a=s.index(" st.header('FX attribution')"); b=s.index(" st.caption('N is",a); s=s[:a]+s[b:]
s=s.replace("st.write('**Market assets and FX** — Yahoo Finance raw Close and actions. Adjusted Close is not used.')","st.write('**Yahoo instruments** — exact user-entered Yahoo Finance ticker symbols; history(auto_adjust=False, actions=True). Close, Dividends and Stock Splits are captured. Adjusted Close is not used. No automatic FX overlay is applied.')")
s=s.replace("st.write('**South African government bonds** — repository GOVI monthly history; STXGVI continuation only after the authoritative GOVI cutoff.')","st.write('**Repository series** — GOVI is the only non-Yahoo selectable series and is monthly-only. STXGVI.JO or any other investable proxy must be selected explicitly by exact Yahoo ticker.')")
s=s.replace("st.write('**Corporate actions** — Yahoo Close is treated as split-normalised; splits are not applied a second time. Cash dividends/distributions are explicit and follow the selected reinvestment setting.')","st.write('**Corporate actions** — Yahoo Close from auto_adjust=False is used; Stock Splits are captured for audit and are not applied a second time. Cash dividends/distributions are explicit and follow the selected reinvestment setting.')")
s=s.replace("st.write(f'**GOVI cutoff** — {bond_validation[\"last_govi\"]:%d %b %Y}. No monthly GOVI observations are interpolated into fake daily prices.')","st.write(f'**GOVI cutoff** — {bond_validation[\"last_govi\"]:%d %b %Y}. GOVI is never interpolated into fake daily observations.')")
p.write_text(s)
