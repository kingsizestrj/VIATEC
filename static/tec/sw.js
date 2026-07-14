const CACHE = "vt-shell-v1";
const SHELL = [
  "/tec/",
  "/static/tec/app.js",
  "/static/tec/tec.css",
  "/static/vendor/leaflet/leaflet.js",
  "/static/vendor/leaflet/leaflet.css",
  "/static/tec/manifest.webmanifest",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/tec/api/")) return; // dados: sempre rede (o app.js trata o cache em localStorage)

  const ehHTML = e.request.mode === "navigation" || url.pathname === "/tec/" || url.pathname === "/tec";
  if (ehHTML) {
    // network-first para o HTML: pega da rede e atualiza o cache; cai no cache se offline
    e.respondWith(
      fetch(e.request)
        .then((resp) => {
          const copia = resp.clone();
          caches.open(CACHE).then((c) => c.put("/tec/", copia));
          return resp;
        })
        .catch(() => caches.match(e.request).then((hit) => hit || caches.match("/tec/")))
    );
    return;
  }

  // cache-first para estáticos
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
