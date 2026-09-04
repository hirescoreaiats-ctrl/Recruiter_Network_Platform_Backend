/* Shared employer workspace. Role/product choices never grant server permission. */
const onboarding = {role: null, mode: null, step: 'role', draft: {}};
const loginChoice = {role: null, step: 'role'};
const legacyRegistrationFields = registrationFields;
const accountLabels = {requirement_vendor: 'Employer / Vendor', candidate: 'Candidate', sourcing_partner: 'Sourcing Partner'};
const modeLabels = {complete: 'Complete HireScoreAI', basic: 'Basic Hiring Dashboard'};
const escapeAccountHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
roles.requirement_vendor.label = accountLabels.requirement_vendor;

function roleCards(selected) {
  return ['requirement_vendor', 'candidate', 'sourcing_partner'].map(role =>
    '<button type="button" class="role-card ' + (selected === role ? 'selected' : '') +
    '" data-account-role="' + role + '" aria-pressed="' + (selected === role) + '">' +
    '<span class="role-icon" aria-hidden="true">' + roles[role].icon + '</span><strong>' +
    accountLabels[role] + '</strong><span>' + roles[role].desc + '</span></button>').join('');
}
function labelAccountFields(form) {
  form.querySelectorAll('.field').forEach((field, index) => {
    const control = field.querySelector('input,select,textarea'), label = field.querySelector('label');
    if (control && label) { control.id ||= 'account-field-' + index; label.htmlFor = control.id; }
  });
}
function showAccountError(message) {
  const error = document.getElementById('account-error');
  if (error) { error.textContent = message; error.hidden = false; }
}
function captureOnboardingDraft() {
  const form = document.getElementById('register');
  if (form) onboarding.draft = Object.fromEntries(new FormData(form));
}
function choicePage(kind) {
  const state = kind === 'register' ? onboarding : loginChoice;
  authShell('<div class="eyebrow">' + (kind === 'register' ? 'Create your account' : 'Welcome back') +
    '</div><h2>How will you use HireScoreAI?</h2><p class="muted">Choose your account type to continue.</p>' +
    '<div class="role-grid account-role-grid" role="group" aria-label="Account type">' + roleCards(state.role) +
    '</div><button type="button" id="account-continue" class="btn btn-primary account-continue"' +
    (state.role ? '' : ' disabled') + '>Continue</button><p class="muted">' +
    (kind === 'register' ? 'Already registered? <a href="/auth/login" data-link>Sign in</a>' :
      'New here? <a href="/auth/register" data-link>Create an account</a>') + '</p>');
  document.querySelectorAll('[data-account-role]').forEach(button => {
    button.onclick = () => {
      if (state.role !== button.dataset.accountRole && kind === 'register') {
        onboarding.mode = null; onboarding.draft = {};
      }
      state.role = button.dataset.accountRole;
      choicePage(kind);
      document.querySelector('[data-account-role="' + state.role + '"]').focus();
    };
  });
  document.getElementById('account-continue').onclick = () => {
    state.step = kind === 'register' && state.role === 'requirement_vendor' ? 'mode' : 'details';
    kind === 'register' ? registerPage() : loginPage();
  };
}
function modeChoicePage() {
  authShell('<button type="button" id="account-back" class="text-link">← Account type</button>' +
    '<div class="eyebrow">Employer / Vendor · Step 2 of 3</div><h2>Choose your hiring workspace</h2>' +
    '<p class="muted">The same HireScoreAI dashboard in both options. Choose whether you want LLM features.</p>' +
    '<div class="product-mode-grid" role="group" aria-label="Hiring workspace">' +
    ['complete', 'basic'].map(mode => '<button type="button" data-product-mode="' + mode +
      '" class="role-card product-mode-card ' + (onboarding.mode === mode ? 'selected' : '') +
      '" aria-pressed="' + (onboarding.mode === mode) + '"><small>' + (mode === 'complete' ? 'FULL FEATURE ACCESS' : 'NO LLM COST') +
      '</small><strong>' + modeLabels[mode] + '</strong><span>' +
      (mode === 'complete' ? 'Jobs, candidates, ranking and recruiter workflows, with access to AI screening, explanations and generative communication when an AI provider is connected.' :
        'The same jobs, candidate profiles, original resumes, pipeline, partner submissions and non-LLM ranking. Paid-model features are disabled.') +
      '</span></button>').join('') +
    '</div><p class="account-local-note">Local preview only. No paid AI provider, email delivery or payment service is connected.</p>' +
    '<button type="button" id="mode-continue" class="btn btn-primary account-continue"' +
    (onboarding.mode ? '' : ' disabled') + '>Continue</button>');
  document.getElementById('account-back').onclick = () => { onboarding.step = 'role'; registerPage(); };
  document.querySelectorAll('[data-product-mode]').forEach(button => button.onclick = () => {
    onboarding.mode = button.dataset.productMode; modeChoicePage();
    document.querySelector('[data-product-mode="' + onboarding.mode + '"]').focus();
  });
  document.getElementById('mode-continue').onclick = () => { onboarding.step = 'details'; registerPage(); };
}
registerPage = function() {
  if (onboarding.step === 'role' || !onboarding.role) return choicePage('register');
  if (onboarding.role === 'requirement_vendor' && (onboarding.step === 'mode' || !onboarding.mode)) return modeChoicePage();
  selectedRole = onboarding.role;
  const employer = selectedRole === 'requirement_vendor', basic = employer && onboarding.mode === 'basic';
  authShell('<button type="button" id="account-back" class="text-link">← Back</button><div class="eyebrow">' +
    escapeAccountHtml(employer ? modeLabels[onboarding.mode] : accountLabels[selectedRole]) +
    '</div><h2>' + (employer ? 'Set up your employer profile' : 'Create your ' + accountLabels[selectedRole].toLowerCase() + ' account') +
    '</h2><p class="muted">Your account and profile stay in this local recruitment platform.</p>' +
    '<p id="account-error" role="alert" class="account-error" hidden></p><form id="register">' +
    '<div class="form-grid"><div class="field"><label>Full name</label><input name="name" autocomplete="name" required maxlength="160"></div>' +
    '<div class="field"><label>' + (employer ? 'Work email' : 'Email') + '</label><input name="email" type="email" autocomplete="email" required></div>' +
    '<div class="field"><label>Password</label><input name="password" type="password" autocomplete="new-password" minlength="8" required></div>' +
    '<div class="field"><label>Phone</label><input name="phone" type="tel" autocomplete="tel" required></div></div>' +
    '<div class="form-grid account-profile-fields">' + legacyRegistrationFields(selectedRole) +
    (employer ? '<div class="field"><label>Company size</label><select name="company_size"' + (basic ? ' required' : '') +
      '><option value="">Select size</option><option>1–10</option><option>11–50</option><option>51–200</option><option>201–500</option><option>501–1000</option><option>1000+</option></select></div>' +
      '<div class="field"><label>Industry</label><input name="industry" maxlength="160"' + (basic ? ' required' : '') + '></div>' +
      '<div class="field wide"><label>Hiring requirements</label><textarea name="hiring_requirements" placeholder="Roles, locations and hiring volume"' + (basic ? ' required' : '') + '></textarea></div>' +
      '<label class="account-consent wide"><input type="checkbox" name="consent_accepted" required> I am authorized to represent this company and consent to storing this employer profile in the local platform. This is not verification of the company.</label>' : '') +
    '</div><div class="actions"><button class="btn btn-primary" id="create-account">Create account</button>' +
    '<a href="/auth/login" data-link>Already have an account?</a></div></form>');
  const form = document.getElementById('register');
  wireCountryFields();
  const countryControl = form.querySelector('[data-country]');
  if (countryControl) {
    const updateCountryFields = countryControl.onchange;
    countryControl.onchange = () => { updateCountryFields(); labelAccountFields(form); };
    if (onboarding.draft.country) {
      countryControl.value = onboarding.draft.country;
      countryControl.onchange();
    }
  }
  if (basic) form.elements.description.required = true;
  for (const [name, value] of Object.entries(onboarding.draft)) {
    const control = form.elements.namedItem(name);
    if (control) control.type === 'checkbox' ? control.checked = value === 'on' : control.value = value;
  }
  labelAccountFields(form);
  document.getElementById('account-back').onclick = () => {
    captureOnboardingDraft(); onboarding.step = employer ? 'mode' : 'role'; registerPage();
  };
  form.onsubmit = async event => {
    event.preventDefault();
    const button = document.getElementById('create-account');
    if (button.disabled || !form.reportValidity()) return;
    button.disabled = true; button.textContent = 'Creating account…';
    const values = Object.fromEntries(new FormData(form)), profile = {...values};
    ['name', 'email', 'password', 'phone'].forEach(key => delete profile[key]);
    ['skills','industries','skill_areas','hiring_markets','role_specializations','locations','employment_expertise','work_authorization_expertise'].forEach(key => {
      if (profile[key]) profile[key] = profile[key].split(',').map(value => value.trim()).filter(Boolean);
    });
    profile.country_specific_data = {};
    for (const key of Object.keys(profile)) if (key.startsWith('extra_')) {
      profile.country_specific_data[key.slice(6)] = profile[key]; delete profile[key];
    }
    if (employer) profile.consent_accepted = form.elements.consent_accepted.checked;
    const payload = {name: values.name, email: values.email, password: values.password, phone: values.phone, role: selectedRole, profile};
    if (employer) payload.product_mode = onboarding.mode;
    try {
      session = await api('/auth/register', {method: 'POST', body: JSON.stringify(payload)});
      localStorage.setItem('tb_session', JSON.stringify(session));
      onboarding.draft = {}; onboarding.step = 'role'; onboarding.role = null; onboarding.mode = null;
      route(roles[session.user.role].home);
    } catch (error) {
      showAccountError(error.message); button.disabled = false; button.textContent = 'Create account';
    }
  };
};
loginPage = function() {
  if (loginChoice.step === 'role' || !loginChoice.role) return choicePage('login');
  authShell('<button type="button" id="account-back" class="text-link">← Account type</button><div class="eyebrow">' +
    accountLabels[loginChoice.role] + '</div><h2>Sign in to your workspace</h2>' +
    '<p class="muted">Your saved account decides your dashboard and feature access.</p>' +
    '<p id="account-error" class="account-error" role="alert" hidden></p><form id="login" class="form-grid">' +
    '<div class="field wide"><label>Email</label><input type="email" name="email" autocomplete="email" required></div>' +
    '<div class="field wide"><label>Password</label><input type="password" name="password" autocomplete="current-password" required></div>' +
    '<button class="btn btn-primary wide">Sign in</button></form><p><a href="/auth/register" data-link>Create an account</a></p>');
  document.getElementById('account-back').onclick = () => { loginChoice.step = 'role'; loginPage(); };
  const form = document.getElementById('login'); labelAccountFields(form);
  form.onsubmit = async event => {
    event.preventDefault(); const button = form.querySelector('button');
    if (button.disabled) return;
    button.disabled = true; button.textContent = 'Signing in…';
    try {
      session = await api('/auth/login', {method: 'POST', body: JSON.stringify({...Object.fromEntries(new FormData(form)), role: loginChoice.role})});
      localStorage.setItem('tb_session', JSON.stringify(session));
      loginChoice.role = null; loginChoice.step = 'role';
      route(roles[session.user.role].home);
    } catch (error) { showAccountError(error.message); button.disabled = false; button.textContent = 'Sign in'; }
  };
};

