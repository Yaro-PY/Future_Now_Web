import {useEffect, useState} from 'react';
import {useApp} from '../context.jsx';
import {Button, DataForm, Dialog, Field, Password, Submit} from '../components/Common.jsx';
import {Icon} from '../components/Icons.jsx';

function Expiry({seconds = 300}) {
  const {t} = useApp();
  const [left,setLeft] = useState(seconds);
  useEffect(() => { const end=Date.now()+seconds*1000; const id=setInterval(()=>setLeft(Math.max(0,Math.ceil((end-Date.now())/1000))),1000); return ()=>clearInterval(id); },[seconds]);
  return <p className="verification-expiry" role="timer">{left ? t('codeExpires',{time:`${Math.floor(left/60)}:${String(left%60).padStart(2,'0')}`}) : t('codeExpired')}</p>;
}

export function FactorFields({challenge, forcedMethod}) {
  const {t} = useApp();
  const available=forcedMethod ? [forcedMethod] : challenge.methods.filter(value=>value!=='none');
  const [method,setMethod]=useState(available[0] || 'totp');
  return <><label className="field"><span>{t('verificationMethod')}</span><select name="method" value={method} onChange={event=>setMethod(event.target.value)}>{available.map(value=><option key={value} value={value}>{t(`factor_${value}`)}</option>)}</select></label>
    {method==='telegram' && <div className="telegram-verification"><p>{t('telegramCodeHelp')}</p><a className="button secondary" data-action="request-telegram-code" href={challenge.telegram_url} target="_blank" rel="noopener noreferrer">{t('openBot')}<Icon name="external" /></a></div>}
    {method==='recovery' && <p className="verification-note">{t('recoveryCodeHelp')}</p>}
    <Field key={method} name="code" label={t(method==='recovery' ? 'recoveryCode' : 'verificationCode')} required minLength={method==='recovery' ? 10 : 6} maxLength={method==='recovery' ? 32 : 6} pattern={method==='recovery' ? undefined : '[0-9]{6}'} inputMode={method==='recovery' ? 'text' : 'numeric'} autoComplete="one-time-code" autoCapitalize="characters" spellCheck={false} />
    <Expiry seconds={challenge.expires_in || 300} />
  </>;
}

export function LoginSecondFactor({challenge,onCancel}) {
  const {api,enter,t} = useApp();
  return <DataForm className="auth-form second-factor-form" kind="second-factor-login" onSubmit={async data=>{ const session=await api.verifyTwoFactor({challenge_token:challenge.challenge_token,method:String(data.get('method')),code:String(data.get('code')).trim()}); await enter(session); }}>
    <FactorFields challenge={challenge} /><Submit wide>{t('verifyAndSignIn')}<Icon name="arrow" /></Submit><button type="button" className="text-button verification-back" data-action="cancel-second-factor" onClick={async()=>{await api.cancelTwoFactor();onCancel();}}>{t('backToLogin')}</button>
  </DataForm>;
}

export function SecuritySettings() {
  const {api,t,setModal} = useApp();
  const [status,setStatus]=useState(null),[error,setError]=useState(false),[revision,setRevision]=useState(0);
  useEffect(()=>{let active=true;setError(false);api.security().then(value=>{if(active)setStatus(value);}).catch(()=>{if(active)setError(true);});return()=>{active=false;};},[revision]);
  function open(action){setModal({type:'security-wizard',action,onComplete:()=>setRevision(value=>value+1)});}
  return <section className="form-section security-settings"><h2>{t('twoFactorTitle')}</h2><p className="subtext">{t('twoFactorDescription')}</p>
    {error ? <p role="alert">{t('serviceError')}</p> : !status ? <p className="subtext">{t('loadingSecurity')}</p> : <>
      {!status.configured && <p className="notice">{t('twoFactorUnavailable')}</p>}
      {['totp','telegram'].map(method=><div className="security-method" key={method}><div><h3>{t(`factor_${method}`)}</h3><p>{t(method==='totp' ? 'authenticatorDescription' : status.telegram_available ? 'telegramFactorDescription' : 'telegramFactorNeedsLink')}</p><span className={`status ${status[`${method}_enabled`] ? 'approved' : ''}`}>{t(status[`${method}_enabled`] ? 'enabled' : 'disabled')}</span></div><Button kind="secondary" action={`security-${method}`} disabled={!status.configured || method==='telegram' && !status.telegram_available} onClick={()=>open(`${method}_${status[`${method}_enabled`] ? 'disable' : 'setup'}`)}>{t(status[`${method}_enabled`] ? 'disableFactor' : 'enableFactor')}</Button></div>)}
      {(status.totp_enabled || status.telegram_enabled) && <div className="security-method"><div><h3>{t('recoveryCodes')}</h3><p>{t('recoveryCodesRemaining',{count:status.recovery_codes_remaining})}</p></div><Button kind="line" action="regenerate-recovery-codes" onClick={()=>open('recovery_codes')}>{t('regenerateCodes')}</Button></div>}
    </>}
  </section>;
}

