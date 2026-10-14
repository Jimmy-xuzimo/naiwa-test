#!/usr/bin/env python3
"""从 campus.html 派生 jump.html（3D 跳转页）。

为什么是生成而不是手抄：跳转页要复用整个 3D 场景（1395 行、几十个程序化贴图函数），
复制一份迟早会跟 campus.html 漂移。这里做**定向注入**——每一处替换都断言必须命中，
命中不了就报错退出，不会静默产出一个半成品。

跑：/usr/local/bin/python3 tools/build_jump.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "campus.html")
DST = os.path.join(ROOT, "jump.html")

s = open(SRC, encoding="utf-8").read()
edits = []


def sub(old, new, label):
    global s
    if old not in s:
        print("✗ 锚点没命中：「%s」" % label)
        print("  期望片段：%r" % old[:120])
        sys.exit(1)
    if s.count(old) != 1:
        print("✗ 锚点不唯一（%d 处）：「%s」" % (s.count(old), label))
        sys.exit(1)
    s = s.replace(old, new)
    edits.append(label)


# ── 1. head ─────────────────────────────────────────────
sub('<title>中国奶娃大学 · 校门报到日</title>',
    '<title>正在前往 · 南京传媒学院</title>', "标题")

sub('<meta name="description" content="全程序化建模与光照的 3D 校门报到日场景，可自由漫游。">',
    '<meta name="description" content="中国奶娃大学 → 南京传媒学院，3D 校门报到日跳转。">\n'
    '<meta name="robots" content="noindex">', "描述")

sub('<link rel="icon" href="favicon.ico" sizes="any">',
    '<link rel="icon" href="favicon.ico" sizes="any">\n'
    '<noscript><meta http-equiv="refresh" content="6;url=https://www.cucn.edu.cn/"></noscript>',
    "noscript 兜底")

# ── 2. 跳转页自己的样式 ──────────────────────────────────
JUMP_CSS = """  /* ── 跳转页专用 ── */
  .bar{justify-content:space-between}
  .bar .to{font-size:12px;letter-spacing:.14em;color:rgba(255,255,255,.9);
    text-shadow:0 1px 3px rgba(0,0,0,.95),0 0 14px rgba(0,0,0,.8)}
  .bar .to i{font-style:normal;color:var(--gold)}
  .bar .ab{pointer-events:auto;font:inherit;font-size:12px;letter-spacing:.1em;
    color:#EAF1FA;cursor:pointer;border:1px solid rgba(255,255,255,.32);border-radius:99px;
    padding:6px 13px;background:rgba(10,22,38,.62);transition:background .2s,border-color .2s}
  .bar .ab:hover{background:rgba(27,75,141,.6);border-color:rgba(255,255,255,.6)}
  .jp{position:fixed;left:0;right:0;bottom:0;z-index:6;padding:0 16px 16px;
    display:flex;flex-direction:column;align-items:center;gap:9px;pointer-events:none;
    background:linear-gradient(to top,rgba(6,14,26,.8),rgba(6,14,26,.3) 55%,transparent)}
  .ring{width:42px;height:42px;transform:rotate(-90deg)}
  .ring circle{fill:none;stroke-width:3;stroke-linecap:round}
  .ring .bg{stroke:rgba(255,255,255,.16)}
  .ring .fg{stroke:var(--gold);transition:stroke-dashoffset .18s linear}
  .jp .who{font-size:12.5px;letter-spacing:.2em;color:rgba(255,255,255,.72);
    text-shadow:0 1px 6px rgba(0,0,0,.7)}
  .jp .who b{color:#fff;font-weight:600;letter-spacing:.06em}
  .jp .hint{font-size:11.5px;letter-spacing:.14em;color:rgba(255,255,255,.5)}
  .go{pointer-events:auto;font:inherit;font-size:13px;letter-spacing:.12em;color:#fff;
    cursor:pointer;padding:11px 30px;border-radius:99px;border:1px solid rgba(255,255,255,.34);
    background:rgba(10,22,38,.72);transition:background .2s,transform .12s}
  .go:hover{background:var(--blue);border-color:transparent}
  .go:active{transform:translateY(1px) scale(.98)}
  #sub{position:fixed;left:0;right:0;top:5.5%;z-index:6;text-align:center;pointer-events:none;
    opacity:0;transition:opacity .9s ease}
  #sub.on{opacity:1}
  #sub b{display:block;font-size:clamp(22px,5.4vw,40px);font-weight:650;letter-spacing:.06em;
    text-shadow:0 2px 24px rgba(0,0,0,.85)}
  #sub span{display:block;margin-top:12px;font-size:13px;letter-spacing:.34em;
    color:rgba(255,255,255,.76);text-shadow:0 1px 10px rgba(0,0,0,.85)}
  .hold{position:fixed;left:0;right:0;top:46%;z-index:7;text-align:center;pointer-events:none;
    opacity:0;transition:opacity .25s}
  .hold.on{opacity:1}
  .hold span{font-size:12px;letter-spacing:.3em;color:#fff;
    background:rgba(8,16,28,.72);padding:8px 18px;border-radius:99px}
