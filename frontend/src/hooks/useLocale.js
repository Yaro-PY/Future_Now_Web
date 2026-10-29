import {useCallback, useEffect, useState} from 'react';
import {words} from '../i18n.js';

export function useLocale(api) {
  const [language, setLanguage] = useState('uk');
  const t = useCallback((key, params = {}) => (words[key]?.[language === 'en' ? 1 : 0] || key).replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? '')), [language]);
  const date = useCallback(value => value && !Number.isNaN(new Date(value).getTime())
    ? new Intl.DateTimeFormat(language === 'uk' ? 'uk-UA' : 'en-GB', {day:'numeric',month:'short',year:'numeric'}).format(new Date(value))
    : t('unknown'), [language,t]);
  const errorMessage = useCallback(error => ['not_ready','database_unavailable'].includes(error?.code)
    ? t('serviceError') : error instanceof TypeError ? t('networkError') : error?.message || t('serviceError'), [t]);
  useEffect(() => { document.documentElement.lang = language; api.language = language; }, [language,api]);
  return {language,setLanguage,t,date,errorMessage};
}
