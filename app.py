import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Portfolio Backtester", layout="wide")
START="2012-02-01"; RF=0.07; INITIAL=1_202_000
ALLOC={"ALSI":400_000,"SP500":200_000,"SA_BONDS":200_000,"EUROPE":125_000,"NEWGOLD":45_000,"EXXARO":50_000,"BERKSHIRE":56_000,"MSCI_EM":65_000,"AGG":61_000}
TICKERS={"ALSI":"^J203.JO","SP500":"^GSPC","EUROPE":"^STOXX","NEWGOLD":"GLD.JO","EXXARO":"EXX.JO","BERKSHIRE":"BRK-B","MSCI_EM":"EEM","AGG":"AGG","USDZAR":"ZAR=X","EURZAR":"EURZAR=X"}

@st.cache_data(show_spinner=False)
def load_govi():
    try:
        d=pd.read_csv('govi_monthly.csv')
        d['Date']=pd.to_datetime(d['Date'])+pd.offsets.MonthEnd(0)
        s=pd.Series(d['SA_BONDS'].astype(float).values,index=d['Date'],name='SA_BONDS').sort_index()
        if len(s)<100: raise ValueError('GOVI repository history is incomplete')
        return s,'SARB KBP2013MM (repository snapshot)'
    except Exception as e:
        raise RuntimeError(f'GOVI repository dataset unavailable: {e}')

@st.cache_data(ttl=3600,show_spinner=False)
def load_yahoo():
    raw=yf.download(list(TICKERS.values()),start=START,auto_adjust=False,actions=False,progress=False,group_by='column')
    if raw.empty: raise RuntimeError('Yahoo Finance returned no data')
    adj=raw['Adj Close'].rename(columns={v:k for k,v in TICKERS.items()})
    for c in ['NEWGOLD','EXXARO']: adj[c]=adj[c]/100.0
    adj['USDZAR']=adj['USDZAR'].ffill(); adj['EURZAR']=adj['EURZAR'].ffill()
    z=pd.DataFrame(index=adj.index)
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

def metrics(v):
    p=v['PORTFOLIO'].dropna(); r=p.pct_change(fill_method=None).dropna(); yrs=(p.index[-1]-p.index[0]).days/365.25; cagr=(p.iloc[-1]/p.iloc[0])**(1/yrs)-1; vol=r.std()*np.sqrt(12); ex=r-((1+RF)**(1/12)-1); down=ex[ex<0]; dvol=np.sqrt(np.mean(down**2))*np.sqrt(12); dd=p/p.cummax()-1; var=r.quantile(.05)
    return {'Initial Value':p.iloc[0],'Ending Value':p.iloc[-1],'Total Return':p.iloc[-1]/p.iloc[0]-1,'CAGR':cagr,'Annualised Volatility':vol,'Sharpe Ratio (RF 7%)':ex.mean()/ex.std()*np.sqrt(12),'Downside Volatility':dvol,'Sortino Ratio':ex.mean()*12/dvol,'Maximum Drawdown':dd.min(),'Calmar Ratio':cagr/abs(dd.min()),'Monthly VaR 95%':var,'Monthly CVaR 95%':r[r<=var].mean(),'Best Month':r.max(),'Worst Month':r.min(),'Positive Months':(r>0).mean(),'Max DD Date':dd.idxmin()}

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
    pct={'Total Return','CAGR','Annualised Volatility','Downside Volatility','Maximum Drawdown','Monthly VaR 95%','Monthly CVaR 95%','Best Month','Worst Month','Positive Months'}; rows=[]
    for k,v in m.items():
        if k=='Max DD Date': x=pd.Timestamp(v).strftime('%Y-%m')
        elif k in ['Initial Value','Ending Value']: x=f'R{v:,.0f}'
        elif k in pct: x=f'{v:.2%}'
        else: x=f'{v:.3f}'
        rows.append((k,x))
    return pd.DataFrame(rows,columns=['Metric','Value'])

st.title('Portfolio Backtester'); st.caption('Live Yahoo Finance market data + SARB GOVI | Starting capital R1,202,000 | Risk-free rate 7%')
try:
    with st.spinner('Updating market data…'): master,govi,govi_source=build_master(); bh=buy_hold(master); rb=annual_rebalanced(master)
except Exception as e:
    st.error(f'Data update failed: {e}'); st.exception(e); st.stop()

bhm,rbm=metrics(bh),metrics(rb)
st.success(f'Data loaded through {master.index[-1]:%d %b %Y} | SARB GOVI through {govi.index[-1]:%d %b %Y}')

