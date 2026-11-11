import { emptyAptitudeState, profileFromSaved } from './studentProfile.js';

export async function loadStudentWorkspace(api, session, fetchImpl = globalThis.fetch) {
  if (!session?.token || !session?.student_id) throw new Error('An authenticated student session is required');
  const headers = { Authorization: `Bearer ${session.token}` };
  const profileUrl = `${api}/student/profile?student_id=${encodeURIComponent(session.student_id)}`;
  const profileResponse = await fetchImpl(profileUrl, { headers });
  const profileBody = await profileResponse.json();
  if (!profileResponse.ok) throw new Error(profileBody.error || 'Could not restore the saved profile');

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
  return { profile: profileFromSaved(profileBody.profile), aptitude };
}
