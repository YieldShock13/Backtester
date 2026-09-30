from pathlib import Path
p=Path('app.py'); s=p.read_text()
needle="""def conditional_beta(v,market_price,threshold=-.10):\n rp=v.PORTFOLIO.pct_change(fill_method=None); rm=market_price.pct_change(fill_method=None); dd=market_price/market_price.cummax()-1; d=pd.concat([rp.rename('P'),rm.rename('M'),dd.rename('DD')],axis=1).dropna(); d=d[d.DD<=threshold]\n return d.P.cov(d.M)/d.M.var() if len(d)>=2 and d.M.var()>0 else np.nan,len(d)\n"""
addition=r'''

@st.cache_data(ttl=3600,show_spinner=False)
def load_macro_factors(daily_mode):
 symbols={'Oil':'CL=F','VIX':'^VIX','MOVE':'^MOVE'}
 yp,_,_=load_ticker_components(tuple(symbols.values()))
 out={}
 for name,sym in symbols.items():
  x=yp[sym].astype(float).sort_index()
  if not daily_mode: x=x.resample('ME').last()
  out[name]=x.rename(name)
 return pd.DataFrame(out)

def macro_scenario_stats(vals,market_price,factor_series,mask,rf,ppy,label,definition):
 rp=vals.PORTFOLIO.pct_change(fill_method=None).rename('P')
 rm=market_price.pct_change(fill_method=None).rename('M')
 f=factor_series.rename('F') if factor_series is not None else pd.Series(index=rp.index,dtype=float,name='F')
 d=pd.concat([rp,rm,f],axis=1).reindex(rp.index)
 d['Stress']=mask.reindex(d.index,fill_value=False).astype(bool)
 d=d.dropna(subset=['P','M']); stress=d[d.Stress]
 n=len(stress); rfp=(1+rf)**(1/ppy)-1
 beta=alpha=np.nan
 if n>=2 and stress.M.var()>0:
  x=stress.M-rfp; y=stress.P-rfp; beta=y.cov(x)/x.var()
  a=y.mean()-beta*x.mean(); alpha=(1+a)**ppy-1 if 1+a>0 else np.nan
 return {'Scenario':label,'Definition':definition,'Stress Obs':n,'Portfolio Return':(1+stress.P).prod()-1 if n else np.nan,'Avg Portfolio Return':stress.P.mean() if n else np.nan,'Annualised Volatility':stress.P.std()*np.sqrt(ppy) if n>=2 else np.nan,'Conditional Beta':beta,'Conditional Alpha':alpha,'Positive Periods':(stress.P>0).mean() if n else np.nan,'Worst Portfolio Period':stress.P.min() if n else np.nan,'Avg JSE Return':stress.M.mean() if n else np.nan}
'''
if addition.strip() not in s:
 if needle not in s: raise SystemExit('conditional_beta anchor missing')
 s=s.replace(needle,needle+addition,1)
