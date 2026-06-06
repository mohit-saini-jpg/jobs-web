// tsj-init.js — Header injection
// Audit Fix R6: Extracted from inline scripts to enable CSP without unsafe-inline
(function(){
  var h=document.getElementById('headerPlaceholder');
  if(!h) return;
  fetch('/header.html',{cache:'force-cache'})
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
