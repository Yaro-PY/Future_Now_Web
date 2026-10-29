// Transport for a future frontend. Passwords and session tokens are not persisted in JS storage.
export class FutureNowAPI {
  constructor(baseURL = '/api/v1') {
    this.baseURL = baseURL.replace(/\/$/, '');
    this.csrfToken = null;
    this.language = 'uk';
  }

  async request(path, { method = 'GET', body } = {}) {
    const headers = { 'Accept-Language': this.language };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (this.csrfToken && method !== 'GET') headers['X-CSRF-Token'] = this.csrfToken;
    const response = await fetch(this.baseURL + path, {
      method, headers, credentials: 'include',
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    const data = response.status === 204 ? null : await response.json();
    if (!response.ok) {
      const error = new Error(data?.error?.message || 'Request failed');
      error.status = response.status;
      error.code = data?.error?.code;
      error.fields = data?.error?.fields || [];
      throw error;
    }
    if (data?.csrf_token) this.csrfToken = data.csrf_token;
    if (data?.user?.language) this.language = data.user.language;
    if (data?.language) this.language = data.language;
    return data;
  }

  bootstrap(language = this.language) { return this.request('/bootstrap?lang=' + encodeURIComponent(language)); }
  register(values) { return this.request('/auth/register', { method: 'POST', body: values }); }
  login(nickname, password) { return this.request('/auth/login', { method: 'POST', body: { nickname, password } }); }
  resume() { return this.request('/auth/session'); }
  me() { return this.request('/me'); }
  saveProfile(values) { return this.request('/me/profile', { method: 'PUT', body: values }); }
  filters() { return this.request('/me/filters'); }
  saveFilters(values) { return this.request('/me/filters', { method: 'PUT', body: values }); }
  saveSettings(values) { return this.request('/me/settings', { method: 'PATCH', body: values }); }
  search(values = {}) { return this.request('/opportunities/search', { method: 'POST', body: values }); }
  detail(id) { return this.request('/opportunities/' + encodeURIComponent(id)); }
  registration(id) { return this.request('/opportunities/' + encodeURIComponent(id) + '/registration'); }
  favorites() { return this.request('/me/favorites'); }
  saveFavorite(id) { return this.request('/me/favorites/' + encodeURIComponent(id), { method: 'PUT' }); }
  removeFavorite(id) { return this.request('/me/favorites/' + encodeURIComponent(id), { method: 'DELETE' }); }
  subscribe(id, enabled) { return this.request('/me/subscriptions/' + encodeURIComponent(id), { method: 'PUT', body: { enabled } }); }
  suggest(values) { return this.request('/me/proposals', { method: 'POST', body: values }); }
  myProposals() { return this.request('/me/proposals'); }
  report(values) { return this.request('/me/reports', { method: 'POST', body: values }); }
  async changePassword(current_password, new_password) {
    const result = await this.request('/auth/password', { method: 'POST', body: { current_password, new_password } });
    this.csrfToken = null;
    return result;
  }
  async logout() {
    await this.request('/auth/logout', { method: 'POST' });
    this.csrfToken = null;
  }
}
