
// ============ AUTOPILOT TEMPLATES – notebook / paper style with GTA 6 hook ============
// PLAN = [{t, s, e, p, c}]  (c = cue seconds relative to scene start, or null)
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
const fit=(lines,max=120,w=960)=>{const L=Math.max(...lines.map(l=>String(l).length),4);return Math.max(52,Math.min(max,Math.floor(w/(L*.52))))};
const VP=(s,st='')=>`<img class="vclip" data-d="a/vp" data-n="951" data-s="${s}" data-a="1" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;${st}">`;
const fmtIN=n=>Math.round(n).toLocaleString('en-IN');
const pick=(a,i)=>a[((i%a.length)+a.length)%a.length];
const CUT_SETS=[[26.0,6.4,20.6,9.6,28.0],[6.4,24.0,9.6,20.6,26.0],[20.6,28.0,6.4,26.0,9.6]];
const MK=(l,hl,i)=>i===hl?`<span class="mk">${esc(l)}</span>`:esc(l);
const C=(C,i,d)=>C[i]!=null?C[i]:d;
const T={};

// ---- HOOK: GTA 6 trailer cuts + logo slam + headline + clip cards ----
T.hook=(s,e,p,Cs,ix)=>{const D=e-s;const lines=(p.lines||['GTA 6 clips','auto banao']).slice(0,3);const hl=p.hl==null?1:p.hl;const cuts=pick(CUT_SETS,ix+(p.cover?1:0));const step=Math.max(.4,Math.min(.6,D/6));
 const c0=C(Cs,0,Math.min(1.6,D*.55));const sz=fit(lines,104,880);
 scene(s,e,`
 <div style="position:absolute;left:40px;top:40px;right:40px;bottom:330px;border:6px solid ${INK};border-radius:34px;overflow:hidden;box-shadow:14px 14px 0 ${INK};background:#000">
  ${cuts.map((c,i)=>`<div class="hk_c" style="position:absolute;inset:0;opacity:0">${VP(c-i*step)}</div>`).join('')}
  <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.25),transparent 40%,rgba(0,0,0,.5))"></div></div>
 <div id="hk_lg" style="position:absolute;left:260px;top:470px;width:560px;height:420px;border:7px solid ${INK};border-radius:28px;overflow:hidden;box-shadow:14px 14px 0 ${ORG};opacity:0;z-index:3"><img src="gta6logo.jpg" style="width:100%;height:100%;object-fit:cover"></div>
 <div id="hk_t" style="position:absolute;left:70px;right:70px;top:110px;opacity:0;z-index:4"><div style="display:inline-block;background:${YEL};border:6px solid ${INK};box-shadow:12px 12px 0 ${INK};padding:18px 30px 24px;transform:rotate(-2deg)"><div class="h" style="font-size:${sz}px;line-height:1;color:var(--onhl)">${lines.map((l,i)=>MK(l,hl,i)).join('<br>')} ${esc(p.emoji||'')}</div></div></div>
 ${[0,1,2].map(i=>`<div class="hk_k" data-r="${[-8,4,10][i]}" style="position:absolute;left:${[60,380,700][i]}px;top:${[1000,1040,990][i]}px;width:300px;background:#fff;border:5px solid ${INK};box-shadow:8px 8px 0 ${INK};padding:10px 10px 14px;opacity:0;z-index:4"><div style="position:relative;height:380px;overflow:hidden;border:3px solid ${INK}">${VP(cuts[i])}<div style="position:absolute;left:8px;top:8px;padding:5px 10px;background:${ORG};color:#fff;font:800 22px/1 B;border-radius:6px">✂️ CLIP 0${i+1}</div></div><div style="font:800 28px/1 B;margin-top:10px">${p.cover?'📱 9:16 ready':'✅ auto clipped'}</div></div>`).join('')}
 ${p.cover?NAMEB('hk_nm',1630):''}`,
 (el,lt)=>{el.querySelectorAll('.hk_c').forEach((c,i)=>{const d=i*step,en=(i+1)*step;const last=i===cuts.length-1;c.style.opacity=(lt>=d&&(lt<en+.05||last))?1:0;c.style.transform=`scale(${1.12-.12*ease((lt-d)/.5)})`});
  const lg=el.querySelector('#hk_lg');const q=clamp((lt-.08)/.22);lg.style.opacity=q;lg.style.transform=`rotate(-3deg) scale(${2.2-1.2*back(q)})`;
  slideIn(el.querySelector('#hk_t'),lt,.35,-300,0);mark(el,lt,.6);el.querySelectorAll('.hk_k').forEach((k,i)=>slideIn(k,lt,c0+i*.15,0,500));const nm=el.querySelector('#hk_nm');if(nm)nm.style.opacity=1;
 },{flashAt:.08,flashColor:'#ffffff',shakeAt:.08});};

