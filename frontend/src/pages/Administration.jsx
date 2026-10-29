import {useEffect, useState} from 'react';
import {useApp} from '../context.jsx';
import {useRemoteResource} from '../hooks/useRemoteResource.js';
import {useDebouncedValue} from '../hooks/useDebouncedValue.js';
import {Button, DataForm, Dialog, Empty, Field, Select, Skeletons, Submit} from '../components/Common.jsx';
import {PageHeading} from '../components/Layout.jsx';
import {Icon} from '../components/Icons.jsx';
import {Pagination} from './Catalog.jsx';
import {ProposalsPage} from './Proposals.jsx';

const reportStatuses=['new','in_progress','resolved','dismissed'];
export function AdministrationPage(){
 const {api,t,language,page,setPage,resourceRevision,fail,setModal,setDetailId,date,reload}=useApp();
 const [tab,setTab]=useState('proposals'); const [query,setQuery]=useState('');
 const [listingState,setListingState]=useState('all'); const [reportState,setReportState]=useState('open');
 const search=useDebouncedValue(query.trim());
 const resource=useRemoteResource({enabled:tab!=='proposals',resourceKey:JSON.stringify([tab,search,listingState,reportState,page,language,resourceRevision]),
  load:async()=>({...await api.request(tab==='published'?`/admin/opportunities?q=${encodeURIComponent(search)}&state=${listingState}&page=${page}`:`/admin/reports?status=${reportState}&page=${page}`),kind:tab}),
  onLoad:result=>{if(page>result.pages)setPage(result.pages);},onError:fail});
 function switchTab(next){setTab(next);setPage(1);}
 function updateFilter(setter,value){setter(value);setPage(1);}
 let content;
 if(tab==='proposals')content=<ProposalsPage embedded />;
 else if(resource.error)content=<Empty title="emptyTitle" text="serviceError" action="reload" actionLabel="retry" onAction={reload}/>;
 else if(!resource.data||resource.data.kind!==tab)content=<Skeletons/>;
 else if(!resource.data.items.length)content=<div className="admin-empty"><Icon name="check"/><h2>{t('adminEmpty')}</h2><p>{t(tab==='reports'?'reportsEmptyText':'publishedEmptyText')}</p></div>;
 else content=<><p className="results-caption">{t('resultCount',{count:resource.data.total})}</p><div className="admin-rows">{resource.data.items.map(item=>tab==='published'?<article key={item.id} className="admin-row" data-listing-id={item.id}>
  <div><p className="eyebrow">#{item.id} · {item.values.source}</p><h2>{item.values.title}</h2><div className="admin-meta"><span className={`status ${item.status==='expired'?'rejected':'approved'}`}>{t(item.status==='expired'?'expired':item.status==='self_paced'?'selfPaced':item.status==='check_source'?'checkSource':'open')}</span>{item.overridden_fields.length>0&&<span>{t('manuallyEdited')}</span>}<span>{date(item.admin_updated_at||item.updated_at)}</span></div></div>
  <div className="admin-row-actions"><Button kind="line" action="detail" onClick={()=>setDetailId(item.id)} aria-label={t('details')}><Icon name="external"/></Button><Button kind="secondary" action="edit-published" onClick={()=>setModal({type:'edit-published',item})}>{t('edit')}<Icon name="arrow"/></Button></div>
 </article>:<article key={item.id} className="admin-row" data-report-id={item.id}>
  <div><p className="eyebrow">#{item.id} · {t(item.category)} · {date(item.created_at)}</p><h2>{item.event_title||t('generalReport')}</h2><p className="report-excerpt">{item.message}</p><span className={`status report-${item.status}`}>{t(`report_${item.status}`)}</span></div>
  <Button kind="secondary" action="review-report" onClick={()=>setModal({type:'review-report',item})}>{t('processReport')}<Icon name="arrow"/></Button>
 </article>)}</div><Pagination result={resource.data}/></>;
 return <main className="page admin-page" id="main-content"><PageHeading title="administrationTitle" subtitle="administrationSubtitle" action={false}/>
  <nav className="admin-tabs" aria-label={t('administrationTitle')}>{['proposals','published','reports'].map(key=><button key={key} type="button" data-admin-tab={key} aria-current={tab===key?'page':undefined} onClick={()=>switchTab(key)}>{t(`admin_${key}`)}</button>)}</nav>
  {tab!=='proposals'&&<div className="admin-tools">{tab==='published'?<><label className="search-box"><span className="sr-only">{t('searchPublished')}</span><Icon name="search"/><input type="search" name="admin_query" value={query} onChange={event=>updateFilter(setQuery,event.target.value)} placeholder={t('searchPublished')}/></label><label className="field"><span className="sr-only">{t('statusFilter')}</span><select name="listing_state" value={listingState} onChange={event=>updateFilter(setListingState,event.target.value)}>{['all','available','expired'].map(key=><option key={key} value={key}>{t(`listing_${key}`)}</option>)}</select></label></>:<label className="field"><span className="sr-only">{t('statusFilter')}</span><select name="report_status" value={reportState} onChange={event=>updateFilter(setReportState,event.target.value)}>{['open','all',...reportStatuses].map(key=><option key={key} value={key}>{t(`report_${key}`)}</option>)}</select></label>}<Button kind="line" action="reload-admin" onClick={reload}><Icon name="refresh"/>{t('refreshCatalog')}</Button></div>}
  <section aria-live="polite">{content}</section></main>;
}

