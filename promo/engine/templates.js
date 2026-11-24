
// ============ AUTOPILOT SCENE TEMPLATES ============
// PLAN = [{t:type, s:start, e:end, p:{params}, c:[cue seconds relative to scene start or null]}]
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
const fit=(lines,max=130,w=980)=>{const L=Math.max(...lines.map(l=>String(l).length),4);return Math.max(54,Math.min(max,Math.floor(w/(L*.5))))};
const pick=(a,i)=>a[((i%a.length)+a.length)%a.length];
function HEAD(id,lines,hl,emoji,top,max=128){const sz=fit(lines.map((l,i)=>i===lines.length-1&&emoji?l+'xxx':l),max);return `<div id="${id}" style="position:absolute;left:20px;right:20px;top:${top}px;text-align:center;font:400 ${sz}px/.95 H;font-style:italic;text-transform:uppercase;opacity:0">${lines.map((l,i)=>`<div style="white-space:nowrap"><span class="${i===hl?'yl':'wh'}" style="padding-right:.12em">${esc(l)}</span>${i===lines.length-1&&emoji?` ${esc(emoji)}`:''}</div>`).join('')}</div>`}
const SUB=(id,txt,top)=>`<div id="${id}" style="position:absolute;left:0;right:0;top:${top}px;text-align:center;opacity:0"><span style="display:inline-block;padding:20px 40px;border-radius:999px;background:${GR};color:#0c0826;font:800 50px/1.1 P;max-width:960px">${esc(txt)}</span></div>`;

const T={};
// ---- HOOK ----
T.hook=(s,e,p,C,ix)=>{const D=e-s;const lines=(p.lines||['GTA 6 clips','auto banao']).slice(0,3);const hl=p.hl==null?1:p.hl;const vis=p.visual||'phone';const c0=C[0]??Math.min(1.4,D*.5);
 let v='';
 if(vis==='sleep')v=`<div style="position:absolute;right:110px;top:690px;font-size:130px">🌙</div><div style="position:absolute;left:80px;top:820px;width:920px;height:360px"><div style="position:absolute;left:0;right:0;bottom:0;height:150px;border-radius:30px;background:linear-gradient(180deg,${BG4},${BG1})"></div><div style="position:absolute;left:30px;bottom:130px;width:260px;height:110px;border-radius:50px;background:#eee"></div><div style="position:absolute;left:300px;right:20px;bottom:110px;height:130px;border-radius:60px 30px 20px 20px;background:${GR}"></div><div style="position:absolute;left:110px;bottom:190px;font-size:140px">😴</div></div><div id="h_n" style="position:absolute;left:300px;right:300px;top:1220px"></div>`;
 else if(vis==='face')v=`<div id="h_v" style="position:absolute;left:290px;top:700px;width:500px;height:500px;border-radius:50%;padding:12px;background:conic-gradient(${OR},${PU},${OR});box-shadow:0 0 90px ${OR}66;opacity:0"><div style="position:relative;width:100%;height:100%;border-radius:50%;overflow:hidden">${RCAM(pick([1,2,3],ix),0,476,476)}</div><div style="position:absolute;left:50%;bottom:-10px;transform:translateX(-50%)" class="live">LIVE</div></div><div id="h_n" style="position:absolute;left:150px;right:150px;top:1260px"></div>`;
 else if(vis==='cards')v=`<div style="position:absolute;left:40px;right:40px;top:720px;height:560px">${[0,1,2].map(i=>`<div class="h_c" style="position:absolute;left:${60+i*300}px;top:${i==1?0:60}px;width:300px;height:500px;border-radius:26px;overflow:hidden;border:4px solid ${OR};box-shadow:0 30px 80px #000a;transform:rotate(${(i-1)*8}deg);opacity:0">${RV(i+1,i*2)}<div style="position:absolute;left:10px;top:10px" class="live">LIVE</div></div>`).join('')}</div>`;
 else v=`<div id="h_v" style="position:absolute;left:330px;top:${215+Math.round(lines.length*fit(lines,128)*.95)}px;width:420px;height:747px;border-radius:48px;overflow:hidden;border:10px solid ${BG1};box-shadow:0 0 0 2px ${OR}88,0 0 90px ${PU}55;opacity:0">${VERT(pick([1,2,3],ix),0,400)}<div style="position:absolute;left:16px;top:16px" class="live">LIVE</div><div id="h_cut" style="position:absolute;left:0;right:0;top:330px;height:8px;background:${OR};box-shadow:0 0 30px ${OR};opacity:0"></div><div id="h_sc" style="position:absolute;left:-80px;top:278px;font-size:100px;opacity:0">✂️</div></div>`;
 scene(s,e,`${HEAD('h_t',lines,hl,p.emoji,170)}${v}${p.cover?NAME('h_nm',1300)+`<div style="position:absolute;left:0;right:0;top:1560px;text-align:center"><span style="display:inline-block;padding:20px 40px;border-radius:999px;background:${GR};color:#0c0826;font:800 52px/1 P">✂️ 50 clips · 📱 No laptop</span></div>`:''}`,(el,lt)=>{popIn(el.querySelector('#h_t'),lt,0);const nm=el.querySelector('#h_nm');if(nm)nm.style.opacity=1;
  const hv=el.querySelector('#h_v');if(hv){const q=clamp((lt-.4)/.35);hv.style.opacity=q;hv.style.transform=`translateY(${(1-ease(q))*400}px)`}
  el.querySelectorAll('.h_c').forEach((c,i)=>{const q=clamp((lt-.4-i*.15)/.3);c.style.opacity=q;c.style.transform=`rotate(${(i-1)*8}deg) translateY(${(1-ease(q))*300}px)`});
  const sc=el.querySelector('#h_sc');if(sc){const sp=clamp((lt-c0+.3)/.6);sc.style.opacity=sp>0&&sp<1?1:0;sc.style.left=(-80+sp*480)+'px';const cu=el.querySelector('#h_cut');cu.style.opacity=sp>.05?1:0;cu.style.clipPath=`inset(0 ${100-sp*100}% 0 0)`}
  const n=el.querySelector('#h_n');if(n){const k=Math.max(0,Math.floor((lt-.8)/.25));n.innerHTML=Array.from({length:Math.min(k,2)},(_,j)=>`<div style="margin-bottom:12px;padding:14px 20px;border-radius:18px;background:rgba(0,0,0,.6);border:2px solid ${OR};font:800 30px/1.2 P">✂️ Clip #${k-j} ready</div>`).join('')}
 },{flashAt:c0,flashColor:OR,shakeAt:c0});};