// ---- APP NAME ----
T.name=(s,e,p,Cs)=>scene(s,e,`${NAMEB('nm_n',620)}<div id="nm_na" style="position:absolute;left:0;right:0;top:860px;text-align:center;font:700 24px/1 B;letter-spacing:.1em;color:#666;opacity:0">NOT AFFILIATED WITH ROCKSTAR GAMES</div>${p.tag?`<div id="nm_t" style="position:absolute;left:0;right:0;top:960px;text-align:center;opacity:0"><span class="tag" style="font-size:46px;background:${YEL}">${esc(p.tag)}</span></div>`:''}`,
 (el,lt)=>{const n=el.querySelector('#nm_n');const q=clamp(lt/.25);n.style.opacity=q;n.style.transform=`scale(${1.8-.8*back(q)})`;el.querySelector('#nm_na').style.opacity=q*.8;const t=el.querySelector('#nm_t');if(t)popIn(t,lt,.5)},{flashAt:0,flashColor:YEL,shakeAt:0});

// ---- STREAMERS ----
T.streamers=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,D*.45);
 scene(s,e,`${H('st_t',esc(p.title||'Kisi bhi bade streamer ki'),170,fit([p.title||'xxxxxxxxxxxxxxxxxxxx'],96,960))}
 <div style="position:absolute;left:0;right:0;top:420px;display:flex;justify-content:center;gap:34px">${[2,1,3].map((k,i)=>`<div class="st_a" style="position:relative;width:${i==1?290:230}px;height:${i==1?290:230}px;margin-top:${i==1?0:30}px;border-radius:50%;border:6px solid ${INK};box-shadow:8px 8px 0 ${i==1?ORG:INK};overflow:hidden;opacity:0">${RCAM(k,0,i==1?278:218,i==1?278:218)}</div>`).join('')}</div>
 <div id="st_p" style="position:absolute;left:0;right:0;top:820px;display:flex;justify-content:center;gap:22px;opacity:0"><span class="tag" style="background:#ff2340;color:#fff;font-size:48px">▶ YouTube</span><span class="tag" style="background:#9146ff;color:#fff;font-size:48px">Twitch</span></div>
 <div class="hand" id="st_h" style="position:absolute;left:0;right:0;top:960px;text-align:center;font-size:72px;opacity:0">koi bhi live stream! 🔴</div>`,
 (el,lt)=>{slideIn(el.querySelector('#st_t'),lt,0,0,60);el.querySelectorAll('.st_a').forEach((a,i)=>popIn(a,lt,.2+i*.18));popIn(el.querySelector('#st_p'),lt,c0);popIn(el.querySelector('#st_h'),lt,c0+.5)},{flashAt:c0,flashColor:YEL});};

// ---- COPY LINK ----
T.copylink=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,D*.45),c1=C(Cs,1,D*.72);
 scene(s,e,`${p.step?STEP(p.step,esc(p.label||'Link copy karo')):''}
 <div id="cl_v" class="card" style="left:60px;top:330px;width:960px;height:620px;opacity:0"><div style="position:absolute;left:0;right:0;top:0;height:470px;overflow:hidden">${RV(2,1)}<div style="position:absolute;left:16px;top:16px" class="live">LIVE</div></div><div style="position:absolute;left:24px;top:495px;font:800 36px/1.2 B">🔴 GTA 6 Live – Insane Chase!</div><div id="cl_sh" style="position:absolute;right:24px;top:550px;padding:12px 24px;border:4px solid ${INK};border-radius:999px;background:#fff;font:800 30px/1 B">↗ Share</div></div>
 <div id="cl_cp" style="position:absolute;left:200px;top:1010px;width:680px;padding:24px;border:5px solid ${INK};border-radius:22px;background:#fff;box-shadow:8px 8px 0 ${INK};font:800 42px/1 B;text-align:center;opacity:0">🔗 Copy link</div>
 <div id="cl_ok" style="position:absolute;left:0;right:0;top:1180px;text-align:center;opacity:0"><span class="tag" style="background:${GRN};color:#fff;font-size:46px">✅ Link copied!</span></div>`,
 (el,lt)=>{if(el.querySelector('#stp'))stepA(el,lt);slideIn(el.querySelector('#cl_v'),lt,.1,0,250);el.querySelector('#cl_sh').style.background=lt>c0?YEL:'#fff';popIn(el.querySelector('#cl_cp'),lt,c0+.1);popIn(el.querySelector('#cl_ok'),lt,c1)},{flashAt:c1,flashColor:YEL});};