</style>"""
sub("</style>", JUMP_CSS, "跳转页样式")

# ── 3. body：换掉顶部条与 HUD ────────────────────────────
sub('<div class="bar"><b>中国奶娃大学 · 报到日</b>'
    '<a href="jump.html" title="3D 校门场景，演完跳南传">3D 跳转版 ↗</a>'
    '<a href="film.html" title="离线路径追踪渲染的成片">看离线渲染版 ↗</a>'
    '<a href="index.html">← 返回护送页</a></div>',
    '<div class="bar"><b>中国奶娃大学</b>'
    '<button class="ab" id="about-btn" type="button">关于</button></div>', "顶栏")

sub("""<div class="hud">
  <div class="row">
    <button id="reset" type="button">回到正门</button>
    <button id="qual" type="button">画质</button>
    <button id="about-btn" type="button">关于</button>
    <button id="go" class="primary" type="button">前往南传官网</button>
  </div>
  <p class="tip" id="tip">拖动旋转 · 滚轮或双指缩放</p>
</div>""",
    """<div class="jp">
  <svg class="ring" viewBox="0 0 52 52" aria-hidden="true">
    <circle class="bg" cx="26" cy="26" r="23"></circle>
    <circle class="fg" id="ring" cx="26" cy="26" r="23"
            stroke-dasharray="144.5" stroke-dashoffset="144.5"></circle>
  </svg>
  <p class="who">正在前往 <b>南京传媒学院</b></p>
  <button class="go" id="go" type="button">立即前往</button>
  <p class="hint" id="tip">轻点画面直接前往 · 长按暂停</p>
