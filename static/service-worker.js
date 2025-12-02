const CACHE_NAME = 'budgetia-v1';
const ASSETS = [
  '/',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  // fichiers CSS/JS essentiels (Bootstrap/Chart.js si locaux)
];

// install
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

// activate
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

// fetch
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((resp) => {
      return resp || fetch(event.request).then((response) => {
        // add fetched resource to cache (optional)
        return caches.open(CACHE_NAME).then((cache) => {
          try { cache.put(event.request, response.clone()); } catch (e) {}
          return response;
        });
      }).catch(() => {
        // fallback if needed: return offline page for navigation
        if (event.request.mode === 'navigate') {
          return caches.match('/');
        }
      });
    })
  );
});
