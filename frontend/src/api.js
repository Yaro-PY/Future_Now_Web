// Shared React API transport. Passwords and session tokens are never persisted in JS storage.
export class FutureNowAPI {
  constructor(baseURL = '/api/v1') {
    this.baseURL = baseURL.replace(/\/$/, '');
    this.csrfToken = null;
    this.language = 'uk';
  }

  async request(path, { method = 'GET', body } = {}) {
    const headers = { 'Accept-Language': this.language };
    const binary = typeof Blob !== 'undefined' && body instanceof Blob;
    if (body !== undefined) headers['Content-Type'] = binary ? body.type : 'application/json';
    if (this.csrfToken && method !== 'GET') headers['X-CSRF-Token'] = this.csrfToken;
    const response = await fetch(this.baseURL + path, {
      method, headers, credentials: 'include',
      ...(body === undefined ? {} : { body: binary ? body : JSON.stringify(body) }),
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
  verifyTwoFactor(values) { return this.request('/auth/2fa/verify',{method:'POST',body:values}); }
  cancelTwoFactor() { return this.request('/auth/2fa/cancel',{method:'POST'}); }
  security() { return this.request('/me/security'); }
  authorizeSecurity(current_password) { return this.request('/me/security/authorize',{method:'POST',body:{current_password}}); }
  uploadAvatar(file) { return this.request('/me/avatar',{method:'PUT',body:file}); }
  removeAvatar() { return this.request('/me/avatar',{method:'DELETE'}); }
  resume() { return this.request('/auth/session'); }
  me() { return this.request('/me'); }
  saveProfile(values) { return this.request('/me/profile', { method: 'PUT', body: values }); }
  filters() { return this.request('/me/filters'); }
  saveFilters(values) { return this.request('/me/filters', { method: 'PUT', body: values }); }
  saveSettings(values) { return this.request('/me/settings', { method: 'PATCH', body: values }); }
  search(values = {}) { return this.request('/opportunities/search', { method: 'POST', body: values }); }
  detail(id) { return this.request('/opportunities/' + encodeURIComponent(id)); }
  catalogStatus() { return this.request('/catalog/status'); }
  registration(id) { return this.request('/opportunities/' + encodeURIComponent(id) + '/registration'); }
  favorites() { return this.request('/me/favorites'); }
  saveFavorite(id) { return this.request('/me/favorites/' + encodeURIComponent(id), { method: 'PUT' }); }
  removeFavorite(id) { return this.request('/me/favorites/' + encodeURIComponent(id), { method: 'DELETE' }); }
  subscribe(id, enabled) { return this.request('/me/subscriptions/' + encodeURIComponent(id), { method: 'PUT', body: { enabled } }); }
  suggest(values) { return this.request('/me/proposals', { method: 'POST', body: values }); }
  editProposal(item, values) { return this.request(`/me/proposals/${item.id}`, {method:'PATCH',body:{expected_revision:item.revision,values}}); }
  withdrawProposal(item) { return this.request(`/me/proposals/${item.id}/withdraw`, {method:'POST',body:{expected_revision:item.revision}}); }
  async deleteAccount(password, confirmation) {
    await this.request('/me', {method:'DELETE',body:{password,confirmation}});
    this.csrfToken = null;
  }
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
