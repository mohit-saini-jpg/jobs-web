// tsj-footer-init.js — Footer injection
// Audit Fix R6: Extracted from inline scripts
(function(){
  var f=document.getElementById('footerPlaceholder');
  if(!f) return;
  fetch('/footer.html',{cache:'force-cache'})
    .then(function(r){return r.ok?r.text():null})
    .catch(function(){return null})
    .then(function(t){if(t&&f)f.outerHTML=t;});
})();
