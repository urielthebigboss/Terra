/* =========================================================
   TERRA — Couche de données simulées (mock DB)
   Toute la "persistance" se fait en localStorage, uniquement
   pour les besoins de la démo frontend (pas de backend).
   Le code est écrit pour être facilement remplacé demain par
   de vrais appels fetch() vers une API REST : chaque fonction
   ci-dessous représente un futur endpoint.
   ========================================================= */

const DB_KEY = "terra_db_v1";

/* ---------- Cycle de développement générique (Tomate) ---------- */
const CYCLE_TOMATE = [
  {
    key: "preparation",
    label: "Préparation du sol",
    dureeJours: 7,
    seuilBas: 50,
    seuilCible: 65,
    desc: "Travail du sol, amendement organique et mise en place du système d'irrigation.",
  },
  {
    key: "semis",
    label: "Semis",
    dureeJours: 10,
    seuilBas: 55,
    seuilCible: 70,
    desc: "Mise en terre des graines ou des jeunes plants en pépinière.",
  },
  {
    key: "levee",
    label: "Levée / reprise",
    dureeJours: 8,
    seuilBas: 55,
    seuilCible: 70,
    desc: "Émergence des plantules, phase très sensible au stress hydrique.",
  },
  {
    key: "croissance",
    label: "Croissance végétative",
    dureeJours: 25,
    seuilBas: 52,
    seuilCible: 70,
    desc: "Développement du feuillage et de la tige, besoins en eau progressifs.",
  },
  {
    key: "floraison",
    label: "Floraison",
    dureeJours: 15,
    seuilBas: 58,
    seuilCible: 75,
    desc: "Apparition des fleurs — stade critique, tout stress hydrique impacte la nouaison.",
  },
  {
    key: "fructification",
    label: "Fructification",
    dureeJours: 20,
    seuilBas: 60,
    seuilCible: 78,
    desc: "Grossissement des fruits — besoins en eau maximaux.",
  },
  {
    key: "maturation",
    label: "Maturation",
    dureeJours: 12,
    seuilBas: 50,
    seuilCible: 65,
    desc: "Coloration et maturation des fruits — arrosage resserré pour préserver la qualité.",
  },
  {
    key: "recolte",
    label: "Récolte",
    dureeJours: 15,
    seuilBas: 45,
    seuilCible: 60,
    desc: "Cueillette échelonnée des fruits mûrs.",
  },
];

function daysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}
function uid(prefix) {
  return prefix + "_" + Math.random().toString(36).slice(2, 9);
}

