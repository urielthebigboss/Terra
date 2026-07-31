/* =========================================================
   TERRA — Utilitaires d'interface (toast, modales, thème…)
   ========================================================= */

/* ---------- Thème clair / sombre ---------- */
function initTheme(){
  const saved=localStorage.getItem('terra_theme')||'light';
  document.body.dataset.theme=saved;
}
function toggleTheme(){
  const b=document.body;
  b.dataset.theme = b.dataset.theme==='dark' ? 'light' : 'dark';
  localStorage.setItem('terra_theme', b.dataset.theme);
  document.querySelectorAll('[data-restyle-chart]').forEach(fnName=>{});
  if(typeof onThemeChange==='function') onThemeChange();
}

/* ---------- Échappement HTML ---------- */
/* Pour insérer du texte utilisateur/moteur dans du HTML sans injection. */
function esc(s){
  return String(s || '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'})[c]);
}

/* ---------- Toast ---------- */
let _toastT;
function toast(msg, type){
  let t=document.getElementById('toast');
  if(!t){t=document.createElement('div');t.id='toast';t.className='toast';document.body.appendChild(t);}
  t.textContent=msg;
  t.className='toast show'+(type?(' '+type):'');
  clearTimeout(_toastT);
  _toastT=setTimeout(()=>t.classList.remove('show'), 2800);
}

/* ---------- Modale générique ----------
   modal({title, sub, bodyHTML, okText, cancelText, danger, onOk})
*/
function ensureModalRoot(){
  let root=document.getElementById('modalRoot');
  if(!root){
    root=document.createElement('div');
    root.id='modalRoot';
    root.className='modal-backdrop';
    root.innerHTML='<div class="modal" role="dialog"><button class="iconbtn modal-close" onclick="closeModal()">✕</button><div id="modalBody"></div></div>';
    document.body.appendChild(root);
    root.addEventListener('click',e=>{if(e.target===root)closeModal();});
  }
  return root;
}
function closeModal(){
  const root=document.getElementById('modalRoot');
  if(root) root.classList.remove('show');
}
function openModal(opts){
  const root=ensureModalRoot();
  const body=document.getElementById('modalBody');
  body.innerHTML =
    '<h3>'+(opts.title||'')+'</h3>'+
    (opts.sub?'<div class="modal-sub">'+opts.sub+'</div>':'') +
    '<div>'+(opts.bodyHTML||'')+'</div>'+
    '<div class="modal-actions">'+
      '<button class="btn-sm" id="modalCancel" type="button">'+(opts.cancelText||'Annuler')+'</button>'+
      '<button class="btn-sm '+(opts.danger?'danger':'primary')+'" id="modalOk" type="button">'+(opts.okText||'Confirmer')+'</button>'+
    '</div>';
  root.classList.add('show');
  document.getElementById('modalCancel').onclick=()=>closeModal();
  document.getElementById('modalOk').onclick=()=>{ if(opts.onOk) opts.onOk(); };
  return root;
}
function confirmAction(message, onOk, opts){
  opts=opts||{};
  openModal({
    title: opts.title||'Confirmer l\'action',
    bodyHTML: '<p class="reco-why">'+message+'</p>',
    okText: opts.okText||'Confirmer',
    danger: opts.danger!==false,
    onOk: ()=>{ closeModal(); onOk(); }
  });
}

/* ---------- Skeleton loading ---------- */
function skeletonCards(container, n, spanClass){
  const el=(typeof container==='string')?document.getElementById(container):container;
  if(!el) return;
  let html='';
  for(let i=0;i<n;i++) html+='<div class="card '+(spanClass||'span4')+' sk-card skeleton"></div>';
  el.innerHTML=html;
}
function withSkeleton(container, n, spanClass, renderFn, delay){
  skeletonCards(container, n, spanClass);
  setTimeout(renderFn, delay||420);
}

/* ---------- Petites aides ---------- */
function fmtDate(d){
  const dt = (d instanceof Date) ? d : new Date(d);
  if(isNaN(dt)) return d;
  return dt.toLocaleDateString('fr-FR',{day:'2-digit',month:'short',year:'numeric'});
}
function fmtDateTime(ts){
  const dt=new Date(ts);
  return dt.toLocaleDateString('fr-FR',{day:'2-digit',month:'short'})+' · '+dt.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});
}
function timeAgo(ts){
  const s=Math.floor((Date.now()-ts)/1000);
  if(s<60) return 'à l\'instant';
  if(s<3600) return 'il y a '+Math.floor(s/60)+' min';
  if(s<86400) return 'il y a '+Math.floor(s/3600)+' h';
  return 'il y a '+Math.floor(s/86400)+' j';
}
function cssv(v){return getComputedStyle(document.body).getPropertyValue(v).trim();}
function downloadCSV(rows, filename){
  const blob=new Blob(['﻿'+rows.join('\n')], {type:'text/csv;charset=utf-8;'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=filename;
  document.body.appendChild(a); a.click(); a.remove();
  toast('Fichier téléchargé ✅','ok');
}
function csvEscape(v){return '"'+String(v).replace(/"/g,'""')+'"';}

document.addEventListener('DOMContentLoaded', initTheme);
