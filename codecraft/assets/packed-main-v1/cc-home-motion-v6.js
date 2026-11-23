/* Home-page animation only: text stays in the DOM, no change to navigation or app state. */
(()=>{'use strict';
 const reduce=matchMedia('(prefers-reduced-motion: reduce)');
 function animateText(root,step,start){
   if(!root||root.dataset.ccAnimated||reduce.matches)return;
   root.dataset.ccAnimated='1';
   const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),nodes=[];
   while(walker.nextNode())nodes.push(walker.currentNode);
   let n=0; const segmenter=typeof Intl.Segmenter==='function'?new Intl.Segmenter(document.documentElement.lang||'th',{granularity:'grapheme'}):null;
   for(const node of nodes){
     const chars=segmenter?[...segmenter.segment(node.data)].map(x=>x.segment):Array.from(node.data);
     const frag=document.createDocumentFragment();
     for(const ch of chars){
       if(ch==='\n'||ch==='\r'){frag.append(document.createTextNode(ch));continue}
       const span=document.createElement('span');span.className='cc-motion-char';span.textContent=ch;span.style.animationDelay=(start+n++*step)+'ms';frag.append(span);
     }
     node.replaceWith(frag);
   }
 }
 function animateCounters(home){
   for(const [i,el] of [...home.querySelectorAll('.cc60-stat strong')].entries()){
     const original=el.textContent.trim(), match=original.match(/^(\d+)(%?)$/);
     if(!match) continue;
     const target=Number(match[1]), suffix=match[2];
     el.setAttribute('aria-label',original);
     if(reduce.matches) continue;
     el.textContent='0'+suffix;
     const started=performance.now()+180, up=1300, down=1000;
     function frame(now){
       if(!el.isConnected)return;
       const elapsed=Math.max(0,now-started);let n;
       if(suffix){
         if(elapsed<up) n=100*(1-Math.pow(1-elapsed/up,3));
         else if(elapsed<up+down) {const f=(elapsed-up)/down;n=100+(target-100)*(1-Math.pow(1-f,3));}
         else n=target;
       } else n=target*(1-Math.pow(1-Math.min(elapsed/up,1),3));
       el.textContent=Math.round(n)+suffix;
       if(elapsed<(suffix?up+down:up))requestAnimationFrame(frame);else el.textContent=original;
     }
     requestAnimationFrame(frame);
   }
 }
 // Preview the built-in starter samples, never the user's saved editor contents.
 let codeTimer=null;
 function initCodePreview(home){
   if(codeTimer)clearTimeout(codeTimer);
   const box=home.querySelector('.cc60-code'), pre=box?.querySelector('pre'), file=box?.querySelector('.cc60-codebar > span');
   if(!box||!pre||!file||typeof editorLanguages==='undefined')return;
   const names=['c','cpp','python','csharp','java']; let idx=0, playing=!reduce.matches;
   const button=document.createElement('button');button.type='button';button.className='cc-code-toggle';
   const en=typeof ccLang!=='undefined'&&ccLang==='en';
   function buttonLabel(){button.textContent=playing?(en?'Pause':'หยุด'):(en?'Play':'เล่น');button.setAttribute('aria-label',playing?(en?'Pause example rotation':'หยุดสลับตัวอย่างโค้ด'):(en?'Play example rotation':'เล่นตัวอย่างโค้ด'));button.setAttribute('aria-pressed',String(!playing));}
   box.querySelector('.cc60-codebar').append(button);
   function schedule(){clearTimeout(codeTimer);if(playing)codeTimer=setTimeout(()=>{if(!home.isConnected)return;idx=(idx+1)%names.length;show();schedule()},8000)}
   button.addEventListener('click',()=>{playing=!playing;buttonLabel();schedule()});buttonLabel();
   function show(){
     const key=names[idx],entry=editorLanguages[key];if(!entry)return;
     file.textContent='▤ '+entry.file+' · '+entry.label;
     box.dataset.codeKey=key;
     box.setAttribute('aria-label',en?'Illustrative '+entry.label+' code; output is an example, not a live execution':'ตัวอย่างโค้ด '+entry.label+' และผลลัพธ์ตัวอย่าง ไม่ใช่ผลการรันจริง');
     pre.replaceChildren(); delete pre.dataset.ccAnimated;
     const code=entry.initial.replace(/\n$/, ''),lines=code.split('\n');
     const tokens=/("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|#include|<[^>]+>|\b(?:int|return|using|static|public|class|void|print|System|Console|String|std)\b)/g;
     lines.forEach((line,i)=>{
       const number=document.createElement('i');number.textContent=String(i+1).padStart(2,'0');pre.append(number,document.createTextNode(' '));
       let last=0,m;tokens.lastIndex=0;
       while((m=tokens.exec(line))){
         pre.append(document.createTextNode(line.slice(last,m.index)));
         let span=document.createElement('span');span.className='cc-syntax-token';span.textContent=m[0];pre.append(span);last=m.index+m[0].length;
       }
       pre.append(document.createTextNode(line.slice(last)));if(i<lines.length-1)pre.append(document.createTextNode('\n'));
     });
     const output=box.querySelector('.cc60-output code');if(output){output.replaceChildren(document.createTextNode('> Hello, world! '));let cursor=document.createElement('i');cursor.textContent='▌';output.append(cursor)}
     animateText(pre,16,150);
   }
   show();schedule();
 }
 function init(){
   const home=document.querySelector('.cc60-home'); if(!home||home.dataset.ccMotionReady)return;
   home.dataset.ccMotionReady='1';
   const heading=home.querySelector('.cc60-copy h1');
   if(heading){heading.setAttribute('aria-label',heading.textContent.trim());animateText(heading,45,160)}
   initCodePreview(home);
   animateCounters(home);
   home.classList.add('cc-motion-ready');
 }
 let pending=false;const observer=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;init()})});
 function start(){init();observer.observe(document.getElementById('app')||document.body,{childList:true,subtree:true})}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
