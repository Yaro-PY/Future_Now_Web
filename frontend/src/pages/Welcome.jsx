import {useApp} from '../context.jsx';
import {AuthMedia, AuthMediaControls, useAuthMedia} from '../components/AuthMedia.jsx';
import {IntroStory} from '../components/IntroStory.jsx';
import {Icon} from '../components/Icons.jsx';
import {internalClick, routeHref} from '../routing/routes.js';
import './welcome.css';

export function WelcomePage() {
  const {go, t} = useApp();
  const media = useAuthMedia();

  return <main id="main-content" className="auth-scene welcome-scene">
    <AuthMedia media={media} />
    <div className="auth-header-tools welcome-controls"><AuthMediaControls media={media} /></div>
    <div className="welcome-content">
      <IntroStory>
        <a className="welcome-catalog" href={routeHref('explore')} onClick={event => {
          if (!internalClick(event)) return;
          event.preventDefault();
          go('explore');
        }}>{t('welcomeCatalog')}<Icon name="arrow" /></a>
      </IntroStory>
    </div>
  </main>;
}
