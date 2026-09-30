from pathlib import Path
p=Path('app.py')
s=p.read_text()

# 1) Add serialisable name/ticker search. Keep source routing explicit and extensible.
needle=""" return prices,divs,splits\n\ndef build_master(selected):"""
insert=""" return prices,divs,splits\n\n@st.cache_data(ttl=3600,show_spinner=False)\ndef search_assets(query):\n q=(query or '').strip()\n if not q: return []\n out=[]\n if 'govi' in q.lower() or 'south african government' in q.lower():\n  out.append({'symbol':'GOVI','name':'South African Government Bond Index (repository series)','source':'Repository'})\n try:\n  srch=yf.Search(q,max_results=12,news_count=0,lists_count=0,recommended=0)\n  for item in (getattr(srch,'quotes',None) or []):\n   symbol=str(item.get('symbol','')).strip()\n   if not symbol: continue\n   out.append({'symbol':symbol,'name':str(item.get('longname') or item.get('shortname') or symbol),'source':'Market data'})\n except Exception:\n  pass\n seen=set(); clean=[]\n for row in out:\n  if row['symbol'] not in seen: clean.append(row); seen.add(row['symbol'])\n return clean\n\ndef build_master(selected):"""
if needle not in s: raise SystemExit('loader insertion anchor missing')
s=s.replace(needle,insert,1)

# 2) Replace exact-ticker-only input with name/ticker search + selected asset set.
old="""ticker_text=st.text_input('Exact Yahoo Finance tickers (comma-separated; GOVI is the repository series)',value=','.join(DEFAULT_TICKERS),help='Any Yahoo Finance ticker may be entered using its exact symbol. No automatic FX overlay is applied.')\nASSETS=list(dict.fromkeys([x.strip().upper() for x in ticker_text.split(',') if x.strip()]))\nif not ASSETS: st.error('Enter at least one exact ticker.'); st.stop()"""
new="""if 'selected_assets' not in st.session_state: st.session_state.selected_assets=DEFAULT_TICKERS.copy()\nst.markdown('**Assets**')\nsearch_query=st.text_input('Search asset',placeholder='Search by company, fund, index or ticker')\nresults=search_assets(search_query) if search_query.strip() else []\nif results:\n labels=[f\"{r['name']} | {r['symbol']} | {r['source']}\" for r in results]\n chosen_label=st.selectbox('Search results',labels,key='asset_search_result')\n chosen=results[labels.index(chosen_label)]['symbol']\n if st.button('Add asset',key='add_asset') and chosen not in st.session_state.selected_assets:\n  st.session_state.selected_assets.append(chosen); st.rerun()\nASSETS=st.multiselect('Selected assets',options=list(dict.fromkeys(st.session_state.selected_assets+DEFAULT_TICKERS+['GOVI'])),default=st.session_state.selected_assets,key='selected_assets_widget')\nst.session_state.selected_assets=ASSETS\nif not ASSETS: st.error('Select at least one asset.'); st.stop()"""
if old not in s: raise SystemExit('asset-selector anchor missing')
s=s.replace(old,new,1)

# 3) Restore the original Pearson heatmap exactly in spirit/layout, replacing plain dataframe regression.
old="""st.divider(); st.subheader('Asset Correlation'); corr=asset_r[ASSETS].dropna().corr(); st.dataframe(corr,use_container_width=True)"""
new="""st.divider(); st.subheader('Asset Correlation'); corr=asset_r[ASSETS].dropna().corr(); mask=np.triu(np.ones(corr.shape,dtype=bool),k=1); net_corr=float(corr.where(mask).stack().mean()) if len(corr)>1 else np.nan; st.metric('Net Inter-Asset Correlation','N/A' if not np.isfinite(net_corr) else f'{net_corr:.3f}'); heat=go.Figure(data=go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,zmin=-1,zmax=1,zmid=0,colorscale='RdBu',reversescale=True,text=np.round(corr.values,2),texttemplate='%{text:.2f}')); heat.update_layout(title='Pearson Correlation Matrix'); st.plotly_chart(heat,use_container_width=True)"""
if old not in s: raise SystemExit('correlation anchor missing')
s=s.replace(old,new,1)

# 4) Remove user-facing Yahoo-only wording while preserving source disclosure in audit.
s=s.replace("Yahoo Finance returned no data for exact ticker {ticker}","Market-data source returned no data for ticker {ticker}")
s=s.replace("GOVI is monthly-only. For daily analysis use an explicit investable Yahoo ticker such as STXGVI.JO.","GOVI is monthly-only. For daily analysis select an instrument with daily observations, such as STXGVI.JO.")
s=s.replace("Exact user-entered Yahoo ticker; history(auto_adjust=False, actions=True). Raw Close plus explicit Dividends.","For market instruments, the selected source identifier is used with raw Close plus explicit Dividends. Repository series use their native validated fields.")
s=s.replace("Yahoo instruments use exact user-entered ticker symbols with history(auto_adjust=False, actions=True). Close, Dividends and Stock Splits are captured as plain pandas series.","Market instruments currently routed through the market-data adapter use history(auto_adjust=False, actions=True); Close, Dividends and Stock Splits are captured as plain pandas series. Repository series use their native validated data. The selector is source-aware and does not present the portfolio as Yahoo-only.")

# Guardrails: cache must contain no yfinance objects in return payload; FX attribution must stay removed.
if 'history_metadata' in s: raise SystemExit('forbidden yfinance metadata cache regression')
if 'FX Attribution' in s or 'fx_decomposition' in s: raise SystemExit('FX attribution regression')
if "title='Pearson Correlation Matrix'" not in s: raise SystemExit('Pearson matrix not restored')
if "text_input('Search asset'" not in s: raise SystemExit('asset search not installed')
p.write_text(s)
print('HOTFIX PATCH: PASS')