// ---- APP NAME ----
T.name=(s,e,p,C)=>scene(s,e,`${NAME('n_n',640)}<div id="n_na" style="position:absolute;left:0;right:0;top:860px;text-align:center;font:600 24px/1 P;color:${MUT};letter-spacing:.1em;opacity:0">NOT AFFILIATED WITH ROCKSTAR GAMES</div>${p.tag?SUB('n_s',p.tag,980):''}`,
 (el,lt)=>{const n=el.querySelector('#n_n');const q=clamp(lt/.3);n.style.opacity=q;n.style.transform=`scale(${.4+.6*back(q)})`;el.querySelector('#n_na').style.opacity=q*.8;const sb=el.querySelector('#n_s');if(sb)popIn(sb,lt,.5)},{flashAt:0,flashColor:OR,shakeAt:0});

// ---- STREAMERS ----
T.streamers=(s,e,p,C)=>{const D=e-s;const c0=C[0]??D*.45;const CS=[2,1,3];
 scene(s,e,`${HEAD('st_t',[p.title||'Kisi bhi bade streamer ki'],0,'',180,84)}
 <div style="position:absolute;left:0;right:0;top:420px;display:flex;justify-content:center;gap:30px">${CS.map(k=>`<div class="st_a" style="opacity:0;width:${k==1?300:240}px;height:${k==1?300:240}px;margin-top:${k==1?0:30}px;border-radius:50%;padding:9px;background:conic-gradient(${OR},${PU},${OR});box-shadow:0 0 50px ${OR}66"><div style="position:relative;width:100%;height:100%;border-radius:50%;overflow:hidden">${RCAM(k,0,(k==1?300:240)-18,(k==1?300:240)-18)}</div></div>`).join('')}</div>
 <div id="st_p" style="position:absolute;left:0;right:0;top:820px;display:flex;justify-content:center;gap:24px;opacity:0"><span style="padding:20px 36px;border-radius:999px;background:#ff2340;font:800 52px/1 P">▶ YouTube</span><span style="padding:20px 36px;border-radius:999px;background:#9146ff;font:800 52px/1 P">🟣 Twitch</span></div>
 <div id="st_l" style="position:absolute;left:0;right:0;top:1000px;text-align:center;opacity:0">${chip('🔴 LIVE stream')}</div>`,
 (el,lt)=>{popIn(el.querySelector('#st_t'),lt,0);el.querySelectorAll('.st_a').forEach((c,i)=>popIn(c,lt,.2+i*.18));popIn(el.querySelector('#st_p'),lt,c0);popIn(el.querySelector('#st_l'),lt,c0+.4)},{flashAt:c0,flashColor:'#ffffff'});};

