#!/usr/bin/env python3
"""Patch the porra dashboard: show each participant's name under their bar
(rotated 45 degrees) in the "Puntos por ronda" chart, and hide the redundant
legend while the names fit. If bars ever get too thin to label (many rounds
x many participants), the chart falls back to the legend automatically.

Usage:
  python patch_round_chart.py porra_mundial_2026.html

A backup is written next to the file (.bak). Safe to run on a dashboard with
any number of participants; it only touches the renderRoundChart function.
"""
import sys
from pathlib import Path

OLD = """function renderRoundChart(scores){
  const el=document.getElementById("ch-round");
  const rounds=ROUND_ORDER.filter(rd=>DATA.schedule.some(m=>m.round===rd&&complete(m.no)));
  if(!rounds.length){el.innerHTML="";legend("lg-round",[]);return;}
  const ptsBy={}; DATA.users.forEach(u=>{ptsBy[u]={};rounds.forEach(rd=>ptsBy[u][rd]=0);});
  DATA.schedule.forEach(m=>{
    if(!complete(m.no))return;
    DATA.users.forEach(u=>{ptsBy[u][m.round]+=scores[u].byMatch[m.no].pts;});
  });
  const max=Math.max(1,...DATA.users.flatMap(u=>rounds.map(rd=>ptsBy[u][rd])));
  const W=920,H=300,L=40,R=10,T=14,B=46;
  const groupW=(W-L-R)/rounds.length, barW=Math.min(34,(groupW-18)/DATA.users.length);
  const Y=v=>T+(H-T-B)*(1-v/max);
  let g="";
  niceTicks(max).forEach(v=>{g+=`<line class="gridline" x1="${L}" x2="${W-R}" y1="${Y(v)}" y2="${Y(v)}"/>
    <text class="axis" x="${L-6}" y="${Y(v)+4}" text-anchor="end">${v}</text>`;});
  rounds.forEach((rd,ri)=>{
    const gx=L+ri*groupW+ (groupW-barW*DATA.users.length)/2;
    DATA.users.forEach((u,ui)=>{
      const v=ptsBy[u][rd], x=gx+ui*barW;
      g+=`<rect x="${x+1}" y="${Y(v)}" width="${barW-2}" height="${(H-T-B)-(Y(v)-T)}" fill="${uColor(u)}" rx="2"/>`;
      if(v>0)g+=`<text class="axis" x="${x+barW/2}" y="${Y(v)-4}" text-anchor="middle" fill="${uColor(u)}">${v}</text>`;
    });
    g+=`<text class="axis" x="${L+ri*groupW+groupW/2}" y="${H-26}" text-anchor="middle">${esc(ROUND_LABEL[rd])}</text>`;
  });
  el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Puntos por ronda">${g}</svg>`;
  legend("lg-round",DATA.users.map(u=>({label:u,color:uColor(u)})));
}"""

NEW = """function renderRoundChart(scores){
  const el=document.getElementById("ch-round");
  const rounds=ROUND_ORDER.filter(rd=>DATA.schedule.some(m=>m.round===rd&&complete(m.no)));
  if(!rounds.length){el.innerHTML="";legend("lg-round",[]);return;}
  const ptsBy={}; DATA.users.forEach(u=>{ptsBy[u]={};rounds.forEach(rd=>ptsBy[u][rd]=0);});
  DATA.schedule.forEach(m=>{
    if(!complete(m.no))return;
    DATA.users.forEach(u=>{ptsBy[u][m.round]+=scores[u].byMatch[m.no].pts;});
  });
  const max=Math.max(1,...DATA.users.flatMap(u=>rounds.map(rd=>ptsBy[u][rd])));
  const W=920,L=40,R=10,T=14;
  const groupW=(W-L-R)/rounds.length, barW=Math.min(34,(groupW-18)/DATA.users.length);
  const longest=Math.max(...DATA.users.map(u=>u.length));
  const named=barW>=9;                      // rotated names fit under the bars
  const B=named?Math.min(150,40+longest*4.6):46, H=named?254+B:300;
  const Y=v=>T+(H-T-B)*(1-v/max);
  let g="";
  niceTicks(max).forEach(v=>{g+=`<line class="gridline" x1="${L}" x2="${W-R}" y1="${Y(v)}" y2="${Y(v)}"/>
    <text class="axis" x="${L-6}" y="${Y(v)+4}" text-anchor="end">${v}</text>`;});
  rounds.forEach((rd,ri)=>{
    const gx=L+ri*groupW+ (groupW-barW*DATA.users.length)/2;
    DATA.users.forEach((u,ui)=>{
      const v=ptsBy[u][rd], x=gx+ui*barW;
      g+=`<rect x="${x+1}" y="${Y(v)}" width="${barW-2}" height="${(H-T-B)-(Y(v)-T)}" fill="${uColor(u)}" rx="2"/>`;
      if(v>0)g+=`<text class="axis" x="${x+barW/2}" y="${Y(v)-4}" text-anchor="middle" fill="${uColor(u)}">${v}</text>`;
      if(named){
        const lx=x+barW/2+3, ly=H-B+14;
        g+=`<text class="axis" x="${lx}" y="${ly}" text-anchor="end" font-size="11.5" fill="${uColor(u)}" transform="rotate(-45 ${lx} ${ly})">${esc(u)}</text>`;
      }
    });
    g+=`<text class="axis" x="${L+ri*groupW+groupW/2}" y="${H-8}" text-anchor="middle" font-size="13" font-weight="700">${esc(ROUND_LABEL[rd])}</text>`;
  });
  el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Puntos por ronda">${g}</svg>`;
  legend("lg-round", named?[]:DATA.users.map(u=>({label:u,color:uColor(u)})));
}"""


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    path = Path(sys.argv[1])
    doc = path.read_text(encoding="utf-8")
    if NEW in doc:
        raise SystemExit(f"{path.name}: already patched — nothing to do.")
    if doc.count(OLD) != 1:
        raise SystemExit(f"{path.name}: could not find the original renderRoundChart "
                         f"function (found {doc.count(OLD)} matches). Has the chart "
                         f"code been modified by hand?")
    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_text(doc, encoding="utf-8")
    path.write_text(doc.replace(OLD, NEW), encoding="utf-8")
    print(f"Patched {path.name} (backup: {backup.name}). "
          f"Participant names now appear rotated under each bar in 'Puntos por ronda'.")


if __name__ == "__main__":
    main()
