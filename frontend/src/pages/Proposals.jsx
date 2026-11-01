import {useState} from 'react';
import {useApp} from '../context.jsx';
import {Icon} from '../components/Icons.jsx';
import {Button, Criteria, DataForm, Empty, Field, Select, Skeletons, Submit} from '../components/Common.jsx';
import {PageHeading} from '../components/Layout.jsx';
import {Pagination} from './Catalog.jsx';

export function ProposalForm({item, owner = false}) {
  const {api, t, options, toast, go, reload, setModal} = useApp();
  const editing = Boolean(item);
  const [conflict, setConflict] = useState(false);
  const original = item?.payload || {};
  const [draft, setDraft] = useState(() => {
    const criteria = [...(original.criteria || [])];
    if (original.is_free === true && !criteria.includes('free')) criteria.push('free');
    if (original.is_free === false && !criteria.includes('paid')) criteria.push('paid');
    return {type:original.event_type || 'course',country:original.country || 'ukraine',city:original.city || 'any',format:original.format || 'online',topics:original.topics || [],criteria};
  });
  const update = (key, value) => setDraft(old => ({...old,[key]:value,...(key === 'country' && value !== 'ukraine' ? {city:'any'} : {})}));
  async function save(data) {
    const min_age = data.get('min_age') === '' ? null : Number(data.get('min_age'));
    const max_age = data.get('max_age') === '' ? null : Number(data.get('max_age'));
    if (min_age != null && max_age != null && min_age > max_age) throw new Error(t('ageRange'));
    const payload = {...original,title:String(data.get('title')).trim(),description:String(data.get('description')).trim(),url:String(data.get('url')).trim(),event_type:draft.type,
      topics:draft.topics,country:draft.country,city:draft.country === 'ukraine' && draft.city !== 'any' ? draft.city : '',format:draft.format,
      min_age,max_age,deadline:data.get('deadline') ? `${data.get('deadline')}T00:00:00` : null,
      is_free:draft.criteria.includes('free') ? true : draft.criteria.includes('paid') ? false : null,criteria:draft.criteria};
    if (editing) {
      try {
        if (owner) await api.editProposal(item,payload);
        else await api.request(`/admin/proposals/${item.id}`,{method:'PATCH',body:{...payload,expected_revision:item.revision}});
      } catch (error) { if (error.status === 409) setConflict(true); throw error; }
      setModal(null); toast(t('savedNotice')); reload();
    } else { await api.suggest(payload); toast(t('proposalSent')); go('proposals'); }
  }
  return <DataForm className="proposal-form" kind="proposal" data-editing={editing || undefined} onSubmit={save}><div className="notice"><Icon name="shield" /><span>{t('moderationNote')}</span></div><div className="form-grid">
    <label className="field full"><span>{t('title')}</span><input name="title" minLength={8} maxLength={150} required defaultValue={original.title || ''} placeholder={t('titlePlaceholder')} /></label>
    <label className="field full"><span>{t('url')}</span><input name="url" type="url" required maxLength={2000} defaultValue={original.url || ''} placeholder="https://" readOnly={editing && !owner} /></label>
    <label className="field full"><span>{t('description')}</span><textarea name="description" minLength={40} maxLength={1500} required defaultValue={original.description || ''} placeholder={t('descriptionPlaceholder')} /></label>
    <Select name="type" label={t('type')} value={draft.type} onChange={value => update('type',value)} excludeAny required /><Select name="country" label={t('country')} value={draft.country} onChange={value => update('country',value)} excludeAny required />
    <div data-city-field hidden={draft.country !== 'ukraine'}><Select name="city" label={t('city')} value={draft.city} onChange={value => update('city',value)} /></div><Select name="format" label={t('format')} value={draft.format} onChange={value => update('format',value)} excludeAny required extra={[{value:'unknown',label:t('unknown')}]} />
    <div className="field"><span>{t('ageRange')} <span className="muted">({t('optional')})</span></span><div className="two-inputs"><input name="min_age" type="number" min="0" max="100" defaultValue={original.min_age ?? ''} aria-label={t('minAge')} placeholder={t('minAge')} /><input name="max_age" type="number" min="0" max="100" defaultValue={original.max_age ?? ''} aria-label={t('maxAge')} placeholder={t('maxAge')} /></div></div>
    <Field name="deadline" label={`${t('deadline')} (${t('optional')})`} type="date" value={original.deadline?.slice(0,10)} />
    <div className="field full"><span>{t('topics')}</span><div className="tag-options">{options('tags').map(row => <label key={row.value} className="tag-option"><input name="topics" type="checkbox" value={row.value} checked={draft.topics.includes(row.value)} onChange={event => update('topics',event.target.checked ? [...draft.topics,row.value] : draft.topics.filter(value => value !== row.value))} /><span>{row.label}</span></label>)}</div></div>
    <div className="field full"><span>{t('criteria')}</span><Criteria chips value={draft.criteria} onChange={value => update('criteria',value)} /></div>
  </div>{conflict && <div className="notice"><span>{t('proposalConflictDraft')} <button type="button" className="text-button" data-action="reload-proposal" onClick={() => { setModal(null); reload(); }}>{t('reloadProposals')}</button></span></div>}<div className="form-actions"><Submit>{t(editing ? 'save' : 'sendProposal')}<Icon name="arrow" /></Submit></div></DataForm>;
}
export function SuggestPage() {
  return <main className="page content-page" id="main-content"><PageHeading title="suggestTitle" subtitle="suggestSubtitle" action={false} /><ProposalForm /></main>;
}
export function ProposalsPage({embedded = false}) {
  const {route, proposalPage, proposalError, t, date, setModal, setDetailId, go, reload} = useApp();
  const admin = route === 'moderation';
  let content;
  if (proposalError) content = <Empty title="emptyTitle" text="serviceError" action="reload" actionLabel="retry" onAction={reload} />;
  else if (!proposalPage) content = <Skeletons />;
  else if (!proposalPage.items.length) content = <Empty title={admin ? 'moderationEmpty' : 'proposalsEmpty'} text={admin ? 'moderationSubtitle' : 'proposalsEmptyText'} symbol="spark" action={admin ? 'explore' : 'suggest'} actionLabel={admin ? 'explore' : 'suggest'} onAction={() => go(admin ? 'explore' : 'suggest')} />;
  else content = <><div className="proposal-rows">{proposalPage.items.map(item => <article key={item.id} className="proposal-row"><div className="proposal-main"><p className="eyebrow">#{item.id} · {date(item.created_at)}</p><h2>{item.payload.title}</h2><span className={`status ${item.status}`}>{t(item.status)}</span>{item.review_note && <p className="review-note">{t('reviewNote')}: {item.review_note}</p>}</div>{admin ? <Button kind="line" action="review" data-id={item.id} onClick={() => setModal({type:'review',item})}>{t('review')}<Icon name="arrow" /></Button> : <div className="proposal-actions">{item.status === 'pending' && <><Button kind="line" action="edit-own-proposal" onClick={() => setModal({type:'edit-own-proposal',item})}>{t('edit')}</Button><Button kind="line" action="withdraw-proposal" onClick={() => setModal({type:'withdraw-proposal',item})}>{t('withdrawProposal')}</Button></>}{item.event_id && <Button kind="line" action="detail" aria-label={t('details')} onClick={() => setDetailId(item.event_id)}><Icon name="arrow" /></Button>}</div>}</article>)}</div><Pagination result={proposalPage} /></>;
  if (embedded) return <section id="proposal-collection">{content}</section>;
  return <main className="page content-page" id="main-content"><PageHeading title={admin ? 'moderationTitle' : 'myProposalsTitle'} subtitle={admin ? 'moderationSubtitle' : 'myProposalsSubtitle'} action={!admin} /><section id="proposal-collection">{content}</section></main>;
}
