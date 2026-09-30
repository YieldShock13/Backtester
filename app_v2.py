from app import *
from feature_config import resolve_window, common_coverage, validate_weights, allocations_from_weights, fx_decomposition, latex_workings, audit_rows
from daily_window import use_daily_window, build_daily_components, align_daily_window, periods_per_year, validate_period_return_identity

# Staged integration shell. It remains off main until runtime/data validation passes.
st.divider()
st.header('Configurable Backtest — validation branch')
st.caption('Short windows use observed daily data; long windows retain the validated month-end engine. No price interpolation.')

c1,c2,c3,c4=st.columns([1.2,1.2,1.2,1.2])
with c1:
    timeline=st.selectbox('Timeline',['1W','1M','3M','6M','1Y','3Y','5Y','10Y','All','Custom'],index=8,key='v2_timeline')
with c2:
    nominal=st.number_input('Nominal amount (ZAR)',min_value=1.0,value=float(INITIAL),step=10000.0,key='v2_nominal')
with c3:
    rf_user=st.number_input('Risk-free rate (%)',min_value=0.0,max_value=100.0,value=7.0,step=.25,key='v2_rf')/100.0
with c4:
    reinvest=st.toggle('Reinvest dividends',value=False,key='v2_reinvest')

custom_start=custom_end=None
if timeline=='Custom':
    d1,d2=st.columns(2)
    with d1: custom_start=st.date_input('Custom start',value=prices.index.min().date(),key='v2_start')
    with d2: custom_end=st.date_input('Custom end',value=pd.Timestamp.today().date(),key='v2_end')

selected=st.multiselect('Assets',ASSETS,default=ASSETS,key='v2_assets')
if not selected:
    st.error('Select at least one asset.'); st.stop()

st.subheader('Portfolio weights')
weight_cols=st.columns(min(3,len(selected)))
default_w={a:ALLOC[a]/INITIAL for a in ASSETS}
weights={}
for i,a in enumerate(selected):
    with weight_cols[i%len(weight_cols)]:
        weights[a]=st.number_input(f'{a} weight (%)',min_value=0.0,max_value=100.0,value=float(default_w[a]*100),step=.25,key=f'v2_w_{a}')/100.0
try:
    w=validate_weights(selected,weights); alloc=allocations_from_weights(selected,weights,nominal)
except Exception as e:
    st.error(str(e)); st.stop()

# Resolve the requested calendar interval first. For short windows the end date is today/current
# market history rather than a fabricated month-end observation.
base_end=pd.Timestamp(custom_end) if timeline=='Custom' and custom_end is not None else pd.Timestamp.today().normalize()
if timeline=='All': requested_start=prices.index.min(); requested_end=prices.index.max()
elif timeline=='Custom': requested_start=pd.Timestamp(custom_start); requested_end=base_end
else:
    offsets={'1W':pd.DateOffset(weeks=1),'1M':pd.DateOffset(months=1),'3M':pd.DateOffset(months=3),'6M':pd.DateOffset(months=6),'1Y':pd.DateOffset(years=1),'3Y':pd.DateOffset(years=3),'5Y':pd.DateOffset(years=5),'10Y':pd.DateOffset(years=10)}
    requested_end=base_end; requested_start=requested_end-offsets[timeline]

daily_mode=use_daily_window(timeline,custom_start,custom_end)
source_notes={}
if daily_mode:
    # Fetch enough leading calendar days to guarantee an observed trading date at/after the request.
    fetch_start=requested_start-pd.Timedelta(days=10); fetch_end=requested_end+pd.Timedelta(days=2)
    needed=set(selected)
    source_map={a:TICKERS[a] for a in selected if a!='SA_BONDS'}
    source_map['USDZAR']=TICKERS['USDZAR']; source_map['EURZAR']=TICKERS['EURZAR']
    if 'SA_BONDS' in selected: source_map['STXGVI']='STXGVI.JO'
    histories={}
    for name,ticker in source_map.items():
        h=yf.Ticker(ticker).history(start=str(fetch_start.date()),end=str(fetch_end.date()),auto_adjust=False,actions=True)
        if h.empty: raise RuntimeError(f'{name}: Yahoo returned no daily history for requested window')
        histories[name]=h
    dp,dd,source_notes=build_daily_components(histories,selected,govi.index.max())
    pw,dw,actual_start,actual_end,coverage_starts,coverage_ends,coverage_flags=align_daily_window(dp,dd,selected,requested_start,requested_end)
    validate_period_return_identity(pw,dw)
    frequency='daily'
else:
    actual_start,actual_end,coverage_starts,coverage_ends,coverage_flags=common_coverage(prices,selected,requested_start,requested_end)
    pw=prices.loc[(prices.index>=actual_start)&(prices.index<=actual_end),selected].copy()
    dw=divs.loc[pw.index,selected].copy(); frequency='monthly'

if coverage_flags:
    st.warning('Requested timeline was shortened to available common observations: '+ '; '.join(dict.fromkeys(coverage_flags)))
st.info(f'Analysis window: {actual_start:%Y-%m-%d} to {actual_end:%Y-%m-%d} | {frequency} observations')


