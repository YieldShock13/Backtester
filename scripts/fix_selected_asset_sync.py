from pathlib import Path
p=Path('app.py')
s=p.read_text()
old=""" if picked is not None:\n  row=results[picked]; symbol=row['symbol']\n  st.session_state.asset_names[symbol]=row['name']\n  if symbol not in st.session_state.selected_assets:\n   st.session_state.selected_assets.append(symbol); st.rerun()\nASSETS=st.multiselect('Selected assets',options=list(dict.fromkeys(st.session_state.selected_assets+DEFAULT_TICKERS+['GOVI'])),default=st.session_state.selected_assets,key='selected_assets_widget')\nst.session_state.selected_assets=ASSETS\n"""
new=""" if picked is not None:\n  row=results[picked]; symbol=row['symbol']\n  st.session_state.asset_names[symbol]=row['name']\n  if symbol not in st.session_state.selected_assets:\n   st.session_state.selected_assets.append(symbol)\n   # The multiselect is a keyed widget: its existing widget state overrides `default` on rerun.\n   # Synchronise the widget state explicitly so a clicked search result appears immediately.\n   current=list(st.session_state.get('selected_assets_widget',st.session_state.selected_assets))\n   if symbol not in current: current.append(symbol)\n   st.session_state.selected_assets_widget=current\n   st.session_state.asset_search_pick=None\n   st.rerun()\nASSETS=st.multiselect('Selected assets',options=list(dict.fromkeys(st.session_state.selected_assets+DEFAULT_TICKERS+['GOVI'])),default=st.session_state.selected_assets,key='selected_assets_widget')\nst.session_state.selected_assets=ASSETS\n"""
assert old in s, 'target search-selection block not found'
s=s.replace(old,new,1)
p.write_text(s)
print('selected asset widget sync patched')
