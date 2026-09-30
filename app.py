import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
import requests

st.set_page_config(page_title="Portfolio Backtester", layout="wide")
START="2012-02-01"; RF=0.07; INITIAL=1_202_000
ALLOC={"ALSI":400_000,"SP500":200_000,"SA_BONDS":200_000,"EUROPE":125_000,"NEWGOLD":45_000,"EXXARO":50_000,"BERKSHIRE":56_000,"MSCI_EM":65_000,"AGG":61_000}
TICKERS={"ALSI":"^J203.JO","SP500":"^GSPC","EUROPE":"^STOXX","NEWGOLD":"GLD.JO","EXXARO":"EXX.JO","BERKSHIRE":"BRK-B","MSCI_EM":"EEM","AGG":"AGG","USDZAR":"ZAR=X","EURZAR":"EURZAR=X"}
SARB_GOVI_API="https://custom.resbank.co.za/SarbWebApi/WebIndicators/Shared/GetTimeseriesObservations/KBP2013M"

@st.cache_data(ttl=3600,show_spinner=False)
def load_govi():
    # Repository history is the validated fallback/base. The official SARB API is
    # then queried for newer KBP2013M observations, so the app no longer depends
    # on manually replacing the CSV every quarter.
    try:
        d=pd.read_csv('govi_monthly.csv')
        d['Date']=pd.to_datetime(d['Date'])+pd.offsets.MonthEnd(0)
        base=pd.Series(d['SA_BONDS'].astype(float).values,index=d['Date'],name='SA_BONDS').sort_index()
        if len(base)<100: raise ValueError('GOVI repository history is incomplete')
    except Exception as e:
        raise RuntimeError(f'GOVI repository dataset unavailable: {e}')

    source='SARB KBP2013M (repository fallback)'
    try:
        headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'}
        r=requests.get(SARB_GOVI_API,headers=headers,timeout=20)
        r.raise_for_status()
        payload=r.json()
        if not isinstance(payload,list) or not payload:
            raise ValueError('SARB API returned no observations')
        live=pd.DataFrame(payload)
        if not {'Period','Value'}.issubset(live.columns):
            raise ValueError('Unexpected SARB API schema')
        live['Date']=pd.to_datetime(live['Period'],errors='coerce')+pd.offsets.MonthEnd(0)
        live['Value']=pd.to_numeric(live['Value'],errors='coerce')
        live=live.dropna(subset=['Date','Value']).drop_duplicates('Date',keep='last').sort_values('Date')
        if live.empty: raise ValueError('SARB API observations could not be parsed')
        live_s=pd.Series(live['Value'].values,index=live['Date'],name='SA_BONDS')
        # API values take precedence on overlapping dates and append new months.
        combined=pd.concat([base[~base.index.isin(live_s.index)],live_s]).sort_index()
        if combined.index.max()<base.index.max():
            raise ValueError('SARB API history is older than repository history')
        base=combined
        source='SARB KBP2013M (live official API; repository fallback enabled)'
    except Exception:
        # A temporary SARB outage must not take the dashboard down. The last
        # validated repository snapshot remains available and its date is shown.
        pass
    return base,source

@st.cache_data(ttl=3600,show_spinner=False)
def load_yahoo():
    raw=yf.download(list(TICKERS.values()),start=START,auto_adjust=False,actions=False,progress=False,group_by='column')
    if raw.empty: raise RuntimeError('Yahoo Finance returned no data')
    adj=raw['Adj Close'].rename(columns={v:k for k,v in TICKERS.items()})
    for c in ['NEWGOLD','EXXARO']: adj[c]=adj[c]/100.0
    adj['USDZAR']=adj['USDZAR'].ffill(); adj['EURZAR']=adj['EURZAR'].ffill(); z=pd.DataFrame(index=adj.index)
    for c in ['ALSI','NEWGOLD','EXXARO']: z[c]=adj[c]
    for c in ['SP500','BERKSHIRE','MSCI_EM','AGG']: z[c]=adj[c]*adj['USDZAR']
    z['EUROPE']=adj['EUROPE']*adj['EURZAR']; return z

def build_master():
    z=load_yahoo(); g,src=load_govi(); m=z.resample('ME').last(); m['SA_BONDS']=g.reindex(m.index).ffill(); m=m[list(ALLOC)].loc['2012-02-01':].dropna(); return m,g,src

