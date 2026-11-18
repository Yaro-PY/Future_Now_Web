import {useEffect,useRef,useState} from 'react';
import {useApp} from '../context.jsx';
import {startElectronicSpider} from '../effects/electronicSpider.js';
import {isFreeBackground,isSpiderPixel} from '../effects/spiderInteraction.js';
import {Button,Dialog} from './Common.jsx';
import {Icon} from './Icons.jsx';
import {SpiderAssistant} from './SpiderAssistant.jsx';
import {useSiteAssistant} from '../hooks/useSiteAssistant.js';
import './electronic-spider.css';

const sessionKey='future-now.spider.hidden';
function hiddenThisSession() {
  try {return sessionStorage.getItem(sessionKey)==='1';} catch {return false;}
}

export function ElectronicSpider() {
  const {language,modal,menuOpen,user,route}=useApp();
  const enabled=user?.appearance?.spider_enabled!==false && route!=='welcome';
  const accent=user?.appearance?.accent||'blue';
  const palette={blue:[215,'#2563eb'],lemon:[54,'#a39100'],orange:[26,'#cb600b'],red:[2,'#c33936'],green:[146,'#168354']};
  const assistant=useSiteAssistant();
  const canvas=useRef(null);
  const engine=useRef(null);
  const panelRef=useRef(null);
  const [hidden,setHidden]=useState(hiddenThisSession);
  const [panel,setPanel]=useState(null);
  const uk=language!=='en';
  panelRef.current=Boolean(panel||modal||menuOpen);
  useEffect(()=>{
    if(hidden||!enabled) return;
    const element=canvas.current;
    const controller=startElectronicSpider(element,{hue:palette[accent][0],color:palette[accent][1]});
    engine.current=controller;
    let press=null;
    function onPress(event) {press={x:event.clientX,y:event.clientY};}
    function onClick(event) {
      if(panelRef.current||event.defaultPrevented||event.button!==0||event.detail===0||
          event.ctrlKey||event.metaKey||event.altKey||event.shiftKey||document.querySelector('dialog[open]')) return;
      if(!press||Math.hypot(event.clientX-press.x,event.clientY-press.y)>8||!isFreeBackground(event.target)) return;
      if(!isSpiderPixel(element,event.clientX,event.clientY,event.pointerType==='touch'?7:3)) return;
      if(window.getSelection()?.toString()) return;
      event.preventDefault();event.stopPropagation();
      setPanel('menu');
    }
    window.addEventListener('pointerdown',onPress,{capture:true,passive:true});
    window.addEventListener('click',onClick,true);
    return ()=>{
      window.removeEventListener('pointerdown',onPress,true);
      window.removeEventListener('click',onClick,true);
      controller.destroy();engine.current=null;
    };
  },[hidden,enabled,accent]);
  useEffect(()=>{
    engine.current?.setPaused(Boolean(panel||modal||menuOpen));
  },[hidden,enabled,accent,panel,modal,menuOpen]);
  useEffect(()=>{
    if(!panel) return;
    const previous=document.body.style.overflow;
    document.body.style.overflow='hidden';
    return ()=>{document.body.style.overflow=previous;};
  },[panel]);
  function hide() {
    try {sessionStorage.setItem(sessionKey,'1');} catch { /* Keep the current page hidden even when storage is unavailable. */ }
    setPanel(null);setHidden(true);
  }
  useEffect(()=>{
    if(!enabled)setPanel(null);
  },[enabled]);
  useEffect(()=>{
    const update=event=>{if(event.detail?.spider_enabled){try{sessionStorage.removeItem(sessionKey);}catch{}setHidden(false);}};
    window.addEventListener('future-now:appearance',update);
    return ()=>window.removeEventListener('future-now:appearance',update);
  },[]);
  if(hidden||!enabled) return null;
  return <>
    <canvas ref={canvas} className="electronic-spider" aria-hidden="true" />
    <button type="button" className="sr-only spider-keyboard-access" data-spider-ui data-action="spider-menu" onClick={()=>setPanel('menu')}>{uk?'Відкрити меню Гоші':'Open Gosha’s menu'}</button>
    {panel==='menu'&&<Dialog id="spider-menu" className="modal spider-menu" title={uk?'Гоша помічник':'Gosha the assistant'} onClose={()=>setPanel(null)}>
      <div className="modal-body" data-spider-ui>
        <p>{uk?'Обери, що зробити.':'Choose an action.'}</p>
        <div className="spider-actions">
          <Button kind="secondary" action="spider-assistant" onClick={()=>setPanel('assistant')}><Icon name="spark"/><span>{uk?'Помічник по сайту':'Site assistant'}</span><Icon name="arrow"/></Button>
          <Button kind="line" action="spider-hide" onClick={hide}><Icon name="close"/>{uk?'Приховати на цю сесію':'Hide for this session'}</Button>
        </div>
        <p className="spider-session-note">{uk?'Приховування діє в цій вкладці, зокрема після оновлення сторінки.':'Stays hidden in this tab, including after a page refresh.'}</p>
      </div>
    </Dialog>}
    {panel==='assistant'&&<SpiderAssistant onClose={()=>setPanel(null)} onBack={()=>setPanel('menu')} assistant={assistant}/>}
  </>;
}