// ---- PASTE + START ----
T.paste=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,D*.35),c1=C(Cs,1,D*.6),c2=C(Cs,2,D*.8);
 scene(s,e,`${p.step?STEP(p.step,esc(p.label||'Paste karo')):''}
 ${PHN('pa_ph',350,320,340,`<img src="shots/live_empty.png" style="position:absolute;inset:0;width:100%;height:100%"><img id="pa_l2" src="shots/live_link.png" style="position:absolute;inset:0;width:100%;height:100%;opacity:0">`,'opacity:0')}
 <div id="pa_pt" style="position:absolute;left:390px;top:620px;padding:14px 26px;border-radius:14px;background:${INK};color:#fff;font:800 34px/1 B;opacity:0;z-index:5">📋 Paste</div>
 <div class="hand" id="pa_h" style="position:absolute;left:780px;top:480px;font-size:72px;opacity:0;transform:rotate(-6deg)">bas<br>link! 🔗</div>
 <div id="pa_go" style="position:absolute;left:300px;top:1110px;width:480px;height:120px;border:5px solid ${INK};border-radius:28px;background:${ORG};color:#fff;display:grid;place-items:center;font:800 62px/1 B;box-shadow:10px 10px 0 ${INK};opacity:0;z-index:5">▶ START</div>
 <div id="pa_d" class="note" data-r="-5" style="left:250px;top:1290px;opacity:0;background:${GRN};color:#fff;white-space:nowrap;font-size:56px;z-index:6">${esc(p.done||'✅ Bas ho gaya!')}</div>`,
 (el,lt)=>{if(el.querySelector('#stp'))stepA(el,lt);slideIn(el.querySelector('#pa_ph'),lt,.1,0,300);popIn(el.querySelector('#pa_h'),lt,.6);el.querySelector('#pa_pt').style.opacity=lt>c0-.4&&lt<c0+.05?1:0;el.querySelector('#pa_l2').style.opacity=lt>c0?1:0;
  const g=el.querySelector('#pa_go');popIn(g,lt,c0+.2);if(lt>c1&&lt<c1+.15)g.style.transform='scale(.92)';stampIn(el.querySelector('#pa_d'),lt,c2)},{flashAt:c2,flashColor:YEL,shakeAt:c2});};

// ---- MONITOR ----
T.monitor=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,D*.35),c1=C(Cs,1,D*.65);
 scene(s,e,`${H('mo_t',`${esc(p.title||'Nazar 24/7')} 👀`,170,96)}
 <div id="mo_v" class="card" style="left:60px;top:330px;width:600px;height:620px;opacity:0">${RV(2,0)}<div style="position:absolute;left:14px;top:14px" class="live">LIVE</div><div id="mo_s" style="position:absolute;left:0;right:0;height:7px;background:${ORG}"></div></div>
 <div id="mo_ch" class="card" style="left:690px;top:330px;width:330px;height:620px;padding:16px;opacity:0"><div style="font:800 30px/1 B;margin-bottom:12px">💬 Live chat</div><div id="mo_m"></div></div>
 <div style="position:absolute;left:0;right:0;top:1030px;display:flex;justify-content:center;gap:20px"><span class="mo_x tag" style="opacity:0;font-size:46px;background:${YEL}">📺 Poori stream</span><span class="mo_x tag" style="opacity:0;font-size:46px">💬 Live chat</span></div>`,
 (el,lt)=>{slideIn(el.querySelector('#mo_t'),lt,0,0,60);slideIn(el.querySelector('#mo_v'),lt,.15,-200,0);slideIn(el.querySelector('#mo_ch'),lt,.35,200,0);el.querySelector('#mo_s').style.top=((lt*360)%620)+'px';
  const M=['bhai 🔥','LOL','GG 🐐','what 😂','OMG'];const n=Math.floor(lt/.45);el.querySelector('#mo_m').innerHTML=Array.from({length:Math.min(n,8)},(_,k)=>`<div style="margin-bottom:9px;padding:7px 12px;border:3px solid ${INK};border-radius:12px;background:#fff;font:700 26px/1.1 B;opacity:${1-k*.1}">${M[(n-k)%5]}</div>`).join('');
  el.querySelectorAll('.mo_x').forEach((x,i)=>popIn(x,lt,[c0,c1][i]))});};

