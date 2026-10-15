// App-shell cache only. API responses are never cached (always the latest published plan).
const CACHE = "hrm-shell-v3";
const SHELL = ["/m.html", "/index.html", "/css/base.css", "/css/mobile.css", "/css/desktop.css", "/css/tablet.css", "/img/scene-day.svg", "/img/scene-night.svg", "/manifest-plan.webmanifest",
  "/js/ui.js", "/js/mobile.js", "/js/desktop.js", "/js/login.js", "/manifest.webmanifest", "/icons/icon.svg",
  "/fonts/ibm-plex-sans-thai-looped-thai-400-normal.woff2", "/fonts/ibm-plex-sans-thai-looped-thai-600-normal.woff2",
  "/fonts/ibm-plex-sans-thai-looped-latin-400-normal.woff2", "/fonts/ibm-plex-sans-thai-looped-latin-600-normal.woff2"];
self.addEventListener("install", e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (u.origin !== location.origin || u.pathname.startsWith("/api/") || e.request.method !== "GET") return;
  // network first so updates land immediately; cache as offline fallback
  e.respondWith(fetch(e.request).then(r => { const c = r.clone(); caches.open(CACHE).then(x => x.put(e.request, c)); return r; })
    .catch(() => caches.match(e.request)));
});
