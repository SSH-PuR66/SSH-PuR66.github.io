/* Independent arithmetic for the reviewed model; no upstream implementation copied. */
(function (root) {
  'use strict';
  function sentenceStats(distribution, age = 40, multiplier = 1, inverse = true) {
    if (!Number.isFinite(age) || age < 15 || age > 69 || !Number.isFinite(multiplier) || multiplier < .5 || multiplier > 3) throw new RangeError('Unsupported sensitivity range');
    if (!Array.isArray(distribution) || !distribution.length) throw new TypeError('Missing aggregate distribution');
    let total = 0, assigned = 0, capped = 0, beyond = 0;
    const bins = Array.from({length: 10}, (_,i) => ({lower:i*10, upper:i===9?Infinity:(i+1)*10, weight:0}));
    for (const row of distribution) {
      if (!Array.isArray(row) || row.length !== 2) throw new TypeError('Invalid aggregate row');
      const [sentence,count] = row;
      if (!Number.isFinite(sentence) || sentence <= 0 || !Number.isSafeInteger(count) || count <= 0) throw new TypeError('Invalid sentence or count');
      const weight = inverse ? count/sentence : count, years = sentence*multiplier;
      total += weight; assigned += weight*years; capped += weight*Math.min(years,69-age);
      if (years > 69-age) beyond += weight;
      bins[Math.min(9,Math.floor(years/10))].weight += weight;
    }
    if (!Number.isFinite(total) || total <= 0) throw new RangeError('Invalid total weight');
    return {assigned:assigned/total,capped:capped/total,excess:(assigned-capped)/total,
      beyond:beyond/total,bins:bins.map(bin=>({...bin,share:bin.weight/total}))};
  }
  function scaleState(k) {
    if (!Number.isFinite(k) || k < .5 || k > 2) throw new RangeError('Unsupported scale');
    return {k, population:175000*k, f:.1*k, g:.05*k, eta:k, theta:1/k, omega:1/k, rho:1, loss:k*k};
  }
  function baselineComparison(reference) {
    if (!['2022','2027'].includes(reference)) throw new RangeError('Unknown baseline');
    const base = reference==='2022'?100:140;
    return {base, unchanged:(140/base-1)*100, double:(108/base-1)*100};
  }
  const api = {sentenceStats,scaleState,baselineComparison};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CartelAuditMath = Object.freeze(api);
})(typeof globalThis !== 'undefined' ? globalThis : this);
