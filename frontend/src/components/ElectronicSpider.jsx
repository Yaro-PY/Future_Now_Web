import {useEffect,useRef,useState} from 'react';
import {useApp} from '../context.jsx';
import {startElectronicSpider} from '../effects/electronicSpider.js';
import {isFreeBackground,isSpiderPixel} from '../effects/spiderInteraction.js';
import {Button,Dialog} from './Common.jsx';
import {Icon} from './Icons.jsx';
import {SpiderAssistant} from './SpiderAssistant.jsx';
import './electronic-spider.css';

const sessionKey='future-now.spider.hidden';
function hiddenThisSession() {
  try {return sessionStorage.getItem(sessionKey)==='1';} catch {return false;}
}

export function ElectronicSpider() {
  const {language,modal,detailId,menuOpen}=useApp();
  const canvas=useRef(null);
  const engine=useRef(null);
  const panelRef=useRef(null);
  const [hidden,setHidden]=useState(hiddenThisSession);
  const [panel,setPanel]=useState(null);
  const uk=language!=='en';
  panelRef.current=Boolean(panel||modal||detailId!=null||menuOpen);
  useEffect(()=>{
    if(hidden) return;
    const element=canvas.current;
    const controller=startElectronicSpider(element);
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
  },[hidden]);
  useEffect(()=>{
    engine.current?.setPaused(Boolean(panel||modal||detailId!=null||menuOpen));
  },[hidden,panel,modal,detailId,menuOpen]);
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
  if(hidden) return null;
  return <>
    <canvas ref={canvas} className="electronic-spider" aria-hidden="true" />
    <button type="button" className="sr-only spider-keyboard-access" data-spider-ui data-action="spider-menu" onClick={()=>setPanel('menu')}>{uk?'Відкрити меню павука':'Open spider menu'}</button>
    {panel==='menu'&&<Dialog id="spider-menu" className="modal spider-menu" title={uk?'Меню павука':'Spider menu'} onClose={()=>setPanel(null)}>
      <div className="modal-body" data-spider-ui>
        <p>{uk?'Обери, що зробити.':'Choose an action.'}</p>
        <div className="spider-actions">
          <Button kind="secondary" action="spider-assistant" onClick={()=>setPanel('assistant')}><Icon name="spark"/><span>{uk?'Відкрити ШІ по сайту':'Open the site AI assistant'}</span><Icon name="arrow"/></Button>
          <Button kind="line" action="spider-hide" onClick={hide}><Icon name="close"/>{uk?'Приховати на цю сесію':'Hide for this session'}</Button>
        </div>
        <p className="spider-session-note">{uk?'Приховування діє в цій вкладці, зокрема після оновлення сторінки.':'Stays hidden in this tab, including after a page refresh.'}</p>
      </div>
    </Dialog>}
    {panel==='assistant'&&<SpiderAssistant onClose={()=>setPanel(null)} onBack={()=>setPanel('menu')}/>}
  </>;
}
