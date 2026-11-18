import {useApp} from '../context.jsx';

export function IntroStory({children}) {
  const {t} = useApp();
  return <section className="auth-story" aria-labelledby="brand-title">
    <p className="eyebrow">{t('brandEyebrow')}</p>
    <h1 id="brand-title" className="auth-brand"><span>Future</span><span>Now<span className="brand-dot">.</span></span></h1>
    <h2>{t('authHeadline')}</h2>
    <p className="auth-description">{t('authStory')}</p>
    {children}
  </section>;
}
