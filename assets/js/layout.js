/* =========================================================
   TERRA — Mise en page partagée + bibliothèque d'icônes Terra
   ---------------------------------------------------------
   ICÔNES PROPRIÉTAIRES : aucune bibliothèque externe. Chaque
   icône est dessinée main sur une grille 24px, trait 2px,
   extrémités rondes — un seul langage graphique inspiré du
   vivant : graine, feuille, tomate, goutte, racine, soleil…

   Usage dans le HTML statique :  <i data-ti="tomate"></i>
   (hydraté en SVG par Layout.hydrateIcons, appelé par mount)
   Usage en JS :                  ticon('feuille')
   ========================================================= */

const ICONS = {
  /* --- Navigation & structure --- */
  champ:
    '<path d="M3 20c2-1 4-1.5 9-1.5s7 .5 9 1.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M5 16c1.5-.7 3-1 7-1s5.5.3 7 1" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity=".55"/><path d="M12 15V9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M12 11c-3 0-4.5-2-5-5 3 0 4.7 1.6 5 4M12 9c2.6-.2 4-1.8 4.4-4.2-2.6.2-4 1.7-4.4 3.8" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',
  parcelle:
    '<path d="M12 21s-7-5.2-7-10a7 7 0 0 1 14 0c0 4.8-7 10-7 10Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 8v4M12 12c-1.6 0-2.6-1-2.9-2.7 1.6 0 2.6.9 2.9 2.2m0 .5c1.4-.1 2.3-1 2.5-2.4-1.4.1-2.3.9-2.5 2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  feuille:
    '<path d="M5 21c0-9 5-16 15-17-1 10-8 15-17 15" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M5 21c3-3 6-6 8-11" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  capteur:
    '<path d="M12 13.5V21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="10" r="2.6" stroke="currentColor" stroke-width="2"/><path d="M7.5 5.5a6.4 6.4 0 0 1 9 0M5.2 3.2a9.6 9.6 0 0 1 13.6 0" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M9 21h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  goutte:
    '<path d="M12 3s6 7 6 11a6 6 0 1 1-12 0c0-4 6-11 6-11Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M9.5 14a2.6 2.6 0 0 0 2 2.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  historique:
    '<path d="M3 12a9 9 0 1 0 3-6.7M3 5v3h3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 8v4l3 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  profil:
    '<circle cx="12" cy="8" r="3.6" stroke="currentColor" stroke-width="2"/><path d="M4.5 20c1.5-4 5-5.5 7.5-5.5s6 1.5 7.5 5.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  equipe:
    '<circle cx="9" cy="8" r="3.2" stroke="currentColor" stroke-width="2"/><path d="M2.5 19c1.2-3.4 4-4.8 6.5-4.8s5.3 1.4 6.5 4.8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="17" cy="8.5" r="2.6" stroke="currentColor" stroke-width="2"/><path d="M15.5 14.3c2.2.2 4 1.6 5 4.7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  cloche:
    '<path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M10 19a2 2 0 0 0 4 0" stroke="currentColor" stroke-width="2"/>',
  sortie:
    '<path d="M15 12H4m0 0 3.5-3.5M4 12l3.5 3.5M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
  theme:
    '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',

  /* --- Univers Terra : le vivant --- */
  tomate:
    '<path d="M12 8.5c4.4 0 7.5 2.6 7.5 6a7.5 6.9 0 0 1-15 0c0-3.4 3.1-6 7.5-6Z" stroke="currentColor" stroke-width="2"/><path d="M12 8.5V6M12 6c-1.8.2-3-.4-3.8-1.8 1.6-.5 3 0 3.8 1.3M12 6c1.8.2 3-.4 3.8-1.8-1.6-.5-3 0-3.8 1.3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
  graine:
    '<path d="M17.5 6.5C15 4 10 4 7.5 6.5s-2.5 7.5 0 10 7.5 2.5 10 0c1.8-1.8 2.3-4.6 1.4-6.9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M12 12c1.5-1.5 3.5-2 5.5-1.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  racine:
    '<path d="M12 3v8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M12 3c-1.4.4-2.6 1.5-3 3 1.6 0 2.7-.9 3-2.4M12 5c1.4.1 2.5-.5 3.2-1.8-1.4-.3-2.6.2-3.2 1.4" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M12 11c0 3-2 4-4 5.5M12 11c0 3 2 4 4 5.5M12 11v7.5M8 16.5 6.5 19M16 16.5 17.5 19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  soleil:
    '<circle cx="12" cy="12" r="4.5" stroke="currentColor" stroke-width="2"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5 5l1.4 1.4M17.6 17.6 19 19M19 5l-1.4 1.4M6.4 17.6 5 19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  nuage:
    '<path d="M7 17a4 4 0 0 1 0-8 5 5 0 0 1 9.6-1.3A3.8 3.8 0 0 1 17 17H7Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
  pluie:
    '<path d="M7 15a4 4 0 0 1 0-8 5 5 0 0 1 9.6-1.3A3.8 3.8 0 0 1 17 15H7Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M8.5 18l-1 2.5M12.5 18l-1 2.5M16.5 18l-1 2.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  thermo:
    '<path d="M14 14V5a2 2 0 1 0-4 0v9a4 4 0 1 0 4 0Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="12" cy="17" r="1.4" fill="currentColor"/>',
  air: '<path d="M3 8h9.5a2.5 2.5 0 1 0-2.4-3.2M3 12h14.5a2.5 2.5 0 1 1-2.4 3.2M3 16h7.5a2.2 2.2 0 1 1-2.1 2.9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  cuve: '<path d="M4 17h16M6 17V9l6-4 6 4v8" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 10.5s2 2.3 2 3.6a2 2 0 1 1-4 0c0-1.3 2-3.6 2-3.6Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>',
  ia: '<rect x="6" y="6" width="12" height="12" rx="3.5" stroke="currentColor" stroke-width="2"/><path d="M12 2.5V6M12 18v3.5M2.5 12H6M18 12h3.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M10 12c.5-1.6 1.4-2.4 2-2.5-.1 1-.6 1.9-2 2.5Zm0 0c-.1 1.2.4 2 1.2 2.5.4-.9.2-1.9-1.2-2.5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>',
  courbe:
    '<path d="M3.5 20.5V13c2.5 0 3.5 1.5 4.5 3.5M3.5 20.5H21M8 16.5c1.5-4 3-8.5 5.5-11 .5 3 .5 6.5 3.5 8 1.5.8 3 .8 4 .7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
  badge:
    '<circle cx="12" cy="9.5" r="5.5" stroke="currentColor" stroke-width="2"/><path d="M8.8 14.2 7.5 21l4.5-2.4L16.5 21l-1.3-6.8" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 7.2v2.3l1.7 1" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
  eclair:
    '<path d="M13 2 5 13.5h5.5L10 22l8.5-11.5H13L13 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
  check:
    '<path d="M4.5 12.5 10 18 19.5 6.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
  alerte:
    '<path d="M12 3 2 20h20L12 3Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v4M12 17v.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  fleche:
    '<path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
  plus: '<path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>',
  telecharger:
    '<path d="M12 3v11M8 10l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  cle: '<circle cx="8" cy="15" r="4.5" stroke="currentColor" stroke-width="2"/><path d="M11.5 11.5 20 3M16 7l3 3M13.5 9.5l2 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  calendrier:
    '<rect x="3.5" y="5" width="17" height="16" rx="3" stroke="currentColor" stroke-width="2"/><path d="M3.5 10h17M8 3v4M16 3v4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M8 14c1.5 0 2.3-.8 2.5-2.3-1.5 0-2.3.8-2.5 2.3Z" stroke="currentColor" stroke-width="1.5"/>',

  /* alias rétro-compatibles (anciens noms v1) */
  grid: null,
  map: null,
  leaf: null,
  sensor: null,
  drop: null,
  clock: null,
  user: null,
  users: null,
  bell: null,
  logout: null,
  chart: null,
};
/* Les anciens noms pointent vers les nouvelles icônes */
ICONS.grid = ICONS.champ;
ICONS.map = ICONS.parcelle;
ICONS.leaf = ICONS.feuille;
ICONS.sensor = ICONS.capteur;
ICONS.drop = ICONS.goutte;
ICONS.clock = ICONS.historique;
ICONS.user = ICONS.profil;
ICONS.users = ICONS.equipe;
ICONS.bell = ICONS.cloche;
ICONS.logout = ICONS.sortie;
ICONS.chart = ICONS.courbe;
ICONS.gear = ICONS.cle;

