import React from 'react';
import { emptyAcademicHistory, updateAcademicHistory } from './studentProfile.js';

const splitSubjects = value => (value || '').split(',').map(item => item.trim()).filter(Boolean);

export default function AcademicHistoryFields({ level, value, onChange }) {
  const history = { ...emptyAcademicHistory(level), ...(value || {}) };
  const update = (key, next) => onChange(current => ({ ...current, academic_history: updateAcademicHistory(current, key, next) }));
  const textField = (label, key, placeholder = '') => <label key={key}>{label}<input value={history[key] || ''} maxLength="200" onChange={event => update(key, event.target.value)} placeholder={placeholder}/></label>;
  const subjectFields = <>
    <label>Actual subjects studied status<select value={history.subjects_status} onChange={event => update('subjects_status', event.target.value)}><option value="unknown">Not recorded</option><option value="selected">I selected the subjects below</option><option value="not_applicable">Not applicable</option></select></label>
  </>;
  const subjectsText = Array.isArray(history.subjects) ? history.subjects.join(', ') : '';
  const renderedSubjects = history.subjects_status === 'selected'
    ? <label>Actual subjects studied (comma separated)<input value={subjectsText} maxLength="1000" onChange={event => update('subjects', splitSubjects(event.target.value))} placeholder="e.g. Mathematics, Physics, Chemistry"/><small>Student reported; this is not a verified transcript.</small></label>
    : subjectFields;
  return <fieldset className="academic-history" aria-describedby="academic-history-note">
    <legend>Academic history</legend>
    <p id="academic-history-note" className="field-note">Record what you actually studied. This is student-reported information, not a verified transcript or admission decision. Leave unknown items unrecorded.</p>
    {(level === '10th' || level === '12th') && <>{textField('Board or examination authority', 'board')}{textField('Qualification name (optional)', 'qualification')}</>}
    {(level === "Bachelor's" || level === "Master's") && <>{textField('Qualification name (optional)', 'qualification')}{textField('Major (optional)', 'major')}{level === "Bachelor's" && textField('Minor (optional)', 'minor')}{textField('Institution or university (optional)', 'institution')}</>}
    <label>Education status<select value={history.study_status} onChange={event => update('study_status', event.target.value)}><option value="unknown">Not recorded</option><option value="current">Currently studying</option><option value="completed">Completed</option><option value="not_applicable">Not applicable</option></select></label>
    {renderedSubjects}
    {level === '12th' && <label>Did you study Mathematics?<select value={history.mathematics} onChange={event => update('mathematics', event.target.value)}><option value="unknown">Unknown / not recorded</option><option value="yes">Yes</option><option value="no">No</option><option value="not_applicable">Not applicable</option></select></label>}
    {level === "Master's" && <><label>Previous Bachelor's qualification status<select value={history.previous_degree_status} onChange={event => update('previous_degree_status', event.target.value)}><option value="unknown">Unknown / not recorded</option><option value="provided">Qualification provided</option><option value="not_applicable">Not applicable</option></select></label>{history.previous_degree_status === 'provided' && textField("Previous Bachelor's degree", 'previous_degree')}</>}
  </fieldset>;
}
