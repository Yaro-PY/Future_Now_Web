import {useState} from 'react';
import {useApp} from '../context.jsx';
import {PageHeading} from '../components/Layout.jsx';
import {Icon} from '../components/Icons.jsx';
import {useGridEntrance} from '../hooks/useGridEntrance.js';

const directionPhotos = new Set([
  'international', 'ukrainian', 'exchange', 'course', 'program', 'volunteer',
  'grant', 'contest', 'internship', 'hackathon', 'other',
]);

export function CategoriesPage() {
  const {t,options,filters,applyFilters,go} = useApp();
  const [query,setQuery] = useState('');
  const directions = options('type',true).filter(item => item.label.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  const [animate, stopEntrance] = useGridEntrance(directions.length > 0);
  function updateQuery(event) {
    stopEntrance();
    setQuery(event.target.value);
  }
  function choose(type) { applyFilters({...filters,type}); go('explore'); }
  return <main className="page" id="main-content"><PageHeading title="categoriesTitle" subtitle="categoriesSubtitle" />
    <div className="section-search"><label className="search-box"><span className="sr-only">{t('findCategory')}</span><Icon name="search" /><input type="search" name="category_query" value={query} onChange={updateQuery} placeholder={t('findCategory')} /></label><button type="button" className="button line" data-action="all-categories" onClick={() => choose('any')}>{t('allOpportunities')}<Icon name="arrow" /></button></div>
    <div className={animate ? 'directions-grid catalog-entrance' : 'directions-grid'}>{directions.map(item => <button type="button" className="direction-card" key={item.value} data-category={item.value} onClick={() => choose(item.value)}>
      <img src={directionPhotos.has(item.value) ? `/assets/images/directions/${item.value}.jpg` : '/assets/images/community.jpg'} alt="" loading="lazy" />
      <span className="direction-body"><span className="direction-heading">{item.label}<Icon name="arrow" /></span><span>{t(`direction_${item.value}`) === `direction_${item.value}` ? t('directionDefault') : t(`direction_${item.value}`)}</span></span>
    </button>)}</div>{!directions.length && <p className="section-empty">{t('noCategories')}</p>}
  </main>;
}