function applyProductAccess() {
  if (session?.user.role !== 'requirement_vendor') return;
  const basic = session.user.product_mode === 'basic';
  const shell = document.querySelector('.shell');
  if (!shell) return;
  shell.classList.toggle('basic-workspace', basic);
  shell.dataset.productMode = session.user.product_mode || 'loading';
  document.querySelectorAll('[data-llm-feature]').forEach(element => {
    element.hidden = !session.user.features?.[element.dataset.llmFeature];
  });
  const actions = shell.querySelector('.top-actions');
  if (actions && !actions.querySelector('.workspace-mode')) {
    const label = document.createElement('span'); label.className = 'workspace-mode';
    label.textContent = modeLabels[session.user.product_mode] || 'Checking access…';
    actions.prepend(label);
  }
  // This existing assistant is deterministic and therefore remains in Basic.
  const agent = shell.querySelector('.vendor-agent');
  const title = agent?.querySelector('header b');
  if (title) title.textContent = 'Workspace Assistant';
  const status = agent?.querySelector('.online-dot');
  if (status) status.textContent = 'Local · No LLM';
  const disclaimer = agent?.querySelector('.ai-disclaimer');
  if (disclaimer) disclaimer.textContent = 'Local structured-data helper. No LLM calls. Scores use declared profile information, not resume-verified AI evidence.';
  const ask = shell.querySelector('[data-ask]');
  if (ask) ask.textContent = 'Workspace help';
  const verification = shell.querySelector('.partner-verification');
  if (verification) {
    verification.querySelector('b').textContent = 'Local employer workspace';
    verification.querySelector('span').textContent = 'Verification not connected';
  }
}
const priorLayout = layout;
layout = function(...args) { const result = priorLayout(...args); applyProductAccess(); return result; };
if (!nav.requirement_vendor.some(([,path]) => path === '/vendor/profile')) nav.requirement_vendor.push(['Company profile', '/vendor/profile']);
const priorProfilePage = profilePage;
profilePage = async function() {
  if (session?.user.role !== 'requirement_vendor') return priorProfilePage();
  try {
    const profile = await api('/vendor/profile');
    const fields = [['Company',profile.company_name],['Recruiter',profile.name],['Work email',profile.email],['Phone',profile.phone],
      ['Company type',profile.company_type],['Location',profile.city + ', ' + profile.country],['Website',profile.website],
      ['Company size',profile.company_size],['Industry',profile.industry],['Description',profile.description],['Hiring requirements',profile.hiring_requirements]];
    layout(head('Employer profile', 'Saved company and recruiter details for your local workspace.') +
      '<section class="panel employer-profile"><span class="workspace-mode">' + escapeAccountHtml(modeLabels[profile.product_mode]) +
      '</span><dl>' + fields.map(([label,value]) => '<div><dt>' + label + '</dt><dd>' + escapeAccountHtml(value || 'Not provided') + '</dd></div>').join('') +
      '</dl><p class="muted">' + (profile.consent_accepted ? 'Profile consent recorded. Company verification is not connected in this local preview.' : 'Legacy account. No onboarding consent record.') + '</p></section>', 'Company profile');
  } catch(error) { toast(error.message, true); }
};
(async () => {
  if (session) {
    try {
      session.user = await api('/auth/me');
      localStorage.setItem('tb_session', JSON.stringify(session));
    } catch(error) {
      if (session) { session.user.features = {}; toast('Feature access could not be refreshed. Please sign in again.', true); }
    }
  }
  render();
})();
