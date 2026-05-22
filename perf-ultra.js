/* perf-ultra.js v2 — Top Sarkari Jobs */
(function(){'use strict';
// Lazy load images
if('IntersectionObserver'in window){var io=new IntersectionObserver(function(e){e.forEach(function(e){if(e.isIntersecting){var i=e.target;if(i.dataset.src){i.src=i.dataset.src;delete i.dataset.src}if(i.dataset.srcset){i.srcset=i.dataset.srcset;delete i.dataset.srcset}io.unobserve(i)}})},{rootMargin:'300px 0px'});document.querySelectorAll('img[data-src],img[data-srcset]').forEach(function(i){io.observe(i)})}
// Prefetch on idle
if('requestIdleCallback'in window){requestIdleCallback(function(){['jobs-index.json','jobs-search-index.json'].forEach(function(f){fetch(f,{cache:'force-cache',priority:'low'}).catch(function(){})})},{timeout:4000})}
// Passive scroll
var p=false;try{window.addEventListener('t',null,Object.defineProperty({},'passive',{get:function(){p=true}}));window.removeEventListener('t',null)}catch(e){}
var t=false;document.addEventListener('scroll',function(){if(!t){requestAnimationFrame(function(){t=false});t=true}},p?{passive:true}:false);
// Prefetch links on hover (instant navigation feel)
var pf={};document.addEventListener('mouseover',function(e){var a=e.target.closest('a[href]');if(!a)return;var h=a.href;if(!h||pf[h]||!h.startsWith(location.origin))return;pf[h]=1;var l=document.createElement('link');l.rel='prefetch';l.href=h;document.head.appendChild(l)},{passive:true});
})();