def buy_hold(m):
    v=m.div(m.iloc[0]).mul(pd.Series(ALLOC),axis=1); v['PORTFOLIO']=v.sum(axis=1); return v

def annual_rebalanced(m):
    assets=list(ALLOC); target=pd.Series(ALLOC,dtype=float)/INITIAL; r=m[assets].pct_change(fill_method=None).fillna(0); v=pd.DataFrame(index=m.index,columns=assets,dtype=float); v.iloc[0]=pd.Series(ALLOC)
    for i in range(1,len(m)):
        prev=v.iloc[i-1].astype(float)
        if m.index[i].year!=m.index[i-1].year: prev=target*prev.sum()
        v.iloc[i]=prev*(1+r.iloc[i])
    v['PORTFOLIO']=v.sum(axis=1); return v

def capm_stats(v,m):
    rp=v['PORTFOLIO'].pct_change(fill_method=None); rm=m['ALSI'].pct_change(fill_method=None); d=pd.concat([rp.rename('P'),rm.rename('M')],axis=1).dropna(); mrf=(1+RF)**(1/12)-1; xp=d['M']-mrf; yp=d['P']-mrf; beta=yp.cov(xp)/xp.var(); alpha_m=yp.mean()-beta*xp.mean(); alpha_ann=(1+alpha_m)**12-1; return beta,alpha_ann

def metrics(v,m):
    p=v['PORTFOLIO'].dropna(); r=p.pct_change(fill_method=None).dropna(); yrs=(p.index[-1]-p.index[0]).days/365.25; cagr=(p.iloc[-1]/p.iloc[0])**(1/yrs)-1; vol=r.std()*np.sqrt(12); ex=r-((1+RF)**(1/12)-1); down=ex[ex<0]; dvol=np.sqrt(np.mean(down**2))*np.sqrt(12); dd=p/p.cummax()-1; var=r.quantile(.05); beta,alpha=capm_stats(v,m)
    return {'Initial Value':p.iloc[0],'Ending Value':p.iloc[-1],'Total Return':p.iloc[-1]/p.iloc[0]-1,'CAGR':cagr,'Annualised Volatility':vol,'Sharpe Ratio (RF 7%)':ex.mean()/ex.std()*np.sqrt(12),'Downside Volatility':dvol,'Sortino Ratio':ex.mean()*12/dvol,'Beta vs ALSI':beta,'CAPM Alpha (Annualised)':alpha,'Maximum Drawdown':dd.min(),'Calmar Ratio':cagr/abs(dd.min()),'Monthly VaR 95%':var,'Monthly CVaR 95%':r[r<=var].mean(),'Best Month':r.max(),'Worst Month':r.min(),'Positive Months':(r>0).mean(),'Max DD Date':dd.idxmin()}

def annual_returns(v):
    r=v['PORTFOLIO'].pct_change(fill_method=None).dropna(); a=(1+r).groupby(r.index.year).prod()-1; o=pd.DataFrame({'Year':a.index.astype(int),'Annual Return':a.values,'Period':'Full Year'})
    if v.index[0].month!=1:o.loc[o.Year==v.index[0].year,'Period']='Partial Year'
    if v.index[-1].month!=12:o.loc[o.Year==v.index[-1].year,'Period']='Partial Year'
    return o

def line_chart(series_map,title,ytitle):
    f=go.Figure()
    for name,s in series_map.items(): f.add_trace(go.Scatter(x=s.index,y=s.values,mode='lines',name=name))
    f.update_layout(title=title,xaxis_title='Date',yaxis_title=ytitle,hovermode='x unified',legend_title_text=''); st.plotly_chart(f,use_container_width=True)

def metric_table(m):
    pct={'Total Return','CAGR','Annualised Volatility','Downside Volatility','CAPM Alpha (Annualised)','Maximum Drawdown','Monthly VaR 95%','Monthly CVaR 95%','Best Month','Worst Month','Positive Months'}; rows=[]
    for k,v in m.items():
        if k=='Max DD Date': x=pd.Timestamp(v).strftime('%Y-%m')
        elif k in ['Initial Value','Ending Value']: x=f'R{v:,.0f}'
        elif k in pct: x=f'{v:.2%}'
        else: x=f'{v:.3f}'
        rows.append((k,x))
    return pd.DataFrame(rows,columns=['Metric','Value'])