// ---- MOMENTS (polaroids) ----
T.moments=(s,e,p,Cs)=>{const D=e-s;const it=(p.items&&p.items.length?p.items:[['🚔','Crazy chase'],['😂','Funny fail'],['🤯','Insane moment']]).slice(0,3);
 scene(s,e,`${p.title?H('mm_t',esc(p.title),170,90):''}
 <div style="position:absolute;left:40px;right:40px;top:${p.title?360:220}px;display:flex;gap:18px">${it.map(([i,t],k)=>`<div class="mm_c" data-r="${[-4,3,-2][k]}" style="flex:1;background:#fff;border:5px solid ${INK};box-shadow:8px 8px 0 ${INK};padding:12px 12px 18px;opacity:0"><div style="position:relative;height:${p.title?600:720}px;overflow:hidden;border:3px solid ${INK}">${RV(k+1,k*3)}</div><div style="font:800 ${String(t).length>11?32:40}px/1.1 B;margin-top:12px;text-align:center">${esc(i)} ${esc(t)}</div></div>`).join('')}</div>`,
 (el,lt)=>{const t=el.querySelector('#mm_t');if(t)slideIn(t,lt,0,0,60);el.querySelectorAll('.mm_c').forEach((c,i)=>popIn(c,lt,C(Cs,i,.15+i*D*.28)))},{shakeAt:C(Cs,0,.15)});};

// ---- HYPE: chat flood + gauge + detect + clip ----
T.hype=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,D*.3),c1=C(Cs,1,D*.6),c2=C(Cs,2,D*.82);
 scene(s,e,`<div id="hy_v" class="card" style="left:60px;top:170px;width:600px;height:340px;opacity:0">${RV(3,2)}<div style="position:absolute;left:12px;top:12px" class="live">LIVE</div></div>
 <div id="hy_ch" class="card" style="left:690px;top:170px;width:330px;height:700px;padding:16px;opacity:0"><div style="font:800 30px/1 B;margin-bottom:12px">💬 Live chat</div><div id="hy_m"></div></div>
 <div id="hy_g" class="card" style="left:60px;top:540px;width:600px;height:330px;padding:20px;opacity:0"><div style="font:800 34px/1 B">🔥 Hype meter</div>
  <svg width="560" height="250" style="position:absolute;left:20px;top:70px"><path d="M 60 230 A 220 220 0 0 1 500 230" fill="none" stroke="#eee" stroke-width="40"/><path id="hy_arc" d="M 60 230 A 220 220 0 0 1 500 230" fill="none" stroke="${ORG}" stroke-width="40" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/><line id="hy_nd" x1="280" y1="230" x2="280" y2="50" stroke="${INK}" stroke-width="10" stroke-linecap="round"/><circle cx="280" cy="230" r="18" fill="${INK}"/></svg>
  <div id="hy_pc" class="h" style="position:absolute;right:26px;top:22px;font-size:60px;color:${ORG}">10%</div></div>
 <div id="hy_a" class="note" data-r="-5" style="left:120px;top:960px;opacity:0;background:${ORG};color:#fff;white-space:nowrap;font-size:58px;z-index:4">${esc(p.stamp1||'🎯 Moment detect!')}</div>
 <div id="hy_b" class="note" data-r="4" style="left:330px;top:1170px;opacity:0;background:${YEL};white-space:nowrap;font-size:62px;z-index:4">${esc(p.stamp2||'✂️ Clip ready!')}</div>`,
 (el,lt)=>{slideIn(el.querySelector('#hy_v'),lt,0,-200,0);slideIn(el.querySelector('#hy_ch'),lt,.2,200,0);slideIn(el.querySelector('#hy_g'),lt,Math.max(.3,c0-.4),-200,0);
  const M=['bhai 🔥','LOL','OMGGG 😱','💀💀💀','CLIP IT','NO WAYYY','GG 🐐','what?! 🤯'];const n=Math.floor(lt<c0?lt/.5:c0/.5+(lt-c0)/.11);
  el.querySelector('#hy_m').innerHTML=Array.from({length:Math.min(n,9)},(_,k)=>{const i=n-k;return `<div style="margin-bottom:9px;padding:7px 12px;border:3px solid ${INK};border-radius:12px;background:${i%3==0?YEL:'#fff'};font:700 25px/1.1 B;opacity:${1-k*.09}">${M[i%8]}</div>`}).join('');
  const h=.1+clamp((lt-c0)/Math.max(.6,c1-c0))*.86;el.querySelector('#hy_arc').style.strokeDashoffset=1-h;const a=(-90+h*180)*Math.PI/180;const nd=el.querySelector('#hy_nd');nd.setAttribute('x2',280+180*Math.sin(a));nd.setAttribute('y2',230-180*Math.cos(a));el.querySelector('#hy_pc').textContent=Math.round(h*100)+'%';
  stampIn(el.querySelector('#hy_a'),lt,c1);stampIn(el.querySelector('#hy_b'),lt,c2)},{flashAt:c2,flashColor:YEL,shakeAt:c1});};