// ---- COPY LINK ----
T.copylink=(s,e,p,C)=>{const D=e-s;const c0=C[0]??D*.45,c1=C[1]??D*.72;
 scene(s,e,`${p.step?STEP('cl_s',p.step,p.label||'Link copy karo'):''}
 <div id="cl_v" class="card" style="left:70px;top:300px;width:940px;height:620px;overflow:hidden;opacity:0;padding:0"><div style="position:absolute;left:0;right:0;top:0;height:470px;overflow:hidden">${RV(2,1)}<div style="position:absolute;left:18px;top:18px" class="live">LIVE</div></div><div style="position:absolute;left:24px;top:490px;font:800 34px/1.2 P">🔴 GTA 6 Live – Insane Chase!</div><div id="cl_sh" style="position:absolute;right:24px;top:550px;padding:12px 24px;border-radius:999px;background:rgba(255,255,255,.12);font:800 30px/1 P">↗ Share</div></div>
 <div id="cl_cp" style="position:absolute;left:200px;top:980px;width:680px;padding:24px;border-radius:24px;background:#fff;color:#111;font:800 40px/1 P;text-align:center;opacity:0">🔗 Copy link</div>
 <div id="cl_ok" style="position:absolute;left:0;right:0;top:1150px;text-align:center;opacity:0">${chip('✅ Link copied!')}</div>${TAP('cl_tap',890,870)}`,
 (el,lt)=>{stepA(el,lt);rise(el.querySelector('#cl_v'),lt,.1,.4,250);tapA(el,'#cl_tap',lt,c0-.25,.6);el.querySelector('#cl_sh').style.background=lt>c0?OR:'rgba(255,255,255,.12)';
  popIn(el.querySelector('#cl_cp'),lt,c0+.1);popIn(el.querySelector('#cl_ok'),lt,c1)},{flashAt:c1,flashColor:'#ffffff'});};

// ---- PASTE + START ----
T.paste=(s,e,p,C)=>{const D=e-s;const c0=C[0]??D*.35,c1=C[1]??D*.6,c2=C[2]??D*.8;
 scene(s,e,`${p.step?STEP('pa_s',p.step,p.label||'App mein paste'):''}
 ${PHONE('pa_ph',365,290,330,`<img src="shots/live_empty.png" style="position:absolute;inset:0;width:100%;height:100%"><img id="pa_l2" src="shots/live_link.png" style="position:absolute;inset:0;width:100%;height:100%;opacity:0">`,'opacity:0')}
 <div id="pa_pt" style="position:absolute;left:150px;top:570px;padding:14px 26px;border-radius:14px;background:#222;color:#fff;font:800 34px/1 P;opacity:0;z-index:5">📋 Paste</div>
 <div id="pa_go" style="position:absolute;left:290px;top:930px;width:500px;height:120px;border-radius:30px;background:${GR};color:#0c0826;display:grid;place-items:center;font:400 70px/1 H;font-style:italic;opacity:0;z-index:5">▶ START</div>${TAP('pa_tap',600,990)}
 ${stamp('pa_d',esc(p.done||'✅ Bas ho gaya!'),1180,92)}`,
 (el,lt)=>{stepA(el,lt);const ph=el.querySelector('#pa_ph');const q=clamp((lt-.1)/.35);ph.style.opacity=q;ph.style.transform=`translateY(${(1-ease(q))*400}px)`;
  el.querySelector('#pa_pt').style.opacity=lt>c0-.4&&lt<c0+.1?1:0;el.querySelector('#pa_l2').style.opacity=lt>c0?1:0;
  const g=el.querySelector('#pa_go');popIn(g,lt,c0+.2);if(lt>c1)g.style.transform=`scale(${lt<c1+.15?.9:1})`;tapA(el,'#pa_tap',lt,c1-.3,.6);stampA(el.querySelector('#pa_d'),lt,c2)},{flashAt:c2,flashColor:OR,shakeAt:c2});};

