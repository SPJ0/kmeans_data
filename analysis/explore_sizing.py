"""Exploratory 2026-09-23: current LETF AUM vs underlying ADV (descriptive only; see RESEARCH_LOG). Run from repo root."""
import json, os, time, yfinance as yf, pandas as pd
# exploratory: (etf, underlying, leverage) -- leverage from fund names, NOT yet verified
funds = [("TSLL","TSLA",2),("TSLQ","TSLA",-1),("TSLZ","TSLA",-2),("TSLT","TSLA",2),("TSLR","TSLA",2),
 ("NVDL","NVDA",2),("NVDX","NVDA",2),("NVDU","NVDA",2),("NVDQ","NVDA",-2),("NVDD","NVDA",-1),
 ("MSTU","MSTR",2),("MSTX","MSTR",2),("MSTZ","MSTR",-2),("SMST","MSTR",-2),
 ("CONL","COIN",2),("CONX","COIN",2),("PLTU","PLTR",2),("PTIR","PLTR",2),("AMDL","AMD",2),
 ("SMCX","SMCI",2),("HOOX","HOOD",2),("RGTU","RGTI",2),("IONX","IONQ",2),("OKLL","OKLO",2),
 ("AVL","AVGO",2),("METU","META",2),("AAPU","AAPL",2),("AMZU","AMZN",2),("GGLL","GOOGL",2),("MSFU","MSFT",2)]
cache="data/raw/yahoo_info/info_%s.json"
def info(t):
    p=cache%t
    if os.path.exists(p): return json.load(open(p))
    try: d=yf.Ticker(t).info
    except Exception as e: d={"error":str(e)}
    json.dump(d,open(p,"w"),default=str); time.sleep(0.5); return d
rows=[]
for etf,und,L in funds:
    d=info(etf); rows.append(dict(etf=etf,und=und,L=L,aum=d.get("totalAssets") or d.get("netAssets"),name=d.get("longName")))
f=pd.DataFrame(rows)
f["gamma"]=f.aum*f.L*(f.L-1)
u=[]
for und in f.und.unique():
    p=f"data/raw/yahoo_info/hist3mo_{und}.parquet"
    if os.path.exists(p): h=pd.read_parquet(p)
    else: h=yf.Ticker(und).history(period="3mo",auto_adjust=False); h.to_parquet(p); time.sleep(0.5)
    dv=(h.Close*h.Volume).tail(20).mean(); vol=h.Close.pct_change().tail(60).std()
    u.append(dict(und=und,adv20=dv,sd_daily=vol))
u=pd.DataFrame(u)
g=f.groupby("und").agg(aum=("aum","sum"),gamma=("gamma","sum"),n=("etf","size")).reset_index().merge(u,on="und")
g["flow_1sd_pct_adv"]=100*g.gamma*g.sd_daily/g.adv20
g["flow_1sd_pct_closeproxy"]=g.flow_1sd_pct_adv/0.10
pd.set_option("display.width",200)
print(f[["etf","und","L","aum","name"]].to_string())
print(g.sort_values("flow_1sd_pct_adv",ascending=False).to_string(float_format=lambda x:f"{x:,.3g}"))
