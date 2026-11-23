'use strict';
/* Prototype only. Not a score authority, sync service, or sandbox. */
(function (root) {
const randomSource = root.crypto && root.crypto.getRandomValues ? root.crypto : (typeof require === 'function' ? require('node:crypto').webcrypto : null);
function secureRandomInt(max) {
  if (!randomSource || !Number.isInteger(max) || max < 1 || max > 0x100000000) throw new Error('Secure randomness unavailable');
  const limit = Math.floor(0x100000000 / max) * max;
  const buf = new Uint32Array(1);
  do { randomSource.getRandomValues(buf); } while (buf[0] >= limit);
  return buf[0] % max;
}
function shuffle(items, randomInt = secureRandomInt) {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) {
    const j = randomInt(i + 1);
    if (!Number.isInteger(j) || j < 0 || j > i) throw new Error('Invalid RNG');
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}
function validateBank(bank) {
  if (!bank || !Array.isArray(bank.questions) || typeof bank.id !== 'string' || !bank.id || !Number.isInteger(bank.version)) throw new Error('Invalid bank');
  const q = bank.questions;
  if (q.length === 0 || q.length % 20) throw new Error('Bank size must be a positive multiple of 20');
  const ids = new Set();
  for (const v of q) {
    if (!v.id || typeof v.id !== 'string' || ids.has(v.id) || !['choice', 'code'].includes(v.type)) throw new Error('Invalid or duplicate question');
    ids.add(v.id);
  }
  const rounds = q.length / 20;
  if (q.filter(v=>v.type==='choice').length !== 15*rounds || q.filter(v=>v.type==='code').length !== 5*rounds) throw new Error('Bank requires exactly 15 choice and 5 code questions per round');
}
function openAttempt(bank, state = null, randomInt = secureRandomInt) {
  validateBank(bank);
  let s = state ? structuredClone(state) : {bankId: bank.id, bankVersion: bank.version, cycle: 1, used: [], active: null};
  if (s.bankId !== bank.id || s.bankVersion !== bank.version) throw new Error('Bank version mismatch: migration required');
  if (!Array.isArray(s.used) || new Set(s.used).size !== s.used.length || !Number.isInteger(s.cycle) || s.cycle < 1) throw new Error('Invalid progress');
  const byId = new Map(bank.questions.map(q=>[q.id,q]));
  if (s.used.some(id=>!byId.has(id))) throw new Error('Unknown used ID');
  if (s.active) {
    if (!Array.isArray(s.active.ids) || s.active.ids.length !== 20 || new Set(s.active.ids).size !== 20 || s.active.ids.some(id=>!s.used.includes(id))) throw new Error('Invalid active attempt');
    return {state:s, questions:s.active.ids.map(id=>byId.get(id))};
  }
  if (s.used.length === bank.questions.length) { s.used = []; s.cycle++; }
  const used = new Set(s.used), remaining=bank.questions.filter(q=>!used.has(q.id));
  const choices=shuffle(remaining.filter(q=>q.type==='choice'),randomInt).slice(0,15);
  const codes=shuffle(remaining.filter(q=>q.type==='code'),randomInt).slice(0,5);
  if(choices.length!==15 || codes.length!==5) throw new Error('Inconsistent progress: refusing to repeat questions');
  const questions=shuffle([...choices,...codes],randomInt);
  const ids=questions.map(q=>q.id);
  s.used.push(...ids); s.active={ids, cycle:s.cycle};
  return {state:s, questions};
}
function closeAttempt(state) {
  if (!state || !state.active) throw new Error('No active attempt');
  const copy=structuredClone(state); copy.active=null; return copy;
}
const api={validateBank,openAttempt,closeAttempt};
if(typeof module !== 'undefined' && module.exports) module.exports=api;
else root.ccBankEngine=api;
})(globalThis);
