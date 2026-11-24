import {useEffect, useRef, useState} from 'react';
import {useApp} from '../context.jsx';
import {Button} from './Common.jsx';

const types = ['image/jpeg', 'image/png', 'image/webp'];

export function readCoverFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export function ProposalCoverInput({file, existing, onChange, label = 'listingCover', help = 'proposalCoverHelp', remove = 'removeProposalCover'}) {
  const {t} = useApp();
  const input = useRef(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const src = file === undefined ? existing : preview?.file === file ? preview.src : null;

  useEffect(() => {
    if (!file) return;
    let active = true;
    readCoverFile(file).then(src => {
      if (active) setPreview({file, src});
    }).catch(() => {
      if (active) setError('coverReadError');
    });
    return () => { active = false; };
  }, [file]);

  function select(event) {
    const next = event.target.files?.[0];
    event.target.value = '';
    if (!next) return;
    if (!next.size || next.size > 2 * 1024 * 1024) return setError('photoSize');
    if (!types.includes(next.type)) return setError('photoFormats');
    setPreview(null);
    setError('');
    onChange(next);
  }

  return <section className="field full" aria-label={t(label)}>
    <span>{t(label)} ({t('optional')})</span>
    {src && <img className="cover-editor-preview" src={src} alt={t(label)} />}
    <div className="photo-actions">
      <input ref={input} type="file" accept={types.join(',')} aria-label={t('chooseCover')} onChange={select} hidden />
      <Button kind="line" action="choose-proposal-cover" onClick={() => input.current.click()}>
        {t(file || src ? 'replaceCover' : 'chooseCover')}
      </Button>
      {(file || src) && <Button kind="line" action="remove-proposal-cover" onClick={() => {setError('');onChange(null);}}>
        {t(remove)}
      </Button>}
    </div>
    <p className="subtext">{t(help)}</p>
    {error && <p className="form-error" role="alert">{t(error)}</p>}
  </section>;
}
