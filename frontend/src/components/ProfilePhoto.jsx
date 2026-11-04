import {useEffect, useRef, useState} from 'react';
import {useApp, initial} from '../context.jsx';
import {AsyncButton, Button} from './Common.jsx';

export function Avatar({user,className='avatar'}) {
  const [failed,setFailed]=useState(null);
  useEffect(()=>setFailed(null),[user.avatar_url,user.public_id]);
  return <span className={className}>{user.avatar_url && failed!==user.avatar_url ? <img src={user.avatar_url} alt="" onError={()=>setFailed(user.avatar_url)}/> : initial(user.display_name || user.nickname || '')}</span>;
}

export function ProfilePhoto() {
  const {api,user,setUser,t,toast,errorMessage}=useApp();
  const input=useRef(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  async function upload(event){
    const file=event.target.files?.[0];event.target.value='';if(!file)return;
    setError('');
    if(file.size>2*1024*1024){setError(t('photoSize'));return;}
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)){setError(t('photoFormats'));return;}
    setBusy(true);
    try{setUser(await api.uploadAvatar(file));toast(t('photoSaved'));}catch(problem){setError(errorMessage(problem));}finally{setBusy(false);}
  }
  return <section className="profile-photo-editor" aria-label={t('profilePhoto')}><div className="photo-actions"><input ref={input} type="file" accept="image/jpeg,image/png,image/webp" aria-label={t('choosePhoto')} onChange={upload} hidden disabled={busy}/><Button kind="secondary" action="choose-photo" onClick={()=>input.current.click()} disabled={busy}>{t(busy ? 'uploadingPhoto' : 'choosePhoto')}</Button>{user.avatar_url && <AsyncButton className="button line" data-action="remove-photo" disabled={busy} onClick={async()=>{setUser(await api.removeAvatar());toast(t('photoRemoved'));}}>{t('removePhoto')}</AsyncButton>}</div><p className="subtext">{t('photoHelp')}</p>{error && <p className="form-error" role="alert">{error}</p>}</section>;
}
