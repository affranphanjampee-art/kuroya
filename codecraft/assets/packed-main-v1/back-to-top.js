(()=>{'use strict';
const button=document.createElement('button');button.type='button';button.className='cc-back-to-top';button.textContent='↑';button.tabIndex=-1;button.setAttribute('aria-hidden','true');
function label(){const en=document.documentElement.lang==='en';const s=en?'Back to top':'กลับขึ้นด้านบนสุด';button.setAttribute('aria-label',s);button.title=s}
function update(){const lesson=!!document.querySelector('#app > main.view-lesson, #app > main.view-cppunit');const show=lesson&&window.scrollY>160;button.classList.toggle('is-lesson',lesson);button.classList.toggle('is-visible',show);button.tabIndex=show?0:-1;button.setAttribute('aria-hidden',String(!show));if(!show&&document.activeElement===button)button.blur()}
label();new MutationObserver(label).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
new MutationObserver(update).observe(document.getElementById('app'),{childList:true});window.addEventListener('scroll',update,{passive:true});button.addEventListener('click',()=>window.scrollTo({top:0,left:0,behavior:'instant'}));document.body.append(button);update();
})();