function seedData() {
  const users = [
    {
      id: "admin1",
      nom: "Admin Système",
      identifiant: "admin",
      motDePasse: "admin2026",
      role: "administrateur",
      creeLe: daysAgo(200),
    },
    {
      id: "u1",
      nom: "Kouassi Yao",
      identifiant: "agriculteur",
      motDePasse: "tomate2026",
      role: "agriculteur",
      parcelles: ["p1", "p2"],
      creeLe: daysAgo(120),
    },
    {
      id: "u2",
      nom: "Aya Brou",
      identifiant: "aya",
      motDePasse: "terra2026",
      role: "agriculteur",
      parcelles: ["p3"],
      creeLe: daysAgo(60),
    },
  ];
  const parcelles = [
    {
      id: "p1",
      nom: "Parcelle A",
      culture: "Tomate",
      superficie: 0.8,
      datePlantation: daysAgo(52),
      etat: "actif",
      proprietaireId: "u1",
    },
    {
      id: "p2",
      nom: "Parcelle B",
      culture: "Tomate",
      superficie: 0.5,
      datePlantation: daysAgo(9),
      etat: "actif",
      proprietaireId: "u1",
    },
    {
      id: "p3",
      nom: "Parcelle C",
      culture: "Tomate",
      superficie: 1.2,
      datePlantation: daysAgo(96),
      etat: "actif",
      proprietaireId: "u2",
    },
  ];
  const capteurs = [
    {
      id: "c1",
      parcelleId: "p1",
      nom: "Sonde humidité du sol",
      type: "Capacitif · 0–40 cm",
      etat: "actif",
      batterie: 82,
      emplacement: "Zone racinaire — rang 3",
      derniereComm: Date.now() - 2 * 60000,
    },
    {
      id: "c2",
      parcelleId: "p1",
      nom: "Capteur DHT22 (air)",
      type: "Température / Humidité",
      etat: "actif",
      batterie: 82,
      emplacement: "Poteau nord",
      derniereComm: Date.now() - 3 * 60000,
    },
    {
      id: "c3",
      parcelleId: "p1",
      nom: "Capteur pluie YL-83",
      type: "Détection de pluie",
      etat: "actif",
      batterie: 76,
      emplacement: "Poteau nord",
      derniereComm: Date.now() - 5 * 60000,
    },
    {
      id: "c4",
      parcelleId: "p1",
      nom: "Passerelle ESP32",
      type: "Wi-Fi · MQTT",
      etat: "actif",
      batterie: 91,
      emplacement: "Abri technique",
      derniereComm: Date.now() - 1 * 60000,
    },
    {
      id: "c5",
      parcelleId: "p2",
      nom: "Sonde humidité du sol",
      type: "Capacitif · 0–40 cm",
      etat: "hors_ligne",
      batterie: 12,
      emplacement: "Zone racinaire — rang 1",
      derniereComm: Date.now() - 9 * 3600000,
    },
    {
      id: "c6",
      parcelleId: "p2",
      nom: "Capteur DHT22 (air)",
      type: "Température / Humidité",
      etat: "actif",
      batterie: 64,
      emplacement: "Poteau sud",
      derniereComm: Date.now() - 4 * 60000,
    },
    {
      id: "c7",
      parcelleId: "p3",
      nom: "Sonde humidité du sol",
      type: "Capacitif · 0–40 cm",
      etat: "panne",
      batterie: 8,
      emplacement: "Zone racinaire — rang 2",
      derniereComm: Date.now() - 30 * 3600000,
    },
    {
      id: "c8",
      parcelleId: "p3",
      nom: "Capteur DHT22 (air)",
      type: "Température / Humidité",
      etat: "actif",
      batterie: 58,
      emplacement: "Poteau est",
      derniereComm: Date.now() - 6 * 60000,
    },
    {
      id: "c9",
      parcelleId: "p3",
      nom: "Passerelle ESP32",
      type: "Wi-Fi · MQTT",
      etat: "actif",
      batterie: 70,
      emplacement: "Abri technique",
      derniereComm: Date.now() - 2 * 60000,
    },
  ];
  const alertes = [
    {
      id: "al1",
      capteurId: "c5",
      parcelleId: "p2",
      utilisateurId: "u1",
      texte: "Sonde humidité du sol hors ligne depuis plusieurs heures",
      etat: "en_attente",
      date: Date.now() - 9 * 3600000,
    },
    {
      id: "al2",
      capteurId: "c7",
      parcelleId: "p3",
      utilisateurId: "u2",
      texte: "Sonde humidité du sol en panne — batterie critique (8%)",
      etat: "en_intervention",
      date: Date.now() - 26 * 3600000,
    },
    {
      id: "al3",
      capteurId: "c1",
      parcelleId: "p1",
      utilisateurId: "u1",
      texte: "Micro-coupure réseau détectée puis rétablie",
      etat: "cloture",
      date: Date.now() - 4 * 86400000,
    },
  ];
  const prescriptions = [
    {
      id: "pr1",
      parcelleId: "p1",
      date: daysAgo(0),
      action: "Irriguer 18 L/m²",
      justification:
        "Humidité du sol à 54% (< seuil bas 58% en floraison) et aucune pluie prévue sous 24h.",
      volumeEau: 18,
      priorite: "haute",
      etat: "a_faire",
    },
    {
      id: "pr2",
      parcelleId: "p1",
      date: daysAgo(0),
      action: "Surveiller demain matin",
      justification:
        "Température élevée annoncée (34°C) : vérifier l'humidité avant midi.",
      volumeEau: 0,
      priorite: "moyenne",
      etat: "a_faire",
    },
    {
      id: "pr3",
      parcelleId: "p2",
      date: daysAgo(0),
      action: "Irriguer 10 L/m²",
      justification:
        "Jeune plant en levée, maintenir une humidité stable autour de 70%.",
      volumeEau: 10,
      priorite: "moyenne",
      etat: "a_faire",
    },
    {
      id: "pr4",
      parcelleId: "p3",
      date: daysAgo(1),
      action: "Irrigation reportée",
      justification: "Pluie prévue à 70% dans les 6 prochaines heures.",
      volumeEau: 0,
      priorite: "basse",
      etat: "faite",
      dateFaite: daysAgo(1),
    },
    {
      id: "pr5",
      parcelleId: "p1",
      date: daysAgo(2),
      action: "Irriguer 16 L/m²",
      justification: "Humidité sous le seuil bas pendant la fructification.",
      volumeEau: 16,
      priorite: "haute",
      etat: "faite",
      dateFaite: daysAgo(2),
    },
    {
      id: "pr6",
      parcelleId: "p1",
      date: daysAgo(3),
      action: "Irriguer 15 L/m²",
      justification: "Sol sec après une journée chaude (33°C).",
      volumeEau: 15,
      priorite: "haute",
      etat: "faite",
      dateFaite: daysAgo(3),
    },
  ];
  const previsions = [
    {
      jour: "Aujourd'hui",
      temps: "ensoleille",
      tempMin: 23,
      tempMax: 33,
      pluiePrevue: false,
      probabilite: 10,
    },
    {
      jour: "Demain",
      temps: "ensoleille",
      tempMin: 24,
      tempMax: 34,
      pluiePrevue: false,
      probabilite: 15,
    },
    {
      jour: "J+2",
      temps: "nuageux",
      tempMin: 22,
      tempMax: 30,
      pluiePrevue: true,
      probabilite: 55,
    },
    {
      jour: "J+3",
      temps: "pluie",
      tempMin: 21,
      tempMax: 27,
      pluiePrevue: true,
      probabilite: 80,
    },
    {
      jour: "J+4",
      temps: "nuageux",
      tempMin: 22,
      tempMax: 29,
      pluiePrevue: false,
      probabilite: 30,
    },
  ];
  /* Historique quotidien (14 jours) par parcelle, pour graphiques + tableau */
  const historique = [];
  ["p1", "p2", "p3"].forEach((pid) => {
    for (let i = 13; i >= 0; i--) {
      historique.push({
        id: uid("h"),
        parcelleId: pid,
        date: daysAgo(i),
        eauL: +(6 + Math.random() * 14).toFixed(1),
        irrigations: 1 + Math.floor(Math.random() * 3),
        humiditeMoy: Math.round(56 + Math.random() * 18),
        tempMoy: Math.round(26 + Math.random() * 8),
      });
    }
  });
  return {
    users,
    parcelles,
    capteurs,
    alertes,
    prescriptions,
    previsions,
    historique,
    cycle: CYCLE_TOMATE,
  };
}

