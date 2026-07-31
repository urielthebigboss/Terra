/* =========================================================
   TERRA — Client WebSocket temps réel
   Se connecte au canal unique du backend (ws://localhost:8000/ws)
   et redistribue chaque message comme un événement DOM :

       message serveur : { "type": "meteo_update", "data": {...} }
       devient         : window "terra:meteo_update"  (detail = data)

   Types d'événements diffusés par le backend :
     meteo_update        nouvelle mesure météo (sync OpenWeather)
     mesure_update       nouvelle mesure d'un capteur (futur IoT réel)
     mesures_bulk        lot de mesures simulées (recharger les graphiques)
     alerte_update       alerte créée ou changée d'état
     capteur_update      capteur créé / état changé (panne, actif…)
     capteur_delete      capteur retiré du parc
     parcelle_update     parcelle créée ou modifiée
     parcelle_delete     parcelle supprimée
     prescription_update prescription créée ou marquée faite
     prescriptions_bulk  lot de prescriptions simulées
     alerte_expert       alerte IMMÉDIATE du moteur expert (hors cycle
                          des 5 min — humidité critique, chaleur, capteur
                          muet…) ; affichée en bandeau permanent dans la
                          carte Recommandation du dashboard (pas de toast)

   Usage dans une page :
       <script src="../assets/js/realtime.js"></script>
       <script>
         TerraRealtime.connecter();
         window.addEventListener('terra:meteo_update', e => majMeteo(e.detail));
         window.addEventListener('terra:capteur_update', e => majCapteur(e.detail));
       </script>
   ========================================================= */

const TerraRealtime = (function () {
  // const URL_WS = 'ws://localhost:8000/ws';
  const URL_WS = "wss://terra-9fg4.onrender.com/ws";
  let ws = null;
  let tentatives = 0; // pour le backoff de reconnexion
  let fermetureVoulue = false; // ne pas se reconnecter après deconnecter()

  function connecter() {
    fermetureVoulue = false;
    ws = new WebSocket(URL_WS);

    ws.onopen = function () {
      tentatives = 0;
      window.dispatchEvent(new CustomEvent("terra:ws_ouvert"));
      console.info("[TERRA] WebSocket connecté —", URL_WS);
    };

    ws.onmessage = function (e) {
      let msg;
      try {
        msg = JSON.parse(e.data);
      } catch (err) {
        return;
      }
      if (!msg || !msg.type) return;
      /* Chaque type de message devient un événement "terra:<type>"
         auquel n'importe quelle page peut s'abonner. */
      window.dispatchEvent(
        new CustomEvent("terra:" + msg.type, { detail: msg.data }),
      );
    };

    ws.onclose = function () {
      window.dispatchEvent(new CustomEvent("terra:ws_ferme"));
      if (fermetureVoulue) return;
      /* Reconnexion automatique : 1 s, 2 s, 4 s… plafonné à 15 s.
         Indispensable sur le terrain : le réseau des zones agricoles coupe. */
      const delai = Math.min(15000, 1000 * Math.pow(2, tentatives++));
      console.warn(
        "[TERRA] WebSocket coupé — reconnexion dans " + delai / 1000 + " s",
      );
      setTimeout(connecter, delai);
    };
  }

  function deconnecter() {
    fermetureVoulue = true;
    if (ws) ws.close();
  }

  function estConnecte() {
    return ws !== null && ws.readyState === WebSocket.OPEN;
  }

  return { connecter, deconnecter, estConnecte };
})();