export function PublishedEditor({item}){
 const {api,t,options,toast,reload,setModal}=useApp(); const [record,setRecord]=useState(null); const [error,setError]=useState(null); const [conflict,setConflict]=useState(false);
 async function load(){setRecord(null);setError(null);setConflict(false);try{setRecord(await api.request(`/admin/opportunities/${item.id}`));}catch(problem){setError(problem);}}
 useEffect(()=>{let active=true;api.request(`/admin/opportunities/${item.id}`).then(value=>{if(active)setRecord(value);}).catch(problem=>{if(active)setError(problem);});return()=>{active=false;};},[item.id]);
 if(error)return <div className="modal-body"><p role="alert">{t('serviceError')}</p><Button kind="line" onClick={load}>{t('retry')}</Button></div>;
 if(!record)return <div className="modal-body"><Skeletons/></div>;
 return <PublishedForm key={record.revision} record={record} conflict={conflict} onReload={load} onSave={async values=>{try{await api.request(`/admin/opportunities/${record.id}`,{method:'PATCH',body:{expected_revision:record.revision,values}});setModal(null);reload();toast(t('savedNotice'));}catch(problem){if(problem.code==='edit_conflict')setConflict(true);throw problem;}}}/>;
}

function PublishedForm({record,conflict,onReload,onSave}){
 const {t,options}=useApp(); const original=record.values; const [draft,setDraft]=useState(original);
 const update=(key,value)=>setDraft(old=>({...old,[key]:value,...(key==='country'&&value!=='ukraine'?{city:''}:{})}));
 function price(value){setDraft(old=>({...old,is_free:value==='unknown'?null:value==='free',price_text:value==='free'?'Безкоштовно':old.is_free===false&&value==='paid'?old.price_text:'',criteria:old.criteria.filter(key=>!['free','paid'].includes(key))}));}
 async function save(data){
  const values={...draft};
  for(const key of ['title','description','url','organizer','participation_language','requirements','price_text'])values[key]=String(data.get(key)).trim();
  for(const key of ['min_age','max_age'])values[key]=data.get(key)===''?null:Number(data.get(key));
  for(const key of ['deadline','start_at']){const value=String(data.get(key));values[key]=value===(original[key]?.slice(0,16)||'')?original[key]:value?`${value}:00`:null;}
  values.city=values.country==='ukraine'?values.city:'';
  if(values.min_age!=null&&values.max_age!=null&&values.min_age>values.max_age)throw new Error(t('ageRange'));
  await onSave(values);
 }
 return <div className="modal-body"><p className="editor-notice">{t('sourceSafeEdits')}</p>{conflict&&<div className="editor-conflict" role="alert"><p>{t('editConflictText')}</p><Button kind="line" onClick={onReload}>{t('reloadRecord')}</Button></div>}
 <DataForm kind="published" onSubmit={save}><div className="form-grid">
  <Field name="title" label={t('title')} value={original.title} required maxLength={500} className="full"/>
  <Field name="url" label={t('url')} value={original.url} type="url" required maxLength={2000} className="full"/>
  <label className="field full"><span>{t('description')}</span><textarea name="description" defaultValue={original.description} maxLength={5000}/></label>
  <Select name="type" label={t('type')} value={draft.event_type} onChange={value=>update('event_type',value)} excludeAny/>
  <Select name="country" label={t('country')} value={draft.country} onChange={value=>update('country',value)} excludeAny/>
  <div hidden={draft.country!=='ukraine'}><Select name="city" label={t('city')} value={draft.city||'any'} onChange={value=>update('city',value==='any'?'':value)}/></div>
  <Select name="format" label={t('format')} value={draft.format} onChange={value=>update('format',value)} excludeAny extra={[{value:'unknown',label:t('unknown')}]}/>
  <Field name="min_age" label={t('minAge')} value={original.min_age??''} type="number" min={0} max={100}/><Field name="max_age" label={t('maxAge')} value={original.max_age??''} type="number" min={0} max={100}/>
  <Field name="deadline" label={t('deadline')} value={original.deadline?.slice(0,16)||''} type="datetime-local"/>
  <Field name="start_at" label={t('startDate')} value={original.start_at?.slice(0,16)||''} type="datetime-local"/>
  <label className="field"><span>{t('criteria')}</span><select name="price" value={draft.is_free===null?'unknown':draft.is_free?'free':'paid'} onChange={event=>price(event.target.value)}>{['unknown','free','paid'].map(key=><option key={key} value={key}>{t(key)}</option>)}</select></label>
  <label className="field"><span>{t('priceText')}</span><input name="price_text" maxLength={200} value={draft.price_text} onChange={event=>update('price_text',event.target.value)}/></label>
  <Field name="organizer" label={t('organizer')} value={original.organizer} maxLength={500}/><Field name="participation_language" label={t('eventLanguage')} value={original.participation_language} maxLength={100}/>
  <label className="field full"><span>{t('requirements')}</span><textarea name="requirements" defaultValue={original.requirements} maxLength={3000}/></label>
  <div className="field full"><span>{t('topics')}</span><div className="tag-options">{options('tags').map(row=><label key={row.value} className="tag-option"><input type="checkbox" checked={draft.topics.includes(row.value)} onChange={event=>update('topics',event.target.checked?[...draft.topics,row.value]:draft.topics.filter(key=>key!==row.value))}/><span>{row.label}</span></label>)}</div></div>
  <div className="field full"><span>{t('additionalCriteria')}</span><div className="tag-options">{['funded','travel'].map(key=><label className="tag-option" key={key}><input type="checkbox" checked={draft.criteria.includes(key)} onChange={event=>update('criteria',event.target.checked?[...draft.criteria,key]:draft.criteria.filter(value=>value!==key))}/><span>{t(key)}</span></label>)}</div></div>
  <div className="editor-switches full"><label><input name="is_self_paced" type="checkbox" checked={draft.is_self_paced} onChange={event=>update('is_self_paced',event.target.checked)}/>{t('selfPaced')}</label><label><input name="is_closed" type="checkbox" checked={draft.is_closed} onChange={event=>update('is_closed',event.target.checked)}/>{t('closeListing')}</label></div>
 </div><div className="form-actions"><Submit disabled={conflict}>{t('save')}<Icon name="check"/></Submit></div></DataForm></div>;
}