def rolling_capm(v,m,window=36):
    rp=v['PORTFOLIO'].pct_change(fill_method=None); rm=m['ALSI'].pct_change(fill_method=None); d=pd.concat([rp.rename('P'),rm.rename('M')],axis=1).dropna(); mrf=(1+RF)**(1/12)-1; xp=d['M']-mrf; yp=d['P']-mrf
    beta=yp.rolling(window).cov(xp)/xp.rolling(window).var(); alpha_m=yp.rolling(window).mean()-beta*xp.rolling(window).mean(); alpha_ann=(1+alpha_m)**12-1
    return beta.rename('Rolling Beta'),alpha_ann.rename('Rolling Alpha')

def conditional_beta(v,m):
    rp=v['PORTFOLIO'].pct_change(fill_method=None); rm=m['ALSI'].pct_change(fill_method=None); alsi_dd=m['ALSI']/m['ALSI'].cummax()-1; d=pd.concat([rp.rename('P'),rm.rename('M'),alsi_dd.rename('DD')],axis=1).dropna(); stress=d[d['DD']<=-.10]; mrf=(1+RF)**(1/12)-1
    if len(stress)<2 or (stress['M']-mrf).var()==0: return np.nan,len(stress),stress
    b=(stress['P']-mrf).cov(stress['M']-mrf)/(stress['M']-mrf).var(); return b,len(stress),stress

st.title('Portfolio Backtester'); st.caption('Live Yahoo Finance market data + SARB GOVI | Starting capital R1,202,000 | Risk-free rate 7%')
try:
    with st.spinner('Updating market data…'): master,govi,govi_source=build_master(); bh=buy_hold(master); rb=annual_rebalanced(master)
except Exception as e: st.error(f'Data update failed: {e}'); st.exception(e); st.stop()

bhm,rbm=metrics(bh,master),metrics(rb,master); st.success(f'Data loaded through {master.index[-1]:%d %b %Y} | SARB GOVI through {govi.index[-1]:%d %b %Y}')
mode=st.radio('Backtest mode',['Buy & Hold','Annual Rebalanced'],horizontal=True,index=0); vals=bh if mode=='Buy & Hold' else rb; met=bhm if mode=='Buy & Hold' else rbm
c1,c2,c3,c4=st.columns(4); c1.metric(f'{mode} Value',f"R{met['Ending Value']:,.0f}"); c2.metric(f'{mode} CAGR',f"{met['CAGR']:.2%}"); c3.metric('Sharpe (7% RF)',f"{met['Sharpe Ratio (RF 7%)']:.3f}"); c4.metric('Max Drawdown',f"{met['Maximum Drawdown']:.2%}")
st.subheader(f'{mode} Analytics'); st.dataframe(metric_table(met),hide_index=True,use_container_width=True)
p=vals['PORTFOLIO']; r=p.pct_change(fill_method=None).dropna(); growth=p/p.iloc[0]*100; dd=(p/p.cummax()-1)*100; roll_ret=((1+r).rolling(12).apply(np.prod,raw=True)-1)*100; roll_vol=r.rolling(12).std()*np.sqrt(12)*100; ex=r-((1+RF)**(1/12)-1); roll_sr=ex.rolling(36).mean()/ex.rolling(36).std()*np.sqrt(12)
line_chart({mode:p},f'{mode} — Portfolio Value','ZAR'); line_chart({mode:growth},f'{mode} — Growth of R100','Value'); line_chart({'Drawdown':dd},f'{mode} — Portfolio Drawdown','%')
bar=go.Figure(go.Bar(x=r.index,y=r.values*100,name='Monthly Return')); bar.update_layout(title=f'{mode} — Monthly Portfolio Returns',xaxis_title='Date',yaxis_title='Return (%)'); st.plotly_chart(bar,use_container_width=True)
line_chart({'12M Return':roll_ret},f'{mode} — Rolling 12-Month Return','%'); line_chart({'12M Volatility':roll_vol},f'{mode} — Rolling 12-Month Annualised Volatility','%'); line_chart({'36M Sharpe':roll_sr},f'{mode} — Rolling 36-Month Sharpe Ratio — RF 7%','Sharpe'); line_chart({c:vals[c] for c in ALLOC},f'{mode} — Portfolio Sleeve Values','ZAR')
st.subheader(f'{mode} Annual Returns'); ar=annual_returns(vals); ar['Annual Return']=ar['Annual Return'].map(lambda x:f'{x:.2%}'); st.dataframe(ar,hide_index=True,use_container_width=True)
weights=vals[list(ALLOC)].div(vals['PORTFOLIO'],axis=0); wt=pd.DataFrame({'Asset':list(ALLOC),'Initial Weight':[ALLOC[a]/INITIAL for a in ALLOC],'Ending Weight':weights.iloc[-1].values}); wt['Initial Weight']=wt['Initial Weight'].map(lambda x:f'{x:.2%}'); wt['Ending Weight']=wt['Ending Weight'].map(lambda x:f'{x:.2%}'); st.subheader(f'{mode} Portfolio Weights'); st.dataframe(wt,hide_index=True,use_container_width=True)
st.divider(); st.subheader('Buy & Hold vs Annual Rebalancing'); line_chart({'Buy & Hold':bh['PORTFOLIO'],'Annual Rebalanced':rb['PORTFOLIO']},'Portfolio Value Comparison','ZAR'); comparison=pd.DataFrame({'Buy & Hold':metric_table(bhm).set_index('Metric')['Value'],'Annual Rebalanced':metric_table(rbm).set_index('Metric')['Value']}); st.dataframe(comparison,use_container_width=True)
with st.expander('Methodology & data'):
    st.write('Buy & Hold invests the original allocations once and permits weights to drift. Annual Rebalanced resets to the original target weights at the start of each calendar year. Foreign sleeves are translated into ZAR. The R400k South African equity sleeve uses FTSE/JSE All Share (^J203.JO). The R200k South African bond sleeve uses SARB KBP2013M GOVI.')
    st.write('Yahoo data refresh hourly. GOVI is queried directly from the official SARB Web API (KBP2013M) and refreshed hourly; the validated repository CSV is retained only as a fallback if SARB is temporarily unavailable. Because GOVI is a monthly series, its latest published level is carried forward inside a newer partial month until SARB publishes the next observation. Beta and CAPM alpha use monthly portfolio and ALSI returns with the same 7% annual risk-free rate used elsewhere.')
    st.write(f'SARB source loaded: {govi_source}')

