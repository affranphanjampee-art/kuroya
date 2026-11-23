/* CODECRAFT prototype: derived progress, no new personal-data storage or network calls. */
(function(){
'use strict';
function diagram(item,kind){
 let en=ccLang==='en', parts=(kind==='cpp'?item.points:item.sections)||[];
 let nodes=parts.slice(0,4).map((p,i)=>`<li><span>${String(i+1).padStart(2,'0')}</span><strong>${esc(String(p[0]))}</strong></li>`).join('');
 if(!nodes)return '';
 return `<figure class="cc57-concept"><div class="cc57-visual" aria-hidden="true"><div class="cc57-orbit"><span>&lt;/&gt;</span><i>✦</i><b>{ }</b></div></div><figcaption><small>${en?'LESSON AT A GLANCE':'ภาพรวมบทเรียน'}</small><h2>${esc(item.title)}</h2><p>${en?'Key topics covered in this lesson':'หัวข้อสำคัญในบทเรียนนี้'}</p><ol>${nodes}</ol></figcaption></figure>`;
}
function videoPlaceholder(item){
 let en=ccLang==='en',code=String(item.code||'').split('\n').slice(0,6).join('\n');
 return `<section class="cc58-video" aria-label="${en?'Lesson video placeholder':'พื้นที่วิดีโอประกอบบทเรียน'}"><div class="cc58-video-head"><div><small>${en?'LESSON VIDEO':'วิดีโอประกอบบทเรียน'}</small><h2>${en?'Video coming soon':'วิดีโอประกอบบทเรียน'}</h2><p>${en?'Not available yet. You can continue with the lesson.':'ยังไม่มีวิดีโอจริง สามารถอ่านบทเรียนต่อได้เลย'}</p></div><span class="cc58-video-status">${en?'COMING SOON':'เร็ว ๆ นี้'}</span></div><div class="cc58-screen"><div class="cc58-screen-top"><span class="cc58-dots" aria-hidden="true">● ● ●</span><span>${esc(item.title)}</span></div><pre aria-label="${en?'Lesson code preview, not a video':'ตัวอย่างโค้ดจากบทเรียน ไม่ใช่วิดีโอ'}"><code>${esc(code)}</code></pre><div class="cc58-screen-overlay"><span class="cc58-play" aria-hidden="true">▶</span><strong>${en?'Video not available':'วิดีโอยังไม่พร้อมใช้งาน'}</strong><small>${en?'Illustration only — not a playable clip':'ภาพตัวอย่างเท่านั้น ยังไม่ใช่คลิปที่เล่นได้'}</small></div></div><div class="cc58-actions"><button type="button" class="cc58-watch" disabled>${en?'Video unavailable':'ยังไม่มีวิดีโอ'}</button><button type="button" class="cc58-skip">${en?'Continue to lesson':'ข้ามไปอ่านบทเรียน'}</button></div></section>`;
}
const oldLesson=lesson,oldCppLesson=cppLesson;
lesson=function(){let html=oldLesson(),item=lessons.find(x=>x.id===current);return item?html.replace('<section class="cc56-pre"',()=>videoPlaceholder(item)+'<section class="cc56-pre"').replace('<div class="article-sections">',()=>diagram(item,'lesson')+'<div class="article-sections">'):html};
cppLesson=function(){let html=oldCppLesson(),item=cppUnits.find(x=>x.id===cppCurrent);return item?html.replace('<section class="cc56-pre"',()=>videoPlaceholder(item)+'<section class="cc56-pre"').replace('<div class="article-sections">',()=>diagram(item,'cpp')+'<div class="article-sections">'):html};
const oldPortfolio=portfolioPage;
portfolioPage=function(){
 let en=ccLang==='en',n=done.length,total=lessons.length,lv=gLevel(),xp=G.xp,rank=gTitles[lv-1],cpp=cppQuizPassed.length,streak=gStreak();
 let goals=[{title:en?'First step':'ก้าวแรก',desc:en?'Complete 1 core lesson':'เรียนจบบทเรียนหลัก 1 บท',value:n,target:1,icon:'✦'},{title:en?'Getting started':'นักเรียนรู้',desc:en?'Complete 5 core lessons':'เรียนจบบทเรียนหลัก 5 บท',value:n,target:5,icon:'◈'},{title:en?'Keep learning':'นักฝึกฝน',desc:en?'Complete 10 core lessons':'เรียนจบบทเรียนหลัก 10 บท',value:n,target:10,icon:'✧'},{title:en?'C++ explorer':'เส้นทาง C++',desc:en?'Pass 1 C++ unit quiz':'ผ่านแบบทดสอบเส้นทาง C++ 1 บท',value:cpp,target:1,icon:'⌘'},{title:en?'A steady streak':'สม่ำเสมอ',desc:en?'Complete daily quests on 3 different days':'ทำภารกิจประจำวัน 3 วัน',value:new Set(G.questDays).size,target:3,icon:'⚡'},{title:en?'Growing skills':'ก้าวต่อไป',desc:en?'Reach level 3':'สะสม XP จนถึงเลเวล 3',value:lv,target:3,icon:'★'}];
 let cards=goals.map(g=>{let unlocked=g.value>=g.target;return `<article class="cc57-ach ${unlocked?'is-earned':'is-locked'}"><span class="cc57-medal" aria-hidden="true">${g.icon}</span><div><strong>${esc(g.title)}</strong><p>${esc(g.desc)}</p><small>${unlocked?(en?'Unlocked':'ได้รับแล้ว'):(en?'Locked':'ยังไม่ปลดล็อก')} · ${Math.min(g.value,g.target)}/${g.target}</small></div></article>`}).join('');
 let badge=`<section class="cc57-profile"><div class="cc57-banner"><div class="cc57-avatar" aria-hidden="true">&lt;/&gt;</div><div><span class="cc57-eyebrow">CODECRAFT / PROFILE</span><h1 class="cc57-name">${esc(portfolioName())}</h1><p>${esc(rank)} · Lv. ${lv} · ${xp} XP</p></div></div><div class="cc57-profile-body"><div class="cc57-stat"><b>${n} / ${total}</b><span>${en?'Core lessons completed':'บทเรียนหลักที่เรียนจบ'}</span></div><div class="cc57-stat"><b>${cpp}</b><span>${en?'C++ units passed':'บท C++ ที่ผ่าน'}</span></div><div class="cc57-stat"><b>${streak}</b><span>${en?'Daily streak':'วันต่อเนื่อง'}</span></div></div><p class="cc57-privacy">${en?'Private to this browser profile. Save or restore manually using Account. Progress is not an official certificate.':'แสดงเฉพาะโปรไฟล์ในเบราว์เซอร์นี้ สำรองหรือกู้คืนผ่านเมนูบัญชีด้วยตนเอง ไม่ใช่ผลรับรองอย่างเป็นทางการ'}</p><h2>${en?'Achievements':'ความสำเร็จ'}</h2><div class="cc57-achievements">${cards}</div><p class="cc57-privacy">${en?'Achievements reflect current progress and may change after reset or restore.':'ความสำเร็จคำนวณจากข้อมูลปัจจุบัน อาจเปลี่ยนหลังรีเซ็ตหรือกู้คืนข้อมูล'}</p></section>`;
 return badge+oldPortfolio();
};
const originalAccountPage=accountPage;
accountPage=function(){
 const en=ccLang==='en';
 return `<div class="cc59-jumps"><button type="button" id="cc59-to-profile">${en?'Profile & achievements':'โปรไฟล์และความสำเร็จ'}</button><button type="button" id="cc59-to-account">${en?'Account & backup':'บัญชีและสำรองข้อมูล'}</button></div><section id="cc59-profile" aria-label="${en?'Profile & achievements':'โปรไฟล์และความสำเร็จ'}">${portfolioPage()}</section><section id="cc59-account" aria-label="${en?'Account & backup':'บัญชีและสำรองข้อมูล'}">${originalAccountPage()}</section>`;
};
const oldGo=go;
go=function(destination,fromHistory){return oldGo(destination==='portfolio'?'account':destination,fromHistory)};
const oldRender=render;
render=function(){
 if(page==='portfolio')page='account';
 oldRender();
 let nav=document.querySelector('#main-nav [data-nav="account"]');
 if(nav){let label=nav.querySelector('span:last-child');if(label)label.textContent=ccLang==='en'?'Profile & account':'โปรไฟล์และบัญชี';nav.title=ccLang==='en'?'Profile & account':'โปรไฟล์และบัญชี'}
 if(page==='account'){
  bindPortfolio();
  for(const [button,target] of [['cc59-to-profile','cc59-profile'],['cc59-to-account','cc59-account']])document.getElementById(button)?.addEventListener('click',()=>document.getElementById(target)?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'}));
 }
 let skip=document.querySelector('.cc58-skip');if(skip)skip.addEventListener('click',()=>document.querySelector('.article-intro')?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'}));
 let name=document.getElementById('portfolioName');if(name)name.addEventListener('input',()=>{let el=document.querySelector('.cc57-name');if(el)el.textContent=name.value.trim()||'ผู้เรียน Codecraft'});
};
if(location.hash==='#portfolio'){page='account';history.replaceState(routeState(),'',location.pathname+location.search+'#account')}
render();
})();
