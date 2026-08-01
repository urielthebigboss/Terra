/* =========================================================
   TERRA — Authentification + client API (backend réel)
   ---------------------------------------------------------
   Ce fichier remplace l'ancienne démo localStorage : toutes
   les données viennent désormais du backend FastAPI
   (http://localhost:8000) branché sur Supabase.

   - login(email, motDePasse)  → POST /auth/login (Supabase Auth)
   - api(chemin, options)      → fetch authentifié (Bearer JWT)
   - requireRole(role)         → garde d'accès des pages
   La session (token + profil + rôle) est conservée dans
   localStorage pour survivre au rechargement de page.
   ========================================================= */

//const TERRA_API = 'http://localhost:8000/api/v1';
const TERRA_API = "https://terra-9fg4.onrender.com/api/v1";
const TERRA_WS = "wss://terra-9fg4.onrender.com/ws";
const SESSION_KEY = "terra_session_v2";

/* ---------- Session ---------- */
function getSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY));
  } catch (e) {
    return null;
  }
}
function setSession(s) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(s));
}
function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

/* Profil de l'utilisateur connecté : {id, id_uuid, nom, role} */
function getCurrentUser() {
  const s = getSession();
  if (!s || !s.profil) return null;
  return Object.assign({ role: s.role }, s.profil);
}

/* ---------- Connexion / déconnexion ---------- */
async function login(email, motDePasse) {
  let r;
  try {
    r = await fetch(TERRA_API + "/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, mot_de_passe: motDePasse }),
    });
  } catch (e) {
    return {
      ok: false,
      msg: "Serveur en cours de démarrage ou injoignable. Veuillez réessayer dans quelques secondes (mise en veille).",
    };
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok)
    return {
      ok: false,
      msg: data.detail || "Email ou mot de passe incorrect.",
    };
  setSession({
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    role: data.role,
    profil: data.profil,
  });
  return { ok: true, role: data.role, user: data.profil };
}

function logout() {
  // L'espace administrateur possède sa propre page de connexion.
  const inAdmin = location.pathname.includes("/admin/");
  clearSession();
  location.href = inAdmin ? "login.html" : _rootPath() + "index.html";
}
function _rootPath() {
  return location.pathname.includes("/pages/") ||
    location.pathname.includes("/admin/")
    ? "../"
    : "";
}

/* À appeler en haut de chaque page protégée : vérifie le rôle
   stocké (le backend re-vérifie de toute façon chaque requête). */
function requireRole(role) {
  const u = getCurrentUser();
  if (!u || u.role !== role) {
    location.href =
      role === "administrateur" ? "login.html" : _rootPath() + "index.html";
    return null;
  }
  return u;
}

/* ---------- Renouvellement de session (connexion permanente) ----------
   Quand l'access_token expire (401), on l'échange contre un neuf via
   le refresh_token — l'utilisateur n'est JAMAIS déconnecté tant que
   sa session Supabase est renouvelable. « Single-flight » : si dix
   requêtes échouent en même temps, UN seul refresh part. */
let _refreshEnCours = null;
async function _rafraichirSession() {
  if (_refreshEnCours) return _refreshEnCours;
  _refreshEnCours = (async () => {
    const s = getSession();
    if (!s || !s.refresh_token) return false;
    try {
      const r = await fetch(TERRA_API + "/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: s.refresh_token }),
      });
      if (!r.ok) return false;
      const d = await r.json();
      setSession({
        access_token: d.access_token,
        refresh_token: d.refresh_token,
        role: d.role,
        profil: d.profil,
      });
      return true;
    } catch (e) {
      return false;
    }
  })();
  try {
    return await _refreshEnCours;
  } finally {
    _refreshEnCours = null;
  }
}

/* ---------- Client API ----------
   api('/parcelles')                       → GET
   api('/parcelles', {method:'POST', body:{...}})
   Options : {method, body, silent} — silent = pas de toast d'erreur.

   Robustesse intégrée :
   - 401  → refresh automatique de la session puis NOUVELLE tentative
            (déconnexion seulement si le refresh échoue) ;
   - GET en erreur réseau ou 5xx → UN retry automatique après 400 ms
            (les micro-coupures ne demandent plus de recharger la page). */
async function api(path, opts) {
  opts = opts || {};
  const methode = opts.method || "GET";
  const _requete = () => {
    const s = getSession();
    return fetch(TERRA_API + path, {
      method: methode,
      headers: Object.assign(
        { "Content-Type": "application/json" },
        s ? { Authorization: "Bearer " + s.access_token } : {},
      ),
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
  };

  let r;
  try {
    r = await _requete();
  } catch (e) {
    // Erreur réseau : les GET (idempotents) ont droit à une 2e chance
    if (methode === "GET" && !opts._retente) {
      await new Promise((res) => setTimeout(res, 400));
      return api(path, Object.assign({}, opts, { _retente: true }));
    }
    const err = new Error(
      "Serveur en cours de démarrage ou injoignable. Veuillez réessayer dans quelques secondes.",
    );
    if (!opts.silent && typeof toast === "function") toast(err.message, "err");
    throw err;
  }

  // Token expiré : on renouvelle la session PUIS on rejoue la requête.
  if (r.status === 401 && getSession() && !opts._apresRefresh) {
    const ok = await _rafraichirSession();
    if (ok) return api(path, Object.assign({}, opts, { _apresRefresh: true }));
    logout(); // refresh impossible → vraie fin de session
    throw new Error("Session expirée");
  }

  // 5xx transitoire (ex. micro-coupure Supabase) : retry des GET
  if (r.status >= 500 && methode === "GET" && !opts._retente) {
    await new Promise((res) => setTimeout(res, 400));
    return api(path, Object.assign({}, opts, { _retente: true }));
  }

  if (!r.ok) {
    let detail = "Erreur " + r.status;
    try {
      const j = await r.json();
      if (j.detail) detail = j.detail;
    } catch (e) {}
    const err = new Error(detail);
    if (!opts.silent && typeof toast === "function") toast(detail, "err");
    throw err;
  }
  if (r.status === 204) return null;
  return r.json();
}
