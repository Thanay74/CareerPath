import { emptyAptitudeState, profileFromSaved } from './studentProfile.js';

export async function loadStudentWorkspace(api, session, fetchImpl = globalThis.fetch) {
  if (!session?.token || !session?.student_id) throw new Error('An authenticated student session is required');
  const headers = { Authorization: `Bearer ${session.token}` };
  const profileUrl = `${api}/student/profile?student_id=${encodeURIComponent(session.student_id)}`;
  const profileResponse = await fetchImpl(profileUrl, { headers });
  const profileBody = await profileResponse.json();
  if (!profileResponse.ok) throw new Error(profileBody.error || 'Could not restore the saved profile');

  // The API evaluates freshness against the profile returned above. Never
  // request saved results before that authenticated profile has loaded.
  const recommendationsUrl = `${api}/recommendations?student_id=${encodeURIComponent(session.student_id)}`;
  let recommendationState = { freshness: 'error', recommendations: [], message: 'Saved recommendations could not be restored.' };
  try {
    const response = await fetchImpl(recommendationsUrl, { headers });
    const body = await response.json();
    if (response.status === 401) {
      const error = new Error(body.error || 'Your session is no longer valid');
      error.status = 401;
      throw error;
    }
    if (response.status === 404) {
      recommendationState = { freshness: 'none', recommendations: [] };
    } else if (!response.ok) {
      recommendationState = { freshness: 'error', recommendations: [], message: body.error || 'Saved recommendations could not be restored.' };
    } else {
      const allowed = ['current', 'stale', 'unverified', 'none'];
      const freshness = allowed.includes(body.freshness) ? body.freshness : 'unverified';
      recommendationState = {
        freshness,
        recommendations: freshness === 'current' && Array.isArray(body.recommendations) ? body.recommendations : [],
        snapshot: freshness === 'current' ? body.snapshot : undefined,
        message: body.message || '',
      };
      if (freshness === 'current' && !Array.isArray(body.recommendations)) {
        recommendationState = { freshness: 'unverified', recommendations: [], message: 'Saved recommendations could not be verified.' };
      }
    }
  } catch (error) {
    if (error.status === 401) throw error;
    recommendationState = { freshness: 'error', recommendations: [], message: error.message || 'Saved recommendations could not be restored.' };
  }

  const historyUrl = `${api}/aptitude/history?student_id=${encodeURIComponent(session.student_id)}`;
  const historyResponse = await fetchImpl(historyUrl, { headers });
  const history = await historyResponse.json();
  if (!historyResponse.ok) throw new Error(history.error || 'Could not restore aptitude history');
  const latest = history.attempts?.find(attempt => attempt.status === 'completed');
  let aptitude = emptyAptitudeState();
  if (latest) {
    const detailUrl = `${api}/aptitude/attempts/${latest.attempt_id}?student_id=${encodeURIComponent(session.student_id)}`;
    const detailResponse = await fetchImpl(detailUrl, { headers });
    const detail = await detailResponse.json();
    if (!detailResponse.ok) throw new Error(detail.error || 'Could not restore the saved aptitude result');
    aptitude = { ...aptitude, phase: 'result', attemptId: latest.attempt_id, result: detail.attempt };
  }
  return { profile: profileFromSaved(profileBody.profile), aptitude, recommendationState };
}
