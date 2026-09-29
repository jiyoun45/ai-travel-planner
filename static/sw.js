const CACHE_NAME = 'travel-planner-cache-v1';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/manifest.json'
];

// 1. Install 이벤트: 정적 파일 캐시 등록
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// 2. Activate 이벤트: 구버전 캐시 정리
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

// 3. Fetch 이벤트: 기존 API 요청을 방해하지 않는 네트워크 우선/캐시 폴백 처리
self.addEventListener('fetch', (event) => {
    // POST 요청 또는 /generate 등 AI API 호출은 캐시를 거치지 않고 네트워크로 직접 전달
    if (event.request.method !== 'GET' || event.request.url.includes('/generate')) {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then((networkResponse) => {
                // 정상 응답이면 최신 정적 자원으로 캐시 갱신
                if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return networkResponse;
            })
            .catch(() => {
                // 오프라인 등 네트워크 단절 시 캐시된 자원 반환
                return caches.match(event.request);
            })
    );
});
