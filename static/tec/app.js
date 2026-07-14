(function () {
  "use strict";
  const N_CAIXAS = 5;
  const CACHE_KEY = "vt_caixas";
  const CACHE_TS = "vt_caixas_ts";

  let caixas = [];
  let pos = null;
  let map = null, meMarker = null, boxLayer = null;

  const $ = (id) => document.getElementById(id);

  function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371000, rad = Math.PI / 180;
    const dphi = (lat2 - lat1) * rad, dl = (lon2 - lon1) * rad;
    const a = Math.sin(dphi / 2) ** 2 +
      Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dl / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function maisProximas(lista, lat, lon, n) {
    return lista
      .map((c) => Object.assign({}, c, { d: haversine(lat, lon, c.lat, c.lon) }))
      .sort((a, b) => a.d - b.d)
      .slice(0, n);
  }

  function fmt(m) { return m >= 1000 ? (m / 1000).toFixed(2) + " km" : Math.round(m) + " m"; }
  function navUrl(lat, lon) { return "https://www.google.com/maps/dir/?api=1&destination=" + lat + "," + lon; }

  async function carregarCaixas() {
    try {
      const r = await fetch("/tec/api/caixas", { credentials: "same-origin" });
      if (r.status === 401 || r.status === 302 || r.redirected) { location.href = "/tec/login"; return; }
      const data = await r.json();
      caixas = data.caixas || [];
      localStorage.setItem(CACHE_KEY, JSON.stringify(caixas));
      localStorage.setItem(CACHE_TS, new Date().toISOString());
      status("Caixas atualizadas agora (" + caixas.length + ")");
    } catch (e) {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        caixas = JSON.parse(cached);
        const ts = localStorage.getItem(CACHE_TS);
        status("Offline — dados de " + (ts ? new Date(ts).toLocaleString("pt-BR") : "?"), true);
      } else {
        status("Sem conexão e sem dados salvos. Conecte-se uma vez para baixar as caixas.", true);
      }
    }
    render();
  }

  function status(msg, off) {
    const el = $("vt-status");
    el.textContent = msg;
    el.classList.toggle("offline", !!off);
  }

  function initMap() {
    if (map || !window.L) return;
    map = L.map("vt-map").setView([-15.78, -47.93], 4);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      { subdomains: "abcd", maxZoom: 19, attribution: "© OSM © CARTO" }).addTo(map);
    boxLayer = L.layerGroup().addTo(map);
  }

  function render() {
    if (!pos) return;
    const perto = maisProximas(caixas, pos.lat, pos.lon, N_CAIXAS);
    const dest = $("vt-destaque");
    if (!perto.length) {
      dest.innerHTML = "<p>Nenhuma caixa cadastrada.</p>";
    } else {
      const c = perto[0];
      dest.innerHTML =
        '<h2>' + c.nome + '</h2>' +
        '<div class="dist">' + fmt(c.d) + '</div>' +
        (c.descricao ? '<div class="desc">' + c.descricao + '</div>' : '') +
        '<a class="vt-nav" href="' + navUrl(c.lat, c.lon) + '" target="_blank" rel="noopener">Navegar ▸</a>';
    }
    const ul = $("vt-lista");
    ul.innerHTML = perto.slice(1).map((c) =>
      '<li><span class="nome">' + c.nome + '</span><span class="m">' + fmt(c.d) + '</span>' +
      '<a class="mini-nav" href="' + navUrl(c.lat, c.lon) + '" target="_blank" rel="noopener">Ir</a></li>'
    ).join("");

    initMap();
    if (map) {
      if (!meMarker) meMarker = L.circleMarker([pos.lat, pos.lon], { radius: 8, color: "#00d4ff" }).addTo(map);
      else meMarker.setLatLng([pos.lat, pos.lon]);
      boxLayer.clearLayers();
      const pts = [[pos.lat, pos.lon]];
      perto.forEach((c) => {
        L.marker([c.lat, c.lon]).addTo(boxLayer).bindPopup("<b>" + c.nome + "</b><br>" + fmt(c.d));
        pts.push([c.lat, c.lon]);
      });
      map.fitBounds(pts, { padding: [40, 40], maxZoom: 17 });
    }
  }

  function iniciarGPS() {
    if (!navigator.geolocation) { status("GPS indisponível neste dispositivo", true); return; }
    navigator.geolocation.watchPosition(
      (p) => { pos = { lat: p.coords.latitude, lon: p.coords.longitude }; render(); },
      () => status("Não foi possível obter o GPS. Verifique a permissão de localização.", true),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 }
    );
  }

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/tec/sw.js").catch(() => {});
  }
  carregarCaixas();
  iniciarGPS();
})();
