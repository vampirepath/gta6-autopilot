import json, sys, numpy as np, soundfile as sf
CFG=json.load(open(sys.argv[1]))
VO,MO,SO=sys.argv[2:5]
from scipy.signal import butter, sosfilt, sosfiltfilt
SR=48000; D=CFG['D']; N=int(SR*D)
rng=np.random.default_rng(CFG['seed'])
def bp(x,lo,hi,o=2): return sosfilt(butter(o,[lo,hi],'bandpass',fs=SR,output='sos'),x)
def lpf(x,f,o=2): return sosfilt(butter(o,f,'lowpass',fs=SR,output='sos'),x)
def hpf(x,f,o=2): return sosfilt(butter(o,f,'highpass',fs=SR,output='sos'),x)
def place(buf,sig,t,g=1.0):
    i=int(t*SR)
    if i>=len(buf) or i+len(sig)<0: return
    a=max(0,i); b=min(len(buf),i+len(sig)); buf[a:b]+=sig[a-i:b-i]*g
mid=lambda m:440*2**((m-69)/12)
tt=lambda d:np.arange(int(SR*d))/SR

# ---------------- MUSIC: dark trap, 140 bpm half-time ----------------
BPM=CFG['bpm']; B=60/BPM; S16=B/4
mus_drums=np.zeros(N); mus_808=np.zeros(N); mus_pad=np.zeros(N); mus_arp=np.zeros(N)
def kick():
    t=tt(.45); f=45+120*np.exp(-t*28); ph=2*np.pi*np.cumsum(f)/SR
    return np.tanh(2.2*np.sin(ph)*np.exp(-t*7))*.9
def clap():
    t=tt(.3); n=rng.standard_normal(len(t)); e=np.zeros(len(t))
    for d in (0,.011,.022): e+=np.exp(-np.clip(t-d,0,None)*60)*(t>=d)
    e+=np.exp(-t*14)*.6
    return bp(n,900,5000)*e*.55
def hat(open_=False):
    t=tt(.25 if open_ else .05); return hpf(rng.standard_normal(len(t)),7000)*np.exp(-t*(18 if open_ else 110))*.22
def b808(m,d):
    t=tt(d); f=mid(m)*(1+.6*np.exp(-t*40)); ph=2*np.pi*np.cumsum(f)/SR
    return np.tanh(1.8*np.sin(ph))*np.exp(-t*1.2)*np.minimum(1,t/.005)*.75
def pad(ms,d):
    t=tt(d); s=np.zeros(len(t))
    for m in ms:
        for det in (-.12,0,.12):
            f=mid(m)*2**(det/12); s+=2*((t*f)%1)-1
    s=lpf(s/ (len(ms)*3),1400)
    env=np.minimum(1,t/.6)*np.minimum(1,(d-t)/.6)
    return s*env*.32
def pluck(m,d=.22):
    t=tt(d); s=np.sign(np.sin(2*np.pi*mid(m)*t))*.5+np.sin(2*np.pi*mid(m)*2*t)*.3
    return lpf(s,3500)*np.exp(-t*14)*.22
