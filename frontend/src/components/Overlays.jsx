import {useEffect, useState} from 'react';
import {useApp, BOT_URL, imageFor, safeExternal} from '../context.jsx';
import {Icon} from './Icons.jsx';
import {AsyncButton, Button, Close, Criteria, DataForm, Dialog, Field, Select, Skeletons, Submit} from './Common.jsx';
import {FavoriteButton, FilterForm, Price} from '../pages/Catalog.jsx';
import {ProposalForm} from '../pages/Proposals.jsx';
import {PublishedEditor, ReportReview} from '../pages/Administration.jsx';

function Fact({label, children}) { return <div><dt>{label}</dt><dd>{children}</dd></div>; }
export function DetailSheet({id}) {
  const {api, user, t, date, language, setDetailId, setModal, toast, fail} = useApp();
  const [event, setEvent] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    setEvent(null); setError(false);
    api.detail(id).then(result => { if (active) setEvent(result); }).catch(problem => { if (active) { setError(true); fail(problem); } });
    return () => { active = false; };
  }, [id,language]);
  async function share() {
    const url = safeExternal(event.url);
    if (navigator.clipboard?.writeText) {
      try { await navigator.clipboard.writeText(url); toast(t('copied')); return; } catch { /* Show a selectable URL if clipboard access is unavailable. */ }
    }
    setModal({type:'share',url});
  }
  const close = () => setDetailId(null);
  return <Dialog id="sheet" title={t('details')} className="detail-sheet" onClose={close} heading={false}>
    {!event ? <><div className="modal-head"><span /><Close action="close-sheet" onClick={close} /></div><div className="sheet-body">{error ? <p role="alert">{t('serviceError')}</p> : <Skeletons />}</div></> : <>
      <div className="sheet-toolbar"><Close className="sheet-close" action="close-sheet" onClick={close} /></div>
      <div className="sheet-image"><img src={`/assets/images/${imageFor(event)}.jpg`} alt="" /></div>
      <div className="sheet-body"><p className="eyebrow">{event.event_type_label}</p><h2>{event.title}</h2><div className="card-tags">{event.tags.map(tag => <span key={tag.value || tag.label}>{tag.label}</span>)}</div><div className="sheet-status"><Icon name="clock" />{t(event.status === 'expired' ? 'expired' : event.status === 'self_paced' ? 'selfPaced' : event.status === 'check_source' ? 'checkSource' : 'open')}</div>
        <dl className="detail-facts"><Fact label={t('country')}>{event.country_label}</Fact><Fact label={t('format')}>{event.format_label}</Fact><Fact label={t('deadline')}>{event.is_self_paced && !event.deadline ? t('selfPaced') : date(event.deadline)}</Fact><Fact label={t('ageRange')}>{event.min_age === 0 && event.max_age == null ? t('noAgeRestriction') : event.min_age == null && event.max_age == null ? t('unknown') : `${event.min_age ?? '…'}–${event.max_age ?? '…'}`}</Fact><Fact label={t('criteria')}><Price event={event} /></Fact><Fact label={t('city')}>{event.city_label || t('unknown')}</Fact></dl>
        <section className="sheet-section"><h3>{t('aboutOpportunity')}</h3><p>{event.description || t('unknown')}</p></section><section className="sheet-section"><h3>{t('organizer')}</h3><p>{event.organizer || event.source}</p></section>{event.requirements && <section className="sheet-section"><h3>{t('requirements')}</h3><p>{event.requirements}</p></section>}
        <dl className="detail-facts"><Fact label={t('startDate')}>{date(event.start_at)}</Fact><Fact label={t('eventLanguage')}>{event.participation_language || t('unknown')}</Fact>{event.verified_at && <Fact label={t('sourceChecked')}>{date(event.verified_at)}</Fact>}</dl>
        <div className="sheet-actions">{event.status !== 'expired' && event.registration_url && <AsyncButton className="button primary" data-action="registration" onClick={async () => { const result = await api.registration(id); location.assign(safeExternal(result.url)); }}>{t('registration')}<Icon name="external" /></AsyncButton>}
          <FavoriteButton event={event} sheet onSaved={saved => setEvent(value => ({...value,saved}))} />
          <AsyncButton className="button secondary" data-action="subscribe" onClick={async () => {
            const enabled = !event.subscribed;
            await api.subscribe(id,enabled); setEvent(value => ({...value,subscribed:enabled}));
            toast(t(!user.telegram_linked ? 'linkTelegram' : !user.notifications.deadlines ? 'enableDeadlines' : enabled ? 'subscribed' : 'unsubscribe'));
          }}><Icon name="bell" /><span>{t(event.subscribed ? 'unsubscribe' : 'subscribe')}</span></AsyncButton>
        </div><div className="sheet-utilities"><AsyncButton className="text-button" data-action="share" onClick={share}><Icon name="share" />{t('share')}</AsyncButton><button type="button" className="text-button" data-action="report" onClick={() => setModal({type:'report',eventId:id})}><Icon name="flag" />{t('report')}</button></div><p className="sheet-note">{t('conditionsNote')}</p>
      </div></>}
  </Dialog>;
}

