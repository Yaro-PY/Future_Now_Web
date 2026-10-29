import {useEffect, useRef, useState} from 'react';
import {FutureNowAPI} from '../api.js';
import {ANY_FILTERS, AppContext} from '../context.jsx';
import {readRoute, ROUTES} from '../routing/routes.js';
import {useDebouncedValue} from '../hooks/useDebouncedValue.js';
import {useLocale} from '../hooks/useLocale.js';
import {useRemoteResource} from '../hooks/useRemoteResource.js';
import {useToast} from '../hooks/useToast.js';

const api = new FutureNowAPI();

export function AppProvider({children}) {
  const [user, setUser] = useState(null);
  const [config, setConfig] = useState(null);
  const [booting, setBooting] = useState(true);
  const [route, setRoute] = useState(readRoute);
  const [filters, setFilters] = useState({...ANY_FILTERS});
  const [query, setQuery] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [savedCount, setSavedCount] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [modal, setModal] = useState(null);
  const [detailId, setDetailId] = useState(null);
  const [revision, setRevision] = useState(0);
  const favoriteLocks = useRef(new Set());
  const {notification,toast} = useToast();
  const {language,setLanguage,t,date,errorMessage} = useLocale(api);
  const debouncedQuery = useDebouncedValue(query.trim());

  function clearSession() {
    setUser(null); setSavedCount(0); setCollection(null); setProposalPage(null);
    setDetailId(null); setModal(null); setMenuOpen(false); api.csrfToken = null;
  }
  function fail(error) {
    if (error?.status === 401 && user) { clearSession(); toast(t('sessionExpired')); }
    else toast(errorMessage(error));
  }
  async function enter(session) {
    const nextUser = session.user;
    const nextLanguage = nextUser.language;
    api.language = nextLanguage;
    const nextConfig = await api.bootstrap(nextLanguage);
    setConfig(nextConfig); setLanguage(nextLanguage);
    setFilters({...ANY_FILTERS, ...nextUser.filters}); setQuery(''); setSearchQuery(''); setPage(1);
    setCollection(null); setProposalPage(null); setUser(nextUser);
    setRoute(readRoute());
    if (nextUser.onboarding_required || nextUser.filters_setup_required) setModal({type:'onboarding'});
  }
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await api.bootstrap('uk');
        if (!active) return;
        setConfig(data);
        if (data.authenticated) {
          try { const session = await api.resume(); if (active) await enter(session); }
          catch (error) { if (![401,403].includes(error.status)) throw error; api.csrfToken = null; }
        }
      } catch (error) { if (active) toast(errorMessage(error)); }
      finally { if (active) setBooting(false); }
    })();
    return () => { active = false; };
  }, []);
  useEffect(() => {
    document.documentElement.lang = language;
    document.title = `Future Now — ${t(user ? route : 'login')}`;
    api.language = language;
  }, [language, route, Boolean(user), t]);
  useEffect(() => {
    document.body.classList.toggle('auth-mode', !user);
    document.body.classList.toggle('modal-open', Boolean(modal || detailId));
    return () => { document.body.classList.remove('auth-mode','modal-open'); };
  }, [Boolean(user), Boolean(modal), Boolean(detailId)]);
  useEffect(() => { setSearchQuery(debouncedQuery); setPage(1); }, [debouncedQuery]);
  useEffect(() => {
    const navigate = () => {
      setRoute(readRoute()); setPage(1); setCollection(null); setProposalPage(null);
      setMenuOpen(false); setModal(null); setDetailId(null); window.scrollTo({top:0,behavior:'instant'});
    };
    const keys = event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        const input = document.querySelector('input[name=query]');
        if (input) { event.preventDefault(); input.focus(); }
      }
      if (event.key === 'Escape') setMenuOpen(false);
    };
    window.addEventListener('hashchange',navigate); window.addEventListener('keydown',keys);
    return () => { window.removeEventListener('hashchange',navigate); window.removeEventListener('keydown',keys); };
  }, []);
  const accountKey = user?.public_id;
  const onboardingOpen = modal?.type === 'onboarding';
  useEffect(() => {
    if (!user) return;
    let active = true;
    api.favorites().then(result => { if (active) setSavedCount(result.total); }).catch(() => {});
    return () => { active = false; };
  }, [accountKey, Boolean(user)]);
  const feed = useRemoteResource({
    enabled:Boolean(user) && !onboardingOpen && ['explore','saved'].includes(route),
    resourceKey:JSON.stringify([route,accountKey,filters,searchQuery,page,language,revision]),
    load:() => route === 'saved' ? api.request(`/me/favorites?page=${page}&page_size=6`) : api.search({filters,query:searchQuery,page,page_size:6}),
    onLoad:result => {
      if (page > result.pages) setPage(Math.max(1,result.pages));
      if (route === 'saved') setSavedCount(result.total);
      if (result.filters) setUser(value => value ? {...value,filters:result.filters,filters_setup_required:false} : value);
    },
    onError:fail,
  });
  const {data:collection,error:collectionError,setData:setCollection} = feed;
  const proposals = useRemoteResource({
    enabled:Boolean(user) && ['proposals','moderation'].includes(route) && (route !== 'moderation' || user.role === 'admin'),
    resourceKey:JSON.stringify([route,accountKey,page,language,revision]),
    load:() => api.request(`${route === 'moderation' ? '/admin/proposals' : '/me/proposals'}?page=${page}&page_size=10`),
    onError:fail,
  });
  const {data:proposalPage,error:proposalError,setData:setProposalPage} = proposals;
  useEffect(() => { if (user && ROUTES[route]?.adminOnly && user.role !== 'admin') go('explore'); }, [route,user?.role]);

  function go(value) {
    setDetailId(null); setModal(null); setMenuOpen(false); setPage(1);
    setCollection(null); setProposalPage(null);
    if (readRoute() === value) { setRoute(value); setRevision(value => value + 1); }
    else location.hash = value;
  }
  async function changeLanguage(value) {
    if (value === language) return;
    const nextUser = user ? await api.saveSettings({language:value}) : null;
    const nextConfig = await api.bootstrap(value);
    if (nextUser) setUser(nextUser);
    setConfig(nextConfig); setLanguage(value);
  }
  function applyFilters(value) {
    setCollection(null); setPage(1); setFilters({...value, city:value.country === 'ukraine' ? value.city : 'any'});
    setRevision(current => current + 1);
    setModal(null);
  }
  function resetFilters() { setQuery(''); setSearchQuery(''); applyFilters({...ANY_FILTERS,criteria:[]}); }
  async function refreshCatalog(reload = true) {
    const catalog = await api.catalogStatus();
    setConfig(value => ({...value,catalog}));
    if (reload) setRevision(value => value + 1);
  }
  async function toggleFavorite(event) {
    if (favoriteLocks.current.has(event.id)) return;
    favoriteLocks.current.add(event.id);
    try {
      if (event.saved) await api.removeFavorite(event.id); else await api.saveFavorite(event.id);
      setSavedCount(value => Math.max(0,value + (event.saved ? -1 : 1)));
      setCollection(value => value ? {...value,items:value.items.map(item => item.id === event.id ? {...item,saved:!event.saved} : item)} : value);
      if (route === 'saved') setRevision(value => value + 1);
      toast(t(event.saved ? 'removed' : 'added'));
    } finally { favoriteLocks.current.delete(event.id); }
  }
  const value = {
    resourceRevision:revision,
    api, user, setUser, config, booting, notification, language, t, date, options:(name, excludeAny = false) => (config?.catalogs?.[name] || []).filter(row => !excludeAny || row.value !== 'any'),
    route, go, filters, applyFilters, resetFilters, query, setQuery, submitQuery:() => { setSearchQuery(query.trim()); setPage(1); setRevision(value => value + 1); },
    page, setPage, collection, collectionError, proposalPage, proposalError, savedCount, menuOpen, setMenuOpen,
    modal, setModal, detailId, setDetailId, toast, fail, errorMessage, enter, changeLanguage, toggleFavorite, refreshCatalog,
    reload:() => setRevision(value => value + 1), logout:async () => { await api.logout(); clearSession(); },
    passwordChanged:() => { clearSession(); toast(t('passwordChanged')); },
  };
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
