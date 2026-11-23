/* CODECRAFT rank journey: existing level data remains the single source of truth. */
(() => {
  G_THRESHOLDS.push(1400,1800,2250,2750,3300);
  gTitles.splice(0,gTitles.length,'บรอนซ์ II','บรอนซ์ I','ซิลเวอร์ II','ซิลเวอร์ I','โกลด์ II','โกลด์ I','แพลทินัม II','แพลทินัม I','ไดมอนด์ II','ไดมอนด์ I','มาสเตอร์','แกรนด์มาสเตอร์');
  const english=['Bronze II','Bronze I','Silver II','Silver I','Gold II','Gold I','Platinum II','Platinum I','Diamond II','Diamond I','Master','Grandmaster'];
  const tiers=['bronze','bronze','silver','silver','gold','gold','platinum','platinum','diamond','diamond','master','grandmaster'];
  if(typeof CC_EN!=='undefined') gTitles.forEach((name,i)=>CC_EN[name]=english[i]);
  const rankImage=level=>`assets/images/codecraft-rank-0${level}.${level<=2?'png':'webp'}`;
  const originalHero=gHero;
  gHero=function(){
    const en=ccLang==='en';
    return originalHero().replace(/<h2>Lv\. ([1-5]) /,(_,lv)=>`<h2><img class="cc84-hero-emblem" src="${rankImage(Number(lv))}" alt="">Lv. ${lv} `).replace('<div class="g-hero"><div>',`<div class="g-hero"><div class="cc82-journey"><button type="button" class="cc82-trigger" aria-haspopup="dialog" aria-label="${en?'View all ranks and XP requirements':'ดูยศทั้งหมดและเงื่อนไข XP'}"><span>${en?'View ranks':'ดูเส้นทางยศ'} <b aria-hidden="true">↗</b></span></button>`);
  };
  document.addEventListener('click',event=>{
    const trigger=event.target.closest('.cc82-trigger');
    if(!trigger)return;
    const en=ccLang==='en',level=gLevel(),xp=Math.max(0,Number(G.xp)||0),next=G_THRESHOLDS[level],name=i=>en?english[i]:gTitles[i];
    let dialog=document.createElement('dialog');dialog.className='cc82-dialog';dialog.setAttribute('aria-labelledby','cc82-heading');
    const status=next===undefined?(en?'You have reached the highest rank.':'คุณถึงยศสูงสุดแล้ว'):(en?`${(next-xp).toLocaleString()} XP to the next rank`:`อีก ${(next-xp).toLocaleString()} XP ถึงยศถัดไป`);
    const items=G_THRESHOLDS.map((threshold,i)=>{
      const current=i===level-1,unlocked=i<level-1;
      const state=current?(en?'Current':'ยศปัจจุบัน'):unlocked?(en?'Passed':'ผ่านแล้ว'):(en?'Upcoming':'ยังไม่ถึง');
      return `<li class="cc82-rank tier-${tiers[i]} ${current?'is-current':unlocked?'is-unlocked':'is-locked'}" ${current?'aria-current="step"':''}>${i<5?`<img class="cc84-emblem" src="${rankImage(i+1)}" alt="">`:`<div class="cc82-icon" aria-hidden="true">${['◆','◆','◆','◆','✦','✦','✧','✧','◇','◇','✺','✹'][i]}</div>`}<div class="cc82-rank-main"><span class="cc82-level">LEVEL ${String(i+1).padStart(2,'0')}</span><strong>${name(i)}</strong><small>${threshold.toLocaleString()} XP ${en?'total':'สะสม'}</small></div><span class="cc82-state">${state}</span></li>`;
    }).join('');
    dialog.innerHTML=`<div class="cc82-shell"><header class="cc82-head"><div><span class="cc82-overline">YOUR CODING JOURNEY</span><h2 id="cc82-heading">${en?'Rank journey':'เส้นทางยศ'}</h2><p>${en?'Advance through game ranks as you earn XP.':'สะสม XP เพื่อเลื่อนยศตามเลเวลโดยอัตโนมัติ'}</p></div><button type="button" class="cc82-close" aria-label="${en?'Close':'ปิด'}">×</button></header><div class="cc82-summary">${level<=5?`<img class="cc84-summary-emblem" src="${rankImage(level)}" alt="">`:''}<div><span>${en?'YOUR RANK':'ยศของคุณ'}</span><strong>Lv. ${level} · ${name(level-1)}</strong></div><div class="cc82-summary-xp"><b>${xp.toLocaleString()} XP</b><small>${status}</small></div></div><div class="cc82-caption"><span>${en?'ALL RANKS':'ยศทั้งหมด'}</span><span>${level} / ${G_THRESHOLDS.length}</span></div><ol class="cc82-list">${items}</ol><p class="cc82-note">${en?'Ranks depend on XP, not achievements. XP is stored in this browser; use Account to back up or restore progress.':'ยศคำนวณจาก XP แยกจากความสำเร็จ · XP บันทึกในเบราว์เซอร์นี้ สำรองหรือกู้คืนได้ที่เมนูบัญชี'}</p></div>`;
    document.body.append(dialog);
    dialog.querySelector('.cc82-close').addEventListener('click',()=>dialog.close());
    dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close()}});
    dialog.addEventListener('close',()=>{dialog.remove();if(trigger.isConnected)trigger.focus()},{once:true});
    dialog.showModal();
  });
})();