</div>
<div id="sub"><b>南京传媒学院</b><span>新生报到</span></div>
<div class="hold" id="hold"><span>已暂停</span></div>""", "HUD")

sub('<div id="load"><div><div class="sp"></div><p>正在打光与烘焙材质</p></div></div>',
    '<div id="load"><div><div class="sp"></div><p>正在搭建校门场景</p></div></div>', "载入文案")

sub('<p>本站与南京传媒学院无任何官方关联，「中国奶娃大学」是虚构校名，仅作趣味用途。</p>',
    '<p>本站与南京传媒学院无任何官方关联，「中国奶娃大学」是虚构校名，仅作趣味用途。'
    '本页看完即跳转至 www.cucn.edu.cn。</p>', "免责声明")

# ── 4. 顶部加 JUMP 标志（必须早于所有引用）────────────────
sub("var Q=location.search;",
    "var Q=location.search;\nvar JUMP=/[?&]jump/.test(Q);", "JUMP 标志")

# ── 5. WebGL 起不来 → 退回 2D 版（他选的兜底）────────────
sub("""if(!window.THREE||!probe){
  load.innerHTML='<div><p style="letter-spacing:.05em">这台设备没开 WebGL，3D 场景起不来。<br>'+
    '<a href="index.html" style="color:#C9A227">← 回到护送页（2D 版）</a></p></div>';
  return;
}""",
    """if(!window.THREE||!probe){
  /* 兜底：3D 起不来就退回 2D 跳转动画（index.html 自己会在 5.9 秒后跳南传） */
  load.innerHTML='<div><p style="letter-spacing:.05em">这台设备跑不动 3D，'+
    '正在退回 2D 版…</p></div>';
  setTimeout(function(){location.replace("index.html");},1200);
  return;
}""", "WebGL 兜底")

# ── 6. 场景侧：捕获脚下 AO、关掉自由漫游推镜、交出控制权 ──
sub("scene.add(ao(3.6,.34,2.05,.05,-4.3));",
    "var heroAO=ao(3.6,.34,2.05,.05,-4.3);scene.add(heroAO);", "捕获脚下 AO")

sub("var intro={t:0,dur:reduce?0:3.4,on:!reduce};",
    "var intro={t:0,dur:reduce?0:3.4,on:!reduce&&!JUMP};", "关掉自由漫游推镜")

sub("  var amp=intro.on?0:1;", "  var amp=JUMP?0:(intro.on?0:1);", "接管手臂空闲动画")

sub("  applyCam(el);",
    "  if(JUMP)jumpTick(dt);\n  applyCam(el);\n  if(JUMP)jumpCam();   /* 跳转模式直接摆相机，压掉上面的轨道控制器 */",
    "相机上轨道")

sub("  hero.userData.eyes.forEach(function(x){x.scale.y=blink;});",
    "  hero.userData.eyes.forEach(function(x){x.scale.y=blink;});\n  if(JUMP)jumpHero();",
    "角色上轨道")

# ── 7. UI 段：跳转页没有画质/回正按钮，原绑定会 Null 崩 ────
sub("""var hi=hiEnd,usePost=!!composer,qualBtn=document.getElementById("qual");
function paintQual(){qualBtn.textContent="画质："+(hi?(usePost?"后期":"高"):"低");}
paintQual();
qualBtn.addEventListener("click",function(){
  hi=!hi;
  /* 关后期不能只把 pass 全 disable（那样没东西渲染到屏幕），要退回直出 */
  usePost=hi&&!!composer;
  if(composer)composer.passes.forEach(function(p){p.enabled=hi;});
  renderer.shadowMap.enabled=hi;sun.castShadow=hi;
  scene.traverse(function(o){if(o.isMesh)o.material.needsUpdate=true;});
  paintQual();
});
if(!hi){renderer.shadowMap.enabled=false;sun.castShadow=hi;}
document.getElementById("reset").addEventListener("click",function(){
  orb.tTheta=HOME.theta;orb.tPhi=HOME.phi;orb.tR=HOME.r;orb.vTheta=0;});
document.getElementById("go").addEventListener("click",function(){location.href="https://www.cucn.edu.cn/";});
var dlg=document.getElementById("about");
document.getElementById("about-btn").addEventListener("click",function(){dlg.showModal();});
document.getElementById("close").addEventListener("click",function(){dlg.close();});
dlg.addEventListener("click",function(e){if(e.target===dlg)dlg.close();});""",
    """/* 跳转页没有「画质 / 回到正门」两个按钮，也不该让别人抢走 #go，
   所以这一段整体换掉（原绑定里 getElementById 会拿到 null 直接抛）。
   注意 usePost 要留着：主循环里 `if(usePost)composer.render()` 在用它，
   整段删掉会变成 ReferenceError，把渲染循环当场打死（表现为"永远不跳转"）。 */
var hi=hiEnd,usePost=!!composer;
if(!hi){renderer.shadowMap.enabled=false;sun.castShadow=hi;}
var dlg=document.getElementById("about");
document.getElementById("about-btn").addEventListener("click",function(){
  jt.paused=true;dlg.showModal();});
document.getElementById("close").addEventListener("click",function(){dlg.close();});
dlg.addEventListener("click",function(e){if(e.target===dlg)dlg.close();});""",
    "UI 段换成跳转版")

# ── 8. 注入跳转模块 ─────────────────────────────────────
JUMP_JS = r"""
/* ══ 99. 跳转模式 ═══════════════════════════════════════
   上轨道的入场：推镜 → 奶娃从画外走入 → 招手 → 鞠躬 → 跳南传。
   时间轴是 t 的纯函数（没有积分状态），所以 ?jump&frame=3.2 能定点截图验收。 */
