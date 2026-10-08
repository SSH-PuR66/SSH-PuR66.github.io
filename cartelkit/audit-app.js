(() => {
  'use strict';
  const app = document.querySelector('[data-model-audit]');
  if (!app) return;
  const math = window.CartelAuditMath;
  const $ = selector => app.querySelector(selector);
  const fmt = (n,places=2) => n.toLocaleString('en-US',{minimumFractionDigits:places,maximumFractionDigits:places});
  let data;
  const state = {age:40,multiplier:1,inverse:true,k:1,baseline:'2027'};
  const tabButtons = [...app.querySelectorAll('[data-audit-tab]')];
  function activate(button) {
    for (const item of tabButtons) {
      const active = item===button;
      item.setAttribute('aria-selected',String(active)); item.tabIndex=active?0:-1;
      document.getElementById(item.getAttribute('aria-controls')).hidden=!active;
    }
  }
  tabButtons.forEach((button,index) => {
    button.addEventListener('click',()=>activate(button));
    button.addEventListener('keydown',event=>{
      const next=event.key==='ArrowRight'?(index+1)%tabButtons.length:event.key==='ArrowLeft'?(index+tabButtons.length-1)%tabButtons.length:event.key==='Home'?0:event.key==='End'?tabButtons.length-1:null;
      if(next===null)return; event.preventDefault();activate(tabButtons[next]);tabButtons[next].focus();
    });
  });
  function render() {
    if (!data) return;
    const result=math.sentenceStats(data.sentences.distribution,state.age,state.multiplier,state.inverse);
    $('[data-assigned]').textContent=fmt(result.assigned);
    $('[data-capped]').textContent=fmt(result.capped);
    $('[data-excess]').textContent=fmt(result.excess);
    $('[data-beyond]').textContent=fmt(result.beyond*100,1)+'%';
    $('[data-sentence-caption]').textContent=`${state.inverse?'Author’s inverse-length assignment weights':'Unweighted surveyed-person distribution'} · sentence multiplier ${fmt(state.multiplier)}× · assumed incarceration age ${state.age}`;
    $('[data-age-output]').textContent=state.age;
    $('[data-multiplier-output]').textContent=fmt(state.multiplier)+'×';
    const bars=[...app.querySelectorAll('[data-bin]')];
    bars.forEach((row,i)=>{const share=result.bins[i].share;row.querySelector('meter').value=share;row.querySelector('span').textContent=fmt(share*100,1)+'%';});
    $('[data-sentence-interpretation]').textContent=state.multiplier<1?
      'This setting shortens sentences. It is included to inspect the supplied code’s 0–2 multiplier domain; the paper’s longer-sentence methods specify α ≥ 1.':
      `At the chosen age, ${fmt(result.excess)} assigned years per sampled sentence lie beyond the model’s age-69 limit. This is a fixed-age sensitivity calculation, not the paper’s cohort-wide effect.`;
    const scaled=math.scaleState(state.k);
    $('[data-scale-output]').textContent=fmt(state.k)+'×';
    for (const key of ['population','f','g','eta','theta','omega','rho','loss']) {
      const value=scaled[key];
      $(`[data-scale-${key}]`).textContent=key==='population'?fmt(value,0):['f','g'].includes(key)?fmt(value*100,1)+'%':fmt(value,2)+'×';
    }
    const comparison=math.baselineComparison(state.baseline);
    $('[data-baseline-unchanged]').textContent=(comparison.unchanged>0?'+':'')+fmt(comparison.unchanged,1)+'%';
    $('[data-baseline-double]').textContent=(comparison.double>0?'+':'')+fmt(comparison.double,1)+'%';
    $('[data-baseline-note]').textContent=state.baseline==='2027'?'Compared with the unchanged 2027 scenario, doubled incapacitation is about 22.9% lower.':'Compared with 2022, both reported 2027 scenarios are higher. The change in baseline changes the question, not either scenario.';
  }
  async function load() {
    try {
      const response=await fetch(app.dataset.source,{credentials:'omit'});
      if(!response.ok)throw new Error('Could not load the audit data');
      data=await response.json();
      if(data.schema_version!==1 || data.upstream.commit!=='224e9cc9382672cd6e48b3de830afbe9706b3d0a')throw new Error('Unexpected audit revision');
      math.sentenceStats(data.sentences.distribution);
      $('[data-audit-loading]').hidden=true;
      app.querySelectorAll('fieldset').forEach(fieldset=>fieldset.disabled=false);
      $('[data-export-audit]').disabled=false;
      render();
    } catch(error) {
      $('[data-audit-loading]').textContent='Interactive data could not load. The findings and reproducible data remain available in the links below.';
    }
  }
  $('#audit-age').addEventListener('input',event=>{state.age=Number(event.target.value);render();});
  $('#audit-multiplier').addEventListener('input',event=>{state.multiplier=Number(event.target.value);render();});
  $('#audit-weighting').addEventListener('change',event=>{state.inverse=event.target.value==='inverse';render();});
  $('#audit-scale').addEventListener('input',event=>{state.k=Number(event.target.value);render();});
  $('#audit-baseline').addEventListener('change',event=>{state.baseline=event.target.value;render();});
  $('[data-reset-audit]').addEventListener('click',()=>{
    Object.assign(state,{age:40,multiplier:1,inverse:true,k:1,baseline:'2027'});
    $('#audit-age').value='40';$('#audit-multiplier').value='1';$('#audit-weighting').value='inverse';$('#audit-scale').value='1';$('#audit-baseline').value='2027';render();
  });
  $('[data-export-audit]').addEventListener('click',()=>{
    const output={edition:data.edition,input_commit:data.upstream.commit,input_hashes:data.upstream.files.map(({name,sha256})=>({name,sha256})),settings:state,
      sentence_slice:math.sentenceStats(data.sentences.distribution,state.age,state.multiplier,state.inverse),scale:math.scaleState(state.k),
      baseline:math.baselineComparison(state.baseline),scope:'User-selected arithmetic sensitivity; not an observed cohort, new population estimate or full-model rerun.'};
    const url=URL.createObjectURL(new Blob([JSON.stringify(output,null,2)+'\n'],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='cartelkit-analysis-slice.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  load();
})();
