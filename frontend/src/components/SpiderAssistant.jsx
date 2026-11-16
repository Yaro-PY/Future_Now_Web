import {useEffect,useRef,useState} from 'react';
import {useApp} from '../context.jsx';
import {Button,Dialog} from './Common.jsx';
import {Icon} from './Icons.jsx';

function CourseResult({event,onOpen}) {
  const {language,t,date}=useApp();
  const uk=language!=='en';
  const price=event.price.known?(event.price.is_free?t('free'):event.price.text||t('paid')):t('unknown');
  return <button type="button" className="assistant-course" data-action="assistant-course" data-id={event.id} onClick={()=>onOpen(event.id)}>
    <span className="assistant-course-title">{event.title}<Icon name="arrow"/></span>
    <span className="assistant-course-meta">{event.format_label} · {price}</span>
    <span className="assistant-course-source">{event.organizer||event.source}{event.min_age!=null&&<> · {event.min_age}{event.max_age!=null?`–${event.max_age}`:'+'} {uk?'років':'years'}</>}</span>
    {event.deadline&&<span className="assistant-course-source">{t('deadline')}: {date(event.deadline)}</span>}
    {!event.deadline&&event.is_self_paced&&<span className="assistant-course-source">{t('selfPaced')}</span>}
    {event.status==='check_source'&&<span className="assistant-course-source">{t('checkSource')}</span>}
  </button>;
}

export function SpiderAssistant({onClose,onBack,assistant}) {
  const {language,go,setDetailId,openAssistantCatalog}=useApp();
  const uk=language!=='en';
  const [question,setQuestion]=useState('');
  const list=useRef(null);
  const {messages,busy,send,clear}=assistant;
  useEffect(()=>{if(list.current) list.current.scrollTop=list.current.scrollHeight;},[messages,busy]);
  const last=messages.findLast(message=>message.role==='assistant'&&!message.failed);
  const suggestions=last?.suggestions||(uk?['Курси програмування','Безкоштовні онлайн-курси','Як зберегти курс?']:['Programming courses','Free online courses','How do I save a course?']);
  function ask(text,previous) {if(busy||!text.trim()) return;setQuestion('');send(text,previous);}
  function openCourse(id) {onClose();setDetailId(id);}
  return <Dialog id="spider-assistant" className="modal spider-assistant" title={uk?'Помічник по сайту':'Site assistant'} onClose={onClose}>
    <div className="modal-body" data-spider-ui>
      <div className="spider-assistant-status"><span>{uk?'Пошук у каталозі':'Catalogue search'}</span><div className="assistant-toolbar"><Button kind="line" action="assistant-clear" onClick={clear} aria-label={uk?'Нова розмова':'New conversation'} title={uk?'Нова розмова':'New conversation'}><Icon name="refresh"/></Button><Button kind="line" action="spider-back" onClick={onBack}><Icon name="arrow"/>{uk?'Меню павука':'Spider menu'}</Button></div></div>
      <div className="spider-messages" ref={list} role="log" aria-live="polite" aria-label={uk?'Розмова з помічником':'Assistant conversation'} aria-busy={busy}>
        {!messages.length&&<div className="spider-message assistant"><Icon name="spark"/><p>{uk?'Привіт! Допоможу знайти курс. Напиши, що хочеш вивчати, а за бажанням — формат, вік і бюджет. Наприклад: «безкоштовні онлайн-курси програмування».':'Hi! I can help you find a course. Tell me what you want to learn, and optionally the format, age and budget. For example: “free online programming courses”.'}</p></div>}
        {messages.map((message,index)=><div key={index} className={`spider-message ${message.role}${message.failed?' failed':''}`}>
          <p>{message.text}</p>
          {!!message.labels?.length&&<div className="assistant-labels" aria-label={uk?'Умови пошуку':'Search preferences'}>{message.labels.map((label,index)=><span key={index}>{label}</span>)}</div>}
          {!!message.results?.length&&<div className="assistant-results">{message.results.map(event=><CourseResult key={event.id} event={event} onOpen={openCourse}/>)}</div>}
          {message.has_more&&<Button kind="line" action="assistant-more" disabled={busy} onClick={()=>ask(message.more_label,message.context)}>{message.more_label}<Icon name="arrow"/></Button>}
          {message.actions?.map((action,index)=><Button key={index} kind="line" action={action.type==='catalog'?'assistant-catalog':'spider-go'} onClick={()=>{onClose();if(action.type==='catalog')openAssistantCatalog(action.filters);else go(action.route);}}>{action.type==='catalog'?(uk?'Показати в каталозі':'Show in catalogue'):(uk?'Відкрити розділ':'Open section')}<Icon name="arrow"/></Button>)}
          {message.failed&&<Button kind="line" action="assistant-retry" disabled={busy} onClick={()=>ask(message.retry)}>{uk?'Спробувати ще раз':'Try again'}<Icon name="refresh"/></Button>}
        </div>)}
        {busy&&<div className="assistant-pending" role="status"><Icon name="refresh"/>{uk?'Готую відповідь…':'Preparing a reply…'}</div>}
      </div>
      <div className="spider-suggestions">{suggestions.map(text=><button type="button" key={text} disabled={busy} onClick={()=>ask(text)}>{text}</button>)}</div>
      <form className="spider-question" onSubmit={event=>{event.preventDefault();ask(question);}}>
        <label className="sr-only" htmlFor="spider-question">{uk?'Запитання про сайт':'Question about the site'}</label>
        <input id="spider-question" name="spider_question" value={question} onChange={event=>setQuestion(event.target.value)} maxLength={1000} autoComplete="off" placeholder={uk?'Який курс хочеш знайти?':'What course are you looking for?'}/>
        <button type="submit" className="button primary" disabled={busy||!question.trim()} aria-label={uk?'Надіслати':'Send'}><Icon name="arrow"/></button>
      </form>
    </div>
  </Dialog>;
}