old="""st.divider(); st.subheader(f'{mode} — Beta & Alpha Evolution vs {BENCHMARK_TICKER}'); roll_beta,roll_alpha,capm_window=rolling_capm(vals,market_r,RF,ppy); line_chart({f'{capm_window}-period Rolling Beta':roll_beta},f'{mode} — Rolling Beta vs {BENCHMARK_TICKER}','Beta'); line_chart({f'{capm_window}-period Rolling Alpha':roll_alpha*100},f'{mode} — Rolling Annualised CAPM Alpha','Alpha (%)'); cb,ncb=conditional_beta(vals,bp); st.metric(f'Conditional Beta — {BENCHMARK_TICKER} drawdown ≥10%','N/A' if not np.isfinite(cb) else f'{cb:.3f}')\n"""
new=r'''st.divider(); st.subheader(f'{mode} — Beta & Alpha Evolution vs {BENCHMARK_TICKER}'); roll_beta,roll_alpha,capm_window=rolling_capm(vals,market_r,RF,ppy); line_chart({f'{capm_window}-period Rolling Beta':roll_beta},f'{mode} — Rolling Beta vs {BENCHMARK_TICKER}','Beta'); line_chart({f'{capm_window}-period Rolling Alpha':roll_alpha*100},f'{mode} — Rolling Annualised CAPM Alpha','Alpha (%)'); cb,ncb=conditional_beta(vals,bp)

st.divider(); st.subheader('Macro Risk & Conditional Performance')
st.caption('Historical conditional regimes within the configured backtest window. σ thresholds are estimated from factor changes over that same configured window; these are conditional historical observations, not hypothetical repricing shocks.')
sc1,sc2,sc3,sc4=st.columns(4)
with sc1: use_jse=st.toggle('JSE drawdown ≥10%',value=True,key='macro_jse')
with sc2: use_oil=st.toggle('Oil shock +2σ',value=False,key='macro_oil')
with sc3: use_vix=st.toggle('VIX shock +2σ',value=False,key='macro_vix')
with sc4: use_move=st.toggle('MOVE shock +1.5σ',value=False,key='macro_move')
scenario_rows=[]; macro_factor_meta=[]
if use_jse:
 jse_dd=bp/bp.cummax()-1; jse_mask=jse_dd<=-.10
 scenario_rows.append(macro_scenario_stats(vals,bp,None,jse_mask,RF,ppy,'JSE Drawdown ≥10%','JSE benchmark drawdown from running peak ≤ -10%'))
 macro_factor_meta.append({'Scenario':'JSE Drawdown ≥10%','Factor':BENCHMARK_TICKER,'Transformation':'drawdown from running peak','Threshold':'≤ -10%','Stress Obs':int(jse_mask.sum())})
if use_oil or use_vix or use_move:
 try:
  mf=load_macro_factors(daily_mode).reindex(prices.index).ffill()
  for name,use,zcut,label in [('Oil',use_oil,2.0,'Oil +2σ'),('VIX',use_vix,2.0,'VIX +2σ'),('MOVE',use_move,1.5,'MOVE +1.5σ')]:
   if not use: continue
   chg=mf[name].pct_change(fill_method=None); mu=chg.mean(); sig=chg.std(); threshold=mu+zcut*sig; mask=chg>=threshold
   scenario_rows.append(macro_scenario_stats(vals,bp,chg,mask,RF,ppy,label,f'{name} percentage change ≥ sample mean + {zcut:g}σ'))
   macro_factor_meta.append({'Scenario':label,'Factor':name,'Transformation':'period percentage change','Mean':mu,'Std Dev':sig,'Threshold':threshold,'Stress Obs':int(mask.sum())})
 except Exception as e:
  st.warning(f'Macro factor data unavailable for selected scenario(s): {e}')
scenario_df=pd.DataFrame(scenario_rows)
macro_factor_meta_df=pd.DataFrame(macro_factor_meta)
if not scenario_df.empty:
 display_scen=scenario_df.copy()
 for c0 in ['Portfolio Return','Avg Portfolio Return','Annualised Volatility','Conditional Alpha','Positive Periods','Worst Portfolio Period','Avg JSE Return']:
  display_scen[c0]=display_scen[c0].map(lambda x:f'{x:.2%}' if pd.notna(x) else 'N/A')
 display_scen['Conditional Beta']=display_scen['Conditional Beta'].map(lambda x:f'{x:.3f}' if pd.notna(x) else 'N/A')
 st.dataframe(display_scen,hide_index=True,use_container_width=True)
else: st.info('Select at least one macro risk scenario.')
'''
if old not in s: raise SystemExit('beta section anchor missing')
s=s.replace(old,new,1)
# Insert macro math before Complete configured metric output in LaTeX dialog.
anchor=" st.header('22. Complete configured metric output')\n"
macro_latex=r''' st.header('22. Macro risk and conditional performance')
 st.latex(r'\Delta F_t=F_t/F_{t-1}-1,\qquad z_t=\frac{\Delta F_t-\overline{\Delta F}}{s(\Delta F)}')
 st.latex(r'\mathcal S_{Oil}=\{t:z^{Oil}_t\ge2\},\quad \mathcal S_{VIX}=\{t:z^{VIX}_t\ge2\},\quad \mathcal S_{MOVE}=\{t:z^{MOVE}_t\ge1.5\}')
 st.latex(r'\mathcal S_{JSE}=\{t:DD^{JSE}_t\le-10\%\}')
 st.latex(r'R_{p|S}=\prod_{t\in\mathcal S}(1+r_{p,t})-1,\qquad \bar r_{p|S}=\frac{1}{|\mathcal S|}\sum_{t\in\mathcal S}r_{p,t}')
 st.latex(r'\sigma_{p|S}=s(r_p\mid t\in\mathcal S)\sqrt N')
 st.latex(r'\beta_{S}=\frac{Cov(r_p-r_f,r_m-r_f\mid t\in\mathcal S)}{Var(r_m-r_f\mid t\in\mathcal S)}')
 st.latex(r'\alpha_{S,period}=\overline{(r_p-r_f)}_{S}-\beta_S\overline{(r_m-r_f)}_{S},\qquad \alpha_{S,ann}=(1+\alpha_{S,period})^N-1')
 st.latex(r'HitRate_S=\frac{\#\{t\in\mathcal S:r_{p,t}>0\}}{|\mathcal S|}')
 st.write('σ thresholds use the sample mean and sample standard deviation of factor percentage changes inside the configured backtest window. The scenario output therefore describes realised historical conditional performance; it is not a hypothetical instantaneous price shock.')
 if not macro_factor_meta_df.empty: st.dataframe(macro_factor_meta_df,hide_index=True,use_container_width=True)
 if not scenario_df.empty: st.dataframe(display_scen,hide_index=True,use_container_width=True)
 st.header('23. Complete configured metric output')
'''
if anchor not in s: raise SystemExit('latex output anchor missing')
s=s.replace(anchor,macro_latex,1)
# Extend data audit dynamically with macro factor methodology.
audit="st.write('GOVI is the only repository series and is monthly-only.'); st.write(f'Configured window: {prices.index[0]:%d %b %Y} to {prices.index[-1]:%d %b %Y}; {len(prices):,} observations.')"
replacement="st.write('GOVI is the only repository series and is monthly-only.'); st.write('Macro risk factors: Oil=CL=F, VIX=^VIX, MOVE=^MOVE through the same raw-Close market-data adapter (auto_adjust=False). Scenario sigma thresholds are estimated from percentage changes inside the configured window; JSE stress uses benchmark drawdown from running peak.'); st.write(f'Configured window: {prices.index[0]:%d %b %Y} to {prices.index[-1]:%d %b %Y}; {len(prices):,} observations.');\n if not macro_factor_meta_df.empty: st.dataframe(macro_factor_meta_df,hide_index=True,use_container_width=True)"
if audit not in s: raise SystemExit('audit anchor missing')
s=s.replace(audit,replacement,1)
p.write_text(s)