function getDB() {
  let raw = localStorage.getItem(DB_KEY);
  if (!raw) {
    const seed = seedData();
    localStorage.setItem(DB_KEY, JSON.stringify(seed));
    return seed;
  }
  try {
    return JSON.parse(raw);
  } catch (e) {
    const seed = seedData();
    localStorage.setItem(DB_KEY, JSON.stringify(seed));
    return seed;
  }
}
function saveDB(db) {
  localStorage.setItem(DB_KEY, JSON.stringify(db));
}
function resetDB() {
  localStorage.removeItem(DB_KEY);
  return getDB();
}

/* ---------- Utilisateurs ---------- */
function dbGetUsers() {
  return getDB().users;
}
function dbGetUser(id) {
  return getDB().users.find((u) => u.id === id);
}
function dbFindByIdentifiant(identifiant) {
  return getDB().users.find((u) => u.identifiant === identifiant);
}
function dbAddUser(user) {
  const db = getDB();
  user.id = uid("u");
  user.creeLe = new Date().toISOString().slice(0, 10);
  user.parcelles = user.parcelles || [];
  db.users.push(user);
  saveDB(db);
  return user;
}
function dbUpdateUser(id, patch) {
  const db = getDB();
  const u = db.users.find((x) => x.id === id);
  if (!u) return null;
  Object.assign(u, patch);
  saveDB(db);
  return u;
}
function dbDeleteUser(id) {
  const db = getDB();
  db.users = db.users.filter((u) => u.id !== id);
  saveDB(db);
}

