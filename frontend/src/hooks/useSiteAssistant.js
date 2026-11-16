import {useEffect,useRef,useState} from 'react';
import {useApp} from '../context.jsx';

// Chat stays in this signed-in React session; no localStorage, database or external API.
export function useSiteAssistant() {
  const {api,language,fail}=useApp();
  const [messages,setMessages]=useState([]);
  const [busy,setBusy]=useState(false);
  const context=useRef(null),serial=useRef(0),locked=useRef(false),alive=useRef(true);
  useEffect(()=>{alive.current=true;return ()=>{alive.current=false;serial.current++;};},[]);
  async function send(value,previous) {
    const text=value.trim();if(!text||locked.current) return;
    locked.current=true;setBusy(true);
    const request=++serial.current;
    setMessages(old=>[...old,{role:'user',text}].slice(-39));
    try {
      const answer=await api.assistant(text,previous||context.current);
      if(!alive.current||request!==serial.current) return;
      context.current=answer.context;
      setMessages(old=>[...old,{role:'assistant',...answer,text:answer.message}].slice(-40));
    } catch(error) {
      if(!alive.current||request!==serial.current) return;
      if(error.status===401) {fail(error);return;}
      setMessages(old=>[...old,{role:'assistant',failed:true,retry:text,
        text:language==='en'?'I couldn’t load the catalogue. Please try again. Your search preferences are still here.':'Не вдалося отримати дані каталогу. Спробуй ще раз — попередні умови пошуку збережено.'}].slice(-40));
    } finally {
      if(alive.current&&request===serial.current) {locked.current=false;setBusy(false);}
    }
  }
  function clear() {serial.current++;locked.current=false;context.current=null;setMessages([]);setBusy(false);}
  return {messages,busy,send,clear};
}
