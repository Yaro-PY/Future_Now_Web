import {createContext, useContext} from 'react';
import {useSiteAssistant} from '../hooks/useSiteAssistant.js';

const AssistantSession = createContext(null);

export function SiteAssistantSession({children}) {
  const assistant = useSiteAssistant();
  return <AssistantSession.Provider value={assistant}>{children}</AssistantSession.Provider>;
}

export function useAssistantSession() {
  return useContext(AssistantSession);
}