// ---- REWIND ----
T.rewind=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,D*.3),c1=C(Cs,1,D*.5),c2=C(Cs,2,D*.75);
 scene(s,e,`${H('rw_q',`${esc(p.q||'Moment miss ho gaya?')} 😱`,160,fit([(p.q||'')+'xxx'],92,960))}
 <div id="rw_ok" style="position:absolute;left:60px;top:300px;opacity:0"><span class="h" style="color:var(--onhl);display:inline-block;padding:6px 26px 14px;background:${YEL};border:5px solid ${INK};box-shadow:8px 8px 0 ${INK};font-size:70px">${esc(p.ok||'Koi tension nahi')} 😌</span></div>
 <div class="card" style="left:60px;top:450px;width:960px;height:500px">${RV(2,4)}<div id="rw_rw" style="position:absolute;inset:0;background:rgba(0,0,0,.45);display:grid;place-items:center;font-size:160px;opacity:0">⏪</div></div>
 <div style="position:absolute;left:90px;right:90px;top:1010px;height:26px;border:4px solid ${INK};border-radius:13px;background:#fff"><div id="rw_sel" style="position:absolute;top:-16px;left:38%;width:16%;height:50px;border:5px solid ${ORG};border-radius:12px;background:${ORG}33;opacity:0"></div><div id="rw_ph" style="position:absolute;top:-24px;width:14px;height:66px;border-radius:7px;background:${INK}"></div></div>
 <div style="position:absolute;left:0;right:0;top:1090px;display:flex;justify-content:center;gap:16px">${['30s','1 min','2 min','5 min'].map((t,i)=>`<span class="rw_c tag" style="opacity:0;white-space:nowrap;font-size:36px;background:${i==2?YEL:'#fff'}">⏪ ${t}</span>`).join('')}</div>
 <div id="rw_d" class="note" data-r="-4" style="left:270px;top:1250px;opacity:0;background:${ORG};color:#fff;white-space:nowrap;font-size:56px">✂️ Peeche ka clip!</div>`,
 (el,lt)=>{slideIn(el.querySelector('#rw_q'),lt,0,0,60);popIn(el.querySelector('#rw_ok'),lt,c0);el.querySelectorAll('.rw_c').forEach((c,i)=>popIn(c,lt,c1+i*.1));
  const r=clamp((lt-c1-.4)/Math.max(.4,c2-c1-.4));el.querySelector('#rw_rw').style.opacity=r>0&&r<1?1:0;el.querySelector('#rw_ph').style.left=(100-r*62)+'%';el.querySelector('#rw_sel').style.opacity=lt>c2?1:0;stampIn(el.querySelector('#rw_d'),lt,c2)},{flashAt:c2,flashColor:YEL});};

// ---- MANUAL TIMESTAMP ----
T.manual=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,D*.35);
 scene(s,e,`${H('ma_t',esc(p.title||'Ya khud choose karo'),170,fit([p.title||'xxxxxxxxxxxxxxxxxxx'],92,960))}
 <div class="card" style="left:60px;top:340px;width:960px;height:460px;padding:24px"><div style="position:absolute;left:24px;right:24px;top:24px;height:260px;border:4px solid ${INK};border-radius:14px;overflow:hidden">${RV(2,2)}</div><div style="position:absolute;left:24px;right:24px;top:310px;height:60px;border:4px solid ${INK};border-radius:12px;background:repeating-linear-gradient(90deg,#eee 0 38px,#fff 38px 42px)"></div><div id="ma_s" style="position:absolute;left:330px;top:298px;height:84px;border:6px solid ${ORG};border-radius:12px;background:${ORG}33;opacity:0"></div><div id="ma_ts" class="hand" style="position:absolute;left:300px;top:390px;font-size:50px;opacity:0">01:12:40 → 01:13:25</div></div>
 <div id="ma_ok" style="position:absolute;left:0;right:0;top:880px;text-align:center;opacity:0"><span class="tag" style="font-size:48px;background:${YEL}">✅ Apna timestamp, apna clip</span></div>`,
 (el,lt)=>{slideIn(el.querySelector('#ma_t'),lt,0,0,60);const sp=clamp((lt-c0)/.8);const sl=el.querySelector('#ma_s');sl.style.opacity=sp>0?1:0;sl.style.width=(40+sp*260)+'px';el.querySelector('#ma_ts').style.opacity=clamp((lt-c0-.5)/.3);popIn(el.querySelector('#ma_ok'),lt,c0+.9)},{flashAt:c0,flashColor:YEL});};

