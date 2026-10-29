import {useState} from 'react';
import {useApp, BOT_URL} from '../context.jsx';
import {PageHeading} from '../components/Layout.jsx';
import {Icon} from '../components/Icons.jsx';
import {Button, DataForm, Submit} from '../components/Common.jsx';

export function HelpPage() {
  const {t,api,toast,go} = useApp();
  const [query,setQuery] = useState('');
  const entries = ['Account','Filters','Saved','Expired','Proposals','Notifications'].filter(key => `${t(`faq${key}Title`)} ${t(`faq${key}Text`)}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  return <main className="page content-page" id="main-content"><PageHeading title="helpTitle" subtitle="helpSubtitle" action={false} />
    <div className="help-layout"><section className="help-guides"><label className="search-box"><span className="sr-only">{t('findAnswer')}</span><Icon name="search" /><input type="search" name="help_query" value={query} onChange={event => setQuery(event.target.value)} placeholder={t('findAnswer')} /></label>
      <div className="help-questions">{entries.map(key => <details key={key}><summary>{t(`faq${key}Title`)}<Icon name="plus" /></summary><p>{t(`faq${key}Text`)}</p></details>)}{!entries.length && <p className="section-empty">{t('noAnswers')}</p>}</div>
      <div className="help-shortcuts"><Button kind="line" onClick={() => go('profile')}>{t('profile')}<Icon name="user" /></Button><Button kind="line" onClick={() => go('settings')}>{t('settings')}<Icon name="settings" /></Button><a className="button line" href={BOT_URL} target="_blank" rel="noopener noreferrer">{t('openBot')}<Icon name="external" /></a></div>
    </section><section className="help-contact"><h2>{t('contactSupport')}</h2><p>{t('contactSupportText')}</p><DataForm kind="support" onSubmit={async data => {
      await api.report({event_id:null,category:String(data.get('category')),message:String(data.get('message')).trim()});
      toast(t('reportSent'));
    }}><label className="field"><span>{t('reportCategory')}</span><select name="category">{['bad_info','bad_link','broken_link','ended','other'].map(key => <option key={key} value={key}>{t(key)}</option>)}</select></label><label className="field"><span>{t('reportMessage')}</span><textarea name="message" required minLength={5} maxLength={2000} /></label><div className="form-actions"><Submit>{t('sendReport')}<Icon name="arrow" /></Submit></div></DataForm></section></div>
  </main>;
}