var TARGET="https://www.cucn.edu.cn/";
var jt={t:0,paused:false,fired:false};
/* 相机：一段纯推轨，起终点视线只差约 4°，几乎没有摇镜头，像小摇臂下压。
   P0/L0 直接抄自由漫游已验证过的 HOME 构图当远景。
   为什么要明确摆 camera.position 而不走 orb：轨道控制器的阻尼会把精确机位吃掉。 */
var P0=new T.Vector3(8.0,5.25,10.6), L0=new T.Vector3(0.0,3.7,-12.0);
/* 终点机位压到接近平视（俯角 2.9°）。上一版俯角 9.5°、机位偏到 x=4，
   结果校门整个被报到处帐篷挡掉、背景只剩展板和楼。
   现在站在门洞轴线上、奶娃摆在门洞正前方 z=0.6，
   这样它背后就是校门中柱 —— 匾额(≈15.1°)和红横幅(≈12.1°)刚好卡在画幅上沿内。 */
var P1=new T.Vector3(0.0,2.05,10.4), L1=new T.Vector3(0.0,1.52,0.20);
var _jp=new T.Vector3(), _jl=new T.Vector3();
/* 角色站位：**z>0 的广场上没人**（人群游走范围是 z∈[-22,-2]，报到队列全部 z<=0.2）。
   早期版本把奶娃摆在 (2.05,-5.4) —— 那是报到队伍正中间，
   终点机位等于一头扎进人群，奶娃被裁掉一半、画面全是别人的后脑勺。 */
var H0={x:-5.6,z:0.90,ry:1.57};        /* 画外左起点，面朝 +x 走 */
var H1={x: 0.0,z:0.60,ry:.06};         /* 站位：门洞正前方，几乎正对机位 */
var HY=hero.position.y;
var DUR=reduce?2.6:7.0;

function sstep(t,a,b){return Math.max(0,Math.min(1,(t-a)/(b-a)));}
function sease(p){return 1-Math.pow(1-p,3);}

function jumpCam(){
  var p=reduce?1:sease(sstep(jt.t,0,2.2));
  _jp.lerpVectors(P0,P1,p);_jl.lerpVectors(L0,L1,p);
  camera.position.copy(_jp);camera.lookAt(_jl);
}
function jumpHero(){
  var aR=hero.userData.armR,aL=hero.userData.armL;
  if(reduce){                            /* 减弱动态：直接落在终态，不动 */
    hero.position.x=H1.x;hero.position.z=H1.z;hero.rotation.y=H1.ry;
    hero.rotation.x=0;aR.rotation.set(0,0,0);aL.rotation.set(0,0,0);
    if(heroAO){heroAO.position.x=H1.x;heroAO.position.z=H1.z;}
    return;
  }
  var w=sstep(jt.t,1.8,4.0),we=sease(w);
  hero.position.x=H0.x+(H1.x-H0.x)*we;
  hero.position.z=H0.z+(H1.z-H0.z)*we;
  hero.rotation.y=H0.ry+(H1.ry-H0.ry)*we;
  var walking=(w>0&&w<1);
  hero.position.y=HY+(walking?Math.abs(Math.sin(jt.t*7.6))*.07:0);
  if(heroAO){heroAO.position.x=hero.position.x;heroAO.position.z=hero.position.z;}

  var sw=walking?Math.sin(jt.t*7.6):0;
  aR.rotation.x=sw*.62;aL.rotation.x=-sw*.62;
  aR.rotation.z=walking?-.12:0;aL.rotation.z=walking?.10:0;

  var wv=sstep(jt.t,4.0,5.7);                 /* 招手 */
  if(wv>0&&jt.t<6.0){
    var k=sstep(jt.t,4.1,4.7);
    aR.rotation.z=-1.05*k-Math.sin(jt.t*11.5)*.30*k;
    aR.rotation.x=Math.sin(jt.t*11.5)*.22*k;
    aL.rotation.z=.24*k;
  }
  var bw=sstep(jt.t,5.8,6.15);                /* 鞠躬 → 起 */
  var bu=sstep(jt.t,6.15,6.55);
  hero.rotation.x=(bw-bu)*.34;
  if(jt.t>5.75){var sb=document.getElementById("sub");if(sb)sb.classList.add("on");}
}