/* Icône Terra prête à insérer : ticon('tomate','ti-lg') */
function ticon(name, cls) {
  return (
    '<svg class="ti' +
    (cls ? " " + cls : "") +
    '" viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    (ICONS[name] || "") +
    "</svg>"
  );
}

/* Le logo TERRA : goutte-feuille (identité de marque) */
const TERRA_LOGO =
  '<svg class="logo" viewBox="0 0 48 48" fill="none" aria-hidden="true">' +
  '<path d="M24 4C24 4 9 20 9 31a15 15 0 0 0 30 0C39 20 24 4 24 4Z" fill="#1bbd7c"/>' +
  '<path d="M24 14c4.5 4.8 8 10.4 8 15" stroke="#0a2e22" stroke-width="2.4" stroke-linecap="round" opacity=".5"/>' +
  '<path d="M24 38a7 7 0 0 1-7-7" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>' +
  "</svg>";

const NAV_USER = [
  {
    key: "dashboard",
    label: "Tableau de bord",
    href: "dashboard.html",
    icon: "champ",
  },
  {
    key: "parcelles",
    label: "Mes parcelles",
    href: "parcelles.html",
    icon: "parcelle",
  },
  {
    key: "cycle",
    label: "Cycle de culture",
    href: "cycle-culture.html",
    icon: "feuille",
  },
  {
    key: "capteurs",
    label: "Capteurs IoT",
    href: "capteurs.html",
    icon: "capteur",
  },
  {
    key: "recommandations",
    label: "Recommandations",
    href: "recommandations.html",
    icon: "goutte",
  },
  {
    key: "historique",
    label: "Historique",
    href: "historique.html",
    icon: "historique",
  },
  { key: "profil", label: "Mon profil", href: "profil.html", icon: "profil" },
];
const NAV_ADMIN = [
  {
    key: "dashboard",
    label: "Vue d'ensemble",
    href: "dashboard.html",
    icon: "champ",
  },
  {
    key: "utilisateurs",
    label: "Utilisateurs",
    href: "utilisateurs.html",
    icon: "equipe",
  },
  {
    key: "parcelles",
    label: "Parcelles",
    href: "parcelles.html",
    icon: "parcelle",
  },
  {
    key: "capteurs",
    label: "Capteurs",
    href: "capteurs.html",
    icon: "capteur",
  },
  {
    key: "alertes",
    label: "Alertes",
    href: "alertes.html",
    icon: "cloche",
    badge: true,
  },
];

