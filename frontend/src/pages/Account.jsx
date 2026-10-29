import {useState} from 'react';
import {useApp, BOT_URL, initial} from '../context.jsx';
import {Icon} from '../components/Icons.jsx';
import {Criteria, DataForm, Field, LanguageSwitch, Password, Select, Submit} from '../components/Common.jsx';
import {AccountRail, PageHeading} from '../components/Layout.jsx';

export function ProfilePage() {
  const {user, setUser, api, t, toast, applyFilters} = useApp();
  const [draft, setDraft] = useState(user.profile || {});
  const update = (key, value) => setDraft(old => ({...old,[key]:value,...(key === 'country' && value !== 'ukraine' ? {city:'any'} : {})}));
  async function save(data) {
    const profile = Object.fromEntries(['age','country','city','format'].map(key => [key,draft[key] || 'any']));
    Object.assign(profile,{nickname:String(data.get('nickname')).trim(),display_name:String(data.get('display_name')).trim(),criteria:draft.criteria || []});
    const next = await api.saveProfile(profile);
    setUser(next); setDraft(next.profile); applyFilters(next.filters); toast(t('savedNotice'));
  }
  return <main className="page content-page" id="main-content"><PageHeading title="profileTitle" subtitle="profileSubtitle" action={false} /><div className="content-layout"><AccountRail /><section>
    <div className="profile-intro"><div className="avatar">{initial(user.display_name || '')}</div><div><h2>{user.display_name}</h2><p>@{user.nickname}</p><span className="account-status"><Icon name={user.telegram_linked ? 'check' : 'user'} />{t(user.telegram_linked ? 'sharedAccount' : 'websiteAccount')}</span></div></div>
    <DataForm kind="profile" onSubmit={save}><section className="form-section"><h2>{t('personalInfo')}</h2><div className="form-grid"><Field name="display_name" label={t('name')} value={user.display_name} required minLength={2} maxLength={80} autoComplete="name" /><Field name="nickname" label={t('nickname')} value={user.nickname} required minLength={3} maxLength={32} autoComplete="username" autoCapitalize="none" /></div></section>
      <section className="form-section"><h2>{t('preferences')}</h2><div className="form-grid"><Select name="age" label={t('age')} value={draft.age || ''} onChange={value => update('age',value)} excludeAny required /><Select name="country" label={t('country')} value={draft.country} onChange={value => update('country',value)} /><div data-city-field hidden={draft.country !== 'ukraine'}><Select name="city" label={t('city')} value={draft.city} onChange={value => update('city',value)} /></div><Select name="format" label={t('format')} value={draft.format} onChange={value => update('format',value)} /></div><div className="criteria-caption profile-criteria">{t('criteria')}</div><Criteria chips value={draft.criteria || []} onChange={value => update('criteria',value)} /></section>
      <div className="form-actions"><Submit>{t('save')}<Icon name="arrow" /></Submit></div>
    </DataForm></section></div></main>;
}
export function SettingsPage() {
  const {user, setUser, api, t, toast, passwordChanged} = useApp();
  return <main className="page content-page" id="main-content"><PageHeading title="settingsTitle" subtitle="settingsSubtitle" action={false} /><div className="content-layout"><AccountRail /><section>
    <section className="form-section"><h2>{t('language')}</h2><LanguageSwitch /></section>
    <DataForm kind="notifications" className="form-section" onSubmit={async data => { setUser(await api.saveSettings({notifications:{new:data.has('new'),deadlines:data.has('deadlines'),expired:data.has('expired')}})); toast(t('savedNotice')); }}><h2>{t('notifications')}</h2>
      {!user.telegram_linked && <div className="notice"><Icon name="bell" /><span>{t('linkTelegram')} <a href={BOT_URL} target="_blank" rel="noopener noreferrer">{t('openBot')}</a></span></div>}
      {[['new','notifyNew','notifyNewText'],['deadlines','notifyDeadlines','notifyDeadlinesText'],['expired','notifyExpired','notifyExpiredText']].map(([key,title,description]) => <label key={key} className="toggle-row"><span><strong>{t(title)}</strong><small>{t(description)}</small></span><input type="checkbox" name={key} defaultChecked={user.notifications[key]} /></label>)}<div className="form-actions"><Submit>{t('save')}</Submit></div>
    </DataForm>
    <DataForm kind="password" className="form-section" onSubmit={async data => {
      if (data.get('new_password') !== data.get('confirmation')) throw new Error(t('mismatch'));
      await api.changePassword(String(data.get('current_password')),String(data.get('new_password'))); passwordChanged();
    }}><h2>{t('security')}</h2><div className="stack"><Password name="current_password" label={t('currentPassword')} /><Password name="new_password" label={t('newPassword')} autoComplete="new-password" minLength={12} /><Password name="confirmation" label={t('confirmPassword')} autoComplete="new-password" minLength={12} /></div><div className="form-actions"><Submit kind="secondary">{t('changePassword')}</Submit></div></DataForm>
  </section></div></main>;
}
export function AboutPage() {
  const {t} = useApp();
  return <main className="page content-page" id="main-content"><section className="about-intro"><div><p className="eyebrow">FUTURE NOW</p><h1>{t('aboutTitle')}</h1><p>{t('aboutText')}</p><a className="button primary" href={BOT_URL} target="_blank" rel="noopener noreferrer">{t('openBot')}<Icon name="external" /></a></div><img className="about-image" src="/assets/images/community.jpg" alt="" /></section><section className="about-steps">{['One','Two','Three'].map((key,index) => <article key={key}><span className="about-step-number">0{index+1}</span><h2>{t(`about${key}`)}</h2><p>{t(`about${key}Text`)}</p></article>)}</section></main>;
}
