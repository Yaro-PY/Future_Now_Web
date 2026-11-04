import {useEffect, useRef, useState} from 'react';
import {useApp, initial} from '../context.jsx';
import {Avatar} from './ProfilePhoto.jsx';
import {Icon, Logo} from './Icons.jsx';
import {AsyncButton, Button, LanguageSwitch} from './Common.jsx';

export function NavLink({page, title = page, symbol}) {
  const {route, go, t, savedCount} = useApp();
  const active = route === page;
  return <a href={`#${page}`} data-page={page} className={active ? 'active' : ''} aria-current={active ? 'page' : undefined} onClick={event => { event.preventDefault(); go(page); }}>
    {symbol && <Icon name={symbol} />}<span>{t(title)}{page === 'saved' && !symbol && <span className="nav-count" data-saved-count>{savedCount || ''}</span>}</span>
  </a>;
}
export function Header() {
  const {user, t, go, menuOpen, setMenuOpen, logout} = useApp();
  const profileRef = useRef(null);
  const [scrolled, setScrolled] = useState(window.scrollY > 12);
  useEffect(() => {
    const scroll = () => setScrolled(window.scrollY > 12);
    const click = event => { if (!profileRef.current?.contains(event.target)) setMenuOpen(false); };
    window.addEventListener('scroll',scroll,{passive:true}); document.addEventListener('click',click);
    return () => { window.removeEventListener('scroll',scroll); document.removeEventListener('click',click); };
  }, []);
  return <header className={`app-header ${scrolled ? 'is-scrolled' : ''}`}><a href="#explore" className="brand" aria-label="Future Now" onClick={event => { event.preventDefault(); go('explore'); }}><Logo /></a>
    <nav className="main-nav" aria-label={t('explore')}><NavLink page="explore" /><NavLink page="categories" /><NavLink page="saved" /><NavLink page="proposals" /></nav>
    <div className="header-actions"><LanguageSwitch /><span className="separator" /><button type="button" className="icon-button" data-action="settings" aria-label={t('settings')} onClick={() => go('settings')}><Icon name="settings" /></button>
      <div className="header-profile-wrap" ref={profileRef}><button type="button" className="header-profile" data-action="profile-menu" aria-label={t('profile')} aria-expanded={menuOpen} onClick={() => setMenuOpen(value => !value)}><Avatar user={user}/><span>{user.display_name?.split(' ')[0] || user.nickname}</span><Icon name="down" /></button>
        {menuOpen && <nav className="profile-menu"><NavLink page="profile" symbol="user" /><NavLink page="categories" symbol="grid" /><NavLink page="settings" symbol="settings" /><NavLink page="suggest" symbol="plus" /><NavLink page="help" symbol="help" /><NavLink page="about" symbol="spark" />{user.role === 'admin' && <NavLink page="moderation" symbol="shield" />}<AsyncButton data-action="logout" onClick={logout}><Icon name="logout" />{t('logout')}</AsyncButton></nav>}
      </div>
    </div>
  </header>;
}
export function MobileNav() {
  const {t} = useApp();
  return <nav className="mobile-nav" aria-label={t('explore')}><NavLink page="explore" symbol="search" /><NavLink page="saved" symbol="heart" /><NavLink page="suggest" symbol="plus" /><NavLink page="profile" symbol="user" /></nav>;
}
export function Footer() {
  const {t, go} = useApp();
  return <footer className="page-footer"><span className="footer-brand"><Logo /></span><span>© {new Date().getFullYear()} Future Now</span><div className="footer-links"><button type="button" data-action="help" onClick={() => go('help')}>{t('help')}</button><button type="button" data-action="about" onClick={() => go('about')}>{t('about')}</button></div></footer>;
}
export function PageHeading({title, subtitle, action = true}) {
  const {user, t, go} = useApp();
  return <div className="page-top"><div><p className="eyebrow">{t('greeting',{name:user.display_name?.split(' ')[0] || user.nickname})}</p><h1>{t(title)}</h1><p className="subtext">{t(subtitle)}</p></div>{action && <Button kind="line" action="suggest" onClick={() => go('suggest')}><Icon name="plus" /><span>{t('suggest')}</span></Button>}</div>;
}
export function AccountRail() {
  const {user, t, logout} = useApp();
  return <nav className="account-rail" aria-label={t('profile')}><NavLink page="profile" symbol="user" /><NavLink page="settings" symbol="settings" /><NavLink page="proposals" symbol="grid" /><NavLink page="categories" symbol="grid" /><NavLink page="help" symbol="help" /><NavLink page="about" symbol="spark" />{user.role === 'admin' && <NavLink page="moderation" symbol="shield" />}<AsyncButton data-action="logout" onClick={logout}><Icon name="logout" />{t('logout')}</AsyncButton></nav>;
}