// ---- MONITOR ----
T.monitor=(s,e,p,C)=>{const D=e-s;const c0=C[0]??D*.35,c1=C[1]??D*.65;
 scene(s,e,`<div style="position:absolute;left:0;right:0;top:160px;text-align:center"><div class="kick" id="mo_k">${esc(p.kicker||'Clipper Engine')}</div></div>${HEAD('mo_t',[p.title||'24/7 monitoring'],0,'👀',220,96)}
 <div id="mo_v" class="card" style="left:60px;top:400px;width:960px;height:540px;overflow:hidden;opacity:0;padding:0">${RV(2,0)}<div style="position:absolute;left:20px;top:20px" class="live">LIVE</div><div id="mo_sc" style="position:absolute;left:0;right:0;height:6px;background:${OR};box-shadow:0 0 30px ${OR}"></div></div>
 <div style="position:absolute;left:60px;right:60px;top:1000px;display:flex;gap:20px;justify-content:center"><span class="mo_x" style="opacity:0">${chip('📺 Poori stream')}</span><span class="mo_x" style="opacity:0">${chip('💬 Live chat')}</span></div>`,
 (el,lt)=>{kickA(el.querySelector('#mo_k'),lt,0);popIn(el.querySelector('#mo_t'),lt,0);popIn(el.querySelector('#mo_v'),lt,.2);el.querySelector('#mo_sc').style.top=((lt*400)%540)+'px';el.querySelectorAll('.mo_x').forEach((c,i)=>popIn(c,lt,[c0,c1][i]))});};

// ---- MOMENTS ----
T.moments=(s,e,p,C)=>{const D=e-s;const it=(p.items&&p.items.length?p.items:[['🚔','Crazy chase'],['😂','Funny fail'],['🤯','Insane moment']]).slice(0,3);
 scene(s,e,`${p.title?HEAD('mm_t',[p.title],0,'',170,84):''}
 <div style="position:absolute;left:60px;right:60px;top:${p.title?330:220}px;display:flex;gap:20px">${it.map(([i,t],k)=>`<div class="mm_c" style="position:relative;flex:1;height:760px;border-radius:26px;overflow:hidden;opacity:0;border:4px solid ${OR}">${RV(k+1,k*3)}<div style="position:absolute;inset:0;background:linear-gradient(transparent 50%,rgba(0,0,0,.92))"></div><div style="position:absolute;left:10px;right:10px;bottom:20px;text-align:center"><div style="font-size:70px">${esc(i)}</div><div style="font:400 ${fit([t],50,280)}px/1 H;font-style:italic;text-transform:uppercase">${esc(t)}</div></div></div>`).join('')}</div>`,
 (el,lt)=>{if(el.querySelector('#mm_t'))popIn(el.querySelector('#mm_t'),lt,0);el.querySelectorAll('.mm_c').forEach((c,i)=>{popIn(c,lt,C[i]??(.15+i*D*.28));})},{shakeAt:C[0]??.15});};

// ---- CHAT HYPE + DETECT + CLIP ----
T.hype=(s,e,p,C)=>{const D=e-s;const c0=C[0]??D*.3,c1=C[1]??D*.6,c2=C[2]??D*.82;
 scene(s,e,`<div id="hy_v" class="card" style="left:60px;top:170px;width:960px;height:480px;overflow:hidden;padding:0">${RV(3,2)}<div style="position:absolute;left:20px;top:20px" class="live">LIVE</div></div>
 <div id="hy_ch" style="position:absolute;left:60px;width:560px;top:690px;height:640px;overflow:hidden"></div>
 <div id="hy_m" class="card" style="left:650px;top:690px;width:370px;padding:24px;opacity:0"><div style="font:400 44px/1 H;font-style:italic">🔥 HYPE</div><div id="hy_p" style="font:400 110px/1 H;color:${OR};margin-top:10px;padding-right:.1em">0%</div><div style="margin-top:14px;height:26px;border-radius:13px;background:rgba(255,255,255,.08);overflow:hidden"><div id="hy_f" style="height:100%;width:0;background:${GR}"></div></div></div>
 ${stamp('hy_a',esc(p.stamp1||'🎯 Moment detect!'),820,96)}${stamp('hy_b',esc(p.stamp2||'✂️ Clip ready!'),1100,108)}`,
 (el,lt)=>{const M=['OMGGG 😱','BHAIIII 🔥','CLIP IT!!','💀💀💀','NO WAYYY','LMAOOO 😂','INSANE 🤯','GG 🐐'];
  const n=Math.floor(lt<c0?lt/.5:c0/.5+(lt-c0)/.09);el.querySelector('#hy_ch').innerHTML=Array.from({length:Math.min(n,8)},(_,k)=>{const i=n-k;return `<div style="margin-bottom:10px;padding:12px 20px;border-radius:20px;background:${i%2?PK+'26':OR+'22'};border:2px solid ${i%2?PK:OR};font:800 34px/1.1 P;opacity:${1-k*.12}">${M[i%M.length]}</div>`}).join('');
  popIn(el.querySelector('#hy_m'),lt,c0);const h=Math.round(15+clamp((lt-c0)/Math.max(.6,c1-c0))*80);el.querySelector('#hy_p').textContent=h+'%';el.querySelector('#hy_f').style.width=h+'%';
  stampA(el.querySelector('#hy_a'),lt,c1);stampA(el.querySelector('#hy_b'),lt,c2)},{flashAt:c2,flashColor:OR,shakeAt:c1});};