function Onboarding() {
  const {user, setUser, api, t, filters, applyFilters, go} = useApp();
  const start = user.onboarding_required ? 0 : 2;
  const [step, setStep] = useState(start);
  const [draft, setDraft] = useState({nickname:user.nickname,display_name:user.display_name,age:user.profile?.age || '',country:user.profile?.country || 'any',city:user.profile?.city || 'any',format:user.profile?.format || 'any',criteria:user.profile?.criteria || []});
  const [preferences, setPreferences] = useState(filters);
  const update = (key, value) => setDraft(old => ({...old,[key]:value,...(key === 'country' && value !== 'ukraine' ? {city:'any'} : {})}));
  const titleKey = ['onboardingAge','onboardingLocation','onboardingFilters'][step];
  async function advance() {
    if (step === 0) { setStep(1); return; }
    if (step === 1) {
      const next = await api.saveProfile(draft); setUser(next); setPreferences(next.filters); setStep(2); return;
    }
    await api.saveFilters(preferences);
    setUser(await api.me()); applyFilters(preferences); go('explore');
  }
  return <Dialog title={t(`${titleKey}Title`)} heading={false} dismissible={false}><div className="onboarding"><div className="onboarding-top"><span className="eyebrow">{t('onboardingEyebrow')}</span><span className="step-label">{t('step',{step:step+1})}</span></div><progress max="3" value={step+1} aria-label={t('step',{step:step+1})} /><h2>{t(`${titleKey}Title`)}</h2><p>{t(`${titleKey}Text`)}</p>
    <DataForm kind="onboarding" key={step} onSubmit={advance}>
      {step === 0 && <div className="age-options">{['13-16','16-18','18+'].map(age => <label key={age} className="age-option"><input type="radio" name="age" value={age} checked={draft.age === age} onChange={() => update('age',age)} required /><span>{age.replace('-','–')}</span></label>)}</div>}
      {step === 1 && <><Select name="country" label={t('country')} value={draft.country} onChange={value => update('country',value)} /><div data-city-field hidden={draft.country !== 'ukraine'}><Select name="city" label={t('city')} value={draft.city} onChange={value => update('city',value)} /></div><Select name="format" label={t('format')} value={draft.format} onChange={value => update('format',value)} /></>}
      {step === 2 && <><Select name="type" label={t('type')} value={preferences.type} onChange={value => setPreferences(old => ({...old,type:value}))} /><p className="criteria-caption">{t('criteria')}</p><Criteria chips value={preferences.criteria} onChange={value => setPreferences(old => ({...old,criteria:value}))} /></>}
      <div className="onboarding-actions">{step > 0 && start === 0 ? <button type="button" className="text-button" data-action="onboarding-back" onClick={() => setStep(value => value - 1)}>{t('back')}</button> : <span />}<Submit>{t(step === 2 ? 'finish' : 'next')}<Icon name="arrow" /></Submit></div>
    </DataForm></div></Dialog>;
}

