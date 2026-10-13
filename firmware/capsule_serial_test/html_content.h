// LightDX live spectrum page, served at http://192.168.4.1/ ; polls /data (JSON) about 3 times a second.
#pragma once
#include <pgmspace.h>

static const char INDEX_HTML[] PROGMEM = R"HTML(<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LightDX dosimeter</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;padding:12px;background:#111;color:#eee}
h1{font-size:1.1rem;margin:0 0 8px}
canvas{width:100%;max-width:720px;height:300px;background:#1b1b1b;border-radius:6px;display:block}
.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;max-width:720px;margin-top:10px}
.c{background:#1b1b1b;border-radius:6px;padding:8px}.c b{display:block;font-size:1.15rem}.c span{font-size:.75rem;color:#999}
#st{color:#999;font-size:.8rem;margin-top:8px}.w{color:#f90}
.rb{background:#1b1b1b;border-radius:6px;padding:10px;margin-top:10px;max-width:720px;color:#999}.rb.on{background:#5a0f0f;color:#fff;font-weight:600}
a{color:#7cf}button{font:inherit;padding:6px 10px;border-radius:6px;border:1px solid #555;background:#222;color:#eee}
</style></head><body>
<h1>LightDX AS7341 live spectrum</h1>
<div id="rb" class="rb">connecting...</div>
<p><button id="go" type="button">Start recording</button> <button id="stp" type="button">Stop recording</button> <span id="recmsg"></span></p>
<canvas id="cv" width="720" height="300"></canvas>
<div class="g">
<div class="c"><span>E_ppix (arb.)</span><b id="e">-</b></div>
<div class="c"><span>J_ppix, this session (arb.)</span><b id="j">-</b></div>
<div class="c"><span>lux (arb. until calibrated)</span><b id="l">-</b></div>
<div class="c"><span>gain / tint</span><b id="gt">-</b></div>
<div class="c"><span>flicker</span><b id="f">-</b></div>
<div class="c"><span>saturated ch.</span><b id="s">-</b></div>
<div class="c"><span>device time (RTC)</span><b id="dt">-</b></div>
<div class="c"><span>battery</span><b id="bt">-</b></div>
<div class="c"><span>SD card free</span><b id="sd">-</b></div>
</div>
<p><a href="/log" download="lightdx_log.csv">Download data (CSV)</a> &nbsp; <button id="clk" type="button">Set device clock from this phone</button> <span id="clkmsg"></span></p>
<div id="st">connecting...</div>
<script>
const NM=[415,445,480,515,555,590,630,680], COL=["#7a2cff","#3b4bff","#00b7ff","#00d46a","#9be000","#ffc400","#ff5a00","#d40000"];
const cv=document.getElementById('cv'),x=cv.getContext('2d');
function draw(c,norm){
  const W=cv.width,H=cv.height,L=40,B=30,T=10,bw=(W-L-10)/8;
  x.clearRect(0,0,W,H);x.fillStyle='#bbb';x.font='12px sans-serif';
  const mx=Math.max(...c,1e-9);
  for(let i=0;i<8;i++){
    const h=(c[i]/mx)*(H-B-T), bx=L+i*bw+6;
    x.fillStyle=COL[i];x.fillRect(bx,H-B-h,bw-12,h);
    x.fillStyle='#bbb';x.textAlign='center';x.fillText(NM[i],bx+(bw-12)/2,H-12);
  }
  x.textAlign='left';x.fillStyle='#bbb';x.fillText('counts/ms/gain, max '+mx.toPrecision(3)+' (bars normalised to tallest)',L,12);
}
async function tick(){
  try{
    const d=await (await fetch('/data',{cache:'no-store'})).json();
    draw(d.cnt.slice(0,8));
    e.textContent=d.e_ppix.toPrecision(4);j.textContent=d.j_ppix.toPrecision(4);l.textContent=d.lux.toPrecision(4);
    gt.textContent=d.gain+'x / '+d.tint_ms.toFixed(0)+' ms';
    f.textContent=d.flicker_hz?d.flicker_hz+' Hz':'none/unknown';
    s.textContent=d.n_sat;s.className=d.n_sat?'w':'';
    dt.textContent=d.dt;
    rb.textContent=d.rec?'● RECORDING session '+d.sid+' - '+hms(d.el)+' of '+hms(d.mx)+' max':'Not recording: live view only, nothing is logged';
    rb.className=d.rec?'rb on':'rb';
    sd.textContent=d.sd_total_mb>0?(d.sd_free_mb>=1024?(d.sd_free_mb/1024).toFixed(1)+' GB':d.sd_free_mb+' MB')+' of '+(d.sd_total_mb/1024).toFixed(1)+' GB':'no card';
    bt.textContent=(d.batt_mv>0?(d.batt_mv/1000).toFixed(2)+' V':'-')+(d.batt_pct>=0?' ('+d.batt_pct+'%)':'');
    st.textContent='updated '+new Date().toLocaleTimeString()+'  (device uptime '+(d.ms/1000|0)+' s)';
  }catch(err){st.textContent='no data: '+err}
}
const e=document.getElementById('e'),j=document.getElementById('j'),l=document.getElementById('l'),
gt=document.getElementById('gt'),f=document.getElementById('f'),s=document.getElementById('s'),st=document.getElementById('st'),
rb=document.getElementById('rb'),dt=document.getElementById('dt'),bt=document.getElementById('bt'),sd=document.getElementById('sd');
const hms=v=>{v=v|0;const p=x=>String(x).padStart(2,'0');return p(v/3600|0)+':'+p(v/60%60|0)+':'+p(v%60)};
const nowStr=()=>{const n=new Date(),p=v=>String(v).padStart(2,'0');return n.getFullYear()+'-'+p(n.getMonth()+1)+'-'+p(n.getDate())+' '+p(n.getHours())+':'+p(n.getMinutes())+':'+p(n.getSeconds())};
async function recCmd(q){
  const m=document.getElementById('recmsg');
  try{const r=await fetch('/rec?'+q);m.textContent=r.ok?'sent':'failed'}catch(e){m.textContent='failed: '+e}
}
document.getElementById('go').onclick=()=>recCmd('cmd=start&t='+encodeURIComponent(nowStr()));
document.getElementById('stp').onclick=()=>recCmd('cmd=stop');
document.getElementById('clk').onclick=async()=>{
  const n=new Date(),p=v=>String(v).padStart(2,'0');
  const t=n.getFullYear()+'-'+p(n.getMonth()+1)+'-'+p(n.getDate())+' '+p(n.getHours())+':'+p(n.getMinutes())+':'+p(n.getSeconds());
  const m=document.getElementById('clkmsg');
  try{const r=await fetch('/settime?t='+encodeURIComponent(t));m.textContent=r.ok?'clock set to '+t:'failed'}catch(e){m.textContent='failed: '+e}
};
let busy=false;async function loop(){if(!busy){busy=true;await tick();busy=false}}loop();setInterval(loop,300);
</script></body></html>
)HTML";