// ---- COUNT ----
T.count=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,Math.min(.5,D*.2));const N=+p.n||50;
 scene(s,e,`<div style="position:absolute;left:60px;top:170px"><span id="co_n" class="h" style="font-size:300px;color:${ORG};-webkit-text-stroke:6px ${INK}">0</span><span class="h" style="font-size:90px"> clips</span><div class="h" style="font-size:56px;margin-top:-10px">${esc(p.top||'ek stream se')} 👇</div></div>
 <div style="position:absolute;left:180px;right:180px;top:640px;display:grid;grid-template-columns:repeat(10,1fr);gap:7px">${Array.from({length:50},(_,i)=>`<img class="co_t" src="fr${1+i%3}/${String(20+(i*41)%150).padStart(4,'0')}.jpg" style="width:100%;aspect-ratio:9/16;object-fit:cover;border:3px solid ${INK};border-radius:6px">`).join('')}</div>
 ${p.sub?`<div id="co_m" class="note" data-r="-3" style="left:260px;top:1380px;opacity:0;white-space:nowrap;font-size:54px">${esc(p.sub)}</div>`:''}`,
 (el,lt)=>{const n=Math.floor(clamp((lt-c0)/1.0)*N);el.querySelector('#co_n').textContent=n;el.querySelectorAll('.co_t').forEach((x,i)=>{x.style.opacity=i<n*50/N?1:.08});const m=el.querySelector('#co_m');if(m)popIn(m,lt,c0+1.1)},{flashAt:c0+1.0,flashColor:YEL,shakeAt:c0+1.0});};

// ---- NO EDIT (crossed list -> app does it) ----
T.noedit=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,D*.3),c1=C(Cs,1,D*.55);const bad=(p.bad||['Ghanton editing']).slice(0,2);
 scene(s,e,`<div id="ne_p" class="card" style="left:110px;top:200px;width:860px;padding:40px 44px 46px;transform:rotate(-2deg);opacity:0;background:#fffdf6"><div class="hand" style="font-size:58px;color:${INK}">to-do list ✍️</div>${bad.map(b=>`<div class="ne_r" style="position:relative;margin-top:24px;font:800 ${String(b).length>18?46:56}px/1.1 B;opacity:0">❌ ${esc(b)}<i style="position:absolute;left:-10px;right:-10px;top:50%;height:10px;background:${ORG};transform:scaleX(0);transform-origin:left;border-radius:5px"></i></div>`).join('')}</div>
 ${PHN('ne_ph',360,700,300,`${VERT(2,3,300)}<div style="position:absolute;left:0;right:0;top:${Math.round(300*16/9*.43)}px;text-align:center"><span id="ne_c" style="display:inline-block;padding:3px 8px;background:#fff;border:3px solid ${INK};border-radius:8px;font:800 32px/1 B"></span></div>`,'opacity:0')}
 <div id="ne_ok" class="note" data-r="5" style="left:640px;top:880px;opacity:0;background:${GRN};color:#fff;font-size:44px;max-width:400px">🤖 ${esc(p.good||'App khud karega')}</div>`,
 (el,lt)=>{slideIn(el.querySelector('#ne_p'),lt,0,0,200);el.querySelectorAll('.ne_r').forEach((r,i)=>{r.style.opacity=clamp((lt-.2-i*.25)/.2);r.querySelector('i').style.transform=`scaleX(${clamp((lt-c0-i*.2)/.2)})`});
  slideIn(el.querySelector('#ne_ph'),lt,c1,0,300);const k=Math.floor(lt/.3)%3;el.querySelector('#ne_c').innerHTML=lt>c1+.3?['BHAI','KYA','SCENE'].map((w,i)=>`<span style="${i===k?`background:${YEL}`:''}">${w}</span>`).join(' '):'';stampIn(el.querySelector('#ne_ok'),lt,c1+.4)},{flashAt:c0,flashColor:YEL,shakeAt:c0});};

