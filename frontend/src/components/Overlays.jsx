import {useEffect, useState} from 'react';
import {useApp, BOT_URL, imageFor, safeExternal} from '../context.jsx';
import {Icon} from './Icons.jsx';
import {AsyncButton, Button, Close, Criteria, DataForm, Dialog, Field, Select, Skeletons, Submit} from './Common.jsx';
import {FilterForm} from '../pages/Catalog.jsx';
import {ProposalForm} from '../pages/Proposals.jsx';
import {SecurityWizard} from '../pages/Security.jsx';
import {AccountActions} from '../pages/AccountActions.jsx';
import {PublishedEditor, ReportReview} from '../pages/Administration.jsx';

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
      {step === 0 && <div className="age-options">{['12-14','14-17','18+'].map(age => <label key={age} className="age-option"><input type="radio" name="age" value={age} checked={draft.age === age} onChange={() => update('age',age)} required /><span>{age.replace('-','–')}</span></label>)}</div>}
      {step === 1 && <><Select name="country" label={t('country')} value={draft.country} onChange={value => update('country',value)} /><div data-city-field hidden={draft.country !== 'ukraine'}><Select name="city" label={t('city')} value={draft.city} onChange={value => update('city',value)} /></div><Select name="format" label={t('format')} value={draft.format} onChange={value => update('format',value)} /></>}
      {step === 2 && <><Select name="type" label={t('type')} value={preferences.type} onChange={value => setPreferences(old => ({...old,type:value}))} /><p className="criteria-caption">{t('criteria')}</p><Criteria chips value={preferences.criteria} onChange={value => setPreferences(old => ({...old,criteria:value}))} /></>}
      <div className="onboarding-actions">{step > 0 && start === 0 ? <button type="button" className="text-button" data-action="onboarding-back" onClick={() => setStep(value => value - 1)}>{t('back')}</button> : <span />}<Submit>{t(step === 2 ? 'finish' : 'next')}<Icon name="arrow" /></Submit></div>
    </DataForm></div></Dialog>;
}

export function ModalContent() {
  const {modal, setModal, api, t, date, options, toast, reload, config} = useApp();
  const close = () => setModal(null);
  async function decide(decision, reason = '') {
    await api.request(`/admin/proposals/${modal.item.id}/decision`,{method:'POST',body:{decision,reason,expected_revision:modal.item.revision}});
    close(); toast(t('decisionSaved')); reload();
  }
  if (modal.type === 'security-wizard') return <SecurityWizard />;
  if (modal.type === 'onboarding') return <Onboarding />;
  if (modal.type === 'edit-published') return <Dialog title={t('editListing')} className="modal wide-modal" onClose={close}><PublishedEditor item={modal.item}/></Dialog>;
  if (modal.type === 'review-report') return <Dialog title={t('processReport')} onClose={close}><ReportReview item={modal.item}/></Dialog>;
  if (['recover-access','delete-account','withdraw-proposal'].includes(modal.type)) return <AccountActions />;
  if (modal.type === 'edit-own-proposal') return <Dialog title={t('edit')} className="modal wide-modal" onClose={close}><div className="modal-body"><ProposalForm key={`${modal.item.id}:${modal.item.revision}`} item={modal.item} owner /></div></Dialog>;
  if (modal.type === 'sources') return <Dialog title={t('catalogSources')} onClose={close}><div className="modal-body"><p>{t('catalogSourceInfo')}</p><div className="source-list">{config?.catalog?.sources?.map(source => <article key={source.key}><a href={safeExternal(source.url)} target="_blank" rel="noopener noreferrer">{source.name}<Icon name="external" /></a><span>{t(source.status === 'ok' ? 'sourceOk' : source.status === 'partial' ? 'sourcePartial' : 'sourceFailed')}</span><small>{source.last_success_at ? t('catalogUpdated',{date:date(source.last_success_at)}) : t('catalogNeverChecked')}</small></article>)}</div></div></Dialog>;
  if (modal.type === 'filters') return <Dialog title={t('filters')} onClose={close}><div className="modal-body filter-modal"><FilterForm /></div></Dialog>;
  if (['how','bot-help'].includes(modal.type)) return <Dialog title={t('howItWorks')} onClose={close}><div className="modal-body"><p>{modal.type === 'bot-help' ? t('botPasswordHint') : ['aboutText','aboutOneText','aboutTwoText','aboutThreeText'].map(key => t(key)).join('\n\n')}</p><div className="form-actions"><a className="button primary" href={BOT_URL} target="_blank" rel="noopener noreferrer">{t('openBot')}<Icon name="external" /></a></div></div></Dialog>;
  if (modal.type === 'share') return <Dialog title={t('share')} onClose={close}><div className="modal-body"><Field name="share_url" label={t('source')} value={modal.url} readOnly /></div></Dialog>;
  if (modal.type === 'report') return <Dialog title={t('reportTitle')} onClose={close}><div className="modal-body"><DataForm kind="report" onSubmit={async data => { await api.report({event_id:modal.eventId,category:String(data.get('category')),message:String(data.get('message')).trim()}); close(); toast(t('reportSent')); }}><label className="field"><span>{t('reportCategory')}</span><select name="category">{['bad_info','bad_link','broken_link','ended','other'].map(key => <option key={key} value={key}>{t(key)}</option>)}</select></label><label className="field"><span>{t('reportMessage')}</span><textarea name="message" required minLength={1} maxLength={2000} /></label><div className="form-actions"><Submit>{t('sendReport')}<Icon name="arrow" /></Submit></div></DataForm></div></Dialog>;
  if (modal.type === 'edit-proposal') return <Dialog title={t('edit')} className="modal wide-modal" onClose={close}><div className="modal-body"><ProposalForm item={modal.item} /></div></Dialog>;
  if (modal.type === 'reject') return <Dialog title={t('reject')} onClose={close}><div className="modal-body"><DataForm kind="reject" onSubmit={data => decide('rejected',String(data.get('reason')))}><label className="field"><span>{t('rejectReason')}</span><textarea name="reason" required minLength={5} maxLength={500} /></label><div className="form-actions"><Submit>{t('reject')}</Submit></div></DataForm></div></Dialog>;
  if (modal.type === 'review') {
    const item = modal.item;
    return <Dialog title={t('review')} onClose={close}><div className="modal-body"><p className="eyebrow">#{item.id}</p><h3 className="review-title">{item.payload.title}</h3>{item.cover_url && <img className="cover-editor-preview review-cover" src={item.cover_url} alt={t('listingCover')} />}<p>{item.payload.description}</p><p className="review-source"><a href={safeExternal(item.payload.url)} target="_blank" rel="noopener noreferrer">{t('source')} <Icon name="external" /></a></p><div className="review-facts"><p>{t('deadline')}: {date(item.payload.deadline)}</p><p>{t('format')}: {options('format').find(row => row.value === item.payload.format)?.label || t('unknown')}</p></div><div className="form-actions"><Button kind="line" action="edit-proposal" onClick={() => setModal({type:'edit-proposal',item})}>{t('edit')}</Button><Button kind="secondary" action="reject" onClick={() => setModal({type:'reject',item})}>{t('reject')}</Button><AsyncButton className="button primary" data-action="approve" onClick={() => decide('approved')}>{t('approve')}<Icon name="check" /></AsyncButton></div></div></Dialog>;
  }
  return null;
}