function jumpFire(){
  if(jt.fired)return;jt.fired=true;
  location.replace(TARGET);
  setTimeout(function(){location.href=TARGET;},900);   /* replace 被拦时的二道保险 */
}

/* 看门狗：11 秒内没出第一帧（着色器编译失败 / 显存不够 / 崩了）就回退 2D 版 */
var FIRST=false;
setTimeout(function(){ if(!FIRST)location.replace("index.html"); },
           reduce?7000:11000);

function jumpUI(){
  var r=document.getElementById("ring");
  if(r)r.setAttribute("stroke-dashoffset",String(144.5*(1-Math.max(0,Math.min(1,jt.t/DUR)))));
  if(jt.t>=DUR&&!FREEZE)jumpFire();
}

/* 交互：轻点立即前往，长按暂停 */
var FREEZE=(function(){var m=/[?&]frame=([-0-9.]+)/.exec(Q);return m?parseFloat(m[1]):null;})();
if(JUMP){
  canvas.style.cursor="pointer";
  document.getElementById("go").addEventListener("click",function(e){
    e.stopPropagation();jumpFire();});
  var jpd=0,jhold=false,jmoved=0,jx=0,jy=0;
  canvas.addEventListener("pointerdown",function(e){
    jpd=performance.now();jhold=false;jmoved=0;jx=e.clientX;jy=e.clientY;});
  canvas.addEventListener("pointermove",function(e){
    if(!jpd)return;
    jmoved=Math.max(jmoved,Math.abs(e.clientX-jx)+Math.abs(e.clientY-jy));
    if(performance.now()-jpd>400&&jmoved<14){
      jhold=true;jt.paused=true;
      var h=document.getElementById("hold");if(h)h.classList.add("on");
    }});
  var jup=function(){
    if(!jpd)return;
    var held=performance.now()-jpd,wasHold=jhold;jpd=0;
    if(wasHold){jt.paused=false;
      var h=document.getElementById("hold");if(h)h.classList.remove("on");}
    else if(held<400&&jmoved<14)jumpFire();      /* 轻点 = 立即前往 */
  };
  ["pointerup","pointercancel","pointerleave"].forEach(function(ev){
    canvas.addEventListener(ev,jup);});
  document.addEventListener("visibilitychange",function(){
    if(document.hidden)jt.paused=true; else if(!jpd)jt.paused=false;});
}

/* 他本机 macOS 开着「减弱动态效果」，不加这行提示的话打开只会看到一张静止图 */
if(reduce){
  var _tp=document.getElementById("tip");
  if(_tp)_tp.textContent="系统开着「减弱动态效果」，这里直接跳到终帧 · 加 ?motion=full 看完整动画";
}

function jumpTick(dt){
  if(FREEZE!==null){jt.t=FREEZE;jumpCam();jumpUI();return;}
  if(!jt.paused)jt.t+=dt;
  jumpCam();jumpUI();
}
"""

sub("applyCam();updateCrowd(0,0);renderer.render(scene,camera);",
    JUMP_JS + "\napplyCam();if(JUMP)jumpTick(0);updateCrowd(0,0);renderer.render(scene,camera);",
    "注入跳转模块")

# 首帧标记：必须放在 frame() 体内最后一行。
# 放到 frame() 外面的话，渲染循环第一帧就抛错它照样是 true，看门狗形同虚设。
sub("  requestAnimationFrame(frame);",
    "  FIRST=true;\n  requestAnimationFrame(frame);", "首帧标记")

open(DST, "w", encoding="utf-8").write(s)
print("✓ 生成 %s（%d 处注入）" % (os.path.relpath(DST, ROOT), len(edits)))
for i, e in enumerate(edits, 1):
    print("   %2d. %s" % (i, e))
