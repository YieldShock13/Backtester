from pathlib import Path
p=Path('app.py'); s=p.read_text()
old="latex_slot=report_col1.empty(); audit_slot=report_col2.empty(); st.subheader('Backtest Configuration'); a,b,c,d=st.columns(4)\nwith a: timeline=st.selectbox('Timeline',['1W','1M','3M','6M','1Y','3Y','5Y','10Y','All','Custom'],index=8)\nwith b: INITIAL=float(st.number_input('Nominal amount',min_value=1.0,value=float(DEFAULT_INITIAL),step=10000.0))\nwith c: RF=float(st.number_input('Risk-free rate (%)',min_value=0.0,max_value=100.0,value=7.0,step=.25))/100\nwith d: REINVEST=st.toggle('Reinvest dividends/distributions',value=False)"
new="latex_slot=report_col1.empty(); audit_slot=report_col2.empty(); st.subheader('Backtest Configuration'); a,b,c,d,e=st.columns(5)\nwith a: timeline=st.selectbox('Timeline',['1W','1M','3M','6M','1Y','3Y','5Y','10Y','All','Custom'],index=8)\nwith b: PORTFOLIO_CCY=st.selectbox('Portfolio currency',['ZAR','USD','EUR','GBP','JPY','CHF','AUD','CAD'],index=0)\nwith c: INITIAL=float(st.number_input(f'Nominal amount ({PORTFOLIO_CCY})',min_value=1.0,value=float(DEFAULT_INITIAL),step=10000.0))\nwith d: RF=float(st.number_input('Risk-free rate (%)',min_value=0.0,max_value=100.0,value=7.0,step=.25))/100\nwith e: REINVEST=st.toggle('Reinvest dividends/distributions',value=False)"
assert old in s, 'CONFIG BLOCK NOT FOUND'
s=s.replace(old,new,1)
# FX hedge base currency must inherit portfolio currency rather than ask for a contradictory second base currency.
old2="with fxc2: BASE_CCY=st.selectbox('Portfolio / base currency',['ZAR','USD','EUR','GBP','JPY','CHF','AUD','CAD'],index=0,disabled=not FX_HEDGED)"
new2="with fxc2:\n BASE_CCY=PORTFOLIO_CCY\n st.text_input('Portfolio / base currency',value=BASE_CCY,disabled=True)"
assert old2 in s, 'FX BASE CURRENCY BLOCK NOT FOUND'
s=s.replace(old2,new2,1)
# Make top caption explicit about currency denomination.
s=s.replace("f' | {frequency} observations | Nominal {INITIAL:,.0f} | RF {RF:.2%}","f' | {frequency} observations | Nominal {PORTFOLIO_CCY} {INITIAL:,.0f} | RF {RF:.2%}",1)
# LaTeX configured run and portfolio initialisation disclose denomination.
s=s.replace("st.write(f'Nominal V0 = {INITIAL:,.2f}; reinvest distributions = {REINVEST}.')","st.write(f'Portfolio currency = {PORTFOLIO_CCY}; nominal V0 = {PORTFOLIO_CCY} {INITIAL:,.2f}; reinvest distributions = {REINVEST}.')",1)
p.write_text(s)
