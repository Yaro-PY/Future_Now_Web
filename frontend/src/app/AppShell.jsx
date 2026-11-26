import {lazy, Suspense} from 'react';
import {useApp} from '../context.jsx';
import {Header, Footer, MobileNav} from '../components/Layout.jsx';
import {PageRouter} from '../routing/PageRouter.jsx';
import {LiquidGlass} from '../components/LiquidGlass.jsx';
import {SiteAssistantSession} from '../components/SiteAssistantSession.jsx';
import {ElectronicSpider} from '../components/ElectronicSpider.jsx';
import './ocean-pearl.css';

const Auth = lazy(() => import('../pages/Auth.jsx').then(module => ({default:module.AuthPage})));
const Opportunity = lazy(() => import('../pages/Opportunity.jsx').then(module => ({default:module.OpportunityPage})));
const ModalContent = lazy(() => import('../components/Overlays.jsx').then(module => ({default:module.ModalContent})));

export function LoadingScreen() { return <main className="boot-screen" aria-live="polite"><span className="boot-orbit" /><p>Future Now<span className="brand-dot">.</span></p></main>; }
export function AppShell() {
  const {user,booting,route,detailId,modal,notification} = useApp();
  const roaming = user?.appearance?.spider_ludicrous === true;
  const showSpider = user?.appearance?.spider_enabled !== false && (roaming || route === 'explore');
  const showAura = !booting && (route === 'opportunity' || (user && route !== 'welcome'));
  let content;
  if (booting) content = <LoadingScreen />;
  else if(route==='opportunity') content=<><Header/><div className="app-view" data-route={route}><Suspense fallback={<LoadingScreen/>}><Opportunity key={detailId}/></Suspense></div><Footer/>{user&&<MobileNav/>}</>;
  else if (!user) content = <Suspense fallback={<LoadingScreen />}><Auth /></Suspense>;
  else content = <><Header /><div className="app-view" data-route={route}><Suspense fallback={<LoadingScreen />}><PageRouter route={route} /></Suspense></div><Footer /><MobileNav /></>;
  return <><LiquidGlass/>
    {showAura && <div className="aura-bg" aria-hidden="true">
      <div className="aura-layer aura-layer-first" />
      <div className="aura-layer aura-layer-second" />
    </div>}
    {user && !booting ? <SiteAssistantSession>{content}{showSpider && <ElectronicSpider roaming={roaming} />}</SiteAssistantSession> : content}<Suspense fallback={null}>{modal && <ModalContent key={modal.type + (modal.item?.id || '')} />}</Suspense><div id="toast" className={`toast ${notification ? 'visible' : ''}`} role="status" aria-live="polite">{notification?.message || ''}</div></>;
}