// ---- REWIND (Clip from) ----
T.rewind=(s,e,p,C)=>{const D=e-s;const c0=C[0]??D*.3,c1=C[1]??D*.5,c2=C[2]??D*.75;
 scene(s,e,`${HEAD('rw_q',[p.q||'Moment miss ho gaya?'],-1,'😱',170,96)}<div id="rw_ok" style="position:absolute;left:0;right:0;top:300px;text-align:center;opacity:0;font:400 80px/1 H;font-style:italic;text-transform:uppercase"><span class="yl" style="padding-right:.12em">${esc(p.ok||'Koi tension nahi')}</span> 😎</div>
 <div class="card" style="left:70px;top:440px;width:940px;height:530px;overflow:hidden;padding:0">${RV(2,4)}<div id="rw_rw" style="position:absolute;inset:0;background:rgba(0,0,0,.45);display:grid;place-items:center;font-size:160px;opacity:0">⏪</div></div>
 <div style="position:absolute;left:90px;right:90px;top:1010px;height:20px;border-radius:10px;background:linear-gradient(90deg,${BG4},${OR})"><div id="rw_sel" style="position:absolute;top:-14px;left:38%;width:16%;height:48px;border:5px solid #fff;border-radius:12px;background:${PU}55;opacity:0"></div><div id="rw_ph" style="position:absolute;top:-22px;width:12px;height:64px;border-radius:6px;background:#fff;box-shadow:0 0 20px #fff"></div></div>
 <div id="rw_lb" style="position:absolute;left:0;right:0;top:1090px;text-align:center;opacity:0;font:400 70px/1 H;font-style:italic">⏪ CLIP FROM</div>
 <div style="position:absolute;left:0;right:0;top:1190px;display:flex;justify-content:center;gap:18px">${['30s','1 min','2 min','5 min'].map((t,i)=>`<span class="rw_c" style="opacity:0;white-space:nowrap;padding:18px 22px;border-radius:999px;background:${i==2?GR:BG1+'f0'};color:${i==2?'#0c0826':'#fff'};border:3px solid ${OR};font:800 36px/1 P">${t} ago</span>`).join('')}</div>${stamp('rw_d','✂️ Peeche ka clip!',1330,90)}`,
 (el,lt)=>{popIn(el.querySelector('#rw_q'),lt,0);popIn(el.querySelector('#rw_ok'),lt,c0);el.querySelector('#rw_lb').style.opacity=clamp((lt-c1)/.3);el.querySelectorAll('.rw_c').forEach((c,i)=>popIn(c,lt,c1+i*.1));
  const r=clamp((lt-c1-.4)/Math.max(.4,c2-c1-.4));el.querySelector('#rw_rw').style.opacity=r>0&&r<1?1:0;el.querySelector('#rw_ph').style.left=(100-r*62)+'%';el.querySelector('#rw_sel').style.opacity=lt>c2?1:0;stampA(el.querySelector('#rw_d'),lt,c2)},{flashAt:c2,flashColor:'#ffffff'});};

// ---- MANUAL TIMESTAMP ----
T.manual=(s,e,p,C)=>{const D=e-s;const c0=C[0]??D*.35;
 scene(s,e,`${HEAD('ma_t',[p.title||'Ya khud choose karo'],0,'',170,84)}<div class="card" style="left:70px;top:330px;width:940px;height:430px;padding:30px;overflow:hidden"><div style="position:absolute;left:30px;right:30px;top:30px;height:250px;border-radius:18px;overflow:hidden">${RV(2,2)}</div><div style="position:absolute;left:30px;right:30px;top:310px;height:56px;border-radius:12px;background:repeating-linear-gradient(90deg,${BG4} 0 38px,${BG1} 38px 40px)"></div><div id="ma_s" style="position:absolute;left:330px;top:300px;height:76px;border:5px solid ${OR};border-radius:14px;background:${OR}33;opacity:0"></div><div id="ma_ts" style="position:absolute;left:300px;top:385px;font:800 30px/1 P;color:${OR};opacity:0">⏱ 01:12:40 → 01:13:25</div></div>
 ${TAP('ma_tap',560,700)}<div id="ma_ok" style="position:absolute;left:0;right:0;top:860px;text-align:center;opacity:0">${chip('✅ Apna timestamp, apna clip')}</div>`,
 (el,lt)=>{popIn(el.querySelector('#ma_t'),lt,0);const sp=clamp((lt-c0)/.8);const sl=el.querySelector('#ma_s');sl.style.opacity=sp>0?1:0;sl.style.width=(40+sp*260)+'px';el.querySelector('#ma_ts').style.opacity=clamp((lt-c0-.5)/.3);tapA(el,'#ma_tap',lt,c0-.3,1.1);popIn(el.querySelector('#ma_ok'),lt,c0+.9)},{flashAt:c0,flashColor:'#ffffff'});};

