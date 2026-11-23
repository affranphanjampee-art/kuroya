/* Move the existing progress card and local backup controls into Account without duplicating them. */
(function(){'use strict';
const previous=accountPage;
accountPage=function(){
 const html=previous(),holder=document.createElement('div');holder.innerHTML=html;
 const profile=holder.querySelector('#cc59-profile'),account=holder.querySelector('#cc59-account'),details=profile?.querySelector(':scope > .cc-card-details'),layout=account?.querySelector(':scope > .account-layout');
 if(!details||!layout)return html;
 const heading=details.previousElementSibling;
 if(heading?.classList.contains('g-header'))heading.remove();
 layout.append(details);
 return holder.innerHTML;
};
if(page==='account')render();
})();
