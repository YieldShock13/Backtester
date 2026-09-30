from pathlib import Path
p=Path('app.py'); s=p.read_text()
needle='st.set_page_config(page_title="Portfolio Backtester", layout="wide")\n'
assert needle in s
block=r'''st.set_page_config(page_title="Orca's Capital Strategies | Portfolio Backtester", page_icon="🐋", layout="wide")

# Orca's Capital Strategies — visual shell only; analytics and methodology remain unchanged.
st.markdown(r"""
<style>
:root{--orca-bg:#06111f;--orca-panel:#0a1929;--orca-line:#16314b;--orca-blue:#43a9ff;--orca-ice:#d9efff;--orca-text:#eaf4ff;--orca-muted:#8fa8bf}
.stApp{background:linear-gradient(180deg,#06111f 0,#081522 24rem,#f7f9fc 24rem,#f7f9fc 100%)}
[data-testid="stHeader"]{background:rgba(5,14,25,.82);backdrop-filter:blur(12px)}
[data-testid="stToolbar"]{color:#d9efff}
.orca-hero{position:relative;overflow:hidden;height:225px;margin:-1rem -1rem 1.6rem;border-bottom:1px solid #1c3d5b;background:radial-gradient(circle at 18% 65%,rgba(28,132,219,.20),transparent 28%),linear-gradient(110deg,#030a12,#071829 58%,#06111f);box-shadow:0 18px 45px rgba(0,0,0,.22)}
.orca-brand{position:absolute;left:31%;top:53px;z-index:5;border-left:1px solid rgba(145,198,238,.35);padding-left:34px}
.orca-name{font-family:Georgia,'Times New Roman',serif;font-size:52px;letter-spacing:.14em;color:#f5f9fc;line-height:1;text-shadow:0 0 28px rgba(108,187,255,.10)}
.orca-sub{font-family:Arial,sans-serif;font-size:15px;letter-spacing:.48em;color:#61b7ff;margin-top:17px;white-space:nowrap}
.orca-mark{position:absolute;left:5%;top:18px;width:350px;height:185px;z-index:3;animation:orcaFloat 5s ease-in-out infinite;filter:drop-shadow(0 8px 18px rgba(31,153,255,.28))}
.orca-wave{position:absolute;right:-4%;bottom:18px;width:55%;height:120px;opacity:.52}
.orca-wave path{fill:none;stroke:#3faaff;stroke-width:2;stroke-dasharray:5 11;animation:waveDash 8s linear infinite}
.orca-wave .w2{opacity:.48;animation-duration:12s}.orca-wave .w3{opacity:.25;animation-duration:16s}
.orca-glow{position:absolute;width:8px;height:8px;border-radius:50%;background:#67c1ff;box-shadow:0 0 16px #47b2ff;animation:pulse 2.7s ease-in-out infinite}
.g1{right:24%;top:63px}.g2{right:13%;top:116px;animation-delay:.8s}.g3{right:35%;top:144px;animation-delay:1.5s}
@keyframes orcaFloat{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-8px) rotate(1deg)}}
@keyframes waveDash{to{stroke-dashoffset:-160}}
@keyframes pulse{0%,100%{opacity:.2;transform:scale(.65)}50%{opacity:1;transform:scale(1.2)}}
/* retain Streamlit usability below the branded shell */
[data-testid="stMetric"]{border-radius:10px}
.stButton>button{border-radius:8px}
@media(max-width:900px){.orca-hero{height:190px}.orca-mark{left:0;width:250px}.orca-brand{left:35%;top:48px}.orca-name{font-size:31px}.orca-sub{font-size:10px;letter-spacing:.28em}}
</style>
<div class="orca-hero">
 <svg class="orca-mark" viewBox="0 0 420 220" aria-label="Animated orca logo">
  <defs><linearGradient id="ob" x1="0" x2="1"><stop offset="0" stop-color="#02070c"/><stop offset=".65" stop-color="#101c28"/><stop offset="1" stop-color="#05090d"/></linearGradient><linearGradient id="ow" x1="0" x2="1"><stop stop-color="#d9efff"/><stop offset="1" stop-color="#ffffff"/></linearGradient></defs>
  <path d="M70 146 C92 88 161 50 245 58 C292 62 337 84 371 107 C336 104 311 108 286 126 C249 153 197 171 142 168 C111 166 86 159 70 146Z" fill="url(#ob)" stroke="#6ebfff" stroke-width="1.5"/>
  <path d="M171 68 C155 35 171 17 201 8 C193 35 204 51 222 59Z" fill="#03090f" stroke="#6ebfff" stroke-width="1.2"/>
  <path d="M285 124 C320 138 333 160 328 184 C308 160 283 151 255 149Z" fill="#03090f" stroke="#6ebfff" stroke-width="1.2"/>
  <path d="M73 143 C49 129 26 130 7 144 C27 149 43 157 57 173 C59 158 64 150 73 143Z" fill="#07111b" stroke="#6ebfff" stroke-width="1.2"/>
  <path d="M251 81 C281 78 311 88 337 104 C304 104 283 112 264 127 C248 139 225 149 204 151 C226 135 238 118 241 99 C243 91 246 85 251 81Z" fill="url(#ow)" opacity=".96"/>
  <ellipse cx="285" cy="88" rx="17" ry="8" fill="#eef8ff" transform="rotate(-8 285 88)"/>
  <circle cx="328" cy="91" r="3" fill="#74c7ff"/>
  <path d="M63 172 Q115 148 164 175 T266 174" fill="none" stroke="#42adff" stroke-width="3" opacity=".8"/>
  <path d="M42 184 Q100 158 160 187 T287 183" fill="none" stroke="#8bd3ff" stroke-width="2" opacity=".35"/>
 </svg>
 <div class="orca-brand"><div class="orca-name">ORCA'S</div><div class="orca-sub">CAPITAL STRATEGIES</div></div>
 <svg class="orca-wave" viewBox="0 0 800 150" preserveAspectRatio="none"><path d="M0 86 C120 20 190 135 310 75 S520 35 800 88"/><path class="w2" d="M0 110 C140 42 220 145 350 92 S590 50 800 106"/><path class="w3" d="M0 58 C130 5 250 105 390 55 S630 20 800 62"/></svg>
 <span class="orca-glow g1"></span><span class="orca-glow g2"></span><span class="orca-glow g3"></span>
</div>
""",unsafe_allow_html=True)
'''
s=s.replace(needle,block,1)
p.write_text(s)
