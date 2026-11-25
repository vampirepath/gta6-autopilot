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

# ---------------- MUSIC: bright lo-fi house, 120 bpm, 4-on-the-floor ----------------
BPM=CFG['bpm']; B=60/BPM; S16=B/4
mus=np.zeros(N); keys=np.zeros(N); bass=np.zeros(N); kick_env=np.ones(N)
def kick():
    t=tt(.35); f=50+90*np.exp(-t*30); ph=2*np.pi*np.cumsum(f)/SR
    return np.tanh(1.8*np.sin(ph)*np.exp(-t*9))*.85
def clap():
    t=tt(.25); n=rng.standard_normal(len(t)); e=np.zeros(len(t))
    for d in (0,.009,.018): e+=np.exp(-np.clip(t-d,0,None)*70)*(t>=d)
    return bp(n,1000,6000)*e*.45
def hat(o=False):
    t=tt(.18 if o else .04); return hpf(rng.standard_normal(len(t)),8000)*np.exp(-t*(22 if o else 120))*(.2 if o else .14)
def shaker():
    t=tt(.06); return bp(rng.standard_normal(len(t)),5000,11000)*np.sin(np.pi*t/.06)*.08
def rhodes(ms,d):
    t=tt(d); s=np.zeros(len(t))
    for m in ms:
        f=mid(m); s+=np.sin(2*np.pi*f*t+.6*np.sin(2*np.pi*f*t)*np.exp(-t*3))+.25*np.sin(2*np.pi*2*f*t)*np.exp(-t*4)
    trem=1+.18*np.sin(2*np.pi*4.5*t)
    return s/len(ms)*np.exp(-t*1.1)*np.minimum(1,t/.008)*trem*.42
def bassn(m,d):
    t=tt(d); f=mid(m); s=np.sin(2*np.pi*f*t)+.3*np.sin(2*np.pi*2*f*t)
    return lpf(s,600)*np.exp(-t*2.2)*np.minimum(1,t/.004)*.55
prog=[tuple(x) for x in CFG['prog']]
start=0.0; t=start; step=0
DROP=CFG['drop']; BREAK=(CFG['drop']-.6,CFG['drop']); END=CFG['end']
while t<END:
    s=step%16; bar=step//16; ch=prog[bar%4]
    brk=BREAK[0]<=t<BREAK[1]; intro=t<DROP
    if not brk:
        if s%4==0:
            place(mus,kick(),t,.55 if intro else 1.0); i=int(t*SR); L=int(.18*SR); kick_env[i:i+L]=np.minimum(kick_env[i:i+L],.45+.55*np.linspace(0,1,min(L,N-i)))
        if not intro:
            if s in (4,12): place(mus,clap(),t)
            if s%4==2: place(mus,hat(True),t)
            if s%2==1: place(mus,shaker(),t)
            if s in (0,3,6,10,14): place(bass,bassn(ch[0]+(12 if s==14 else 0),B*.9),t)
        if s in (0,6,10): place(keys,rhodes(ch[1],B*(1.4 if s==0 else .9)),t,1.0 if s==0 else .7)
    t+=S16; step+=1
rt=tt(BREAK[1]-BREAK[0]); riser=hpf(rng.standard_normal(len(rt)),900)*(rt/rt[-1])**2*.4
place(mus,riser,BREAK[0])
keys=lpf(keys,2600)*kick_env; bass=bass*kick_env
music=mus+keys*1.0+bass*.9
music[:int(.2*SR)]*=np.linspace(0,1,int(.2*SR))
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
def swish():
    t=tt(.35); return bp(rng.standard_normal(len(t)),1500,7000)*np.sin(np.pi*t/.35)**2*.5
def scribble(d=.4):
    t=tt(d); return bp(rng.standard_normal(len(t)),2500,6000)*(.5+.5*np.sign(np.sin(2*np.pi*14*t)))*np.minimum(1,(d-t)/.05)*.35
def type1(): t=tt(.03); return bp(rng.standard_normal(len(t)),1500,5000)*np.exp(-t*160)*.6
ARGS={'whoosh':lambda x:swish(),'impact':lambda x:impact(),'pop':lambda x:pop(x or 1000),'tick':lambda x:tick(),'click':lambda x:click(),
 'shutter':lambda x:shutter(),'ding':lambda x:ding(x or 1568),'riser':lambda x:riser(x or 1.0),'glitch':lambda x:glitch(),'cash':lambda x:cash(),'scribble':lambda x:scribble(x or .4),'type':lambda x:type1()}
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
