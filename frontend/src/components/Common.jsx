import {useEffect, useRef, useState, useId} from 'react';
import {createPortal} from 'react-dom';
import {useApp} from '../context.jsx';
import {Icon} from './Icons.jsx';

export function Button({children, kind = 'primary', action, onClick, ...props}) {
  return <button type="button" className={`button ${kind}`} data-action={action} onClick={onClick} {...props}>{children}</button>;
}
export function AsyncButton({onClick, children, className = '', ...props}) {
  const {fail} = useApp();
  const [busy, setBusy] = useState(false);
  return <button type="button" {...props} disabled={busy || props.disabled} aria-busy={busy || undefined} className={`${className} ${busy ? 'is-busy' : ''}`} onClick={async () => {
    if (busy) return;
    setBusy(true);
    try { await onClick(); } catch (error) { fail(error); } finally { setBusy(false); }
  }}>{children}</button>;
}
export function LanguageSwitch() {
  const {t, language, changeLanguage} = useApp();
  return <div className="language-switch" aria-label={t('language')}>{['uk','en'].map(lang => <AsyncButton key={lang} className={language === lang ? 'active' : ''} data-lang={lang} aria-pressed={language === lang} onClick={() => changeLanguage(lang)}>{lang === 'uk' ? 'UK' : 'EN'}</AsyncButton>)}</div>;
}
export function Field({name, label, value, className = '', ...props}) {
  return <label className={`field ${className}`}><span>{label}</span><input name={name} defaultValue={value ?? ''} {...props} /></label>;
}
export function Select({name, label, value = 'any', onChange, excludeAny = false, extra = [], required = false}) {
  const {options, t} = useApp();
  const rows = [...options(name, excludeAny), ...extra];
  return <label className="field"><span>{label}</span><select name={name} value={value ?? 'any'} onChange={event => onChange?.(event.target.value)} required={required}>
    {!rows.some(row => row.value === value) && <option value={value || ''} disabled>{t('unknown')}</option>}
    {rows.map(row => <option key={row.value} value={row.value}>{row.label}</option>)}
  </select></label>;
}
export function Password({name, label, autoComplete = 'current-password', minLength = 1}) {
  const {t} = useApp();
  const [visible, setVisible] = useState(false);
  return <label className="field"><span>{label}</span><span className="password-wrap"><input type={visible ? 'text' : 'password'} name={name} required minLength={minLength} maxLength={128} autoComplete={autoComplete} /><button type="button" className="icon-button" data-action="password-visibility" aria-label={t(visible ? 'hidePassword' : 'showPassword')} onClick={() => setVisible(value => !value)}><Icon name="eye" /></button></span></label>;
}
export function Criteria({value = [], onChange, chips = false}) {
  const {options} = useApp();
  return <div className={chips ? 'tag-options' : 'criteria-list'}>{options('criteria').map(row => <label key={row.value} className={chips ? 'tag-option' : 'check-label'}><input type="checkbox" name="criteria" value={row.value} checked={value.includes(row.value)} onChange={event => {
    let next = value.filter(key => key !== row.value);
    if (event.target.checked) {
      if (row.value === 'free') next = next.filter(key => key !== 'paid');
      if (row.value === 'paid') next = next.filter(key => key !== 'free');
      next.push(row.value);
    }
    onChange(next);
  }} /><span>{row.label}</span></label>)}</div>;
}
export function DataForm({kind, onSubmit, children, className, ...props}) {
  const {fail, errorMessage} = useApp();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const errorRef = useRef(null);
  return <form data-form={kind} className={className} aria-busy={busy || undefined} {...props} onSubmit={async event => {
    event.preventDefault();
    if (busy) return;
    const data = new FormData(event.currentTarget);
    setBusy(true); setError('');
    try { await onSubmit(data); } catch (problem) {
      if (problem.status === 401) fail(problem);
      else { setError(errorMessage(problem)); requestAnimationFrame(() => errorRef.current?.scrollIntoView({block:'nearest'})); }
    } finally { setBusy(false); }
  }}><fieldset className="form-fields" disabled={busy}>{children}<p ref={errorRef} className="form-error" role="alert">{error}</p></fieldset></form>;
}
export function Submit({children, kind = 'primary', wide = false}) {
  return <button type="submit" className={`button ${kind} ${wide ? 'wide' : ''}`}>{children}</button>;
}
export function Dialog({id = 'modal', title, children, onClose, className = 'modal', dismissible = true, heading = true}) {
  const ref = useRef(null);
  const titleId = useId();
  useEffect(() => {
    const element = ref.current;
    element.showModal();
    return () => { if (element.open) element.close(); };
  }, []);
  return createPortal(<dialog ref={ref} id={id} className={className} aria-label={title} aria-labelledby={heading ? titleId : undefined} onCancel={event => { event.preventDefault(); if (dismissible) onClose(); }} onClick={event => {
    if (!dismissible || event.target !== ref.current) return;
    const bounds = ref.current.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose();
  }}>{heading && <div className="modal-head"><h2 id={titleId}>{title}</h2>{dismissible && <Close onClick={onClose} />}</div>}{children}</dialog>, document.body);
}
export function Close({onClick, action = 'close-modal', className = ''}) {
  const {t} = useApp();
  return <button type="button" className={`icon-button ${className}`} data-action={action} aria-label={t('close')} onClick={onClick}><Icon name="close" /></button>;
}
export function Skeletons() { return <div className="opportunities-grid">{[0,1,2,3].map(key => <div key={key} className="skeleton"><span className="skeleton-image" /><span className="skeleton-line" /><span className="skeleton-line short" /></div>)}</div>; }
export function Empty({title, text, symbol = 'search', action = 'reset-filters', actionLabel = 'resetFilters', onAction}) {
  const {t} = useApp();
  return <div className="empty-state"><div className="empty-symbol"><Icon name={symbol} /></div><h2>{t(title)}</h2><p>{t(text)}</p><Button action={action} onClick={onAction}>{t(actionLabel)}<Icon name="arrow" /></Button></div>;
}
