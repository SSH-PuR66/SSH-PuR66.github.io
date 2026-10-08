const test=require('node:test');
const assert=require('node:assert/strict');
const math=require('./audit-math.js');
const data=require('./model-audit.json');
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-10,`${a} differs from ${b}`);

test('browser arithmetic matches the independently derived Python expectations',()=>{
  close(math.sentenceStats(data.sentences.distribution).assigned,data.sentences.inverse_weighted_mean_years);
  close(math.sentenceStats(data.sentences.distribution,40,1,false).assigned,data.sentences.survey_mean_years);
});
test('known two-length distribution detects inverse weighting and lifetime cap',()=>{
  const result=math.sentenceStats([[1,1],[20,1]],60);
  close(result.assigned,40/21);close(result.capped,29/21);close(result.beyond,1/21);
});
test('histogram conserves probability even above its final bin',()=>{
  const result=math.sentenceStats(data.sentences.distribution,40,3);
  close(result.bins.reduce((s,b)=>s+b.share,0),1);
  assert.ok(result.bins.at(-1).share>0);
});
test('age-limit endpoint has no remaining years',()=>{
  const result=math.sentenceStats(data.sentences.distribution,69);
  close(result.capped,0);close(result.beyond,1);close(result.excess,result.assigned);
});
test('multiplier scales assigned length after probability selection',()=>{
  close(math.sentenceStats(data.sentences.distribution,40,2).assigned,2*math.sentenceStats(data.sentences.distribution).assigned);
});
test('bad sensitivity values fail instead of silently extrapolating',()=>{
  for(const [age,m] of [[NaN,1],[14,1],[70,1],[40,Infinity],[40,0],[40,4]])assert.throws(()=>math.sentenceStats([[1,1]],age,m));
});
test('malformed aggregate data is rejected',()=>{
  for(const data of [[],[[0,1]],[[NaN,1]],[[1,0]],[[1,1.2]],[[1,1,'extra']]])assert.throws(()=>math.sentenceStats(data));
});
test('equation-scale control transforms all required quantities',()=>{
  assert.deepEqual(math.scaleState(2),{k:2,population:350000,f:.2,g:.1,eta:2,theta:.5,omega:.5,rho:1,loss:4});
  assert.throws(()=>math.scaleState(10));
});
test('baseline switch changes comparison without changing published indices',()=>{
  close(math.baselineComparison('2027').double,-22.85714285714286);
  close(math.baselineComparison('2022').double,8);
  close(math.baselineComparison('2022').unchanged,40);
  assert.throws(()=>math.baselineComparison('2030'));
});
