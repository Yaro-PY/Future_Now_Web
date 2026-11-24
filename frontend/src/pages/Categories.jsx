import {useState} from 'react';
import {useApp} from '../context.jsx';
import {Button, Empty, Skeletons} from '../components/Common.jsx';
import {PageHeading} from '../components/Layout.jsx';
import {Icon} from '../components/Icons.jsx';
import {useGridEntrance} from '../hooks/useGridEntrance.js';
import {useRemoteResource} from '../hooks/useRemoteResource.js';
import {words} from '../i18n.js';

function directionDescription(item, language) {
  const [uk, en] = words[`direction_${item.key}`] || words.directionDefault;
  return language === 'en' ? item.description_en || item.description_uk || en : item.description_uk || uk;
}

export function CategoriesPage() {
  const {t, language, api, openDirection, user, setModal, resourceRevision, reload} = useApp();
  const [query, setQuery] = useState('');
  const {data, error} = useRemoteResource({
    enabled: true,
    resourceKey: resourceRevision,
    load: () => api.request('/directions'),
  });
  const admin = user.role === 'admin';
  const needle = query.trim().toLocaleLowerCase(language);
  const directions = (data?.items || [])
    .map(item => ({...item, title: language === 'en' ? item.title_en || item.title_uk : item.title_uk}))
    .filter(item => item.title.toLocaleLowerCase(language).includes(needle));
  const [animate, stopEntrance] = useGridEntrance(directions.length > 0);

  return <main className="page" id="main-content">
    <PageHeading title="categoriesTitle" subtitle="categoriesSubtitle" />
    <div className="section-search">
      <label className="search-box"><span className="sr-only">{t('findCategory')}</span><Icon name="search" />
        <input type="search" name="category_query" value={query} onChange={event => {
          stopEntrance(); setQuery(event.target.value);
        }} placeholder={t('findCategory')} />
      </label>
      <Button kind="line" action="all-categories" onClick={() => openDirection()}>{t('allOpportunities')}<Icon name="arrow" /></Button>
      {admin && <Button action="create-direction" onClick={() => setModal({type:'edit-direction'})}><Icon name="plus" />{t('createDirection')}</Button>}
    </div>
    {error && <Empty title="emptyTitle" text="serviceError" action="reload" actionLabel="retry" onAction={reload} />}
    {!data && !error && <Skeletons />}
    {data && <div className={animate ? 'directions-grid catalog-entrance' : 'directions-grid'}>
      {directions.map(item => <article className="direction-entry" key={item.key}>
        <button type="button" className="direction-card" data-category={item.key} onClick={() => openDirection(item)}>
          <img src={item.cover_url || item.default_cover_url} alt="" loading="lazy" />
          <span className="direction-body">
            <span className="direction-heading">{item.title}<Icon name="arrow" /></span>
            <span>{directionDescription(item, language)}</span>
          </span>
        </button>
        {admin && <Button kind="line" action="edit-direction" aria-label={`${t('editDirection')} · ${item.title}`}
          onClick={() => setModal({type:'edit-direction', item:{...item,
            description_uk:directionDescription(item, 'uk'), description_en: item.revision ? item.description_en : directionDescription(item, 'en'),
          }})}>{t('editDirection')}</Button>}
      </article>)}
    </div>}
    {data && !directions.length && <p className="section-empty">{t('noCategories')}</p>}
  </main>;
}
