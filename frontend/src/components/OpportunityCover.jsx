import {useRef, useState} from 'react';
import {imageFor, useApp} from '../context.jsx';
import {Button} from './Common.jsx';

export function OpportunityCover({event, ...props}) {
  const [failedUrl, setFailedUrl] = useState(null);
  const customUrl = event.cover_url && event.cover_url !== failedUrl ? event.cover_url : null;
  return <img {...props} src={customUrl || `/assets/images/${imageFor(event)}.jpg`} alt=""
    onError={customUrl ? () => setFailedUrl(customUrl) : undefined} />;
}

export function CoverEditor({record}) {
  const {api, t, toast, errorMessage} = useApp();
  const input = useRef(null);
  const [coverUrl, setCoverUrl] = useState(record.cover_url);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const path = `/admin/opportunities/${record.id}/cover`;

  async function updateCover(file) {
    setError('');
    setBusy(true);
    try {
      const result = await api.request(path, file ? {method:'PUT',body:file} : {method:'DELETE'});
      setCoverUrl(result?.cover_url ?? null);
      toast(t(file ? 'coverSaved' : 'coverRemoved'));
    } catch (problem) {
      setError(errorMessage(problem));
    } finally {
      setBusy(false);
    }
  }

  function selectFile(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) return setError(t('photoSize'));
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return setError(t('photoFormats'));
    updateCover(file);
  }

  return <section className="cover-editor" aria-label={t('listingCover')}>
    <h3>{t('listingCover')}</h3>
    <OpportunityCover className="cover-editor-preview" event={{id:record.id,...record.values,cover_url:coverUrl}} />
    <div className="photo-actions">
      <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" aria-label={t('chooseCover')}
        onChange={selectFile} hidden disabled={busy} />
      <Button kind="secondary" action="choose-cover" disabled={busy} onClick={() => input.current.click()}>
        {t(busy ? 'uploadingPhoto' : coverUrl ? 'replaceCover' : 'chooseCover')}
      </Button>
      {coverUrl && <Button kind="line" action="remove-cover" disabled={busy} onClick={() => updateCover()}>
        {t('removeCover')}
      </Button>}
    </div>
    <p className="subtext">{t('coverHelp')}</p>
    {error && <p className="form-error" role="alert">{error}</p>}
  </section>;
}
