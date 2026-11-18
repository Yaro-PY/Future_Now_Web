import {useApp} from '../context.jsx';
import './intro-title.css';

export function IntroStory({children}) {
  const {t} = useApp();
  return <section className="auth-story" aria-labelledby="brand-title">
    <p className="eyebrow">{t('brandEyebrow')}</p>
    <h1 id="brand-title" className="auth-brand intro-title" aria-label="Future Now.">
      <span className="intro-word" aria-hidden="true">
        {Array.from('Future', (letter, index) => <span className="intro-letter" key={index}>{letter}</span>)}
      </span>
      <span className="intro-word" aria-hidden="true">
        {Array.from('Now', (letter, index) => <span className="intro-letter" key={index}>{letter}</span>)}
        <span className="intro-letter"><span className="brand-dot intro-dot">.</span></span>
      </span>
    </h1>
    <h2>{t('authHeadline')}</h2>
    <p className="auth-description">{t('authStory')}</p>
    {children}
  </section>;
}
