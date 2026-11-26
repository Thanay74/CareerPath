import React, { useEffect, useMemo, useState } from 'react';
import { scoreRatingControl, updateProfileRating } from './scoreRating.js';
import { addCustomSkill, filterOptionalSkillGroups, removeCustomSkill, setSkillApplicability, updateCustomSkill, validateCustomSkill } from './skillAssessment.js';

const VISIBLE_GROUPS = [
  ['domain_skills', 'Relevant skills for my education'],
  ['employability_skills', 'Employability skills'],
];
const SOURCES = [['', 'Choose a source (optional)'], ['course', 'Course'], ['self_learning', 'Self-learning'], ['certification', 'Certification'], ['internship', 'Internship'], ['work_experience', 'Work experience'], ['other', 'Other']];

export default function SkillAssessment({ api, profile, setProfile, degree, specialization }) {
  const [catalog, setCatalog] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [name, setName] = useState('');
  const [score, setScore] = useState('');
  const [category, setCategory] = useState('technical');
  const [source, setSource] = useState('');
  const [formError, setFormError] = useState('');
  const [skillSearch, setSkillSearch] = useState('');
  const [selectedOptionalKeys, setSelectedOptionalKeys] = useState(() => new Set());
  useEffect(() => {
    let active = true;
    const query = new URLSearchParams({
      education_level: profile.education_level || '', stream: profile.stream || '',
      degree: degree ?? profile.degree ?? '', specialization: specialization ?? profile.specialization ?? '',
    });
    fetch(`${api}/education/skills?${query}`).then(async response => {
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'Could not load skill suggestions.');
      if (active) { setCatalog(body.catalog); setLoadError(''); }
    }).catch(error => { if (active) { setCatalog(null); setLoadError(error.message); } });
    return () => { active = false; };
  }, [api, profile.education_level, profile.stream, profile.degree, profile.specialization, degree, specialization]);

  const visibleGroups = useMemo(() => VISIBLE_GROUPS.map(([key, title]) => [key, title, catalog?.[key] || []]), [catalog]);
  const allOptionalGroups = useMemo(() => filterOptionalSkillGroups(catalog), [catalog]);
  const optionalGroups = useMemo(() => filterOptionalSkillGroups(catalog, skillSearch), [catalog, skillSearch]);
  const details = profile.skill_assessments || [];
  const custom = details.filter(item => item.is_custom);
  const customCanonical = new Set(custom.map(item => item.canonical_skill).filter(Boolean));
  const allSkills = [...visibleGroups, ...optionalGroups].map(([, , skills]) => skills);
  const savedOptionalKeys = new Set(allOptionalGroups.flatMap(([, , skills]) => skills.filter(skill => {
    const canonical = skill.canonical_skill || skill.key;
    return profile[skill.category]?.[canonical] !== null && profile[skill.category]?.[canonical] !== undefined
      || details.some(item => item.skill_key === skill.key && item.applicability === 'not_applicable');
  }).map(skill => skill.key)));
  const visibleOptionalKeys = new Set([...selectedOptionalKeys, ...savedOptionalKeys]);

  function ratingInput(skill) {
    const canonical = skill.canonical_skill || skill.key;
    const current = profile[skill.category]?.[canonical];
    const control = scoreRatingControl(current);
    const notApplicable = details.some(item => item.skill_key === skill.key && item.applicability === 'not_applicable');
    if (customCanonical.has(canonical)) return null;
    return <div className="education-skill-rating" key={skill.key}>
      <label className="score"><span>{skill.name}</span><b>{notApplicable ? 'Not applicable' : control.label}</b>
        {!notApplicable && <input aria-label={`${skill.name} proficiency`} aria-valuetext={control.ariaValueText} className={control.sliderClass} style={{ '--rating-progress': control.progress }} type="range" min="0" max="100" step="1" value={control.value} onChange={event => setProfile(previous => {
          const next = updateProfileRating(previous, skill.category, canonical, event.target.value);
          next.skill_assessments = (previous.skill_assessments || []).filter(item => item.skill_key !== skill.key);
          return next;
        })} />}
      </label>
      <button type="button" className="secondary skill-applicability" aria-pressed={notApplicable} onClick={() => setProfile(previous => setSkillApplicability(previous, skill, notApplicable ? 'assessed' : 'not_applicable'))}>{notApplicable ? 'Rate this skill' : 'Not applicable'}</button>
    </div>;
  }

  function updateCustom(item, changes) {
    setProfile(previous => updateCustomSkill(previous, item.skill_key, changes));
  }
  function submitCustom(event) {
    event.preventDefault();
    const error = validateCustomSkill(name, allSkills, custom);
    if (error) { setFormError(error); return; }
    if (score === '' || !Number.isFinite(Number(score)) || Number(score) < 0 || Number(score) > 100) { setFormError('Choose a proficiency from 0 to 100.'); return; }
    setProfile(previous => addCustomSkill(previous, { name, category, proficiency: score, source_context: source }));
    setName(''); setScore(''); setSource(''); setFormError('');
  }

  if (loadError) return <p className="catalog-error" role="alert">{loadError}</p>;
  if (!catalog) return <p className="catalog-status" role="status">Loading education-aware skill suggestions…</p>;
  return <section className="skill-assessment" aria-label="Education-aware skill assessment">
    <p className="field-note">These are suggestions, not course requirements. Rate only skills you can assess. Missing ratings stay unknown; zero is an explicit rating.</p>
    {visibleGroups.map(([key, title, skills]) => <section className="skill-group" key={key} aria-labelledby={`skill-${key}`}>
      <h3 id={`skill-${key}`}>{title}</h3>
      {key === 'domain_skills' && !skills.length && <p className="field-note">No domain-specific suggestions are mapped for this selection. Add skills from your actual course or vocational specialization if useful.</p>}
      <div className="score-grid">{skills.map(ratingInput)}</div>
    </section>)}
    <details className="optional-skill-explorer">
      <summary>Other digital and advanced skills <small>Optional · choose only skills you want to assess</small></summary>
      <p className="field-note">These suggestions are optional and are not assumed to be part of your course. Choosing a skill does not rate it; unanswered skills remain unassessed.</p>
      <label className="skill-search">Search optional skills<input type="search" value={skillSearch} onChange={event => setSkillSearch(event.target.value)} placeholder="Search digital or advanced skills" /></label>
      {optionalGroups.map(([key, title, skills]) => <section className="skill-group optional-skill-group" key={key} aria-labelledby={`skill-${key}`}>
        <h3 id={`skill-${key}`}>{title}</h3>
        {!skills.length && <p className="field-note">{skillSearch ? 'No matching skills.' : 'No suggestions are currently listed.'}</p>}
        <div className="optional-skill-options">{skills.map(skill => {
          const selected = visibleOptionalKeys.has(skill.key);
          return <button type="button" key={skill.key} className="secondary" aria-pressed={selected} onClick={() => setSelectedOptionalKeys(previous => {
            const next = new Set(previous);
            if (next.has(skill.key)) next.delete(skill.key); else next.add(skill.key);
            return next;
          })}>{selected ? 'Added · ' : 'Add · '}{skill.name}</button>;
        })}</div>
      </section>)}
      {[...allOptionalGroups.flatMap(([, , skills]) => skills)].filter(skill => visibleOptionalKeys.has(skill.key)).length > 0 && <section className="selected-optional-skills" aria-label="Selected optional skills">
        <h3>Selected optional skills</h3>
        <div className="score-grid">{allOptionalGroups.flatMap(([, , skills]) => skills).filter(skill => visibleOptionalKeys.has(skill.key)).map(ratingInput)}</div>
      </section>}
    </details>
    <section className="custom-skill-list" aria-labelledby="custom-skill-heading">
      <h3 id="custom-skill-heading">My custom skills</h3>
      {!custom.length && <p className="field-note">Add a skill that is not already listed. Unmatched custom skills are saved to your profile but do not affect recommendation scores.</p>}
      {custom.map(item => <div className="custom-skill-row" key={item.skill_key}>
        <label>Skill name<input aria-label="Custom skill name" value={item.display_name} onChange={event => updateCustom(item, { display_name: event.target.value })} onBlur={() => { const validation = validateCustomSkill(item.display_name, allSkills, custom, item.skill_key); setFormError(validation); }} /></label>
        <label>Proficiency (0–100)<input aria-label={`${item.display_name} proficiency`} type="number" min="0" max="100" step="1" value={item.proficiency ?? ''} onChange={event => updateCustom(item, { proficiency: event.target.value === '' ? null : Number(event.target.value) })} /></label>
        <label>Category<select value={item.category} onChange={event => updateCustom(item, { category: event.target.value })}><option value="technical">Technical / domain</option><option value="employability">Employability</option></select></label>
        <label>Source / context<select value={item.source_context || ''} onChange={event => updateCustom(item, { source_context: event.target.value || null })}>{SOURCES.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
        <button type="button" className="secondary" onClick={() => setProfile(previous => removeCustomSkill(previous, item.skill_key))}>Remove</button>
      </div>)}
    </section>
    <form className="custom-skill-form" onSubmit={submitCustom}>
      <h3>Add your own skill</h3>
      <label>Skill name<input value={name} onChange={event => setName(event.target.value)} maxLength="255" /></label>
      <label>Proficiency (0–100)<input type="number" min="0" max="100" step="1" value={score} onChange={event => setScore(event.target.value)} /></label>
      <label>Category<select value={category} onChange={event => setCategory(event.target.value)}><option value="technical">Technical / domain</option><option value="employability">Employability</option></select></label>
      <label>Source / context<select value={source} onChange={event => setSource(event.target.value)}>{SOURCES.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <button type="submit" className="button">Add skill</button>
      {formError && <p role="alert" className="error">{formError}</p>}
    </form>
    {custom.some(item => item.canonical_skill) && <p className="field-note">Recognized custom skills are scored once using their standardized skill mapping.</p>}
  </section>;
}
