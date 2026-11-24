import {useState} from 'react';
import {useApp} from '../context.jsx';
import {Button, DataForm, Field, Select, Submit} from '../components/Common.jsx';
import {ProposalCoverInput, readCoverFile} from '../components/ProposalCoverInput.jsx';

export function DirectionEditor({item}) {
  const {api, t, setModal, toast, reload} = useApp();
  const [filterType, setFilterType] = useState(item?.filter_type || 'any');
  const [topic, setTopic] = useState(item?.topic || 'any');
  const [file, setFile] = useState(undefined);
  const [conflict, setConflict] = useState(false);

  async function save(data) {
    const body = {
      title_uk: data.get('title_uk').trim(),
      title_en: data.get('title_en').trim(),
      description_uk: data.get('description_uk').trim(),
      description_en: data.get('description_en').trim(),
      filter_type: filterType,
      topic: topic === 'any' ? null : topic,
    };
    if (item) body.expected_revision = item.revision;
    if (file === null) body.cover_image = null;
    if (file) {
      try { body.cover_image = (await readCoverFile(file)).split(',')[1]; }
      catch { throw new Error(t('coverReadError')); }
    }
    try {
      await api.request(item ? `/admin/directions/${item.key}` : '/admin/directions', {
        method: item ? 'PATCH' : 'POST',
        body,
      });
    } catch (error) {
      if (error.code === 'edit_conflict') setConflict(true);
      throw error;
    }
    setModal(null);
    reload();
    toast(t('savedNotice'));
  }

  return <div className="modal-body">
    <DataForm kind="direction-editor" onSubmit={save}>
      <div className="form-grid">
        <Field name="title_uk" label={t('directionNameUk')} value={item?.title_uk} maxLength={100} required />
        <Field name="title_en" label={t('directionNameEn')} value={item?.title_en} maxLength={100} />
        <label className="field"><span>{t('directionDescriptionUk')}</span>
          <textarea name="description_uk" defaultValue={item?.description_uk} rows={4} maxLength={600} required />
        </label>
        <label className="field"><span>{t('directionDescriptionEn')}</span>
          <textarea name="description_en" defaultValue={item?.description_en} rows={4} maxLength={600} />
        </label>
        <Select name="type" label={t('type')} value={filterType} onChange={setFilterType} />
        <Select name="tags" label={t('directionTopic')} value={topic} onChange={setTopic}
          extra={[{value:'any', label:t('directionAnyTopic')}]} />
        <ProposalCoverInput file={file} existing={item?.cover_url} onChange={setFile}
          label="directionCover" help="directionCoverHelp" remove="removeCover" />
      </div>
      <div className="form-actions">
        {conflict && <Button kind="line" onClick={() => {setModal(null); reload();}}>{t('reloadRecord')}</Button>}
        <Submit>{t('save')}</Submit>
      </div>
    </DataForm>
  </div>;
}
