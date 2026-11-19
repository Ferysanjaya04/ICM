"use strict";
document.addEventListener('DOMContentLoaded', () => {
 const trigger=document.getElementById('menu-button'), nav=document.getElementById('sidebar'), overlay=document.getElementById('sidebar-overlay');
 const mobile=matchMedia('(max-width: 1000px)');
 // Some pages contain their header inside main. Never make the menu's ancestor inert.
 const roots=[...document.querySelectorAll('main')].flatMap(main => main.contains(nav) ? [...main.children].filter(el => !el.contains(nav) && el !== overlay) : [main]);let open=false;
 const focusables=()=>[...nav.querySelectorAll('a[href],button:not([disabled])')].filter(e=>e.getClientRects().length);
 function menu(value,restore=true){const was=open;open=value&&mobile.matches;nav.classList.toggle('is-open',open);nav.inert=mobile.matches&&!open;overlay.hidden=!open;trigger.setAttribute('aria-expanded',String(open));roots.forEach(e=>e.inert=open);if(open)focusables()[0]?.focus();else if(was&&restore)trigger.focus();}
 if(trigger&&nav&&overlay){trigger.addEventListener('click',()=>menu(!open));overlay.addEventListener('click',()=>menu(false));mobile.addEventListener('change',()=>menu(false,false));document.addEventListener('keydown',e=>{if(!open)return;if(e.key==='Escape'){e.preventDefault();menu(false);}if(e.key==='Tab'){const a=focusables();if(e.shiftKey&&document.activeElement===a[0]){e.preventDefault();a.at(-1)?.focus();}else if(!e.shiftKey&&document.activeElement===a.at(-1)){e.preventDefault();a[0]?.focus();}}});document.addEventListener('focusin',e=>{if(open&&!nav.contains(e.target))focusables()[0]?.focus();});menu(false,false);}
 document.querySelectorAll('#logout-button,[data-logout]').forEach(button=>button.addEventListener('click',()=>{if(button.disabled)return;button.disabled=true;AuthStorage.clear();window.location.replace('./login.html');}));
});
