/* Pause only decorative animations on roster rows outside the viewport. */
(()=>{
 if(!('IntersectionObserver' in window)||!('MutationObserver' in window))return;
 const rows=new Set();let pending=false;
 const observer=new IntersectionObserver(entries=>{for(const e of entries)e.target.classList.toggle('cc79-offscreen',!e.isIntersecting)},{rootMargin:'100px 0px'});
 function scan(){pending=false;for(const row of rows)if(!row.isConnected){observer.unobserve(row);rows.delete(row)}for(const row of document.querySelectorAll('#cc50-roster-output .cc50-roster-table tbody tr[data-plate]'))if(!rows.has(row)){rows.add(row);observer.observe(row)}}
 function schedule(){if(!pending){pending=true;requestAnimationFrame(scan)}}
 new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});schedule();
})();
