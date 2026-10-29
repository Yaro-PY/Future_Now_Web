import {createContext, useContext} from 'react';

export const AppContext = createContext(null);
export function useApp() { return useContext(AppContext); }
export const ANY_FILTERS = {type:'any', age:'any', country:'any', city:'any', format:'any', date:'any', criteria:[]};
export const BOT_URL = 'https://t.me/FutureNowAssistantBot';
export {readRoute} from './routing/routes.js';
export function safeExternal(value) {
  const url = new URL(value);
  if (!['http:','https:'].includes(url.protocol) || url.username || url.password) throw new Error('Invalid source URL');
  return url.href;
}
export function imageFor(event) {
  if (event.event_type === 'grant') return 'earthrise';
  if (['exchange','international','ukrainian','program'].includes(event.event_type)) return 'campus';
  if (['hackathon','internship'].includes(event.event_type) || event.topics?.includes('it')) return 'technology';
  if (event.event_type === 'course') return ['technology','community','campus'][event.id % 3];
  return 'community';
}
export function initial(name = '') {
  return name.trim().split(/\s+/).slice(0,2).map(part => Array.from(part)[0] || '').join('').toUpperCase();
}