// ---- COUNT 50 ----
T.count=(s,e,p,C)=>{const D=e-s;const c0=C[0]??Math.min(.5,D*.2);const N=+p.n||50;
 scene(s,e,`<div style="position:absolute;left:0;right:0;top:200px;text-align:center;font:400 70px/1 H;font-style:italic;text-transform:uppercase">${esc(p.top||'Ek stream se')} 👇</div>
 <div style="position:absolute;left:0;right:0;top:300px;text-align:center"><span id="co_n" class="yl" style="font:400 260px/1 H;font-style:italic;display:inline-block;padding-right:.2em">0</span><span style="font:400 110px/1 H;font-style:italic"> CLIPS</span></div>
 <div style="position:absolute;left:200px;right:200px;top:640px;display:grid;grid-template-columns:repeat(10,1fr);gap:8px">${Array.from({length:50},(_,i)=>`<img class="co_t" src="fr${1+i%3}/${String(20+(i*41)%150).padStart(4,'0')}.jpg" style="width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;border:2px solid ${OR}">`).join('')}</div>${p.sub?pill('co_m',esc(p.sub),1330):''}`,
 (el,lt)=>{const n=Math.floor(clamp((lt-c0)/1.0)*N);el.querySelector('#co_n').textContent=n;el.querySelectorAll('.co_t').forEach((x,i)=>{x.style.opacity=i<n*50/N?1:.06});const m=el.querySelector('#co_m');if(m)pillA(m,lt,c0+1.1)},{flashAt:c0+1.0,flashColor:'#ffffff',shakeAt:c0+1.0});};

// ---- NO EDITING ----
T.noedit=(s,e,p,C)=>{const D=e-s;const c0=C[0]??D*.3,c1=C[1]??D*.55;const bad=(p.bad||['Ghanton editing']).slice(0,2);
 scene(s,e,`<div style="position:absolute;left:110px;top:170px;width:860px;display:flex;flex-direction:column;gap:20px">${bad.map(b=>`<div class="ne_b card" style="position:relative;left:0;top:0;padding:26px 36px;border-color:${PK}99;opacity:0;font:400 ${fit([b],64,760)}px/1.05 H;font-style:italic;text-transform:uppercase">⏳ ${esc(b)}<div class="ne_x" style="position:absolute;left:0;right:0;top:50%;height:12px;margin-top:-6px;border-radius:6px;background:#ff2340;box-shadow:0 0 20px #ff2340;transform:scaleX(0);transform-origin:left"></div></div>`).join('')}</div>
 <div id="ne_ph" style="position:absolute;left:330px;top:${bad.length>1?470:380}px;width:420px;height:747px;border-radius:48px;overflow:hidden;border:10px solid ${BG1};box-shadow:0 0 0 2px ${OR}88,0 0 90px ${PU}55;opacity:0">${VERT(2,3,400)}<div style="position:absolute;left:0;right:0;top:${Math.round(400*16/9*.42)}px;text-align:center"><span id="ne_c" style="font:400 56px/1 H;text-transform:uppercase;-webkit-text-stroke:3px #000;paint-order:stroke"></span></div></div>
 <div id="ne_ok" style="position:absolute;left:0;right:0;top:${bad.length>1?1260:1180}px;text-align:center;opacity:0"><span style="display:inline-block;padding:18px 34px;border-radius:999px;background:${GR};color:#0c0826;font:800 44px/1 P">🤖 ${esc(p.good||'App khud: captions + editing')}</span></div>`,
 (el,lt)=>{el.querySelectorAll('.ne_b').forEach((b,i)=>{popIn(b,lt,.1+i*.25);const x=b.querySelector('.ne_x');x.style.transform=`scaleX(${clamp((lt-c0-i*.2)/.2)})`;if(lt>c0+i*.2+.2)b.style.filter='grayscale(1) brightness(.6)'});
  const ph=el.querySelector('#ne_ph');const q=clamp((lt-c1)/.35);ph.style.opacity=q;ph.style.transform=`translateY(${(1-ease(q))*300}px)`;const k=Math.floor(lt/.28)%3;el.querySelector('#ne_c').innerHTML=lt>c1+.3?['BHAI','KYA','SCENE'].map((w,i)=>`<span style="color:${i===k?'#ffc21e':'#fff'}">${w}</span>`).join(' '):'';popIn(el.querySelector('#ne_ok'),lt,c1+.4)},{flashAt:c0,flashColor:'#ff2340',shakeAt:c0});};

