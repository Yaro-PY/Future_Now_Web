import {useEffect,useState} from 'react';
import {useApp} from '../context.jsx';
import {DataForm,Submit} from '../components/Common.jsx';

export function AppearanceSettings(){
  const {user,setUser,api,t,toast}=useApp();
  const [draft,setDraft]=useState(user.appearance||{accent:'blue',spider_enabled:true});
  useEffect(()=>setDraft(user.appearance||{accent:'blue',spider_enabled:true}),[user.appearance]);
  return <DataForm kind="appearance" className="form-section" onSubmit={async()=>{
    const next=await api.saveSettings({appearance:draft});setUser(next);
    window.dispatchEvent(new CustomEvent('future-now:appearance',{detail:next.appearance}));toast(t('savedNotice'));
  }}><h2>{t('appearanceTitle')}</h2><p className="subtext appearance-help">{t('appearanceHelp')}</p>
    <fieldset className="accent-options"><legend>{t('accentColor')}</legend><div className="accent-choices">{['blue','lemon','orange','red','green'].map(color=><label key={color} className={`accent-choice accent-${color}`}><input type="radio" name="accent" value={color} checked={draft.accent===color} onChange={()=>setDraft(value=>({...value,accent:color}))}/><span className="accent-swatch" aria-hidden="true"/><span>{t(`accent_${color}`)}</span></label>)}</div></fieldset>
    <label className="toggle-row"><span><strong>{t('spiderEnabled')}</strong><small>{t('spiderEnabledHelp')}</small></span><input type="checkbox" name="spider_enabled" checked={draft.spider_enabled} onChange={event=>setDraft(value=>({...value,spider_enabled:event.target.checked}))}/></label>
    <div className="form-actions"><Submit>{t('save')}</Submit></div>
  </DataForm>;
}