export function ReportReview({item}){
 const {api,t,date,toast,reload,setModal,setDetailId}=useApp(); const [status,setStatus]=useState(item.status); const [conflict,setConflict]=useState(false);
 return <div className="modal-body"><p className="eyebrow">#{item.id} · {t(item.category)} · {date(item.created_at)}</p><h3>{item.event_title||t('generalReport')}</h3><p className="report-message">{item.message}</p>
  {item.event_id&&<div className="report-actions"><Button kind="line" action="report-open-listing" onClick={()=>{setModal(null);setDetailId(item.event_id);}}>{t('details')}<Icon name="external"/></Button><Button kind="line" action="report-edit-listing" onClick={()=>setModal({type:'edit-published',item:{id:item.event_id}})}>{t('editListing')}<Icon name="arrow"/></Button></div>}
  {conflict&&<p className="editor-conflict" role="alert">{t('editConflictText')}</p>}
  <DataForm kind="report-review" onSubmit={async data=>{try{await api.request(`/admin/reports/${item.id}`,{method:'PATCH',body:{expected_revision:item.revision,status,review_note:String(data.get('review_note')).trim()}});setModal(null);reload();toast(t('reportProcessed'));}catch(problem){if(problem.code==='edit_conflict')setConflict(true);throw problem;}}}>
   <label className="field"><span>{t('reportStatus')}</span><select name="status" value={status} onChange={event=>setStatus(event.target.value)}>{reportStatuses.map(key=><option key={key} value={key}>{t(`report_${key}`)}</option>)}</select></label>
   <label className="field"><span>{t('resolutionNote')}</span><textarea name="review_note" defaultValue={item.review_note} required={['resolved','dismissed'].includes(status)} minLength={['resolved','dismissed'].includes(status)?5:0} maxLength={2000}/></label>
   <div className="form-actions">{conflict?<Button kind="line" onClick={()=>{setModal(null);reload();}}>{t('reloadRecord')}</Button>:<Submit>{t('save')}<Icon name="check"/></Submit>}</div>
  </DataForm></div>;
}
