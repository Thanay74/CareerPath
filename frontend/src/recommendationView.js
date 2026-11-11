export function profileSnapshot(profile) {
  return JSON.stringify(profile);
}

export function recommendationView({ authenticated, promptRequested, resultCount, resultToken, activeToken, resultProfile, activeProfile }) {
  if (!authenticated) return promptRequested ? 'login-prompt' : 'empty';
  if (!resultCount || !activeToken || resultToken !== activeToken || resultProfile !== activeProfile) return 'empty';
  return 'results';
}
