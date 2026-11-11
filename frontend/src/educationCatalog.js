export async function fetchEducationCatalog(api, fetchImpl = globalThis.fetch) {
  let response;
  try {
    response = await fetchImpl(`${api}/education/catalog`);
  } catch {
    throw new Error('Could not reach the education catalog API. Check that Flask is running and the frontend API proxy is configured, then retry.');
  }

  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error(`The education catalog API returned an invalid response (HTTP ${response.status}).`);
  }
  if (!response.ok) {
    throw new Error(body?.error || `The education catalog API request failed (HTTP ${response.status}).`);
  }
  if (!body || typeof body.levels !== 'object' || body.levels === null || Array.isArray(body.levels)) {
    throw new Error('The education catalog API response is missing its levels catalog.');
  }
  return body.levels;
}

export function educationOptions(catalog, level) {
  const record = catalog?.[level];
  if (level === '10th' || level === '12th') {
    return Array.isArray(record?.streams) ? record.streams : [];
  }
  return Array.isArray(record?.degrees) ? record.degrees : [];
}

export function subjectsForProfile(catalog, profile) {
  const record = catalog?.[profile.education_level];
  if (!record) return [];
  let key = profile.education_level === '10th'
    ? 'default'
    : profile.education_level === '12th'
      ? profile.stream
      : `${profile.degree}|${profile.specialization}`;
  let subjects = record.subjects?.[key] || record.subjects?.[profile.degree] || [];
  if (!subjects.length && !profile.specialization && ['B.Sc', 'B.Tech/BE'].includes(profile.degree)) {
    subjects = (record.specializations?.[profile.degree] || [])
      .flatMap(specialization => record.subjects?.[`${profile.degree}|${specialization}`] || []);
  }
  return [...new Set(Array.isArray(subjects) ? subjects : [])];
}