// ---- POST KIT ----
T.postkit=(s,e,p,C)=>{const D=e-s;const it=(p.items&&p.items.length?p.items:[['💬','Captions'],['🪝','Hook'],['🏷️','Title']]).slice(0,4);
 scene(s,e,`${HEAD('pk_t',[p.title||'Har clip mein ready'],0,'',160,80)}<div id="pk_ph" style="position:absolute;left:70px;top:300px;width:420px;height:909px;border-radius:44px;overflow:hidden;border:10px solid ${BG1};box-shadow:0 0 0 2px ${OR}88,0 0 90px ${PU}55"><img src="shots/postkit.png" style="width:100%;height:100%;display:block"></div>
 <div style="position:absolute;left:530px;top:400px;width:500px;display:flex;flex-direction:column;gap:30px">${it.map(([i,t])=>`<div class="pk_k" style="opacity:0;display:flex;align-items:center;gap:16px;padding:24px 26px;border-radius:26px;background:${BG1}f0;border:3px solid ${OR};font:800 ${String(t).length>11?38:48}px/1 P">${esc(i)} ${esc(t)} <span class="tick" style="width:50px;height:50px;font-size:30px;flex:none">✓</span></div>`).join('')}</div>`,
 (el,lt)=>{popIn(el.querySelector('#pk_t'),lt,0);rise(el.querySelector('#pk_ph'),lt,0,.4,300);el.querySelectorAll('.pk_k').forEach((c,i)=>popIn(c,lt,C[i]??(.3+i*(D-.6)/it.length)))});};

// ---- EXPORT ----
T.export=(s,e,p,C)=>{const D=e-s;const c0=C[0]??D*.25,c1=C[1]??D*.5,c2=C[2]??D*.7,c3=C[3]??D*.82;
 scene(s,e,`<div id="ex_v" style="position:absolute;left:90px;top:170px;width:400px;height:711px;border-radius:44px;overflow:hidden;border:8px solid ${BG1};box-shadow:0 0 0 2px ${OR}88;opacity:0">${VERT(1,2,384)}<div style="position:absolute;left:0;right:0;bottom:16px;text-align:center"><span style="padding:8px 16px;border-radius:999px;background:#000a;font:800 28px/1 P">📱 9:16</span></div></div>
 <div id="ex_w" style="position:absolute;left:530px;top:330px;width:470px;height:264px;border-radius:24px;overflow:hidden;border:6px solid ${OR};opacity:0">${RV(3,6)}<div style="position:absolute;left:0;right:0;bottom:12px;text-align:center"><span style="padding:8px 16px;border-radius:999px;background:#000a;font:800 26px/1 P">🖥 16:9</span></div></div>
 ${stamp('ex_x','⬇ Export!',920,116)}<div style="position:absolute;left:0;right:0;top:1150px;display:flex;justify-content:center;gap:20px"><span class="ex_u" style="opacity:0;padding:20px 32px;border-radius:999px;background:linear-gradient(90deg,#f58529,#dd2a7b,#8134af);font:800 46px/1 P">📸 Reels ✅</span><span class="ex_u" style="opacity:0;padding:20px 32px;border-radius:999px;background:#ff2340;font:800 46px/1 P">▶ Shorts ✅</span></div>`,
 (el,lt)=>{popIn(el.querySelector('#ex_v'),lt,0);popIn(el.querySelector('#ex_w'),lt,c0);stampA(el.querySelector('#ex_x'),lt,c1);el.querySelectorAll('.ex_u').forEach((u,i)=>popIn(u,lt,[c2,c3][i]))},{flashAt:c1,flashColor:OR});};

