from app import *
from feature_config import resolve_window, common_coverage, validate_weights, allocations_from_weights, fx_decomposition, latex_workings, audit_rows

# NOTE: staged integration shell. This file intentionally does not replace app.py until validated.
# It imports the existing engine unchanged and adds the requested configuration/audit layer.

st.divider()
st.header('Configurable Backtest — validation branch')
st.caption('This staged interface is isolated from the live app until its accounting and coverage checks pass.')

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
    with d2: custom_end=st.date_input('Custom end',value=prices.index.max().date(),key='v2_end')

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
    w=validate_weights(selected,weights)
    alloc=allocations_from_weights(selected,weights,nominal)
except Exception as e:
    st.error(str(e)); st.stop()

requested_start,requested_end=resolve_window(prices.index,timeline,custom_start,custom_end)
actual_start,actual_end,coverage_starts,coverage_ends,coverage_flags=common_coverage(prices,selected,requested_start,requested_end)
if coverage_flags:
    st.warning('Requested timeline was shortened to the maximum common history: '
               f'{actual_start:%Y-%m-%d} to {actual_end:%Y-%m-%d}. Reason(s): '+ '; '.join(coverage_flags))
else:
    st.info(f'Analysis window: {actual_start:%Y-%m-%d} to {actual_end:%Y-%m-%d}')

# Month-end engine currently governs portfolio accounting. A sub-month request is therefore
# transparently clipped to available month-end observations rather than silently interpolated.
pw=prices.loc[(prices.index>=actual_start)&(prices.index<=actual_end),selected].copy()
dw=divs.loc[pw.index,selected].copy()
if len(pw)<2:
    st.warning('The selected window contains fewer than two validated month-end observations. Portfolio risk statistics are not calculated for this window.')
else:
    # Construct isolated custom portfolio without modifying legacy globals.
    def custom_bh(p,d,a,reinv):
        out=pd.DataFrame(index=p.index,columns=list(a.index),dtype=float)
        cash=pd.Series(0.0,index=a.index)
        units=pd.Series({x:a[x]/float(p[x].iloc[0]) for x in a.index},dtype=float)
        out.iloc[0]=a
        for i in range(1,len(p)):
            dt=p.index[i]
            if reinv:
                for x in a.index:
                    if d.loc[dt,x]!=0:
                        units[x]+=units[x]*d.loc[dt,x]/p.loc[dt,x]
                out.loc[dt]=units*p.loc[dt]
            else:
                cash=cash+units*d.loc[dt]
                out.loc[dt]=units*p.loc[dt]+cash
        out['PORTFOLIO']=out[list(a.index)].sum(axis=1)
        return out

    cv=custom_bh(pw,dw,alloc,reinvest)
    if not np.isclose(cv.PORTFOLIO.iloc[0],nominal,atol=.01): raise RuntimeError('Custom portfolio nominal reconciliation failed')
    if not np.allclose(cv[selected].sum(axis=1),cv.PORTFOLIO,atol=.01,rtol=0): raise RuntimeError('Custom sleeve reconciliation failed')
    line_chart({'Configured portfolio':cv.PORTFOLIO},'Configured Portfolio Value','ZAR')
    cr=cv.PORTFOLIO.pct_change(fill_method=None).dropna()
    yrs=max((cv.index[-1]-cv.index[0]).days/365.25,1/365.25)
    cagr=(cv.PORTFOLIO.iloc[-1]/cv.PORTFOLIO.iloc[0])**(1/yrs)-1
    rf_m=(1+rf_user)**(1/12)-1
    sr=(cr-rf_m).mean()/(cr-rf_m).std()*np.sqrt(12) if cr.std()>0 else np.nan
    q1,q2,q3=st.columns(3); q1.metric('Ending value',f'R{cv.PORTFOLIO.iloc[-1]:,.0f}'); q2.metric('CAGR',f'{cagr:.2%}'); q3.metric('Sharpe',f'{sr:.3f}' if np.isfinite(sr) else 'N/A')

st.divider()
right1,right2=st.columns([1,1])
with right1:
    show_latex=st.toggle('Show workings in LaTeX',value=False,key='v2_latex')
with right2:
    show_audit=st.toggle('Data audit report',value=False,key='v2_audit')

if show_latex:
    st.subheader('Workings')
    for title,equation in latex_workings(rf_user,nominal,reinvest,w):
        st.markdown(f'**{title}**'); st.latex(equation)

if show_audit:
    st.subheader('Data Audit Report')
    audit=audit_rows(selected,coverage_starts,coverage_ends,bond_validation,reinvest)
    st.dataframe(audit,hide_index=True,use_container_width=True)
    st.markdown('**Validation concerns / deeper inspection**')
    st.write('• Yahoo raw Close is used rather than Adjusted Close. Corporate-action completeness remains source-dependent and should be independently checked for material events.')
    st.write('• JSE instruments quoted in cents are normalised to rand where explicitly identified by the existing methodology.')
    st.write('• SA_BONDS is a stitched series: repository GOVI through the validated cutoff, followed by STXGVI. This is an instrument substitution/proxy and is explicitly flagged rather than hidden.')
    st.write('• Foreign sleeves use observed USD/ZAR or EUR/ZAR translation. No FX interpolation is presented as observed market data.')
    if coverage_flags: st.write('• Requested history was truncated because one or more selected assets lacked complete coverage: '+ '; '.join(coverage_flags))

st.divider()
st.subheader('Macro Tracker — FX vs Asset Appreciation')
foreign=[a for a in selected if a in ['SP500','BERKSHIRE','MSCI_EM','AGG','EUROPE']]
if not foreign:
    st.caption('No foreign-currency assets selected.')
else:
    # Pull local-currency prices and FX from the same Yahoo source used by the engine.
    raw=load_yahoo_components()
    # load_yahoo_components returns translated series, so fetch local/FX explicitly for attribution only.
    fx_rows=[]
    for a in foreign:
        ticker=TICKERS[a]; h=yf.Ticker(ticker).history(start=str(actual_start.date()),end=str((actual_end+pd.Timedelta(days=2)).date()),auto_adjust=False,actions=False)
        if h.empty: continue
        lp=pd.to_numeric(h['Close'],errors='coerce'); lp.index=pd.to_datetime(lp.index).tz_localize(None)
        fx_t='ZAR=X' if a!='EUROPE' else 'EURZAR=X'; fh=yf.Ticker(fx_t).history(start=str(actual_start.date()),end=str((actual_end+pd.Timedelta(days=2)).date()),auto_adjust=False,actions=False)
        if fh.empty: continue
        fx=pd.to_numeric(fh['Close'],errors='coerce'); fx.index=pd.to_datetime(fx.index).tz_localize(None)
        dec=fx_decomposition(lp,fx,actual_start,actual_end); dec['Asset']=a; fx_rows.append(dec)
    if fx_rows:
        fxd=pd.DataFrame(fx_rows).set_index('Asset')
        for c in fxd.columns: fxd[c]=fxd[c].map(lambda x:f'{x:.2%}')
        st.dataframe(fxd,use_container_width=True)
        st.caption('Identity check: ZAR price return = local appreciation + FX contribution + interaction. This tracker decomposes price return; cash distributions are reported separately in total-return analytics.')
    else: st.warning('FX attribution data could not be retrieved for the selected common window.')