# One control drives ALL single-portfolio outputs below.
mode=st.radio('Backtest mode',['Buy & Hold','Annual Rebalanced'],horizontal=True,index=0)
vals=bh if mode=='Buy & Hold' else rb
met=bhm if mode=='Buy & Hold' else rbm

c1,c2,c3,c4=st.columns(4)
c1.metric(f'{mode} Value',f"R{met['Ending Value']:,.0f}")
c2.metric(f'{mode} CAGR',f"{met['CAGR']:.2%}")
c3.metric('Sharpe (7% RF)',f"{met['Sharpe Ratio (RF 7%)']:.3f}")
c4.metric('Max Drawdown',f"{met['Maximum Drawdown']:.2%}")

st.subheader(f'{mode} Analytics')
st.dataframe(metric_table(met),hide_index=True,use_container_width=True)

p=vals['PORTFOLIO']; r=p.pct_change(fill_method=None).dropna(); growth=p/p.iloc[0]*100; dd=(p/p.cummax()-1)*100
roll_ret=((1+r).rolling(12).apply(np.prod,raw=True)-1)*100
roll_vol=r.rolling(12).std()*np.sqrt(12)*100
ex=r-((1+RF)**(1/12)-1); roll_sr=ex.rolling(36).mean()/ex.rolling(36).std()*np.sqrt(12)

line_chart({mode:p},f'{mode} — Portfolio Value','ZAR')
line_chart({mode:growth},f'{mode} — Growth of R100','Value')
line_chart({'Drawdown':dd},f'{mode} — Portfolio Drawdown','%')
bar=go.Figure(go.Bar(x=r.index,y=r.values*100,name='Monthly Return')); bar.update_layout(title=f'{mode} — Monthly Portfolio Returns',xaxis_title='Date',yaxis_title='Return (%)'); st.plotly_chart(bar,use_container_width=True)
line_chart({'12M Return':roll_ret},f'{mode} — Rolling 12-Month Return','%')
line_chart({'12M Volatility':roll_vol},f'{mode} — Rolling 12-Month Annualised Volatility','%')
line_chart({'36M Sharpe':roll_sr},f'{mode} — Rolling 36-Month Sharpe Ratio — RF 7%','Sharpe')
line_chart({c:vals[c] for c in ALLOC},f'{mode} — Portfolio Sleeve Values','ZAR')

st.subheader(f'{mode} Annual Returns')
ar=annual_returns(vals); ar['Annual Return']=ar['Annual Return'].map(lambda x:f'{x:.2%}'); st.dataframe(ar,hide_index=True,use_container_width=True)

weights=vals[list(ALLOC)].div(vals['PORTFOLIO'],axis=0)
wt=pd.DataFrame({'Asset':list(ALLOC),'Initial Weight':[ALLOC[a]/INITIAL for a in ALLOC],'Ending Weight':weights.iloc[-1].values})
wt['Initial Weight']=wt['Initial Weight'].map(lambda x:f'{x:.2%}'); wt['Ending Weight']=wt['Ending Weight'].map(lambda x:f'{x:.2%}')
st.subheader(f'{mode} Portfolio Weights'); st.dataframe(wt,hide_index=True,use_container_width=True)

# Keep the direct comparison as an additional section; nothing removed.
st.divider(); st.subheader('Buy & Hold vs Annual Rebalancing')
line_chart({'Buy & Hold':bh['PORTFOLIO'],'Annual Rebalanced':rb['PORTFOLIO']},'Portfolio Value Comparison','ZAR')
comparison=pd.DataFrame({'Buy & Hold':metric_table(bhm).set_index('Metric')['Value'],'Annual Rebalanced':metric_table(rbm).set_index('Metric')['Value']}); st.dataframe(comparison,use_container_width=True)

with st.expander('Methodology & data'):
    st.write('Buy & Hold invests the original allocations once and permits weights to drift. Annual Rebalanced resets to the original target weights at the start of each calendar year. Foreign sleeves are translated into ZAR. The R400k South African equity sleeve uses FTSE/JSE All Share (^J203.JO). The R200k South African bond sleeve uses SARB KBP2013MM GOVI.')
    st.write('Yahoo data refresh hourly. GOVI is monthly and stored as the official SARB history in the repository; its latest published level is carried forward until the snapshot is updated. No synthetic daily GOVI return is invented.')
    st.write(f'SARB source loaded: {govi_source}')