const Layout = {
  user: null,
  mount(opts) {
    const user = requireRole(opts.role);
    if (!user) return null;
    this.user = user;
    this._buildRail(opts, user);
    this._buildTopbar(opts, user);
    this._wireGlobal(opts, user);
    this.hydrateIcons();
    if (opts.parcelleSelector) this._wireParcelleSelector(opts, user);
    return user;
  },
  /* Convertit tous les <i data-ti="nom"> du document en icônes Terra */
  hydrateIcons(root) {
    (root || document).querySelectorAll("[data-ti]").forEach((el) => {
      const name = el.dataset.ti;
      if (ICONS[name]) {
        el.outerHTML = ticon(name, el.className);
      }
    });
  },
  _buildRail(opts, user) {
    const isAdmin = opts.role === "administrateur";
    const nav = isAdmin ? NAV_ADMIN : NAV_USER;
    let html =
      '<button class="rail-close" onclick="Layout.closeMobile()" aria-label="Fermer le menu">✕</button>';
    html +=
      '<div class="rail-brand">' +
      TERRA_LOGO +
      "<span>TERRA</span></div>";

    nav.forEach((item) => {
      // Si l'item est "Mes parcelles", on le remplace par le dropdown
      if (item.key === "parcelles" && opts.parcelleSelector) {
        html +=
          '<div class="parc-select" id="parcSelect">' +
          '<button type="button" class="parc-trigger navlink" id="parcTrigger" aria-haspopup="listbox" aria-expanded="false">' +
          ticon("parcelle") +
          "<span>Mes parcelles</span>" +
          '<svg class="parc-chevron" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>' +
          "</button>" +
          '<div class="parc-menu-wrapper" id="parcMenuWrapper">' +
          '<ul class="parc-menu" id="parcMenu" role="listbox" aria-label="Parcelles"></ul>' +
          '<div class="parc-menu-footer"><a href="parcelles.html">Gérer mes parcelles</a></div>' +
          '</div>' +
          "</div>";
        return; // on saute le navlink normal
      }

      // Si l'item est "profil", on crée le menu déroulant
      if (item.key === "profil") {
        html +=
          '<div class="parc-select" id="profSelect">' +
          '<button type="button" class="parc-trigger navlink" id="profTrigger" aria-haspopup="true" aria-expanded="false">' +
          ticon(item.icon) +
          "<span>" + item.label + "</span>" +
          '<svg class="parc-chevron" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>' +
          "</button>" +
          '<div class="parc-menu-wrapper" id="profMenuWrapper" style="min-width: 200px;">' +
          '<ul class="parc-menu" style="padding: 6px;">' +
          '<li role="menuitem" class="parc-row" onclick="window.location.href=\'' + item.href + '\'">' +
          '<div class="parc-info"><span class="parc-name" style="font-weight: 600;">Mon compte</span></div>' +
          '</li>' +
          '<li role="menuitem" class="parc-row" onclick="logout(); return false;">' +
          '<div class="parc-info"><span class="parc-name" style="color: var(--red); font-weight: 600;">Déconnexion</span></div>' +
          '</li>' +
          '</ul>' +
          '</div>' +
          "</div>";
        return;
      }

      const active = item.key === opts.active ? " active" : "";
      const badge = item.badge
        ? '<span class="navbadge hidden" id="navAlertBadge"></span>'
        : "";
      html +=
        '<a class="navlink' +
        active +
        '" href="' +
        item.href +
        '">' +
        ticon(item.icon) +
        "<span>" +
        item.label +
        "</span>" +
        badge +
        "</a>";
    });

    if (isAdmin) {
      html += '<div class="spacer"></div>';
      html +=
        '<a class="navlink" href="../index.html" onclick="logout();return false;">' +
        ticon("sortie") +
        "<span>Déconnexion</span></a>";
    }

    const mount = document.getElementById("railMount");
    mount.className = "rail";
    mount.innerHTML = html;
    if (isAdmin) this.refreshAlertBadge();
  },
  /* Badge « alertes à traiter » du rail admin — rechargeable après action */
  async refreshAlertBadge() {
    try {
      const alertes = await api("/alertes", { silent: true });
      const n = alertes.filter(
        (a) => a.etat === "en_attente" || a.etat === "en_intervention",
      ).length;
      const b = document.getElementById("navAlertBadge");
      if (!b) return;
      b.textContent = n > 9 ? "9+" : n;
      b.classList.toggle("hidden", n === 0);
    } catch (e) {
      /* silencieux : le badge n'est pas critique */
    }
  },
  _buildTopbar(opts, user) {
    const html =
      '<button class="hamburger" onclick="Layout.openMobile()" aria-label="Ouvrir le menu" aria-expanded="false">' +
      ticon("menu") +
      '</button>' +
      "<div><h1>" +
      (opts.title || "") +
      '</h1><div class="greet">' +
      (opts.greet || "") +
      "</div></div>" +
      '<div class="tb-right"></div>';
    const mount = document.getElementById("topbarMount");
    mount.className = "topbar";
    mount.innerHTML = html;
  },
  _wireGlobal() {
    let bd = document.getElementById("railBackdrop");
    if (!bd) {
      bd = document.createElement("div");
      bd.id = "railBackdrop";
      bd.className = "rail-backdrop";
      document.body.appendChild(bd);
    }
    bd.onclick = () => Layout.closeMobile();

    // Gestion du menu Profil
    const profSelect = document.getElementById("profSelect");
    const profTrigger = document.getElementById("profTrigger");
    if (profTrigger && profSelect) {
      profTrigger.addEventListener("click", (e) => {
        e.stopPropagation();
        const isOpen = profSelect.classList.contains("open");
        document.querySelectorAll('.parc-select').forEach(el => el.classList.remove('open'));
        if (!isOpen) {
          profSelect.classList.add("open");
          profTrigger.setAttribute("aria-expanded", "true");
        } else {
          profTrigger.setAttribute("aria-expanded", "false");
        }
      });
      document.addEventListener("click", (e) => {
        if (!profSelect.contains(e.target)) {
          profSelect.classList.remove("open");
          profTrigger.setAttribute("aria-expanded", "false");
        }
      });
    }
  },
  openMobile() {
    document.getElementById("railMount").classList.add("open");
    document.getElementById("railBackdrop").classList.add("show");
  },
  closeMobile() {
    document.getElementById("railMount").classList.remove("open");
    document.getElementById("railBackdrop").classList.remove("show");
  },
  /* Sélecteur de parcelles : chargé depuis l'API réelle.
     Layout.parcelles garde la liste en cache pour les pages. */
  parcelles: [],
  async _wireParcelleSelector(opts, user) {
    const root = document.getElementById("parcSelect");
    const trigger = document.getElementById("parcTrigger");
    const label = document.getElementById("parcLabel");
    const menu = document.getElementById("parcMenu");

    // Le référentiel des stades (profil_culture) doit être prêt AVANT
    // le premier rendu : les pages calculent le stade dès onParcelleChange.
    if (typeof chargerProfilCulture === "function") {
      try {
        await chargerProfilCulture();
      } catch (e) {}
    }

    // Cas dégradés : on affiche l'état dans le déclencheur et on le désactive.
    const desactiver = (texte) => {
      trigger.querySelector("span").textContent = texte;
      trigger.classList.add("is-disabled");
      trigger.disabled = true;
    };

    let parcelles = [];
    try {
      parcelles = await api("/parcelles", { silent: true });
    } catch (e) {
      desactiver("API indisponible");
      if (typeof toast === "function") {
        toast("Serveur en cours de démarrage ou injoignable (mise en veille).", "err");
      }
      if (opts.onParcelleChange) opts.onParcelleChange(null);
      return;
    }
    this.parcelles = parcelles;
    if (!parcelles.length) {
      desactiver("Aucune parcelle");
      if (opts.onParcelleChange) opts.onParcelleChange(null);
      return;
    }

    // Construction des options (liste entièrement stylable).
    const check =
      '<svg class="parc-check" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    menu.innerHTML = parcelles
      .map(
        (p) =>
          '<li role="option" data-id="' +
          p.id +
          '" aria-selected="false" class="parc-row">' +
          '<div class="parc-info">' +
          '<span class="parc-name">' +
          p.nom +
          '</span>' +
          '<span class="parc-meta">' +
          p.culture +
          '</span>' +
          '</div>' +
          check +
          "</li>",
      )
      .join("");

    const key = "terra_active_parcelle_" + user.id;
    let active = localStorage.getItem(key);
    if (!active || !parcelles.some((p) => String(p.id) === String(active)))
      active = String(parcelles[0].id);

    const items = () => Array.from(menu.querySelectorAll("li"));
    const ouvrir = () => {
      root.classList.add("open");
      trigger.setAttribute("aria-expanded", "true");
      const sel = menu.querySelector('li[aria-selected="true"]');
      if (sel) sel.scrollIntoView({ block: "nearest" });
    };
    const fermer = () => {
      root.classList.remove("open");
      trigger.setAttribute("aria-expanded", "false");
      items().forEach((li) => li.classList.remove("active"));
    };

    // Sélectionne une parcelle : met à jour le libellé, la coche, le
    // stockage local, et notifie la page (onParcelleChange).
    const choisir = (id, notifier) => {
      const p = parcelles.find((x) => String(x.id) === String(id));
      if (!p) return;
      // Remarque: le label principal reste "Mes parcelles", seul le menu indique la sélection
      items().forEach((li) =>
        li.setAttribute(
          "aria-selected",
          li.dataset.id === String(id) ? "true" : "false",
        ),
      );
      localStorage.setItem(key, String(id));
      if (notifier && opts.onParcelleChange) opts.onParcelleChange(+id);
    };

    // État initial (sans notifier deux fois : un seul appel plus bas).
    choisir(active, false);

    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      root.classList.contains("open") ? fermer() : ouvrir();
    });
    menu.addEventListener("click", (e) => {
      const li = e.target.closest("li");
      if (!li) return;
      choisir(li.dataset.id, true);
      fermer();
    });
    // Clic en dehors → on referme.
    document.addEventListener("click", (e) => {
      if (!root.contains(e.target)) fermer();
    });
    // Navigation clavier (flèches + Entrée + Échap).
    root.addEventListener("keydown", (e) => {
      const lis = items();
      if (!lis.length) return;
      let idx = lis.findIndex((li) => li.classList.contains("active"));
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (!root.classList.contains("open")) ouvrir();
        idx =
          e.key === "ArrowDown"
            ? Math.min(lis.length - 1, idx + 1)
            : Math.max(0, idx < 0 ? 0 : idx - 1);
        lis.forEach((li) => li.classList.remove("active"));
        lis[idx].classList.add("active");
        lis[idx].scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter" && root.classList.contains("open")) {
        e.preventDefault();
        const li =
          lis[idx] || menu.querySelector('li[aria-selected="true"]');
        if (li) {
          choisir(li.dataset.id, true);
          fermer();
        }
      } else if (e.key === "Escape") {
        fermer();
      }
    });

    // Premier rendu de la page sur la parcelle active.
    if (opts.onParcelleChange) opts.onParcelleChange(+active);
  },
};
