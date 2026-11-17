export const ROUTES = Object.freeze({
  explore: {title:'explore', group:'discover'},
  categories: {title:'categories', group:'discover'},
  saved: {title:'saved', group:'discover'},
  suggest: {title:'suggest', group:'community'},
  proposals: {title:'proposals', group:'community'},
  profile: {title:'profile', group:'account'},
  settings: {title:'settings', group:'account'},
  about: {title:'about', group:'support'},
  help: {title:'help', group:'support'},
  moderation: {title:'moderation', group:'administration', adminOnly:true},
  login: {title:'login'},
  opportunity: {title:'details'},
});

export function readOpportunityId(path=location.pathname) {
  const match=path.match(/^\/opportunities\/([1-9]\d*)(?:\/[^?#]*)?\/?$/);
  const value=match?Number(match[1]):null;
  return Number.isSafeInteger(value)?value:null;
}
export function readRoute() {
  if (location.pathname.startsWith('/opportunities/')) return 'opportunity';
  const value=location.hash.replace(/^#\/?/,'');
  return Object.hasOwn(ROUTES,value)&&value!=='opportunity'?value:'explore';
}
export function routeHref(page) { return `/#${page}`; }
export function opportunityHref(event) {
  if(typeof event==='object'&&event?.page_url) return event.page_url;
  const id=typeof event==='object'?event?.id:event;
  return `/opportunities/${Number(id)}`;
}
export function internalClick(event) {
  return event.button===0&&!event.metaKey&&!event.ctrlKey&&!event.shiftKey&&!event.altKey;
}
export function moveTo(path,{replace=false}={}) {
  if(location.pathname+location.search+location.hash===path) return;
  history.replaceState({...history.state,fnScroll:window.scrollY},'');
  history[replace?'replaceState':'pushState']({fnNavigation:true,fnScroll:0},'',path);
  window.dispatchEvent(new PopStateEvent('popstate',{state:history.state}));
  window.scrollTo({top:0,behavior:'instant'});
}
export function authReturnPath() {
  const next=new URLSearchParams(location.search).get('next');
  // Return targets are restricted to local public listing pages, never arbitrary URLs.
  return next&&next.startsWith('/opportunities/')&&!next.includes('//')&&!/[?#\\]/.test(next)&&readOpportunityId(next)?next:null;
}
