import {useEffect,useRef,useState} from 'react';
import {useApp,safeExternal} from '../context.jsx';
import {OpportunityCover} from '../components/OpportunityCover.jsx';
import {internalClick,opportunityHref} from '../routing/routes.js';
import {AsyncButton,Button,Skeletons} from '../components/Common.jsx';
import {Icon} from '../components/Icons.jsx';
import {FavoriteButton,Price} from './Catalog.jsx';
import './opportunity.css';

function Fact({label,children}) {return <div><dt>{label}</dt><dd>{children}</dd></div>;}

export function OpportunityPage() {
  const {api,user,detailId,language,t,date,go,requestLogin,setModal,toast,fail}=useApp();
  const [event,setEvent]=useState(null),[error,setError]=useState(null),[retry,setRetry]=useState(0);
  const heading=useRef(null);
  useEffect(()=>{
    let active=true;setEvent(null);setError(null);
    if(!detailId){setError(404);return;}
    api.detail(detailId).then(result=>{if(active)setEvent(result);}).catch(problem=>{
      if(active){setError(problem.status||503);if(problem.status!==404)fail(problem);}
    });
    return ()=>{active=false;};
  },[detailId,language,user?.public_id,retry]);
  useEffect(()=>{
    if(!event)return;
    document.title=`${event.title} — Future Now`;
    const path=opportunityHref(event);
    if(location.pathname!==path)history.replaceState(history.state,'',path);
    const canonical=document.querySelector('link[rel="canonical"]');
    canonical?.setAttribute('href',new URL(path,location.origin).href);
    heading.current?.focus({preventScroll:true});
  },[event?.id,event?.title,event?.page_url]);
  async function share(){
    const url=new URL(opportunityHref(event),location.origin).href;
    try {if(navigator.share){await navigator.share({title:event.title,url});return;}}
    catch(problem){if(problem.name==='AbortError')return;}
    try {if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(url);toast(t('copied'));return;}}
    catch {/* A selectable URL remains available when the browser blocks copying. */}
    setModal({type:'share',url});
  }
  const back=<a className="opportunity-back" href="/#explore" onClick={e=>{if(internalClick(e)){e.preventDefault();if(history.state?.fnNavigation)history.back();else go('explore');}}}><Icon name="arrow"/>{t('backToCatalog')}</a>;
  if(error)return <main className="page opportunity-page" id="main-content">{back}<section className="opportunity-error" role="alert"><p className="eyebrow">{error===404?'404':'Future Now'}</p><h1>{t(error===404?'opportunityMissing':'serviceError')}</h1><p>{t(error===404?'opportunityMissingText':'tryAgain')}</p>{error!==404&&<Button action="retry-opportunity" onClick={()=>setRetry(value=>value+1)}>{t('retry')}</Button>}</section></main>;
  if(!event)return <main className="page opportunity-page" id="main-content" aria-busy="true">{back}<Skeletons/></main>;
  const expired=event.status==='expired';
  const age=event.min_age===0&&event.max_age==null?t('noAgeRestriction'):event.min_age==null&&event.max_age==null?t('unknown'):event.max_age==null?`${event.min_age}+`:event.min_age==null?`≤ ${event.max_age}`:`${event.min_age}–${event.max_age}`;
  return <main className="page opportunity-page" id="main-content" data-opportunity-id={event.id}>
    <nav className="opportunity-breadcrumb" aria-label={t('details')}>{back}<span>{event.event_type_label}</span></nav>
    <div className="opportunity-layout">
      <article className="opportunity-content">
        <figure className="opportunity-cover"><OpportunityCover event={event} fetchPriority="high"/><figcaption>{event.event_type_label}</figcaption></figure>
        <header className="opportunity-heading"><p className="eyebrow">{event.organizer||event.source}</p><h1 ref={heading} tabIndex={-1}>{event.title}</h1><div className="card-tags">{event.tags.map(tag=><span key={tag.value||tag.label}>{tag.label}</span>)}</div></header>
        <div className={`opportunity-availability ${expired?'is-expired':''}`} role="status"><Icon name="clock"/><span>{t(expired?'expired':event.status==='self_paced'?'selfPaced':event.status==='check_source'?'checkSource':'open')}</span>{expired&&<p>{t('expiredPageNote')}</p>}</div>
        <section className="opportunity-section"><h2>{t('aboutOpportunity')}</h2><p>{event.description||t('unknown')}</p></section>
        {event.requirements&&<section className="opportunity-section"><h2>{t('requirements')}</h2><p>{event.requirements}</p></section>}
        <section className="opportunity-section"><h2>{t('organizer')}</h2><p>{event.organizer||event.source}</p>{event.url&&<a className="opportunity-source" href={safeExternal(event.url)} target="_blank" rel="noopener noreferrer">{t('source')}<Icon name="external"/></a>}</section>
      </article>
      <aside className="opportunity-sidebar" aria-label={t('participationDetails')}>
        <div className="opportunity-summary"><p className="eyebrow">{t('participationDetails')}</p><div className="opportunity-price"><Price event={event}/></div>
          <dl className="opportunity-facts"><Fact label={t('format')}>{event.format_label}</Fact><Fact label={t('country')}>{event.country_label}</Fact>{event.city&&event.city!=='any'&&<Fact label={t('city')}>{event.city_label}</Fact>}<Fact label={t('ageRange')}>{age}</Fact><Fact label={t('deadline')}>{event.is_self_paced&&!event.deadline?t('selfPaced'):date(event.deadline)}</Fact><Fact label={t('startDate')}>{date(event.start_at)}</Fact><Fact label={t('eventLanguage')}>{event.participation_language||t('unknown')}</Fact></dl>
          <div className="opportunity-actions">{!expired&&event.registration_url&&<AsyncButton className="button primary" data-action="registration" onClick={async()=>{const result=await api.registration(event.id);location.assign(safeExternal(result.url));}}>{t('registration')}<Icon name="external"/></AsyncButton>}
          {user?<FavoriteButton event={event} sheet onSaved={saved=>setEvent(value=>({...value,saved}))}/>:<Button kind="line" action="login-to-save" onClick={requestLogin}><Icon name="heart"/>{t('loginToSave')}</Button>}
          {!expired&&<AsyncButton className="button secondary" data-action="subscribe" onClick={async()=>{
            if(!user){requestLogin();return;}
            const enabled=!event.subscribed;await api.subscribe(event.id,enabled);setEvent(value=>({...value,subscribed:enabled}));
            toast(t(!user.telegram_linked?'linkTelegram':!user.notifications.deadlines?'enableDeadlines':enabled?'subscribed':'unsubscribe'));
          }}><Icon name="bell"/>{t(event.subscribed?'unsubscribe':'subscribe')}</AsyncButton>}</div>
          {!user&&<p className="opportunity-signin-note">{t('publicOpportunityHint')}</p>}
          <div className="opportunity-utilities"><AsyncButton className="text-button" data-action="share" onClick={share}><Icon name="share"/>{t('share')}</AsyncButton><button className="text-button" type="button" data-action="report" onClick={()=>user?setModal({type:'report',eventId:event.id}):requestLogin()}><Icon name="flag"/>{t('report')}</button></div>
          <p className="opportunity-note">{t('conditionsNote')}</p>{event.verified_at&&<p className="opportunity-verified">{t('sourceChecked')}: {date(event.verified_at)}</p>}
        </div>
      </aside>
    </div>
  </main>;
}
