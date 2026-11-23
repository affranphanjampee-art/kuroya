/* Levels 0–50, with five XP-based ranks; XP rewards and saved XP remain unchanged. */
(() => {
  const starts=[0,6,11,16,36],ends=[5,10,15,35,50];
  const thai=['บรอนซ์ II','บรอนซ์ I','ซิลเวอร์ II','ซิลเวอร์ I','โกลด์ II'];
  const english=['Bronze II','Bronze I','Silver II','Silver I','Gold II'];
  const colors=['bronze','bronze','silver','silver','gold'];
  const tier=level=>level<=5?0:level<=10?1:level<=15?2:level<=35?3:4;
  const image=i=>`assets/images/codecraft-rank-0${i+1}.${i<2?'png':'webp'}`;
  G_THRESHOLDS.splice(0,G_THRESHOLDS.length,...Array.from({length:51},(_,n)=>20*n+5*n*(n-1)/2));
  gLevel=function(){const xp=Math.max(0,Number(G.xp)||0);let n=0;while(n<50&&xp>=G_THRESHOLDS[n+1])n++;return n};
  gTitles.splice(0,gTitles.length,...Array.from({length:50},(_,i)=>thai[tier(i+1)]));
  gTitles[-1]=thai[0];
  if(typeof CC_EN!=='undefined')thai.forEach((name,i)=>CC_EN[name]=english[i]);
  const oldMultiplier=gMultiplier;gMultiplier=function(){return gLevel()===0?1:oldMultiplier()};
  gHero=function(){
    const en=ccLang==='en',level=gLevel(),t=tier(level),xp=Math.max(0,Number(G.xp)||0),low=G_THRESHOLDS[level],next=G_THRESHOLDS[level+1];
    const progress=next===undefined?100:Math.max(0,Math.min(100,Math.round((xp-low)/(next-low)*100)));
    return `<div class="g-hero"><div class="cc82-journey"><button type="button" class="cc82-trigger" aria-haspopup="dialog" aria-label="${en?'View all ranks and XP requirements':'ดูยศทั้งหมดและเงื่อนไข XP'}"><span>${en?'View ranks':'ดูเส้นทางยศ'} <b aria-hidden="true">↗</b></span></button><div class="g-small">YOUR CODING JOURNEY</div><h2><img class="cc84-hero-emblem" src="${image(t)}" alt="">Lv. ${level} <span>${en?english[t]:thai[t]}</span></h2><p>${en?'Practice and earn experience as you go.':'ฝึกทีละนิด สะสมประสบการณ์ไปด้วยกัน'}</p><div class="g-bar"><i style="width:${progress}%"></i></div><div class="g-bar-label"><span>${xp.toLocaleString()} XP</span><span>${next===undefined?(en?'MAX LEVEL':'เลเวลสูงสุด'):en?`${next.toLocaleString()} XP for next level`:`${next.toLocaleString()} XP เพื่อเลเวลถัดไป`}</span></div></div><div class="g-balance"><span>${en?'Tokens':'ยอดโทเคน'}</span><b>◉ ${G.tokens}</b><small>${en?'Saved in this browser':'บันทึกในเบราว์เซอร์นี้'}</small></div></div>`;
  };
  document.addEventListener('click',event=>{
    const trigger=event.target.closest('.cc82-trigger');if(!trigger)return;
    const en=ccLang==='en',level=gLevel(),current=tier(level),xp=Math.max(0,Number(G.xp)||0),next=G_THRESHOLDS[level+1];
    const status=next===undefined?(en?'You have reached level 50 MAX.':'คุณถึงเลเวล 50 MAX แล้ว'):(en?`${(next-xp).toLocaleString()} XP to the next level`:`อีก ${(next-xp).toLocaleString()} XP ถึงเลเวลถัดไป`);
    const items=starts.map((start,i)=>{const state=i===current?(en?'Current':'ยศปัจจุบัน'):i<current?(en?'Passed':'ผ่านแล้ว'):(en?'Upcoming':'ยังไม่ถึง');return `<li class="cc82-rank tier-${colors[i]} ${i===current?'is-current':i<current?'is-unlocked':'is-locked'}" ${i===current?'aria-current="step"':''}><img class="cc84-emblem" src="${image(i)}" alt=""><div class="cc82-rank-main"><span class="cc82-level">LEVEL ${start}–${ends[i]}${i===4?' MAX':''}</span><strong>${en?english[i]:thai[i]}</strong><small>${G_THRESHOLDS[start].toLocaleString()} XP ${en?'total':'สะสม'}</small></div><span class="cc82-state">${state}</span></li>`}).join('');
    const dialog=document.createElement('dialog');dialog.className='cc82-dialog';dialog.setAttribute('aria-labelledby','cc82-heading');
    dialog.innerHTML=`<div class="cc82-shell"><header class="cc82-head"><div><span class="cc82-overline">YOUR CODING JOURNEY</span><h2 id="cc82-heading">${en?'Rank journey':'เส้นทางยศ'}</h2><p>${en?'Advance through ranks as you earn XP.':'สะสม XP เพื่อเลื่อนยศตามเลเวลโดยอัตโนมัติ'}</p></div><button type="button" class="cc82-close" aria-label="${en?'Close':'ปิด'}">×</button></header><div class="cc82-summary"><img class="cc84-summary-emblem" src="${image(current)}" alt=""><div><span>${en?'YOUR RANK':'ยศของคุณ'}</span><strong>Lv. ${level} · ${en?english[current]:thai[current]}</strong></div><div class="cc82-summary-xp"><b>${xp.toLocaleString()} XP</b><small>${status}</small></div></div><div class="cc82-caption"><span>${en?'ALL RANKS':'ยศทั้งหมด'}</span><span>${current+1} / 5</span></div><ol class="cc82-list">${items}</ol><p class="cc82-note">${en?'Ranks depend on XP, not achievements. XP is stored in this browser; use Account to back up or restore progress.':'ยศคำนวณจาก XP แยกจากความสำเร็จ · XP บันทึกในเบราว์เซอร์นี้ สำรองหรือกู้คืนได้ที่เมนูบัญชี'}</p></div>`;
    document.body.append(dialog);dialog.querySelector('.cc82-close').addEventListener('click',()=>dialog.close());
    dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close()}});
    dialog.addEventListener('close',()=>{dialog.remove();if(trigger.isConnected)trigger.focus()},{once:true});dialog.showModal();
  });
})();