/* ---------- Parcelles ---------- */
function dbGetParcelles() {
  return getDB().parcelles;
}
function dbGetParcelle(id) {
  return getDB().parcelles.find((p) => p.id === id);
}
function dbGetParcellesForUser(userId) {
  const db = getDB();
  const u = db.users.find((x) => x.id === userId);
  if (!u) return [];
  return db.parcelles.filter((p) => (u.parcelles || []).includes(p.id));
}
function dbAddParcelle(p) {
  const db = getDB();
  p.id = uid("p");
  p.etat = p.etat || "actif";
  db.parcelles.push(p);
  saveDB(db);
  return p;
}
function dbUpdateParcelle(id, patch) {
  const db = getDB();
  const p = db.parcelles.find((x) => x.id === id);
  if (!p) return null;
  Object.assign(p, patch);
  saveDB(db);
  return p;
}
function dbDeleteParcelle(id) {
  const db = getDB();
  db.parcelles = db.parcelles.filter((p) => p.id !== id);
  db.capteurs = db.capteurs.filter((c) => c.parcelleId !== id);
  saveDB(db);
}

/* ---------- Capteurs ---------- */
function dbGetCapteurs() {
  return getDB().capteurs;
}
function dbGetCapteursForParcelle(parcelleId) {
  return getDB().capteurs.filter((c) => c.parcelleId === parcelleId);
}
function dbAddCapteur(c) {
  const db = getDB();
  c.id = uid("c");
  c.derniereComm = Date.now();
  db.capteurs.push(c);
  saveDB(db);
  return c;
}
function dbUpdateCapteur(id, patch) {
  const db = getDB();
  const c = db.capteurs.find((x) => x.id === id);
  if (!c) return null;
  Object.assign(c, patch);
  saveDB(db);
  return c;
}
function dbDeleteCapteur(id) {
  const db = getDB();
  db.capteurs = db.capteurs.filter((c) => c.id !== id);
  saveDB(db);
}

/* ---------- Alertes ---------- */
function dbGetAlertes() {
  return getDB().alertes.sort((a, b) => b.date - a.date);
}
function dbGetAlertesForUser(userId) {
  return dbGetAlertes().filter((a) => a.utilisateurId === userId);
}
function dbAddAlerte(a) {
  const db = getDB();
  a.id = uid("al");
  a.date = Date.now();
  a.etat = "en_attente";
  db.alertes.push(a);
  saveDB(db);
  return a;
}
function dbUpdateAlerte(id, patch) {
  const db = getDB();
  const a = db.alertes.find((x) => x.id === id);
  if (!a) return null;
  Object.assign(a, patch);
  saveDB(db);
  return a;
}
const ALERTE_ETAPES = ["en_attente", "en_intervention", "repare", "cloture"];
const ALERTE_LABELS = {
  en_attente: "En attente",
  en_intervention: "En intervention",
  repare: "Réparé",
  cloture: "Clôturé",
};