def custom_bh(p,d,a,reinv):
    out=pd.DataFrame(index=p.index,columns=list(a.index),dtype=float)
    cash=pd.Series(0.0,index=a.index); units=pd.Series({x:a[x]/float(p[x].iloc[0]) for x in a.index},dtype=float)
    out.iloc[0]=a
    for i in range(1,len(p)):
        dt=p.index[i]
        if reinv:
            for x in a.index:
                if d.loc[dt,x]!=0: units[x]+=units[x]*d.loc[dt,x]/p.loc[dt,x]
            out.loc[dt]=units*p.loc[dt]
        else:
            cash=cash+units*d.loc[dt]; out.loc[dt]=units*p.loc[dt]+cash
    out['PORTFOLIO']=out[list(a.index)].sum(axis=1)
    return out

if len(pw)<2:
    st.error('Fewer than two validated common observations. Backtest not calculated.'); st.stop()
cv=custom_bh(pw,dw,alloc,reinvest)
if not np.isclose(cv.PORTFOLIO.iloc[0],nominal,atol=.01): raise RuntimeError('Custom portfolio nominal reconciliation failed')
if not np.allclose(cv[selected].sum(axis=1),cv.PORTFOLIO,atol=.01,rtol=0): raise RuntimeError('Custom sleeve reconciliation failed')
line_chart({'Configured portfolio':cv.PORTFOLIO},'Configured Portfolio Value','ZAR')
cr=cv.PORTFOLIO.pct_change(fill_method=None).dropna(); ppy=periods_per_year(frequency)
yrs=max((cv.index[-1]-cv.index[0]).days/365.25,1/365.25); cagr=(cv.PORTFOLIO.iloc[-1]/cv.PORTFOLIO.iloc[0])**(1/yrs)-1
rf_period=(1+rf_user)**(1/ppy)-1; ex=cr-rf_period
sr=ex.mean()/ex.std()*np.sqrt(ppy) if ex.std()>0 else np.nan
q1,q2,q3=st.columns(3); q1.metric('Ending value',f'R{cv.PORTFOLIO.iloc[-1]:,.0f}'); q2.metric('CAGR',f'{cagr:.2%}'); q3.metric('Sharpe',f'{sr:.3f}' if np.isfinite(sr) else 'N/A')

st.divider(); right1,right2=st.columns([1,1])
with right1: show_latex=st.toggle('Show workings in LaTeX',value=False,key='v2_latex')
with right2: show_audit=st.toggle('Data audit report',value=False,key='v2_audit')
if show_latex:
    st.subheader('Workings')
    for title,equation in latex_workings(rf_user,nominal,reinvest,w): st.markdown(f'**{title}**'); st.latex(equation)
if show_audit:
    st.subheader('Data Audit Report')
    audit=audit_rows(selected,coverage_starts,coverage_ends,bond_validation,reinvest)
    audit['Observation frequency']=frequency
    if daily_mode:
        audit['Short-window note']=audit['Asset'].map(source_notes).fillna('Observed daily raw Close; no price interpolation.')
    st.dataframe(audit,hide_index=True,use_container_width=True)
    st.markdown('**Validation concerns / deeper inspection**')
    st.write('• Raw Close only; Adjusted Close is not used. Dividends/distributions remain explicit cash flows unless reinvestment is selected.')
    st.write('• Yahoo Close is treated as split-normalised; split events are not applied a second time.')
    st.write('• SA_BONDS long history is GOVI followed by STXGVI. For daily short windows, SA_BONDS is available only after the validated GOVI cutoff because monthly GOVI is never interpolated into fake daily observations.')
    st.write('• Foreign sleeves translate raw local prices and cash dividends with observed FX. Missing asset prices are not forward-filled.')
    if coverage_flags: st.write('• Window truncation: '+ '; '.join(dict.fromkeys(coverage_flags)))

st.divider(); st.subheader('Macro Tracker — FX vs Asset Appreciation')
foreign=[a for a in selected if a in ['SP500','BERKSHIRE','MSCI_EM','AGG','EUROPE']]
if not foreign: st.caption('No foreign-currency assets selected.')
else:
    fx_rows=[]
    for a in foreign:
        ticker=TICKERS[a]
        h=yf.Ticker(ticker).history(start=str((actual_start-pd.Timedelta(days=5)).date()),end=str((actual_end+pd.Timedelta(days=2)).date()),auto_adjust=False,actions=False)
        if h.empty: continue
        lp=pd.to_numeric(h['Close'],errors='coerce'); lp.index=pd.to_datetime(lp.index).tz_localize(None)
        fx_t='ZAR=X' if a!='EUROPE' else 'EURZAR=X'
        fh=yf.Ticker(fx_t).history(start=str((actual_start-pd.Timedelta(days=5)).date()),end=str((actual_end+pd.Timedelta(days=2)).date()),auto_adjust=False,actions=False)
        if fh.empty: continue
        fx=pd.to_numeric(fh['Close'],errors='coerce'); fx.index=pd.to_datetime(fx.index).tz_localize(None)
        dec=fx_decomposition(lp,fx,actual_start,actual_end); dec['Asset']=a; fx_rows.append(dec)
    if fx_rows:
        fxd=pd.DataFrame(fx_rows).set_index('Asset')
        for c in fxd.columns: fxd[c]=fxd[c].map(lambda x:f'{x:.2%}')
        st.dataframe(fxd,use_container_width=True)
        st.caption('Identity: ZAR price return = local appreciation + FX contribution + interaction. Cash distributions are separate in total-return analytics.')
    else: st.warning('FX attribution data could not be retrieved for the selected common window.')
