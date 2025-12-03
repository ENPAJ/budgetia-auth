    // Dark mode: persist in localStorage
    (function(){
      const root = document.documentElement;
      const stored = localStorage.getItem('budgetia-theme');
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      const theme = stored || (prefersDark ? 'dark' : 'light');
      if(theme === 'dark') root.setAttribute('data-theme','dark');

      window.toggleTheme = function(){
        const now = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        if(now === 'dark') document.documentElement.setAttribute('data-theme','dark');
        else document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('budgetia-theme', now);
      };
    })();

    // Register service worker
    if('serviceWorker' in navigator){
      navigator.serviceWorker.register('/static/service-worker.js')
        .then(reg => console.log('Service worker registered.', reg))
        .catch(err => console.log('Service worker failed:', err));
    }

    // Progressive Web App install prompt
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      const btn = document.getElementById('btn-install-pwa');
      if(btn) btn.style.display = 'inline-block';
    });

    function promptInstall(){
      if(deferredPrompt){
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(() => {
          deferredPrompt = null;
          document.getElementById('btn-install-pwa').style.display = 'none';
        });
      }
    }
