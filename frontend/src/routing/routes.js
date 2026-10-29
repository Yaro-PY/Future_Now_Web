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
});
export function readRoute() {
  const value = location.hash.replace(/^#\/?/, '');
  return Object.hasOwn(ROUTES,value) ? value : 'explore';
}
