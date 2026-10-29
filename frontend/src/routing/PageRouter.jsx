import {lazy} from 'react';

const named = (load, name) => lazy(() => load().then(module => ({default:module[name]})));
const Catalog = named(() => import('../pages/Catalog.jsx'),'CatalogPage');
const Profile = named(() => import('../pages/Account.jsx'),'ProfilePage');
const Settings = named(() => import('../pages/Account.jsx'),'SettingsPage');
const About = named(() => import('../pages/Account.jsx'),'AboutPage');
const Suggest = named(() => import('../pages/Proposals.jsx'),'SuggestPage');
const Proposals = named(() => import('../pages/Proposals.jsx'),'ProposalsPage');
const Categories = named(() => import('../pages/Categories.jsx'),'CategoriesPage');
const Help = named(() => import('../pages/Help.jsx'),'HelpPage');
const Administration = named(() => import('../pages/Administration.jsx'),'AdministrationPage');
const screens = {explore:Catalog,saved:Catalog,profile:Profile,settings:Settings,about:About,suggest:Suggest,proposals:Proposals,moderation:Administration,categories:Categories,help:Help};

export function PageRouter({route}) { const Page = screens[route] || Catalog; return <Page key={route} />; }