// ---- FLOW A -> B ----
T.flow=(s,e,p,C)=>{const D=e-s;const c0=C[0]??D*.3,c1=C[1]??D*.6;
 scene(s,e,`<div style="position:absolute;left:0;right:0;top:330px;display:flex;flex-direction:column;align-items:center;gap:24px"><div class="fl_s" style="opacity:0;max-width:980px;text-align:center;padding:28px 44px;border-radius:28px;background:${BG1}f2;border:3px solid ${PU};font:400 ${fit([p.a||''],80,900)}px/1.05 H;font-style:italic;text-transform:uppercase">${esc(p.a||'4 ghante ki stream')}</div><div class="fl_s" style="opacity:0;font-size:100px">⬇</div><div class="fl_s" style="opacity:0;max-width:980px;text-align:center;padding:28px 44px;border-radius:28px;background:${GR};color:#0c0826;font:400 ${fit([p.b||''],80,900)}px/1.05 H;font-style:italic;text-transform:uppercase">${esc(p.b||'Ready-to-post clips')}</div></div>`,
 (el,lt)=>{const x=el.querySelectorAll('.fl_s');popIn(x[0],lt,0);popIn(x[1],lt,c0);popIn(x[2],lt,c1)},{flashAt:c1,flashColor:OR,shakeAt:c1});};

// ---- STATEMENT ----
T.statement=(s,e,p,C)=>{const lines=(p.lines||['Ye app game changer hai']).slice(0,3);const c0=C[0]??.5;
 scene(s,e,`${HEAD('sm_t',lines,p.hl==null?lines.length-1:p.hl,p.emoji,260,120)}<div id="sm_v" class="card" style="left:120px;top:${330+lines.length*fit(lines,120)}px;width:840px;height:472px;overflow:hidden;padding:0;opacity:0;transform:rotate(-2deg)">${RV(1+((s*10|0)%3),2)}</div>`,
 (el,lt)=>{popIn(el.querySelector('#sm_t'),lt,0);rise(el.querySelector('#sm_v'),lt,c0,.4,200)},{flashAt:0,flashColor:OR});};

// ---- CTA ----
T.cta=(s,e,p,C)=>{const D=e-s;const c0=C[0]??D*.35,c1=C[1]??D*.65;
 scene(s,e,`${NAME('ct_n',300)}<div id="ct_f" style="position:absolute;left:250px;top:620px;width:580px;height:140px;border-radius:30px;background:#4f6bff;display:grid;place-items:center;font:800 64px/1 P;color:#fff;box-shadow:0 0 70px rgba(79,107,255,.6);opacity:0">Follow</div>${TAP('ct_tap',640,710)}${pill('ct_l','🔗 LINK IN BIO 👆',840)}`,
 (el,lt)=>{const n=el.querySelector('#ct_n');const q=clamp(lt/.3);n.style.opacity=q;n.style.transform=`scale(${.4+.6*back(q)})`;const f=el.querySelector('#ct_f');const fp=clamp((lt-.3)/.3);f.style.opacity=fp;const tp=lt>c0;f.textContent=tp?'Following ✓':'Follow';f.style.background=tp?BG1:'#4f6bff';f.style.transform=`scale(${(.5+.5*back(fp))*(lt>c0-.1&&lt<c0+.05?.92:1)})`;tapA(el,'#ct_tap',lt,c0-.4,.8);pillA(el.querySelector('#ct_l'),lt,c1)},{flashAt:c1,flashColor:OR});};

// ---- PERMISSION ----
T.permission=(s,e,p,C)=>scene(s,e+.5,`<div id="pe_w" style="position:absolute;left:0;right:0;top:330px;text-align:center;font-size:170px">⚠️</div><div id="pe_c" class="card" style="left:90px;top:620px;width:900px;padding:44px 50px;border-color:${OR};opacity:0"><div style="font:400 70px/1.05 H;font-style:italic;text-transform:uppercase">Sirf unhi streamers ko clip karo</div><div style="font:400 70px/1.05 H;font-style:italic;text-transform:uppercase;color:${OR};margin-top:10px">jo permission dete hain ✅</div><div style="font:800 34px/1.3 P;color:${LT};margin-top:24px">🙏 Hamesha credit do</div></div>`,
 (el,lt)=>{el.querySelector('#pe_w').style.transform=`scale(${(.4+.6*back(clamp(lt/.3)))*(1+.04*Math.sin(lt*8))})`;const c=el.querySelector('#pe_c');const q=clamp((lt-.4)/.35);c.style.opacity=q;c.style.transform=`translateY(${(1-ease(q))*150}px)`},{flashAt:0,flashColor:OR});

PLAN.forEach((b,i)=>{const f=T[b.t]||T.statement;try{f(b.s,b.e,b.p||{},b.c||[],i)}catch(err){console.error(err);T.statement(b.s,b.e,{lines:['GTA 6 Super Clipper']},[],i)}});