export function SecurityWizard() {
  const {api,t,modal,setModal,toast} = useApp();
  const [phase,setPhase]=useState('password'),[challenge,setChallenge]=useState(null),[setup,setSetup]=useState(null),[codes,setCodes]=useState([]),[ack,setAck]=useState(false),[copied,setCopied]=useState(false);
  const title=t(modal.action==='totp_setup' ? 'setupAuthenticator' : modal.action==='telegram_setup' ? 'setupTelegramFactor' : modal.action==='recovery_codes' ? 'recoveryCodes' : 'disableFactorTitle');
  const close=()=>setModal(null);
  function done(result){modal.onComplete?.();if(result.recovery_codes?.length){setCodes(result.recovery_codes);setPhase('codes');}else{close();toast(t('securitySaved'));}}
  async function execute(authorization){
    if(modal.action==='recovery_codes'){done(await api.request('/me/security/recovery-codes',{method:'POST',body:authorization}));return;}
    const [method,action]=modal.action.split('_');
    const result=await api.request(`/me/security/${method}/${action}`,{method:'POST',body:authorization});
    if(action==='disable'){done(result);return;}
    setSetup(result);setPhase(method==='totp' ? 'totp' : 'telegram');
  }
  const restart=()=>{setPhase('password');setChallenge(null);setSetup(null);};
  return <Dialog title={phase==='codes' ? t('recoveryCodes') : title} onClose={close} dismissible={phase!=='codes'}><div className="modal-body security-wizard">
    {phase==='password' && <><p>{t('securityPasswordHelp')}</p><DataForm kind="security-authorize" onSubmit={async data=>{const value=await api.authorizeSecurity(String(data.get('current_password')));setChallenge(value);if(value.methods.includes('none'))await execute({challenge_token:value.challenge_token,method:'none',code:''});else setPhase('authorize');}}><Password name="current_password" label={t('currentPassword')} /><div className="form-actions"><Submit>{t('continue')}</Submit></div></DataForm></>}
    {phase==='authorize' && <DataForm kind="security-factor" onSubmit={data=>execute({challenge_token:challenge.challenge_token,method:String(data.get('method')),code:String(data.get('code')).trim()})}><p>{t('securityFactorHelp')}</p><FactorFields challenge={challenge}/><div className="form-actions"><Submit>{t('confirmSecurityAction')}</Submit></div></DataForm>}
    {phase==='totp' && <><p>{t('scanAuthenticatorQR')}</p><img className="totp-qr" src={setup.qr_code} alt={t('authenticatorQR')} /><details className="manual-secret"><summary>{t('manualSetup')}</summary><Field name="totp_secret" label={t('setupKey')} value={setup.secret} readOnly autoComplete="off" /></details><DataForm kind="totp-confirm" onSubmit={async data=>done(await api.request('/me/security/totp/enable',{method:'POST',body:{setup_token:setup.setup_token,code:String(data.get('code'))}}))}><Field name="code" label={t('verificationCode')} required minLength={6} maxLength={6} pattern="[0-9]{6}" inputMode="numeric" autoComplete="one-time-code" /><div className="form-actions"><Submit>{t('enableFactor')}</Submit></div></DataForm></>}
    {phase==='telegram' && <DataForm kind="telegram-confirm" onSubmit={async data=>done(await api.request('/me/security/telegram/enable',{method:'POST',body:{challenge_token:setup.challenge_token,method:'telegram',code:String(data.get('code'))}}))}><p>{t('telegramEnrollmentHelp')}</p><FactorFields challenge={setup} forcedMethod="telegram"/><div className="form-actions"><Submit>{t('enableFactor')}</Submit></div></DataForm>}
    {phase==='codes' && <><p>{t('saveRecoveryCodes')}</p><div className="recovery-code-grid">{codes.map(code=><code key={code}>{code}</code>)}</div><Button kind="secondary" action="copy-recovery-codes" onClick={async()=>{try{await navigator.clipboard.writeText(codes.join('\n'));setCopied(true);}catch{toast(t('copyCodesManually'));}}}>{t(copied ? 'copied' : 'copyRecoveryCodes')}</Button><label className="check-label recovery-ack"><input type="checkbox" checked={ack} onChange={event=>setAck(event.target.checked)}/><span>{t('savedRecoveryCodes')}</span></label><div className="form-actions"><Button disabled={!ack} action="finish-security-setup" onClick={close}>{t('doneSecurity')}</Button></div></>}
    {['authorize','totp','telegram'].includes(phase) && <button type="button" className="text-button verification-back" data-action="restart-security-setup" onClick={restart}>{t('restartVerification')}</button>}
  </div></Dialog>;
}
