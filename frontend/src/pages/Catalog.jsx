import {useEffect, useState} from 'react';
import {useApp, imageFor} from '../context.jsx';
import {Icon} from '../components/Icons.jsx';
import {AsyncButton, Button, Criteria, DataForm, Empty, Select, Skeletons, Submit} from '../components/Common.jsx';
import {PageHeading} from '../components/Layout.jsx';

export function FilterForm() {
  const {filters, applyFilters, t} = useApp();
  const [draft, setDraft] = useState(filters);
  useEffect(() => setDraft(filters), [filters]);
  const update = (key, value) => setDraft(old => ({...old,[key]:value,...(key === 'country' && value !== 'ukraine' ? {city:'any'} : {})}));
  return <DataForm className="filter-form" kind="filters" onSubmit={() => applyFilters(draft)}>
    <Select name="type" label={t('type')} value={draft.type} onChange={value => update('type',value)} />
    <Select name="age" label={t('age')} value={draft.age} onChange={value => update('age',value)} />
    <Select name="country" label={t('country')} value={draft.country} onChange={value => update('country',value)} />
    <div data-city-field hidden={draft.country !== 'ukraine'}><Select name="city" label={t('city')} value={draft.city} onChange={value => update('city',value)} /></div>
    <Select name="format" label={t('format')} value={draft.format} onChange={value => update('format',value)} />
    <Select name="date" label={t('date')} value={draft.date} onChange={value => update('date',value)} />
    <div className="filter-divider" /><div><p className="criteria-caption">{t('criteria')}</p><Criteria value={draft.criteria} onChange={value => update('criteria',value)} /></div>
    <Submit wide>{t('apply')}<Icon name="arrow" /></Submit>
  </DataForm>;
}
export function FavoriteButton({event, sheet = false, onSaved}) {
  const {t, toggleFavorite} = useApp();
  return <AsyncButton className={`${sheet ? 'button line' : 'favorite-button'} ${event.saved ? 'is-saved' : ''}`} data-action="favorite" data-id={event.id} data-saved={Boolean(event.saved)} aria-label={t(event.saved ? 'removeFavorite' : 'saveFavorite')} aria-pressed={Boolean(event.saved)} onClick={async () => { await toggleFavorite(event); onSaved?.(!event.saved); }}><Icon name="heart" />{sheet && <span>{t(event.saved ? 'removeFavorite' : 'saveFavorite')}</span>}</AsyncButton>;
}
export function Price({event}) {
  const {t} = useApp();
  return !event.price?.known ? t('unknown') : event.price.is_free ? t('free') : event.price.text || t('paid');
}
function OpportunityCard({event}) {
  const {t, date, setDetailId} = useApp();
  return <article className="opportunity"><button type="button" className="card-open" data-action="detail" data-id={event.id} aria-label={`${t('details')}: ${event.title}`} onClick={() => setDetailId(event.id)}>
    <span className="card-image"><img src={`/assets/images/${imageFor(event)}.jpg`} alt="" loading="lazy" width="600" height="360" /><span className="card-type">{event.event_type_label}</span><span className="card-country"><Icon name="pin" />{event.country_label}</span></span>
    <span className="card-body"><span className="card-kicker"><span>{event.organizer || event.source}</span><span className="price"><Price event={event} /></span></span><span className="card-title">{event.title}</span><span className="card-tags">{event.tags.slice(0,2).map(tag => <span key={tag.value || tag.label}>{tag.label}</span>)}</span><span className="card-bottom"><span><Icon name="laptop" />{event.format_label}</span><span><Icon name="clock" />{event.is_self_paced && !event.deadline ? t('selfPaced') : date(event.deadline)}</span><Icon name="arrow" className="card-arrow" /></span></span>
  </button><FavoriteButton event={event} />{event.status === 'expired' && <p className="ended-caption">{t('expired')}</p>}</article>;
}
export function Pagination({result}) {
  const {page, setPage, t} = useApp();
  return result.pages > 1 && <div className="pagination"><Button kind="line" action="previous" disabled={page <= 1} onClick={() => setPage(value => value - 1)}>{t('previous')}</Button><span>{t('page',{page,pages:result.pages})}</span><Button kind="line" action="next-page" disabled={page >= result.pages} onClick={() => setPage(value => value + 1)}>{t('nextPage')}</Button></div>;
}
function Collection() {
  const {collection, collectionError, route, filters, query, t, reload, resetFilters, go} = useApp();
  if (collectionError) return <Empty title="emptyTitle" text="serviceError" action="reload" actionLabel="retry" onAction={reload} />;
  if (!collection) return <Skeletons />;
  if (!collection.items.length) {
    if (route === 'saved') return <Empty title="savedEmpty" text="savedEmptyText" symbol="heart" action="explore" actionLabel="explore" onAction={() => go('explore')} />;
    const unrestricted = ['type','age','country','city','format','date'].every(key => !filters[key] || filters[key] === 'any') && !filters.criteria?.length && !query.trim();
    return unrestricted ? <Empty title="catalogEmpty" text="noListings" symbol="spark" action="suggest" actionLabel="suggest" onAction={() => go('suggest')} /> : <Empty title="emptyTitle" text="emptyText" onAction={resetFilters} />;
  }
  return <><div className="results-caption"><span>{t('resultCount',{count:collection.total})}</span><span className="view-indicator"><Icon name="grid" />{t(route === 'saved' ? 'saved' : 'explore')}</span></div><div className="opportunities-grid">{collection.items.map(event => <OpportunityCard key={event.id} event={event} />)}</div><Pagination result={collection} /></>;
}
export function CatalogPage() {
  const {t, route, query, setQuery, submitQuery, filters, applyFilters, options, resetFilters, setModal} = useApp();
  if (route === 'saved') return <main className="page" id="main-content"><PageHeading title="savedTitle" subtitle="savedSubtitle" /><section id="collection"><Collection /></section></main>;
  return <main className="page" id="main-content"><PageHeading title="discoverTitle" subtitle="discoverSubtitle" /><div className="catalog-layout">
    <aside className="filter-sidebar" aria-label={t('filters')}><div className="filter-title"><h2><Icon name="filter" />{t('filters')}</h2><button type="button" className="text-button" data-action="reset-filters" onClick={resetFilters}>{t('reset')}</button></div><FilterForm /></aside>
    <section className="catalog-main" aria-label={t('explore')}><CatalogHealth /><form className="catalog-tools" data-form="query" onSubmit={event => { event.preventDefault(); submitQuery(); }}><label className="search-box"><span className="sr-only">{t('search')}</span><Icon name="search" /><input type="search" name="query" value={query} onChange={event => setQuery(event.target.value)} placeholder={t('search')} autoComplete="off" /><span className="search-key">⌘ K</span></label><button type="button" className="button secondary mobile-only" data-action="filters" aria-label={t('filters')} onClick={() => setModal({type:'filters'})}><Icon name="filter" /></button></form>
      <div className="category-tabs" aria-label={t('type')}>{['any','course','exchange','grant','program'].map(key => <button key={key} type="button" data-type={key} className={filters.type === key ? 'active' : ''} onClick={() => applyFilters({...filters,type:key})}>{options('type').find(row => row.value === key)?.label || key}</button>)}</div>
      <div id="collection"><Collection /></div>
    </section></div></main>;
}

function CatalogHealth() {
  const {config,t,date,setModal,refreshCatalog} = useApp();
  const status = config?.catalog;
  return <div className="catalog-health"><span>{status?.last_checked_at ? t('catalogUpdated',{date:date(status.last_checked_at)}) : t('catalogNeverChecked')}</span><div><AsyncButton className="text-button" data-action="catalog-sources" onClick={async () => { await refreshCatalog(false); setModal({type:'sources'}); }}>{t('catalogSources')}<Icon name="external" /></AsyncButton><AsyncButton className="text-button" data-action="catalog-refresh" onClick={() => refreshCatalog()}>{t('refreshCatalog')}</AsyncButton></div>{status?.status === 'degraded' && <p>{t('catalogDegraded')}</p>}</div>;
}
