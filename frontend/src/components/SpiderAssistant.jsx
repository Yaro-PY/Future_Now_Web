import {useEffect,useRef,useState} from 'react';
import {useApp} from '../context.jsx';
import {Button,Dialog} from './Common.jsx';
import {Icon} from './Icons.jsx';

const subjects=[
  {key:'Saved',route:'saved',terms:/збер|сохран|обран|избран|saved|favou?rite/i},
  {key:'Expired',route:'saved',terms:/дедлайн|простроч|истек|заверш|deadline|expired|ended/i},
  {key:'Proposals',route:'suggest',terms:/пропоз|предлож|додат|добав|публік|публик|оголош|объяв|suggest|propos|publish|listing/i},
  {key:'Notifications',route:'settings',terms:/сповіщ|уведом|повідом|notif/i},
  {key:'Account',route:'profile',terms:/проф|парол|вхід|вход|аккаунт|акаунт|телеграм|telegram|login|password|account|profile/i},
  {key:'Filters',route:'explore',terms:/курс|курc|пошук|поиск|знай|найт|фільтр|фильтр|вік|возраст|search|course|filter|age/i},
];

export function SpiderAssistant({onClose,onBack}) {
  const {language,t,go}=useApp();
  const uk=language!=='en';
  const [question,setQuestion]=useState('');
  const [messages,setMessages]=useState([]);
  const list=useRef(null);
  useEffect(()=>{if(list.current) list.current.scrollTop=list.current.scrollHeight;},[messages]);
  function ask(text) {
    text=text.trim();if(!text) return;
    const subject=subjects.find(item=>item.terms.test(text));
    setMessages(old=>[...old,{role:'user',text},{role:'assistant',
      text:subject?t(`faq${subject.key}Text`):(uk?'У тестовому перегляді можу підказати щодо пошуку, фільтрів, обраного, профілю та пропозицій. Обери тему нижче або відкрий довідку сайту.':'In this preview I can help with search, filters, saved listings, your profile and suggestions. Choose a topic below or open the site help.'),
      route:subject?.route||'help'}]);
    setQuestion('');
  }
  const suggestions=uk?['Як знайти курс?','Як зберегти можливість?','Як додати пропозицію?']:['How do I find a course?','How do I save a listing?','How do I suggest a listing?'];
  return <Dialog id="spider-assistant" className="modal spider-assistant" title={uk?'ШІ по сайту':'Site AI assistant'} onClose={onClose}>
    <div className="modal-body" data-spider-ui>
      <div className="spider-assistant-status"><span>{uk?'Тестова панель':'Preview panel'}</span><Button kind="line" action="spider-back" onClick={onBack}><Icon name="arrow"/>{uk?'Меню павука':'Spider menu'}</Button></div>
      <div className="spider-messages" ref={list} role="log" aria-live="polite" aria-label={uk?'Розмова з помічником':'Assistant conversation'}>
        {!messages.length&&<div className="spider-message assistant"><Icon name="spark"/><p>{uk?'Що підказати про сайт?':'What would you like to know about the site?'}</p></div>}
        {messages.map((message,index)=><div key={index} className={`spider-message ${message.role}`}><p>{message.text}</p>{message.route&&<Button kind="line" action="spider-go" onClick={()=>{onClose();go(message.route);}}>{uk?'Відкрити розділ':'Open section'}<Icon name="arrow"/></Button>}</div>)}
      </div>
      <div className="spider-suggestions">{suggestions.map(text=><button type="button" key={text} onClick={()=>ask(text)}>{text}</button>)}</div>
      <form className="spider-question" onSubmit={event=>{event.preventDefault();ask(question);}}>
        <label className="sr-only" htmlFor="spider-question">{uk?'Запитання про сайт':'Question about the site'}</label>
        <input id="spider-question" name="spider_question" value={question} onChange={event=>setQuestion(event.target.value)} maxLength={500} autoComplete="off" placeholder={uk?'Напиши запитання…':'Ask a question…'}/>
        <button type="submit" className="button primary" disabled={!question.trim()} aria-label={uk?'Надіслати':'Send'}><Icon name="arrow"/></button>
      </form>
    </div>
  </Dialog>;
}