# Am - F - Dm - E  (2 bars each = 8 beats)
prog=[tuple(x) for x in CFG['prog']]
start=0.0; t=start; step=0
DROP=CFG['drop']      # big drop on "So I built"
BREAK=(CFG['drop']-.6,CFG['drop'])
END=CFG['end']
while t<END:
    beat=step//4; s=step%16; bar=step//16; chord=prog[(bar//2)%4]
    in_break=BREAK[0]<=t<BREAK[1]
    intro=t<0.0
    if not in_break:
        # kick pattern (half-time trap)
        if s in (0,10) or (s==7 and bar%2==1): place(mus_drums,kick(),t,1.0 if not intro else .6)
        if s in (8,) and not intro: place(mus_drums,clap(),t)
        # hats: 8ths with 1/32 rolls every other bar end
        if not intro:
            if s%2==0: place(mus_drums,hat(),t,.9 if s%4==0 else .6)
            if bar%2==1 and s>=12:
                for r in range(2): place(mus_drums,hat(),t+r*S16/2,.45)
            if s==14 and bar%4==3: place(mus_drums,hat(True),t,.7)
        # 808
        if s==0: place(mus_808,b808(chord[0],B*2.6),t)
        if s==10 and bar%2==0: place(mus_808,b808(chord[0]+12 if bar%4==2 else chord[0],B*1.2),t,.8)
        # arp after drop
        if t>=DROP and s%2==0:
            notes=chord[1]+[chord[1][0]+12]; place(mus_arp,pluck(notes[(s//2)%4]+12),t)
    if s==0 and bar%2==0:
        place(mus_pad,pad(chord[1],B*8),t)
    t+=S16; step+=1
# riser into drop + drop impact
rt=tt(BREAK[1]-BREAK[0]); riser=hpf(rng.standard_normal(len(rt)),800)*(rt/rt[-1])**2*.5
riser+=np.sin(2*np.pi*np.cumsum(200+1800*(rt/rt[-1])**2)/SR)*(rt/rt[-1])**2*.18
place(mus_drums,riser,BREAK[0])
music=mus_drums*1.0+mus_808*.9+mus_pad*1.0+mus_arp*.9
# intro filter: lowpassed until 1.35 then open
cut=int(0.01*SR); music[:cut]=lpf(music[:cut],900)
music[:int(.15*SR)]*=np.linspace(0,1,int(.15*SR))
fo=int(2.0*SR); music[int(END*SR)-fo:int(END*SR)]*=np.linspace(1,0,fo); music[int(END*SR):]=0

# ---------------- SFX ----------------
sfx=np.zeros(N)
def whoosh(d=.42,up=True):
    t=tt(d); x=rng.standard_normal(len(t)); y=np.zeros(len(t))
    # sweep via chunked bandpass
    nch=12; L=len(t)//nch
    for k in range(nch):
        f=300*(12**(k/nch)) if up else 3600/(12**(k/nch))
        seg=bp(x[k*L:(k+1)*L+200],f,min(f*3,20000))[:L]; y[k*L:k*L+len(seg)]=seg
    return y*np.sin(np.pi*t/d)**1.4*.9
def impact():
    t=tt(1.2); f=40+110*np.exp(-t*20); ph=2*np.pi*np.cumsum(f)/SR
    body=np.tanh(2*np.sin(ph)*np.exp(-t*3.5)); nz=lpf(rng.standard_normal(len(t)),2500)*np.exp(-t*9)*.7
    return (body+nz)*.85
def pop(f=700):
    t=tt(.14); return np.sin(2*np.pi*np.cumsum(f*(1+1.5*np.exp(-t*60)))/SR)*np.exp(-t*35)*.5
def tick(): t=tt(.025); return np.sin(2*np.pi*2600*t)*np.exp(-t*220)*.35
def click(): t=tt(.03); return hpf(rng.standard_normal(len(t)),2500)*np.exp(-t*180)*.5
def shutter():
    a=click()*1.4; b=np.zeros(int(SR*.09)); return np.concatenate([a,b,click()*1.1])
def ding(f=1320):
    t=tt(1.0); return (np.sin(2*np.pi*f*t)+.5*np.sin(2*np.pi*f*2.01*t))*np.exp(-t*5)*.35
def riser(d):
    t=tt(d); p=(t/d)**2; return (hpf(rng.standard_normal(len(t)),1200)*.35+np.sin(2*np.pi*np.cumsum(300+2200*p)/SR)*.15)*p
def glitch():
    t=tt(.25); s=np.sign(np.sin(2*np.pi*90*t))*(rng.random(len(t))>.3); return lpf(s,4000)*np.exp(-t*8)*.35
def cash():
    return np.concatenate([ding(2093)[:int(SR*.12)],ding(2637)])*.8
ARGS={'whoosh':lambda x:whoosh(x or .42),'impact':lambda x:impact(),'pop':lambda x:pop(x or 1000),'tick':lambda x:tick(),'click':lambda x:click(),
 'shutter':lambda x:shutter(),'ding':lambda x:ding(x or 1568),'riser':lambda x:riser(x or 1.0),'glitch':lambda x:glitch(),'cash':lambda x:cash()}
for name,at,g,x in CFG['sfx']:
    if 0<=at<D: place(sfx,ARGS[name](x),at,g)

# ---------------- duck music under VO ----------------
import librosa
vo,_=librosa.load(VO,sr=SR,mono=True); vo=np.pad(vo,(0,max(0,N-len(vo))))[:N]
win=int(.05*SR); env=np.sqrt(np.convolve(vo**2,np.ones(win)/win,'same')); env/=env.max()+1e-9
duck=1-0.45*np.clip(env*3,0,1); duck=lpf(duck,6)
music_d=music*duck
music_d/=np.abs(music_d).max()+1e-9; sfx/=np.abs(sfx).max()+1e-9
sf.write(MO,music_d,SR); sf.write(SO,sfx,SR)
print('ok', N/SR)