export function ModalContent() {
  const {modal, setModal, api, t, date, options, toast, reload, config} = useApp();
  const close = () => setModal(null);
  async function decide(decision, reason = '') {
    await api.request(`/admin/proposals/${modal.item.id}/decision`,{method:'POST',body:{decision,reason}});
    close(); toast(t('decisionSaved')); reload();
  }
  if (modal.type === 'onboarding') return <Onboarding />;
  if (modal.type === 'edit-published') return <Dialog title={t('editListing')} className="modal wide-modal" onClose={close}><PublishedEditor item={modal.item}/></Dialog>;
  if (modal.type === 'review-report') return <Dialog title={t('processReport')} onClose={close}><ReportReview item={modal.item}/></Dialog>;
  if (modal.type === 'sources') return <Dialog title={t('catalogSources')} onClose={close}><div className="modal-body"><p>{t('catalogSourceInfo')}</p><div className="source-list">{config?.catalog?.sources?.map(source => <article key={source.key}><a href={safeExternal(source.url)} target="_blank" rel="noopener noreferrer">{source.name}<Icon name="external" /></a><span>{t(source.status === 'ok' ? 'sourceOk' : source.status === 'partial' ? 'sourcePartial' : 'sourceFailed')}</span><small>{source.last_success_at ? t('catalogUpdated',{date:date(source.last_success_at)}) : t('catalogNeverChecked')}</small></article>)}</div></div></Dialog>;
  if (modal.type === 'filters') return <Dialog title={t('filters')} onClose={close}><div className="modal-body filter-modal"><FilterForm /></div></Dialog>;
  if (['how','bot-help'].includes(modal.type)) return <Dialog title={t('howItWorks')} onClose={close}><div className="modal-body"><p>{modal.type === 'bot-help' ? t('botPasswordHint') : ['aboutText','aboutOneText','aboutTwoText','aboutThreeText'].map(key => t(key)).join('\n\n')}</p><div className="form-actions"><a className="button primary" href={BOT_URL} target="_blank" rel="noopener noreferrer">{t('openBot')}<Icon name="external" /></a></div></div></Dialog>;
  if (modal.type === 'share') return <Dialog title={t('share')} onClose={close}><div className="modal-body"><Field name="share_url" label={t('source')} value={modal.url} readOnly /></div></Dialog>;
  if (modal.type === 'report') return <Dialog title={t('reportTitle')} onClose={close}><div className="modal-body"><DataForm kind="report" onSubmit={async data => { await api.report({event_id:modal.eventId,category:String(data.get('category')),message:String(data.get('message')).trim()}); close(); toast(t('reportSent')); }}><label className="field"><span>{t('reportCategory')}</span><select name="category">{['bad_info','bad_link','broken_link','ended','other'].map(key => <option key={key} value={key}>{t(key)}</option>)}</select></label><label className="field"><span>{t('reportMessage')}</span><textarea name="message" required minLength={1} maxLength={2000} /></label><div className="form-actions"><Submit>{t('sendReport')}<Icon name="arrow" /></Submit></div></DataForm></div></Dialog>;
  if (modal.type === 'edit-proposal') return <Dialog title={t('edit')} className="modal wide-modal" onClose={close}><div className="modal-body"><ProposalForm item={modal.item} /></div></Dialog>;
  if (modal.type === 'reject') return <Dialog title={t('reject')} onClose={close}><div className="modal-body"><DataForm kind="reject" onSubmit={data => decide('rejected',String(data.get('reason')))}><label className="field"><span>{t('rejectReason')}</span><textarea name="reason" required minLength={5} maxLength={500} /></label><div className="form-actions"><Submit>{t('reject')}</Submit></div></DataForm></div></Dialog>;
  if (modal.type === 'review') {
    const item = modal.item;
    return <Dialog title={t('review')} onClose={close}><div className="modal-body"><p className="eyebrow">#{item.id}</p><h3 className="review-title">{item.payload.title}</h3><p>{item.payload.description}</p><p className="review-source"><a href={safeExternal(item.payload.url)} target="_blank" rel="noopener noreferrer">{t('source')} <Icon name="external" /></a></p><div className="review-facts"><p>{t('deadline')}: {date(item.payload.deadline)}</p><p>{t('format')}: {options('format').find(row => row.value === item.payload.format)?.label || t('unknown')}</p></div><div className="form-actions"><Button kind="line" action="edit-proposal" onClick={() => setModal({type:'edit-proposal',item})}>{t('edit')}</Button><Button kind="secondary" action="reject" onClick={() => setModal({type:'reject',item})}>{t('reject')}</Button><AsyncButton className="button primary" data-action="approve" onClick={() => decide('approved')}>{t('approve')}<Icon name="check" /></AsyncButton></div></div></Dialog>;
  }
  return null;
}
