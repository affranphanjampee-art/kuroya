'use strict';
/* Draft selection engine. Storage, synchronization, grading and security are NOT provided here. */
(function(root){
 const cryptoSource=root.crypto?.getRandomValues?root.crypto:(typeof require==='function'?require('node:crypto').webcrypto:null);
 function rand(n){if(!cryptoSource||!Number.isInteger(n)||n<1||n>0x100000000)throw Error('Invalid RNG');let limit=Math.floor(0x100000000/n)*n,b=new Uint32Array(1);do{cryptoSource.getRandomValues(b)}while(b[0]>=limit);return b[0]%n;}
 function shuffle(a,rng){a=[...a];for(let i=a.length-1;i>0;i--){let j=rng(i+1);if(!Number.isInteger(j)||j<0||j>i)throw Error('Invalid RNG');[a[i],a[j]]=[a[j],a[i]]}return a}
 function validate(bank,topic){
  if(!bank||typeof bank.id!=='string'||!bank.id||!Number.isInteger(bank.version)||!Array.isArray(bank.questions)||bank.questions.length<15)throw Error('Language bank must contain at least 15 items');
  let ids=new Set();for(let q of bank.questions){if(!q||typeof q.id!=='string'||!q.id||ids.has(q.id)||!['choice','code'].includes(q.type)||!Array.isArray(q.topics)||!q.topics.length||q.topics.some(x=>typeof x!=='string'||!x))throw Error('Invalid item');ids.add(q.id)}
  if(topic!==null&&(typeof topic!=='string'||!topic))throw Error('Invalid topic');const pool=topic===null?bank.questions:bank.questions.filter(q=>q.topics.includes(topic));if(!pool.length)throw Error('No questions for this topic');return pool;
 }
 function openAttempt(bank,topic,state=null,rng=rand){
  const pool=validate(bank,topic), byId=new Map(pool.map(q=>[q.id,q])), count=Math.min(20,pool.length),scope=topic??'*';
  let s=state?structuredClone(state):{bankId:bank.id,bankVersion:bank.version,scope,cycle:1,used:[],active:null};
  if(s.bankId!==bank.id||s.bankVersion!==bank.version||s.scope!==scope)throw Error('Bank or scope mismatch; migration required');
  if(!Number.isInteger(s.cycle)||s.cycle<1||!Array.isArray(s.used)||new Set(s.used).size!==s.used.length||s.used.some(x=>!byId.has(x)))throw Error('Invalid progress');
  if(s.active){
   if(!Array.isArray(s.active.items)||(s.active.items.length<1||s.active.items.length>20)||new Set(s.active.items.map(x=>x.id)).size!==s.active.items.length||s.active.items.some(x=>!byId.has(x.id)||!Number.isInteger(x.cycle)||x.cycle<1||x.cycle>s.cycle)||s.active.items.filter(x=>x.cycle===s.cycle).some(x=>!s.used.includes(x.id)))throw Error('Invalid active attempt');
   return {state:s,questions:s.active.items.map(x=>byId.get(x.id))};
  }
  const chosen=[],taken=new Set();
  while(chosen.length<count){
   if(s.used.length===pool.length){s.used=[];s.cycle++}
   let used=new Set(s.used),available=pool.filter(q=>!used.has(q.id)&&!taken.has(q.id));
   let size=Math.min(count-chosen.length,available.length);if(!size)throw Error('Insufficient distinct questions');
   const c=shuffle(available.filter(q=>q.type==='choice'),rng),k=shuffle(available.filter(q=>q.type==='code'),rng);
   let choiceCount=Math.round(size*c.length/available.length);choiceCount=Math.max(size-k.length,Math.min(c.length,choiceCount));
   if(size>=2&&c.length&&k.length)choiceCount=Math.max(1,Math.min(size-1,choiceCount));
   // For expanded C knowledge, ration code items across remaining 20-question sets.
   // Legacy history may already be imbalanced; never violate cycle/no-duplicate rules.
   if(bank.language==='c'&&topic===null&&k.length&&c.length){
    let reserve=Math.ceil((available.length-size)/count);
    let maxCode=Math.max(1,k.length-reserve);
    let nCode=Math.max(1,Math.min(size-choiceCount,maxCode));
    choiceCount=Math.max(size-k.length,Math.min(c.length,size-nCode));
   }
   // During rollover prefer a missing type if possible without repeating in the set.
   if(bank.language==='c'&&size&&k.length&&!chosen.some(x=>byId.get(x.id).type==='code'))choiceCount=Math.min(choiceCount,size-1);
   if(bank.language==='c'&&size&&c.length&&!chosen.some(x=>byId.get(x.id).type==='choice'))choiceCount=Math.max(choiceCount,1);
   for(let q of shuffle([...c.slice(0,choiceCount),...k.slice(0,size-choiceCount)],rng)){chosen.push({id:q.id,cycle:s.cycle});taken.add(q.id);s.used.push(q.id)}
  }
  chosen.splice(0,chosen.length,...shuffle(chosen,rng));s.active={items:chosen};return {state:s,questions:chosen.map(x=>byId.get(x.id))};
 }
 function closeAttempt(state){if(!state?.active)throw Error('No active attempt');let s=structuredClone(state);s.active=null;return s;}
 const api={validate,openAttempt,closeAttempt};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ccSharedBankEngine=api;
})(globalThis);
