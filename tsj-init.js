// tsj-init.js — Header injection
// Audit Fix R6: Extracted from inline scripts to enable CSP without unsafe-inline
(function(){
  var h=document.getElementById('headerPlaceholder');
  if(!h) return;
  // cache:'no-cache' = always revalidate with the server (conditional
  // request) instead of blindly trusting a stale local copy. force-cache
  // was keeping edited header.html invisible to users for up to the full
  // 2h Cache-Control window (see _headers: /*.html max-age=7200) since
  // it skips revalidation entirely. Server still returns 304 when nothing
  // changed, so repeat loads stay fast — this only fixes propagation.
  fetch('/header.html',{cache:'no-cache'})
    .then(function(r){return r.ok?r.text():null})
    .catch(function(){return null})
    .then(function(t){
      if(t&&h){
        h.outerHTML=t;
        // tsj-menu.js (deferred) may not have defined __TSJ_INIT_HEADER yet,
        // so retry a few times until it's available. The delegated dropdown
        // handler in tsj-menu.js also works independently of this.
        var tries=0;
        (function callInit(){
          if(window.__TSJ_INIT_HEADER){ window.__TSJ_INIT_HEADER(); return; }
          if(tries++ < 40){ setTimeout(callInit, 50); }
        })();
      }
    });
})();

// TSJ AI floating assistant — loaded on every page that includes this file.
// Deferred script tag (not a fetch+eval) so it behaves like a normal script
// include: cached by the browser, executes after parse, doesn't block render.
(function(){
  if(document.querySelector('script[src^="/tsj-chat.js"]')) return;
  var s = document.createElement('script');
  s.src = '/tsj-chat.js';
  s.defer = true;
  document.head.appendChild(s);
})();
