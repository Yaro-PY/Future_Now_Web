import {lazy, Suspense} from 'react';
import {useApp} from '../context.jsx';
import {Header, Footer, MobileNav} from '../components/Layout.jsx';
import {PageRouter} from '../routing/PageRouter.jsx';

const Auth = lazy(() => import('../pages/Auth.jsx').then(module => ({default:module.AuthPage})));
const DetailSheet = lazy(() => import('../components/Overlays.jsx').then(module => ({default:module.DetailSheet})));
const ModalContent = lazy(() => import('../components/Overlays.jsx').then(module => ({default:module.ModalContent})));

export function LoadingScreen() { return <main className="boot-screen" aria-live="polite"><span className="boot-orbit" /><p>Future Now<span className="brand-dot">.</span></p></main>; }
export function AppShell() {
  const {user,booting,route,detailId,modal,notification} = useApp();
  let content;
  if (booting) content = <LoadingScreen />;
  else if (!user) content = <Suspense fallback={<LoadingScreen />}><Auth /></Suspense>;
  else content = <><Header /><div className="app-view" data-route={route}><Suspense fallback={<LoadingScreen />}><PageRouter route={route} /></Suspense></div><Footer /><MobileNav /></>;
  return <>{content}<Suspense fallback={null}>{user && detailId != null && <DetailSheet key={detailId} id={detailId} />}{modal && <ModalContent key={modal.type + (modal.item?.id || '')} />}</Suspense><div id="toast" className={`toast ${notification ? 'visible' : ''}`} role="status" aria-live="polite">{notification?.message || ''}</div></>;
}