// ---- POST KIT ----
T.postkit=(s,e,p,Cs)=>{const D=e-s;const it=(p.items&&p.items.length?p.items:[['💬','Captions'],['🪝','Hook'],['🏷️','Title']]).slice(0,4);
 scene(s,e,`${H('pk_t',esc(p.title||'Har clip ready'),160,88)}
 ${PHN('pk_ph',60,320,360,`<img src="shots/postkit.png" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover">`,'opacity:0')}
 <div style="position:absolute;left:500px;top:380px;width:520px;display:flex;flex-direction:column;gap:26px">${it.map(([i,t])=>`<div class="pk_k tag" style="opacity:0;font-size:${String(t).length>11?38:46}px;justify-content:space-between">${esc(i)} ${esc(t)} <span style="color:${GRN}">✓</span></div>`).join('')}</div>`,
 (el,lt)=>{slideIn(el.querySelector('#pk_t'),lt,0,0,60);slideIn(el.querySelector('#pk_ph'),lt,.1,-300,0);el.querySelectorAll('.pk_k').forEach((c,i)=>slideIn(c,lt,C(Cs,i,.3+i*(D-.6)/it.length),200,0))});};

// ---- EXPORT ----
T.export=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,D*.25),c1=C(Cs,1,D*.5),c2=C(Cs,2,D*.7),c3=C(Cs,3,D*.82);
 scene(s,e,`${PHN('ex_ph',60,180,360,`${VERT(1,2,360)}<div style="position:absolute;left:0;right:0;bottom:16px;text-align:center"><span style="padding:6px 14px;background:${YEL};border:3px solid ${INK};border-radius:999px;font:800 28px/1 B">📱 9:16</span></div>`,'opacity:0')}
 <div id="ex_w" style="position:absolute;left:500px;top:300px;width:520px;height:292px;border:5px solid ${INK};border-radius:20px;overflow:hidden;box-shadow:10px 10px 0 ${INK};opacity:0">${RV(3,6)}<div style="position:absolute;left:0;right:0;bottom:12px;text-align:center"><span style="padding:6px 14px;background:#fff;border:3px solid ${INK};border-radius:999px;font:800 26px/1 B">🖥 16:9</span></div></div>
 <div id="ex_x" style="position:absolute;left:520px;top:680px;width:480px;height:120px;border:5px solid ${INK};border-radius:24px;background:${ORG};color:#fff;display:grid;place-items:center;font:800 56px/1 B;box-shadow:8px 8px 0 ${INK};opacity:0">⬇ Export</div>
 <div style="position:absolute;left:0;right:0;top:1100px;display:flex;justify-content:center;gap:18px"><span class="ex_u tag" style="opacity:0;font-size:46px;background:linear-gradient(90deg,#f9a03f,#e1306c,#833ab4);color:#fff">📸 Reels</span><span class="ex_u tag" style="opacity:0;font-size:46px;background:#ff2340;color:#fff">▶ Shorts</span></div>`,
 (el,lt)=>{slideIn(el.querySelector('#ex_ph'),lt,0,-300,0);popIn(el.querySelector('#ex_w'),lt,c0);popIn(el.querySelector('#ex_x'),lt,c1);if(lt>c1+.3&&lt<c1+.45)el.querySelector('#ex_x').style.transform='scale(.92)';el.querySelectorAll('.ex_u').forEach((u,i)=>popIn(u,lt,[c2,c3][i]))},{flashAt:c1,flashColor:YEL});};

// ---- FLOW A -> B ----
T.flow=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,D*.3),c1=C(Cs,1,D*.6);
 scene(s,e,`<div style="position:absolute;left:0;right:0;top:330px;display:flex;flex-direction:column;align-items:center;gap:30px">
 <div class="fl_s card" style="position:relative;left:0;top:0;opacity:0;max-width:960px;padding:30px 44px;text-align:center"><div class="h" style="font-size:${fit([p.a||''],80,860)}px">${esc(p.a||'4 ghante ki stream')}</div></div>
 <svg class="fl_s" width="120" height="160" style="opacity:0"><path d="M 60 10 C 40 60, 80 90, 60 140 M 60 140 L 30 110 M 60 140 L 92 112" fill="none" stroke="${ORG}" stroke-width="10" stroke-linecap="round"/></svg>
 <div class="fl_s" style="opacity:0;max-width:960px;padding:30px 44px 40px;text-align:center;background:${YEL};border:6px solid ${INK};box-shadow:12px 12px 0 ${ORG}"><div class="h" style="color:var(--onhl);font-size:${fit([p.b||''],84,860)}px">${esc(p.b||'Ready-to-post clips')}</div></div></div>`,
 (el,lt)=>{const x=el.querySelectorAll('.fl_s');slideIn(x[0],lt,0,0,100);popIn(x[1],lt,c0);popIn(x[2],lt,c1)},{flashAt:c1,flashColor:YEL,shakeAt:c1});};

// ---- STATEMENT ----
T.statement=(s,e,p,Cs,ix)=>{const lines=(p.lines||['Ye app game changer hai']).slice(0,3);const c0=C(Cs,0,.5);const hl=p.hl==null?lines.length-1:p.hl;
 scene(s,e,`<div id="sm_t" style="position:absolute;left:60px;right:60px;top:200px;opacity:0"><div class="h" style="font-size:${fit(lines,118,940)}px">${lines.map((l,i)=>MK(l,hl,i)).join('<br>')} ${esc(p.emoji||'')}</div></div>
 <div id="sm_v" data-r="-3" style="position:absolute;left:120px;top:${330+lines.length*fit(lines,118,940)}px;width:840px;background:#fff;border:5px solid ${INK};box-shadow:10px 10px 0 ${INK};padding:14px 14px 20px;opacity:0"><div style="position:relative;height:440px;overflow:hidden;border:3px solid ${INK}">${(ix%2)?VP(pick([26,6.4,20.6,28],ix)):RV(1+(ix%3),2)}</div></div>`,
 (el,lt)=>{slideIn(el.querySelector('#sm_t'),lt,0,-200,0);mark(el,lt,.3);slideIn(el.querySelector('#sm_v'),lt,c0,0,200)},{flashAt:0,flashColor:YEL});};

// ---- CTA ----
T.cta=(s,e,p,Cs)=>{const D=e-s;const c0=C(Cs,0,D*.35),c1=C(Cs,1,D*.65);
 scene(s,e,`${H('ct_q',`App <span class="mk">chahiye?</span>`,180,130,'text-align:center')}${NAMEB('ct_n',420)}
 <div id="ct_f" style="position:absolute;left:240px;top:760px;width:600px;height:150px;border:5px solid ${INK};border-radius:30px;background:${BLU};color:#fff;display:grid;place-items:center;font:800 70px/1 B;box-shadow:10px 10px 0 ${INK};opacity:0">Follow</div>
 <div id="ct_tap" style="position:absolute;left:640px;top:850px;font-size:110px;opacity:0">👆</div>
 <div id="ct_l" class="note" data-r="-3" style="left:220px;top:1010px;opacity:0;font-size:64px;white-space:nowrap">🔗 Link in bio 👆</div>${ARROW('ct_ar',800,1040,140,180,'M 20 170 C 40 100, 90 60, 120 10 M 120 10 L 80 30 M 120 10 L 126 56')}`,
 (el,lt)=>{el.querySelector('#ct_q').style.opacity=clamp(lt/.2);mark(el,lt,.3);const n=el.querySelector('#ct_n');const q=clamp((lt-.3)/.3);n.style.opacity=q;n.style.transform=`scale(${.5+.5*back(q)})`;
  const f=el.querySelector('#ct_f');popIn(f,lt,Math.max(.4,c0-.5));const tp=lt>c0;f.textContent=tp?'Following ✓':'Follow';f.style.background=tp?INK:BLU;
  const t=el.querySelector('#ct_tap');const tq=clamp((lt-c0+.4)/.3);t.style.opacity=lt<c0+.6?tq:0;t.style.transform=`translate(${(1-tq)*120}px,${(1-tq)*160}px) scale(${lt>c0-.1&&lt<c0+.05?.85:1})`;
  popIn(el.querySelector('#ct_l'),lt,c1);draw(el,'#ct_ar',lt,c1+.2)},{flashAt:c1,flashColor:YEL});};

// ---- PERMISSION ----
T.permission=(s,e,p,Cs)=>scene(s,e+.5,`<div id="pe_w" style="position:absolute;left:0;right:0;top:300px;text-align:center;font-size:170px">⚠️</div>
 <div id="pe_c" class="card" style="left:100px;top:560px;width:880px;padding:40px 46px;opacity:0;transform:rotate(-1deg)"><div class="h" style="font-size:66px">Sirf unhi streamers ko clip karo jo <span class="mk">permission</span> dete hain ✅</div><div class="hand" style="font-size:60px;margin-top:16px">🙏 hamesha credit do</div></div>
 <div style="position:absolute;left:0;right:0;top:1200px;text-align:center;font:700 24px/1 B;letter-spacing:.1em;color:#666">NOT AFFILIATED WITH ROCKSTAR GAMES</div>`,
 (el,lt)=>{el.querySelector('#pe_w').style.transform=`scale(${(.4+.6*back(clamp(lt/.3)))*(1+.04*Math.sin(lt*8))})`;slideIn(el.querySelector('#pe_c'),lt,.3,0,150);mark(el,lt,.8)},{flashAt:0,flashColor:YEL});

PLAN.forEach((b,i)=>{const f=T[b.t]||T.statement;try{f(b.s,b.e,b.p||{},b.c||[],i)}catch(err){console.error(err);T.statement(b.s,b.e,{lines:['GTA 6 Super Clipper']},[],i)}});
