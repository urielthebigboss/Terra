/* =========================================================
   TERRA — Référentiel agronomique (culture de la tomate)
   ---------------------------------------------------------
   API-FIRST : les stades affichés viennent de la table
   `profil_culture` du backend (GET /profil-culture) — celle
   que l'administrateur maintient et que le futur Moteur
   Expert utilisera. Le référentiel statique ci-dessous ne
   sert que de REPLI si la table est vide ou l'API muette.

   Pages : appelez `await chargerProfilCulture()` avant le
   premier `computeStade()` (layout.js le fait déjà pour les
   pages à sélecteur de parcelle).
   ========================================================= */

/* Descriptions pédagogiques par stade (la table n'en stocke pas) */
const _DESCS = [
  [/prepar/, "Travail du sol, amendement organique et mise en place du système d'irrigation."],
  [/semis/, "Mise en terre des graines ou des jeunes plants en pépinière."],
  [/lev/, "Émergence des plantules, phase très sensible au stress hydrique."],
  [/croissance/, "Développement du feuillage et de la tige, besoins en eau progressifs."],
  [/florais/, "Apparition des fleurs — stade critique, tout stress hydrique impacte la nouaison."],
  [/fructif/, "Grossissement des fruits — besoins en eau maximaux."],
  [/matur/, "Coloration et maturation des fruits — arrosage resserré pour préserver la qualité."],
  [/recolte|récolte/, "Cueillette échelonnée des fruits mûrs."]
];
function _desc(label){
  const l = (label||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');
  const m = _DESCS.find(([re])=>re.test(l));
  return m ? m[1] : '';
}

/* ---------- Repli statique (si la table profil_culture est vide) ---------- */
const _CYCLE_REPLI_BRUT = [
  {label:'Préparation du sol',    dureeJours:7,  seuilBas:50, seuilCible:65},
  {label:'Semis',                 dureeJours:10, seuilBas:55, seuilCible:70},
  {label:'Levée / reprise',       dureeJours:8,  seuilBas:55, seuilCible:70},
  {label:'Croissance végétative', dureeJours:25, seuilBas:52, seuilCible:70},
  {label:'Floraison',             dureeJours:15, seuilBas:58, seuilCible:75},
  {label:'Fructification',        dureeJours:20, seuilBas:60, seuilCible:78},
  {label:'Maturation',            dureeJours:12, seuilBas:50, seuilCible:65},
  {label:'Récolte',               dureeJours:15, seuilBas:45, seuilCible:60}
];
function _normaliserRepli(){
  let debut = 1;
  return _CYCLE_REPLI_BRUT.map(s=>{
    const st = {label:s.label, dureeJours:s.dureeJours, seuilBas:s.seuilBas, seuilCible:s.seuilCible,
                kc:null, desc:_desc(s.label), debut, fin: debut + s.dureeJours - 1};
    debut += s.dureeJours;
    return st;
  });
}

/* Le cycle ACTIF : remplacé par les données réelles dès que
   chargerProfilCulture() a répondu. */
let CYCLE_ACTIF = _normaliserRepli();
let _profilPromesse = null;

/* Conversion lignes API → stades normalisés du frontend */
function _normaliserProfil(rows){
  return rows
    .sort((a,b)=>a.debut_jour-b.debut_jour)
    .map(r=>({
      label: r.stade,
      debut: r.debut_jour,
      fin: r.fin_jour,
      dureeJours: r.fin_jour - r.debut_jour + 1,
      seuilBas: r.seuil_bas,
      seuilCible: r.seuil_cible,
      humiditeMin: r.humidite_min,
      humiditeMax: r.humidite_max,
      kc: r.kc,
      desc: _desc(r.stade)
    }));
}

/* PERFORMANCE : le référentiel change rarement — on le met en cache
   de session (10 min). Appliqué DÈS le chargement du script : les
   pages n'attendent plus un aller-retour réseau avant le 1er rendu. */
const _PROFIL_CACHE_KEY = 'terra_profil_culture';
const _PROFIL_CACHE_TTL = 0; // Toujours récupérer depuis la BD
(function(){
  try{
    const c = JSON.parse(sessionStorage.getItem(_PROFIL_CACHE_KEY));
    if(c && c.rows && c.rows.length && (Date.now() - c.t) < _PROFIL_CACHE_TTL){
      CYCLE_ACTIF = _normaliserProfil(c.rows);
      _profilPromesse = Promise.resolve(CYCLE_ACTIF); // rien à attendre
    }
  }catch(e){}
})();

function chargerProfilCulture(){
  if(!_profilPromesse){
    _profilPromesse = api('/profil-culture', {silent:true}).then(rows=>{
      if(!rows || !rows.length){
        // Table vide : on garde le repli, mais on réessaiera plus tard
        _profilPromesse = null;
        return CYCLE_ACTIF;
      }
      CYCLE_ACTIF = _normaliserProfil(rows);
      try{ sessionStorage.setItem(_PROFIL_CACHE_KEY, JSON.stringify({t: Date.now(), rows})); }catch(e){}
      return CYCLE_ACTIF;
    }).catch(()=>{
      // Échec (API muette, session expirée…) : on NE mémorise pas
      // l'échec — le prochain appel retentera le chargement.
      _profilPromesse = null;
      return CYCLE_ACTIF;
    });
  }
  return _profilPromesse;
}

function dbGetCycle(){ return CYCLE_ACTIF; }

/* Position dans le cycle à partir d'une parcelle du backend.
   Le backend calcule `jour_actuel` (aujourd'hui − date_plantation,
   0 le jour de la plantation) ; les stades de profil_culture
   commencent au jour 1. */
function computeStade(parcelle){
  const cycle = CYCLE_ACTIF;
  let jourActuel = parcelle.jour_actuel;
  if(jourActuel === undefined || jourActuel === null){
    const start = new Date(parcelle.date_plantation || parcelle.datePlantation);
    jourActuel = Math.max(0, Math.floor((new Date() - start)/86400000));
  }
  const j = jourActuel + 1; // jour de culture (1 = jour de plantation)
  let idx = cycle.findIndex(s => j >= s.debut && j <= s.fin);
  if(idx === -1) idx = (j < cycle[0].debut) ? 0 : cycle.length - 1;
  const stade = cycle[idx];
  const jourDansStade = Math.max(0, Math.min(j, stade.fin) - stade.debut);
  const joursRestants = Math.max(0, stade.fin - j);
  const prochain = cycle[idx+1] || null;
  return {jourActuel, idx, stade, jourDansStade, joursRestants, prochain,
          totalJours: cycle[cycle.length-1].fin};
}

/* ---------- Constantes partagées (états métier du backend) ---------- */
const ALERTE_ETAPES = ['en_attente','en_intervention','repare','cloture'];
const ALERTE_LABELS = {en_attente:'En attente', en_intervention:'En intervention', repare:'Réparé', cloture:'Clôturé'};
const CAPTEUR_ETATS  = ['actif','hors_ligne','panne','maintenance'];
const CAPTEUR_LABELS = {actif:'Actif', hors_ligne:'Hors ligne', panne:'En panne', maintenance:'Maintenance'};
/* ---------- Capteurs réels du projet ----------
   Deux capteurs physiques sont déployés :
     - capacitif sol → humidité du sol      {"humidite": 27.6}
     - DHT22         → température + humidité de l'air
                       {"temperature": 27.6, "humidite": 30}
   La base ne stocke QUE des valeurs numériques : les unités
   ci-dessous n'existent que pour l'affichage. */
const CAPTEUR_TYPES  = [
  {value:'humidite_sol', label:'Capacitif — humidité du sol', grandeurs:['humidite_sol']},
  {value:'dht22',        label:'DHT22 — température + humidité air', grandeurs:['temperature','humidite_air']}
];
/* Libellés des anciens types encore présents en base (lecture seule) */
const _TYPES_HERITES = {
  temperature_air:"Température de l'air", humidite_air:"Humidité de l'air", pluie:'Pluviomètre'
};
function capteurTypeLabel(t){
  const f = CAPTEUR_TYPES.find(x=>x.value===t);
  return f ? f.label : (_TYPES_HERITES[t] || t || 'Capteur');
}

/* ---------- Mise en forme des prescriptions du moteur expert ----------
   Format « conseiller agricole » à deux volets. Point UNIQUE de mise
   en forme (utilisé par le dashboard ET la page Recommandations). */
function formatPrescription(p){
  const irrigation = (p.volume_eau || 0) > 0;
  // On retire la signature technique « [Moteur expert] » à l'affichage
  const pourquoi = (p.justification || '').replace(/^\[Moteur expert\]\s*/, '');
  return {
    irrigation,
    pourquoiLabel: irrigation ? 'Pourquoi arroser ?' : 'Pourquoi ?',
    actionLabel: irrigation ? 'Recommandation' : 'Action requise',
    pourquoi,
    action: p.action || '',
    footer: 'Prescription du ' + _dateHeurePrescription(p),
  };
}
/* « 21 juil. 2026 à 08h00 » à partir de cree_le (ou date à défaut) */
function _dateHeurePrescription(p){
  if(p.cree_le){
    const d = new Date(p.cree_le);
    const heure = d.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'}).replace(':', 'h');
    return fmtDate(d) + ' à ' + heure;
  }
  return fmtDate(p.date);
}

/* ---------- Fraîcheur des mesures ----------
   Miroir du backend (moteur_expert.FRAICHEUR_MESURE_H) : au-delà de
   24h sans nouvelle mesure, une donnée n'est plus considérée comme
   fiable — le frontend doit refuser de l'afficher comme "actuelle",
   exactement comme le moteur expert refuse de décider à l'aveugle. */
const FRAICHEUR_MESURE_H = 24;
function mesureEstFraiche(dateMesure){
  if(!dateMesure) return false;
  return (Date.now() - new Date(dateMesure).getTime()) <= FRAICHEUR_MESURE_H * 3600 * 1000;
}

/* Unités d'AFFICHAGE par grandeur (jamais stockées en base) */
const UNITES = {humidite_sol:'%', temperature:'°C', humidite_air:'%', pluie:'mm'};
const GRANDEUR_LABELS = {humidite_sol:'Humidité sol', temperature:'Température', humidite_air:'Humidité air', pluie:'Pluie'};

/* Lecture NORMALISÉE d'une mesure — miroir du backend
   (mesure_service.extraire_grandeurs). Accepte le nouveau format
   multi-grandeurs ET l'ancien {"valeur": x} des historiques.
   Retourne {humidite_sol?, temperature?, humidite_air?, pluie?}. */
function valeursMesure(typeCapteur, donnees){
  if(!donnees || typeof donnees !== 'object') return {};
  const t = (typeCapteur||'').toLowerCase();
  const num = x => (typeof x === 'number' ? x : null);
  const ancien = num(donnees.valeur);
  const v = {};
  if(t.includes('humidite_sol') || t.includes('capacitif')){
    const x = num(donnees.humidite) ?? ancien; if(x !== null) v.humidite_sol = x;
  } else if(t.includes('dht')){
    const vt = num(donnees.temperature); if(vt !== null) v.temperature = vt;
    const vh = num(donnees.humidite);    if(vh !== null) v.humidite_air = vh;
  } else if(t.includes('temperature')){
    const x = num(donnees.temperature) ?? ancien; if(x !== null) v.temperature = x;
  } else if(t.includes('humidite_air')){
    const x = num(donnees.humidite) ?? ancien; if(x !== null) v.humidite_air = x;
  } else if(t.includes('pluie')){
    const x = num(donnees.pluie) ?? ancien; if(x !== null) v.pluie = x;
  } else {
    for(const [k,x] of Object.entries(donnees)) if(typeof x === 'number') v[k] = x;
  }
  return v;
}
/* Affichage « 27.6 °C » : la valeur vient de la base, l'unité de l'UI */
function formatGrandeur(grandeur, valeur){
  if(valeur === null || valeur === undefined) return '—';
  return valeur + ' ' + (UNITES[grandeur] || '');
}
