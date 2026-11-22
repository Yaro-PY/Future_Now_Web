import {useEffect, useRef, useState} from 'react';
import {useApp} from '../context.jsx';
import {startElectronicSpider} from '../effects/electronicSpider.js';
import {isSpiderPixel} from '../effects/spiderInteraction.js';
import {Button, Dialog} from './Common.jsx';
import {Icon} from './Icons.jsx';
import {SpiderAssistant} from './SpiderAssistant.jsx';
import {useAssistantSession} from './SiteAssistantSession.jsx';
import './electronic-spider.css';

const palette = {blue:[215,'#2563eb'],lemon:[54,'#a39100'],orange:[26,'#cb600b'],red:[2,'#c33936'],green:[146,'#168354']};

export function ElectronicSpider() {
  const {language, modal, menuOpen, user} = useApp();
  const accent = user?.appearance?.accent || 'blue';
  const followPointer = user?.appearance?.spider_ludicrous ?? false;
  const assistant = useAssistantSession();
  const canvas = useRef(null);
  const engine = useRef(null);
  const press = useRef(null);
  const [panel, setPanel] = useState(null);
  const uk = language !== 'en';
  const title = uk ? 'Гоша помічник' : 'Gosha the assistant';
  const paused = Boolean(panel || modal || menuOpen);

  useEffect(() => {
    const [hue,color] = palette[accent];
    const controller = startElectronicSpider(canvas.current, {hue,color,followPointer});
    engine.current = controller;
    return () => { controller.destroy(); engine.current = null; };
  }, [accent,followPointer]);
  useEffect(() => {
    engine.current?.setPaused(paused);
  }, [accent,followPointer,paused]);
  useEffect(() => {
    if (!panel) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previous; };
  }, [panel]);

  function openFromCanvas(event) {
    const down = press.current;
    press.current = null;
    if (event.target !== event.currentTarget || paused || event.button !== 0 || event.detail === 0 ||
        event.ctrlKey || event.metaKey || event.altKey || event.shiftKey || document.querySelector('dialog[open]')) return;
    if (!down || Math.hypot(event.clientX-down.x,event.clientY-down.y) > 8 || window.getSelection()?.toString()) return;
    if (isSpiderPixel(canvas.current,event.clientX,event.clientY,down.touch ? 7 : 3)) setPanel('menu');
  }

  return <aside className="spider-area" aria-label={title}
    onPointerDown={event => { press.current = {x:event.clientX,y:event.clientY,touch:event.pointerType==='touch'}; }}
    onPointerCancel={() => { press.current = null; }} onClick={openFromCanvas}>
    <canvas ref={canvas} className="electronic-spider" aria-hidden="true" />
    <button type="button" className="sr-only spider-keyboard-access" data-action="spider-menu" onClick={() => setPanel('menu')}>
      {uk ? 'Відкрити меню Гоші' : 'Open Gosha’s menu'}
    </button>
    {panel === 'menu' && <Dialog id="spider-menu" className="modal spider-menu" title={title} onClose={() => setPanel(null)}>
      <div className="modal-body spider-actions">
        <Button kind="secondary" action="spider-assistant" onClick={() => setPanel('assistant')}><Icon name="spark"/><span>{uk?'Помічник по сайту':'Site assistant'}</span><Icon name="arrow"/></Button>
      </div>
    </Dialog>}
    {panel === 'assistant' && <SpiderAssistant onClose={() => setPanel(null)} onBack={() => setPanel('menu')} assistant={assistant}/>}
  </aside>;
}
