/* Isolated lesson bank pilot; not for production deployment. */
(() => {
  'use strict';
  const oldHtml = lessonCheckHtml, oldBind = bindLessonCheck;
  const banks = {variables: window.ccPilotBank, 'python-variables': window.ccPythonPilotBank, 'python-control': window.ccPythonControlPilotBank, cpp: window.ccCppPilotBank};
  const storageKey = id => 'cc-pilot-lesson-20-v1:' + id;
  let busy = false;
  const empty = () => ({engine: null, answers: {}, order: {}, result: null});
  function read(id) {
    const raw = localStorage.getItem(storageKey(id));
    if (!raw) return empty();
    const v = JSON.parse(raw);
    if (!v || typeof v !== 'object' || !v.answers || !v.order) throw Error('ข้อมูลชุดทดลองไม่ถูกต้อง');
    return v;
  }
  function save(v,id) { localStorage.setItem(storageKey(id), JSON.stringify(v)); }
  function shuffle(values) {
    const a = [...values];
    for (let i=a.length-1;i>0;i--) {
      const limit=Math.floor(4294967296/(i+1))*(i+1), b=new Uint32Array(1);
      do { crypto.getRandomValues(b); } while(b[0]>=limit);
      const j=b[0]%(i+1); [a[i],a[j]]=[a[j],a[i]];
    }
    return a;
  }
  function start(id) {
    const bank=banks[id];
    let state=read(id);
    const next=ccBankEngine.openAttempt(bank,state.engine);
    state.engine=next.state; state.answers={}; state.result=null; state.order={};
    for(const q of next.questions) if(q.type==='choice') state.order[q.id]=shuffle([0,1,2,3]);
    save(state,id);
  }
  function formatMessage(e){return e && e.message ? e.message : 'ไม่สามารถใช้งานพื้นที่เก็บข้อมูลได้';}
  function html(id) {
    if(!banks[id]) return oldHtml(id);
    const bank=banks[id];
    let data;
    try {data=read(id);} catch(e){return `<section class="mini-quiz lesson-check"><h2>แบบทดสอบท้ายบท · รุ่นทดลอง</h2><p role="alert">${esc(formatMessage(e))}</p></section>`;}
    let head='<div class="overline">LESSON CHECK · PILOT</div><h2>แบบทดสอบท้ายบท · ทดลอง</h2><p>20 ข้อ: ปรนัย 15 ข้อและเขียนโค้ด 5 ข้อ สุ่มไม่ซ้ำจนใช้ครบ 40 ข้อของบทนี้ เก็บชุดและคำตอบเฉพาะเบราว์เซอร์นี้</p><p>รุ่นทดลอง: ตรวจโค้ดจากผลลัพธ์ในเบราว์เซอร์ ไม่พิสูจน์ว่าใช้โครงสร้างตามโจทย์ และไม่ใช่การสอบป้องกันการทุจริต</p>';
    if (data.result) {
      const details=data.result.items.map((v,i)=>`<li>${i+1}. ${v.ok?'✓ ถูก':'✗ ยังไม่ถูก'} · ${esc(v.prompt)}${v.why?' — '+esc(v.why):''}</li>`).join('');
      return `<section class="mini-quiz lesson-check">${head}<p role="status"><strong>ได้ ${data.result.score} / 20 คะแนน ${data.result.score>=14?'· ผ่าน':'· ยังไม่ผ่าน'}</strong></p><p>เกณฑ์ทดลอง 14/20 อิงเกณฑ์เดิมที่ต้องถูกอย่างน้อยสองในสาม และไม่ลบผลผ่านเดิม</p><details><summary>ดูผลรายข้อ</summary><ol>${details}</ol></details><button class="btn btn-dark" id="ccPilotStart">เริ่มชุดถัดไป</button><p id="ccPilotStatus" role="status"></p></section>`;
    }
    if(!data.engine?.active) return `<section class="mini-quiz lesson-check">${head}<button class="btn btn-dark" id="ccPilotStart">เริ่มชุด 20 ข้อ</button><p id="ccPilotStatus" role="status">${passedLessonCheck(id)?'✓ มีผลผ่านเดิมอยู่แล้ว':''}</p></section>`;
    let qs;
    try {qs=ccBankEngine.openAttempt(bank,data.engine).questions;}catch(e){return `<section class="mini-quiz lesson-check">${head}<p role="alert">${esc(formatMessage(e))}</p></section>`;}
    const cards=qs.map((q,i)=>{
      if(q.type==='choice'){
        const order=data.order[q.id];
        if(!Array.isArray(order)||order.length!==4||new Set(order).size!==4||order.some(x=>!Number.isInteger(x)||x<0||x>3)) throw Error('ลำดับตัวเลือกไม่ถูกต้อง');
        return `<fieldset class="cc-pilot-question" data-pilot-question="${esc(q.id)}"><legend>${i+1}. ${esc(q.prompt)} <small>ปรนัย</small></legend>${order.map(n=>`<label><input type="radio" name="pilot-${esc(q.id)}" data-pilot-answer="${esc(q.id)}" value="${n}" ${data.answers[q.id]===n?'checked':''}> ${esc(q.options[n])}</label>`).join('')}</fieldset>`;
      }
      const value=typeof data.answers[q.id]==='string'?data.answers[q.id]:q.starter;
      return `<fieldset class="cc-pilot-question" data-pilot-question="${esc(q.id)}"><legend>${i+1}. ${esc(q.prompt)} <small>เขียนโค้ดภาษา ${bank.language==='python'?'Python':bank.language==='cpp'?'C++':'C'}</small></legend><p>แสดงเฉพาะผลลัพธ์ตามโจทย์ สามารถขึ้นบรรทัดใหม่ท้ายผลลัพธ์ได้</p><textarea data-pilot-code="${esc(q.id)}" aria-label="โค้ดคำตอบข้อ ${i+1}" rows="7" spellcheck="false" style="width:100%;font-family:monospace">${esc(value)}</textarea></fieldset>`;
    }).join('');
    return `<section class="mini-quiz lesson-check">${head}<p>ชุดที่ ${data.engine.active.cycle} · โจทย์ที่ใช้แล้ว ${data.engine.used.length} / 40</p><form id="ccPilotForm">${cards}<button type="submit" class="btn btn-dark">ตรวจคำตอบทั้ง 20 ข้อ</button><p id="ccPilotStatus" role="status" aria-live="polite"></p></form></section>`;
  }
  function bind() {
    if(!banks[current] || page!=='lesson') return oldBind();
    const lessonId=current, bank=banks[lessonId];
    const startButton=document.getElementById('ccPilotStart');
    if(startButton) startButton.onclick=()=>{try{start(lessonId);render();document.querySelector('.lesson-check')?.scrollIntoView({block:'start'});}catch(e){document.getElementById('ccPilotStatus').textContent=formatMessage(e);}};
    const form=document.getElementById('ccPilotForm'); if(!form)return;
    form.addEventListener('change',e=>{const id=e.target.dataset.pilotAnswer;if(!id)return;try{const s=read(lessonId);s.answers[id]=Number(e.target.value);save(s,lessonId);}catch(err){document.getElementById('ccPilotStatus').textContent=formatMessage(err);}});
    form.addEventListener('input',e=>{const id=e.target.dataset.pilotCode;if(!id)return;try{const s=read(lessonId);s.answers[id]=e.target.value;save(s,lessonId);}catch(err){document.getElementById('ccPilotStatus').textContent=formatMessage(err);}});
    form.onsubmit=async event=>{
      event.preventDefault(); if(busy)return;
      const status=document.getElementById('ccPilotStatus'), button=form.querySelector('button[type=submit]');
      let state, questions;
      try {
        state=read(lessonId); questions=ccBankEngine.openAttempt(bank,state.engine).questions;
        const missing=questions.findIndex(q=>q.type==='choice'?!Number.isInteger(state.answers[q.id]):!(typeof state.answers[q.id]==='string' && state.answers[q.id].trim() && state.answers[q.id]!==q.starter));
        if(missing>=0){status.textContent='กรุณาตอบให้ครบ โดยยังไม่ได้ตอบข้อ '+(missing+1);form.querySelectorAll('fieldset')[missing].scrollIntoView({block:'center'});return;}
      } catch(e){status.textContent=formatMessage(e);return;}
      busy=true;button.disabled=true;const fields=[...form.querySelectorAll('input,textarea')];fields.forEach(field=>field.disabled=true);status.textContent='กำลังตรวจข้อเขียนโค้ด โปรดรอสักครู่...';
      try{
        let items=[];let count=0;
        for(const q of questions){
          let ok=false, why='';
          if(q.type==='choice'){ok=state.answers[q.id]===q.answer;why=q.explanation;}
          else{
            count++;status.textContent=`กำลังตรวจโค้ด ${count}/5 ...`;
            ok=true;
            for(const t of q.tests){
              const r=await runLocal(bank.language,state.answers[q.id],t.stdin);
              if(r.exitCode!==0 || String(r.stdout||'').replace(/\r\n/g,'\n').replace(/\n+$/,'')!==t.expected.replace(/\r\n/g,'\n').replace(/\n+$/,'')) {ok=false;break;}
            }
            why='ตรวจจากผลลัพธ์ของโปรแกรม';
          }
          items.push({id:q.id,prompt:q.prompt,ok,why});
        }
        // Preserve existing pass records; never remove a previously earned pass.
        const score=items.filter(x=>x.ok).length;
        state.engine=ccBankEngine.closeAttempt(state.engine);state.result={score,items};state.answers={};state.order={};
        if(score>=14){const key='codecraft-lesson-check-v1';let passed=JSON.parse(localStorage.getItem(key)||'[]');if(!Array.isArray(passed))throw Error('ข้อมูลความก้าวหน้าผิดรูปแบบ');if(!passed.includes(lessonId))passed.push(lessonId);localStorage.setItem(key,JSON.stringify(passed));}
        save(state,lessonId);
        render();document.querySelector('.lesson-check')?.scrollIntoView({block:'start'});
      } catch(e){status.textContent='ตรวจไม่สำเร็จ ชุดเดิมยังอยู่ กรุณาลองใหม่: '+formatMessage(e);button.disabled=false;fields.forEach(field=>field.disabled=false);}
      finally{busy=false;}
    };
  }
  lessonCheckHtml=html;
  bindLessonCheck=bind;
})();