st.divider(); st.subheader('Asset Correlation'); asset_returns=master[list(ALLOC)].pct_change(fill_method=None).dropna(); corr=asset_returns.corr(method='pearson'); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()); st.metric('Net Inter-Asset Correlation',f'{net_corr:.3f}',help='Arithmetic mean of all unique off-diagonal Pearson correlations. Each asset pair is counted once.')
heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}',hovertemplate='%{y} vs %{x}<br>Pearson r = %{z:.3f}<extra></extra>',colorbar=dict(title='Pearson r'))); heat.update_layout(title='Pearson Correlation Matrix — Monthly ZAR Asset Returns',height=650); st.plotly_chart(heat,use_container_width=True); st.caption(f'Calculated from {len(asset_returns):,} common monthly observations from {asset_returns.index[0]:%b %Y} to {asset_returns.index[-1]:%b %Y}.')

st.divider(); st.subheader(f'{mode} — ALSI Beta & Alpha Through Time')
roll_beta,roll_alpha=rolling_capm(vals,master,36); cond_beta,n_stress,stress=conditional_beta(vals,master)
c1,c2,c3=st.columns(3); c1.metric('Full-Sample Beta vs ALSI',f"{met['Beta vs ALSI']:.3f}"); c2.metric('Annualised CAPM Alpha',f"{met['CAPM Alpha (Annualised)']:.2%}"); c3.metric('Conditional Beta: ALSI DD ≤ -10%',('N/A' if np.isnan(cond_beta) else f'{cond_beta:.3f}'))
line_chart({'36M Rolling Beta':roll_beta},f'{mode} — 36-Month Rolling Beta vs ALSI','Beta'); line_chart({'36M Rolling Annualised Alpha':roll_alpha*100},f'{mode} — 36-Month Rolling CAPM Alpha','Alpha (%)')
alsi_dd=(master['ALSI']/master['ALSI'].cummax()-1)*100; line_chart({'ALSI Drawdown':alsi_dd},'ALSI Drawdown — Conditional-Beta Regime','Drawdown (%)')
st.caption(f'Conditional beta uses the {n_stress} monthly observations for which the ALSI level was at least 10% below its prior peak (drawdown ≤ -10%). Rolling beta/alpha use 36-month windows. Alpha is CAPM alpha annualised from monthly excess returns; RF = 7% p.a.')