/* ---------- Prescriptions / recommandations ---------- */
function dbGetPrescriptions() {
  return getDB().prescriptions.sort(
    (a, b) => new Date(b.date) - new Date(a.date),
  );
}
function dbGetPrescriptionsForParcelle(pid) {
  return dbGetPrescriptions().filter((p) => p.parcelleId === pid);
}
function dbGetPrescriptionsForUser(userId) {
  const pids = dbGetParcellesForUser(userId).map((p) => p.id);
  return dbGetPrescriptions().filter((p) => pids.includes(p.parcelleId));
}
function dbMarkPrescriptionDone(id) {
  const db = getDB();
  const p = db.prescriptions.find((x) => x.id === id);
  if (!p) return null;
  p.etat = "faite";
  p.dateFaite = new Date().toISOString().slice(0, 10);
  saveDB(db);
  db.historique.push({
    id: uid("h"),
    parcelleId: p.parcelleId,
    date: p.dateFaite,
    eauL: p.volumeEau || 0,
    irrigations: p.volumeEau > 0 ? 1 : 0,
    humiditeMoy: null,
    tempMoy: null,
    type: "irrigation",
    recommandationId: p.id,
  });
  saveDB(db);
  return p;
}

/* ---------- Historique ---------- */
function dbGetHistoriqueForParcelle(pid) {
  return getDB()
    .historique.filter((h) => h.parcelleId === pid)
    .sort((a, b) => new Date(b.date) - new Date(a.date));
}
function dbGetHistoriqueForUser(userId) {
  const pids = dbGetParcellesForUser(userId).map((p) => p.id);
  return getDB()
    .historique.filter((h) => pids.includes(h.parcelleId))
    .sort((a, b) => new Date(b.date) - new Date(a.date));
}

/* ---------- Prévisions météo ---------- */
function dbGetPrevisions() {
  return getDB().previsions;
}

/* ---------- Cycle de culture ---------- */
function dbGetCycle() {
  return getDB().cycle;
}
function computeStade(parcelle) {
  const cycle = dbGetCycle();
  const start = new Date(parcelle.datePlantation);
  const today = new Date();
  const jourActuel = Math.max(0, Math.floor((today - start) / 86400000));
  let cum = 0,
    idx = 0;
  for (let i = 0; i < cycle.length; i++) {
    const next = cum + cycle[i].dureeJours;
    if (jourActuel < next || i === cycle.length - 1) {
      idx = i;
      break;
    }
    cum = next;
  }
  const stade = cycle[idx];
  const jourDansStade = jourActuel - cum;
  const joursRestants = Math.max(0, stade.dureeJours - jourDansStade);
  const prochain = cycle[idx + 1] || null;
  return {
    jourActuel,
    idx,
    stade,
    jourDansStade,
    joursRestants,
    prochain,
    totalJours: cycle.reduce((a, s) => a + s.dureeJours, 0),
  };
}

/* ---------- Mesures simulées en temps réel (par parcelle) ---------- */
const _liveState = {};
function getLiveMesure(parcelleId) {
  if (!_liveState[parcelleId]) {
    const info = computeStade(dbGetParcelle(parcelleId));
    _liveState[parcelleId] = {
      moist: info.stade.seuilBas + 8 + Math.random() * 10,
      temp: 28 + Math.random() * 5,
      air: 55 + Math.random() * 20,
      water: 0,
    };
  }
  return _liveState[parcelleId];
}
function tickLiveMesure(parcelleId, opts) {
  const s = getLiveMesure(parcelleId);
  const info = computeStade(dbGetParcelle(parcelleId));
  const rainSoon = opts && opts.rainSoon;
  if (!rainSoon && s.moist < info.stade.seuilBas) {
    s.moist += 1.6;
    s.water += 0.25;
  } else {
    s.moist -= 0.35 + (s.temp - 28) * 0.04;
  }
  s.temp += (Math.random() - 0.5) * 0.6;
  s.temp = Math.max(22, Math.min(40, s.temp));
  s.air += (Math.random() - 0.5) * 1.6;
  s.air = Math.max(35, Math.min(90, s.air));
  s.moist = Math.max(15, Math.min(95, s.moist));
  return s;
}
