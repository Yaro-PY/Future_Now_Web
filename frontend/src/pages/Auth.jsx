import {useEffect, useState} from 'react';
import {useApp} from '../context.jsx';
import {LoginSecondFactor} from './Security.jsx';
import {Icon, Logo} from '../components/Icons.jsx';
import {DataForm, Field, LanguageSwitch, Password, Submit} from '../components/Common.jsx';

export function AuthPage() {
  const {api, t, language, enter, setModal} = useApp();
  const [mode, setMode] = useState('login');
  const [pending, setPending] = useState(null);
  const [draft, setDraft] = useState({nickname:'',display_name:''});
  const registering = mode === 'register';
  useEffect(()=>{if(pending)window.scrollTo({top:0,behavior:'instant'});},[pending?.challenge_token]);
  async function authenticate(data) {
    const nickname = String(data.get('nickname')).trim();
    const password = String(data.get('password'));
    if (registering && password !== data.get('confirmation')) throw new Error(t('mismatch'));
    const session = registering ? await api.register({nickname,display_name:String(data.get('display_name')).trim(),password,language}) : await api.login(nickname,password);
    if (session.two_factor_required) { setPending(session); return; }
    await enter(session);
  }
  return <div className={`auth-scene ${registering ? 'auth-registration' : ''} ${pending ? 'auth-verification' : ''}`}><img className="auth-background" src="/assets/images/earthrise.jpg" alt="" fetchPriority="high" />
    <header className="auth-header"><a className="brand" href="#explore" aria-label="Future Now"><Logo /></a><LanguageSwitch /></header>
    <main className="auth-grid"><section className="auth-story" aria-labelledby="brand-title"><p className="eyebrow">{t('brandEyebrow')}</p><h1 id="brand-title" className="auth-brand"><span>Future</span><span>Now<span className="brand-dot">.</span></span></h1><h2>{t('authHeadline')}</h2><p className="auth-description">{t('authStory')}</p><button type="button" className="text-button" data-action="how" onClick={() => setModal({type:'how'})}>{t('howItWorks')}<Icon name="arrow" /></button></section>
      <section className="auth-form-panel" aria-labelledby="auth-title"><h2 id="auth-title">{t(pending ? 'twoFactorLoginTitle' : registering ? 'registerTitle' : 'loginTitle')}</h2><p className="subtext">{t(pending ? 'twoFactorLoginHelp' : registering ? 'registerSubtitle' : 'loginSubtitle')}</p>
        {!pending && <div className="auth-tabs" role="tablist" aria-label={t('login')}>{['login','register'].map(value => <button key={value} type="button" role="tab" aria-selected={mode === value} className={mode === value ? 'active' : ''} data-auth={value} onClick={() => setMode(value)}>{t(value)}</button>)}</div>}
        {pending ? <LoginSecondFactor key={pending.challenge_token} challenge={pending} onCancel={()=>setPending(null)}/> : <DataForm key={mode} className="auth-form" kind="auth" onSubmit={authenticate} onChange={event => { if (['nickname','display_name'].includes(event.target.name)) setDraft(value => ({...value,[event.target.name]:event.target.value})); }}>
          {registering && <Field name="display_name" label={t('name')} value={draft.display_name} required minLength={2} maxLength={80} autoComplete="name" />}
          <Field name="nickname" label={t('nickname')} value={draft.nickname} required minLength={3} maxLength={32} autoComplete="username" autoCapitalize="none" spellCheck={false} placeholder="yaro_ua" />
          <Password name="password" label={t('password')} autoComplete={registering ? 'new-password' : 'current-password'} minLength={registering ? 8 : 1} />
          {registering && <Password name="confirmation" label={t('confirmPassword')} autoComplete="new-password" minLength={8} />}{registering && <p className="subtext">{t('passwordHint')}</p>}
          <Submit wide>{t(registering ? 'register' : 'continue')}<Icon name="arrow" /></Submit>
        </DataForm>}{!registering && !pending && <button type="button" className="text-button recovery-link" data-action="recover-access" onClick={() => setModal({type:'recover-access'})}>{t('forgotPassword')}</button>}<div className="auth-bot-note">{t('botLoginHint')}<br /><button type="button" data-action="bot-help" onClick={() => setModal({type:'bot-help'})}>{t('howItWorks')} <Icon name="external" /></button></div>
      </section></main><footer className="auth-footer"><span>{t('authFooter')}</span><span className="coordinates">MADE FOR WHAT’S NEXT</span></footer>
  </div>;
}
