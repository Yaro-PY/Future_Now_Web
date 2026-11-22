import {useEffect,useState} from 'react';
import {useApp} from '../context.jsx';
import {DataForm,Submit} from '../components/Common.jsx';

export function AppearanceSettings(){
  const {user,setUser,api,t,toast}=useApp();
  const accent = user.appearance?.accent || 'blue';
  const ludicrous = user.appearance?.spider_ludicrous ?? false;
  const [draft,setDraft] = useState({accent,spider_ludicrous:ludicrous});
  useEffect(() => setDraft({accent,spider_ludicrous:ludicrous}), [accent,ludicrous]);
  return <DataForm kind="appearance" className="form-section" onSubmit={async()=>{
    const next = await api.saveSettings({appearance:draft});
    const {accent,spider_ludicrous} = next.appearance;
    setUser(current => current?.public_id === next.public_id
      ? {...current,appearance:{...current.appearance,accent,spider_ludicrous}} : current);
    toast(t('savedNotice'));
  }}><h2>{t('appearanceTitle')}</h2><p className="subtext appearance-help">{t('appearanceHelp')}</p>
    <fieldset className="accent-options"><legend>{t('accentColor')}</legend><div className="accent-choices">{['blue','lemon','orange','red','green'].map(color=><label key={color} className={`accent-choice accent-${color}`}><input type="radio" name="accent" value={color} checked={draft.accent===color} onChange={()=>setDraft(value=>({...value,accent:color}))}/><span className="accent-swatch" aria-hidden="true"/><span>{t(`accent_${color}`)}</span></label>)}</div></fieldset>
    <label className="toggle-row"><span><strong>{t('spiderLudicrous')}</strong><small>{t('spiderLudicrousHelp')}</small></span><input type="checkbox" name="spider_ludicrous" checked={draft.spider_ludicrous} onChange={event=>setDraft(value=>({...value,spider_ludicrous:event.target.checked}))}/></label>
    <div className="form-actions"><Submit>{t('save')}</Submit></div>
  </DataForm>;
}
