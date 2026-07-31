/* =========================================================
   TERRA — Petits utilitaires autour de Chart.js
   Centralise les couleurs (thème clair/sombre) pour que tous
   les graphiques du site restent cohérents.
   ========================================================= */

const _registeredCharts=[];

function chartColors(){
  return {
    ink:cssv('--ink'), muted:cssv('--muted'), line:cssv('--line'),
    green:cssv('--green'), red:cssv('--red'), blue:cssv('--blue'), amber:cssv('--amber')
  };
}

/* Dégradé vertical (couleur pleine en haut -> transparente en bas) pour
   les remplissages d'aire — un flat rgba() a un rendu "plat" ; un
   dégradé donne un aspect plus vivant et professionnel. Se recalcule à
   chaque appel (nécessite le canvas déjà attaché au DOM). */
function areaGradient(canvasId, hex, alphaTop){
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext('2d');
  const g = ctx.createLinearGradient(0, 0, 0, canvas.clientHeight || 260);
  const r = parseInt(hex.slice(1,3),16), gg = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  g.addColorStop(0, `rgba(${r},${gg},${b},${alphaTop ?? .28})`);
  g.addColorStop(1, `rgba(${r},${gg},${b},0)`);
  return g;
}

function makeLineChart(canvasId, labels, datasets){
  const c=chartColors();
  const chart=new Chart(document.getElementById(canvasId), {
    type:'line',
    data:{labels, datasets},
    options:{
      responsive:true, maintainAspectRatio:false, animation:{duration:280},
      interaction:{mode:'index', intersect:false},
      elements:{
        line:{borderCapStyle:'round', borderJoinStyle:'round'},
        point:{hoverBorderWidth:2}
      },
      plugins:{
        legend:{labels:{usePointStyle:true, boxWidth:8, color:c.ink, font:{family:'Plus Jakarta Sans', size:12}}},
        tooltip:{
          enabled:true,
          backgroundColor:c.ink==='#14231c' ? '#14231c' : c.ink, // texte -> fond du tooltip (contraste garanti par le thème)
          titleColor:'#fff', bodyColor:'#fff',
          padding:10, cornerRadius:10, displayColors:true, boxPadding:4,
          titleFont:{family:'Plus Jakarta Sans', weight:'700', size:12},
          bodyFont:{family:'Plus Jakarta Sans', size:12},
        }
      },
      scales:{
        y:{grid:{color:c.line}, ticks:{color:c.muted}},
        x:{grid:{display:false}, ticks:{color:c.muted}}
      }
    }
  });
  _registeredCharts.push(chart);
  return chart;
}

function makeBarChart(canvasId, labels, data, color, opts){
  opts=opts||{};
  const c=chartColors();
  const chart=new Chart(document.getElementById(canvasId), {
    type:'bar',
    data:{labels, datasets:[{data, backgroundColor:color||c.blue, borderRadius:8}]},
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{legend:{display:false}},
      scales:{
        y:{ticks:{color:c.muted, callback:v=>v+(opts.unit||'')}, grid:{color:c.line}},
        x:{ticks:{color:c.muted}, grid:{display:false}}
      }
    }
  });
  _registeredCharts.push(chart);
  return chart;
}

function restyleCharts(){
  const c=chartColors();
  _registeredCharts.forEach(chart=>{
    if(chart.options.scales){
      if(chart.options.scales.y){chart.options.scales.y.ticks.color=c.muted; if(chart.options.scales.y.grid) chart.options.scales.y.grid.color=c.line;}
      if(chart.options.scales.x){chart.options.scales.x.ticks.color=c.muted; if(chart.options.scales.x.grid) chart.options.scales.x.grid.color=c.line;}
    }
    if(chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) chart.options.plugins.legend.labels.color=c.ink;
    chart.update('none');
  });
}
function onThemeChange(){ restyleCharts(); }
