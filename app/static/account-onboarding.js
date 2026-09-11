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
function candidateRegistrationPage() {
  app.innerHTML = '<div class="candidate-register-page"><header class="candidate-register-header"><a href="/auth/register" data-link class="candidate-register-brand"><span>H</span>HireScoreAI</a><p>Already registered? <a href="/auth/login" data-link>Login</a> here</p></header>' +
    '<main class="candidate-register-main"><aside class="candidate-register-benefits" aria-label="Registration benefits"><div class="candidate-register-illustration" aria-hidden="true"><span>✓</span><i>♙</i></div><h2>On registering, you can</h2><ul><li>Build your profile and let recruiters find you</li><li>Get relevant opportunities delivered to you</li><li>Find the right role and grow your career</li></ul></aside>' +
    '<section class="candidate-register-card"><button type="button" id="account-back" class="candidate-register-back">← Account type</button><h1>Create your account</h1><p>First, create your account. Then complete your profile in six guided steps.</p><p id="account-error" role="alert" class="account-error" hidden></p>' +
    '<form id="register" class="candidate-register-form"><div class="field"><label for="candidate-name">Full name <b>*</b></label><input id="candidate-name" name="name" autocomplete="name" placeholder="What is your name?" required maxlength="160"></div>' +
    '<div class="field"><label for="candidate-email">Email ID <b>*</b></label><input id="candidate-email" name="email" type="email" autocomplete="email" placeholder="Tell us your email ID" required><small>We’ll send relevant opportunities and updates to this email.</small></div>' +
    '<div class="field"><label for="candidate-password">Password <b>*</b></label><input id="candidate-password" name="password" type="password" autocomplete="new-password" minlength="8" placeholder="Minimum 8 characters" required><small>This helps your account stay protected.</small></div>' +
    '<div class="field"><label for="candidate-phone">Mobile number <b>*</b></label><div class="candidate-phone"><span>+91</span><input id="candidate-phone" name="phone" type="tel" inputmode="numeric" autocomplete="tel-national" minlength="10" maxlength="10" pattern="[0-9]{10}" placeholder="Enter your mobile number" required></div><small>Recruiters may contact you on this number.</small></div>' +
    '<fieldset class="candidate-work-status"><legend>Work status <b>*</b></legend><label><input type="radio" name="career_stage" value="experienced" required><span class="candidate-status-icon">▣</span><strong>I’m experienced</strong><small>I have work experience (excluding internships)</small></label><label><input type="radio" name="career_stage" value="fresher" required><span class="candidate-status-icon">◇</span><strong>I’m a fresher</strong><small>I’m a student or haven’t worked after graduation</small></label></fieldset>' +
    '<div class="candidate-status-detail" data-stage-detail="experienced" hidden><label for="candidate-resume">Resume <b>*</b></label><label class="candidate-resume-picker"><span>⌕</span><strong data-resume-name>Upload resume</strong><small>PDF, DOC or DOCX · max 5 MB</small><input id="candidate-resume" name="resume" type="file" accept=".pdf,.doc,.docx"></label></div>' +
    '<div class="candidate-status-detail" data-stage-detail="fresher" hidden><label for="candidate-city">Current city <b>*</b></label><input id="candidate-city" name="city" list="candidate-city-options" placeholder="Enter your current city"><datalist id="candidate-city-options"><option value="New Delhi"><option value="Mumbai"><option value="Bengaluru"><option value="Hyderabad"><option value="Chennai"><option value="Pune"><option value="Kolkata"></datalist><small>This helps recruiters know your location.</small></div>' +
    '<label class="candidate-updates"><input type="checkbox" name="updates"> Send me useful profile and opportunity updates.</label><p class="candidate-terms">By clicking Register now, you agree to use this platform for your recruitment profile.</p><button class="btn btn-primary" id="create-account">Register now</button></form></section></main></div>';
  const form = document.getElementById('register');
  for (const [name, value] of Object.entries(onboarding.draft)) {
    const control = form.elements.namedItem(name);
    if (!control) continue;
    if (control instanceof RadioNodeList) [...control].forEach(item => { item.checked = item.value === value; });
    else control.type === 'checkbox' ? control.checked = value === 'on' : control.value = value;
  }
  const stageControls = [...form.querySelectorAll('[name="career_stage"]')];
  const resumeInput = form.elements.resume, cityInput = form.elements.city;
  const syncStage = () => {
    const stage = stageControls.find(control => control.checked)?.value;
    form.querySelectorAll('[data-stage-detail]').forEach(detail => { detail.hidden = detail.dataset.stageDetail !== stage; });
    resumeInput.required = stage === 'experienced'; cityInput.required = stage === 'fresher';
  };
  stageControls.forEach(control => control.onchange = syncStage);
  resumeInput.onchange = () => {
    form.querySelector('[data-resume-name]').textContent = resumeInput.files[0]?.name || 'Upload resume';
  };
  syncStage();
  document.getElementById('account-back').onclick = () => { captureOnboardingDraft(); onboarding.step = 'role'; registerPage(); };
  form.onsubmit = async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const button = document.getElementById('create-account');
    button.disabled = true; button.textContent = 'Creating profile…';
    const values = Object.fromEntries(new FormData(form));
    const payload = {name: values.name, email: values.email, password: values.password, phone: '+91' + values.phone,
      role: 'candidate', profile: {onboarding_stage: 'account', career_stage: values.career_stage, city: values.city || ''}};
    try {
      session = await api('/auth/register', {method: 'POST', body: JSON.stringify(payload)});
      localStorage.setItem('tb_session', JSON.stringify(session));
      onboarding.draft = {}; onboarding.step = 'role'; onboarding.role = null;
      if (values.career_stage === 'experienced' && resumeInput.files[0]) {
        try {
          const profile = await api('/candidate/profile'), upload = new FormData();
          upload.append('file', resumeInput.files[0]);
          await api(`/candidates/${profile.id}/resume`, {method: 'POST', body: upload});
        } catch (uploadError) { toast('Account created, but resume upload failed: ' + uploadError.message, true); }
      }
      let delivery;
      try { delivery = await api('/auth/mobile-otp/send', {method: 'POST'}); }
      catch (otpError) { candidateVerificationPage(values.name, '+91 ' + values.phone, values.career_stage, null, otpError.message); return; }
      candidateVerificationPage(values.name, '+91 ' + values.phone, values.career_stage, delivery);
    } catch (error) { showAccountError(error.message); button.disabled = false; button.textContent = 'Register now'; }
  };
}
function candidateVerificationPage(name, phone, careerStage, delivery = null, sendError = '') {
  if (location.pathname !== '/candidate/verify-mobile') history.replaceState({}, '', '/candidate/verify-mobile');
  app.innerHTML = '<div class="candidate-register-page"><header class="candidate-register-header"><a href="/auth/register" class="candidate-register-brand"><span>H</span>HireScoreAI</a><p>Welcome, ' + escapeAccountHtml(name) + '</p></header>' +
    '<main class="candidate-register-main candidate-verify-main"><aside class="candidate-register-benefits"><div class="candidate-register-illustration" aria-hidden="true"><span>✓</span><i>♙</i></div><h2>Great, now you can</h2><ul><li>Build your profile and let recruiters find you</li><li>Get relevant opportunities delivered to you</li><li>Find the right role and grow your career</li></ul></aside>' +
    '<section class="candidate-register-card candidate-verify-card"><h1>Verify mobile number</h1><p>We sent a text message with a verification code to <strong>' + escapeAccountHtml(phone) + '</strong></p><p id="account-error" role="alert" class="account-error"' + (sendError ? '' : ' hidden') + '>' + escapeAccountHtml(sendError) + '</p>' +
    '<form id="candidate-otp-form"><div class="candidate-otp-inputs" aria-label="Four digit verification code">' + [0,1,2,3].map(index => '<input inputmode="numeric" autocomplete="one-time-code" maxlength="1" pattern="[0-9]" aria-label="Digit ' + (index + 1) + '">').join('') + '</div><p class="candidate-otp-note" data-otp-note></p><button class="btn btn-primary" id="verify-mobile" disabled>Verify</button></form><button type="button" class="candidate-resend" data-resend disabled>Resend code in 30s</button></section></main></div>';
  const inputs = [...document.querySelectorAll('.candidate-otp-inputs input')], verify = document.getElementById('verify-mobile');
  const note = document.querySelector('[data-otp-note]'), resend = document.querySelector('[data-resend]');
  const error = document.getElementById('account-error');
  const applyDelivery = result => {
    delivery = result;
    note.textContent = result?.delivery === 'development' ? 'Development OTP: ' + result.development_code : 'Your OTP should arrive shortly.';
    let seconds = result?.retry_after_seconds || 30;
    resend.disabled = true; resend.textContent = 'Resend code in ' + seconds + 's';
    const timer = setInterval(() => {
      seconds -= 1; resend.textContent = seconds > 0 ? 'Resend code in ' + seconds + 's' : 'Resend verification code';
      if (seconds <= 0) { clearInterval(timer); resend.disabled = false; }
    }, 1000);
  };
  if (delivery) applyDelivery(delivery);
  else { resend.disabled = false; resend.textContent = 'Send verification code'; }
  const refreshButton = () => { verify.disabled = inputs.some(input => !/^\d$/.test(input.value)); };
  inputs.forEach((input, index) => {
    input.oninput = () => { input.value = input.value.replace(/\D/g, '').slice(-1); if (input.value) inputs[index + 1]?.focus(); refreshButton(); };
    input.onkeydown = event => { if (event.key === 'Backspace' && !input.value) inputs[index - 1]?.focus(); };
    input.onpaste = event => {
      const digits = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 4);
      if (digits.length === 4) { event.preventDefault(); inputs.forEach((item, itemIndex) => { item.value = digits[itemIndex]; }); inputs[3].focus(); refreshButton(); }
    };
  });
  inputs[0].focus();
  document.getElementById('candidate-otp-form').onsubmit = async event => {
    event.preventDefault(); if (verify.disabled) return;
    verify.disabled = true; verify.textContent = 'Verifying…'; error.hidden = true;
    try { await api('/auth/mobile-otp/verify', {method: 'POST', body: JSON.stringify({code: inputs.map(input => input.value).join('')})}); session.user.phone_verified = true; localStorage.setItem('tb_session', JSON.stringify(session)); route('/candidate/onboarding'); }
    catch (verifyError) { error.textContent = verifyError.message; error.hidden = false; verify.disabled = false; verify.textContent = 'Verify'; }
  };
  resend.onclick = async () => {
    resend.disabled = true; error.hidden = true;
    try { applyDelivery(await api('/auth/mobile-otp/send', {method: 'POST'})); }
    catch (resendError) { error.textContent = resendError.message; error.hidden = false; resend.disabled = false; resend.textContent = 'Resend verification code'; }
  };
}
async function restoreCandidateVerificationPage() {
  try {
    const [user, profile] = await Promise.all([api('/auth/me'), api('/candidate/profile')]);
    session.user = user; localStorage.setItem('tb_session', JSON.stringify(session));
    if (user.phone_verified) return route('/candidate/dashboard');
    candidateVerificationPage(user.name, user.phone, profile.country_specific_data?.career_stage || 'fresher', null, 'Request a verification code to continue.');
  } catch (error) { toast(error.message, true); }
}
async function candidateEmploymentPage() {
  try {
    const profile = await api('/candidate/profile'), saved = profile.country_specific_data || {}, work = saved.work_experiences?.[0] || {};
    const years = Math.floor(profile.total_experience || 0), months = Math.round(((profile.total_experience || 0) - years) * 12);
    const noticeOptions = ['15 Days or less', '1 Month', '2 Months', '3 Months', 'More than 3 Months'];
    app.innerHTML = `<div class="candidate-register-page"><header class="candidate-register-header"><a class="candidate-register-brand"><span>H</span>HireScoreAI</a><p>Welcome, ${escapeAccountHtml(profile.full_name)}</p></header><main class="candidate-employment-main"><aside class="candidate-onboarding-steps"><div class="done"><i>✓</i><span>Basic details</span></div><div class="active"><i></i><span><b>Employment</b><small>Your experience is your success story, talk about it</small></span></div><div><i></i><span>Education</span></div><div><i></i><span>Last step</span></div></aside><section class="candidate-register-card candidate-employment-card"><h1>Employment details</h1><p>These details help recruiters identify your professional experience.</p><p id="account-error" role="alert" class="account-error" hidden></p><form id="candidate-employment-form">
      <fieldset class="candidate-pill-field"><legend>Are you currently employed? <b>*</b></legend><label><input type="radio" name="currently_employed" value="true" ${work.is_current !== false ? 'checked' : ''}><span>Yes</span></label><label><input type="radio" name="currently_employed" value="false" ${work.is_current === false ? 'checked' : ''}><span>No</span></label></fieldset>
      <div class="candidate-onboarding-field"><label>Total work experience <b>*</b></label><div class="candidate-field-row"><select name="experience_years" required>${Array.from({length:61},(_,value)=>`<option value="${value}" ${years===value?'selected':''}>${value} Year${value===1?'':'s'}</option>`).join('')}</select><select name="experience_months" required>${Array.from({length:12},(_,value)=>`<option value="${value}" ${months===value?'selected':''}>${value} Month${value===1?'':'s'}</option>`).join('')}</select></div></div>
      <div class="candidate-onboarding-field"><label>Company name <b>*</b></label><input name="company_name" value="${escapeAccountHtml(work.company_name || profile.current_employer || '')}" placeholder="Eg. Amazon" required maxlength="200"></div>
      <div class="candidate-onboarding-field"><label>Current job title <b>*</b></label><input name="job_title" value="${escapeAccountHtml(work.job_title || profile.current_title || '')}" placeholder="Eg. Software Developer" required maxlength="200"></div>
      <div class="candidate-onboarding-field"><label>Current city <b>*</b></label><input name="city" value="${escapeAccountHtml(profile.city || '')}" list="employment-city-options" placeholder="Enter your current city" required><datalist id="employment-city-options"><option value="New Delhi"><option value="Mumbai"><option value="Bengaluru"><option value="Hyderabad"><option value="Chennai"><option value="Pune"><option value="Kolkata"></datalist><small>This helps recruiters know your location.</small></div>
      <div class="candidate-onboarding-field"><label>Duration <b>*</b></label><div class="candidate-field-row candidate-duration"><input type="month" name="start_date" value="${escapeAccountHtml(work.start_date || '')}" required><span>To</span><input type="month" name="end_date" value="${escapeAccountHtml(work.end_date || '')}" ${work.is_current === false ? 'required' : ''}><em>Present</em></div></div>
      <div class="candidate-onboarding-field"><label>Annual salary <b>*</b></label><div class="candidate-salary"><span>₹</span><input name="annual_salary" type="number" min="0" step="1000" value="${escapeAccountHtml(saved.current_ctc || '')}" placeholder="Eg. 5,64,000" required></div></div>
      <fieldset class="candidate-pill-field candidate-notice"><legend>Notice period <b>*</b></legend>${noticeOptions.map(option=>`<label><input type="radio" name="notice_period" value="${option}" ${saved.notice_period===option?'checked':''} required><span>${option}</span></label>`).join('')}</fieldset>
      <button class="btn btn-primary" id="save-employment">Save and continue</button></form></section></main></div>`;
    const form = document.getElementById('candidate-employment-form'), end = form.elements.end_date;
    const syncEmployment = () => { const current = form.elements.currently_employed.value === 'true'; end.hidden = current; end.required = !current; form.querySelector('.candidate-duration em').hidden = !current; };
    [...form.querySelectorAll('[name="currently_employed"]')].forEach(control => control.onchange = syncEmployment); syncEmployment();
    form.onsubmit = async event => {
      event.preventDefault(); if (!form.reportValidity()) return;
      const button = document.getElementById('save-employment'), values = Object.fromEntries(new FormData(form));
      button.disabled = true; button.textContent = 'Saving…';
      const body = {...values, currently_employed: values.currently_employed === 'true', experience_years: Number(values.experience_years), experience_months: Number(values.experience_months), annual_salary: Number(values.annual_salary), end_date: values.currently_employed === 'true' ? null : values.end_date};
      try { await api('/candidate/onboarding/employment', {method: 'PUT', body: JSON.stringify(body)}); route('/candidate/onboarding/education'); }
      catch (saveError) { showAccountError(saveError.message); button.disabled = false; button.textContent = 'Save and continue'; }
    };
  } catch (error) { toast(error.message, true); route('/candidate/dashboard'); }
}
function onboardingSteps(active, employmentDone = true) {
  const steps = [
    ['basic', 'Basic details', ''], ['employment', 'Employment', 'Your experience is your success story, talk about it'],
    ['education', 'Education', 'Employers prefer to know about your education'], ['last', 'Last step', 'Add your resume headline and preferences to make your profile richer']
  ];
  const activeIndex = steps.findIndex(([key]) => key === active);
  return '<aside class="candidate-onboarding-steps">' + steps.map(([key,label,help], index) => {
    const done = index < activeIndex && (key !== 'employment' || employmentDone);
    return `<div class="${done?'done':key===active?'active':''}"><i>${done?'✓':''}</i><span>${key===active?`<b>${label}</b>`:label}${key===active&&help?`<small>${help}</small>`:''}</span></div>`;
  }).join('') + '</aside>';
}
async function candidateEducationPage() {
  try {
    const profile = await api('/candidate/profile'), saved = profile.country_specific_data || {}, education = saved.education_history?.[0] || {};
    const fresher = saved.career_stage === 'fresher', currentYear = new Date().getFullYear();
    app.innerHTML = `<div class="candidate-register-page"><header class="candidate-register-header"><a class="candidate-register-brand"><span>H</span>HireScoreAI</a><p>Welcome, ${escapeAccountHtml(profile.full_name)}</p></header><main class="candidate-employment-main">${onboardingSteps('education', !fresher)}<section class="candidate-register-card candidate-employment-card"><h1>Education details</h1><p>These details help recruiters identify your background.</p>${education.course||education.institution_name?'<div class="resume-prefill-note">✓ Details found in your resume. Please review and edit if needed.</div>':''}<p id="account-error" role="alert" class="account-error" hidden></p><form id="candidate-education-form">
      <div class="candidate-onboarding-field"><label>Highest qualification <b>*</b></label><select name="qualification" required><option value="">Select qualification</option>${['Doctorate / PhD','Post graduation','Graduation','Diploma','12th','10th'].map(value=>`<option ${value===(education.qualification||saved.highest_qualification)?'selected':''}>${value}</option>`).join('')}</select></div>
      <div class="candidate-onboarding-field"><label>Course <b>*</b></label><input name="course" value="${escapeAccountHtml(education.course||'')}" placeholder="Eg. B.Tech / B.E." required></div>
      <fieldset class="candidate-pill-field"><legend>Course type <b>*</b></legend>${['Full time','Part time','Correspondence / Distance'].map(value=>`<label><input type="radio" name="course_type" value="${value}" ${(education.course_type||'Full time')===value?'checked':''} required><span>${value}</span></label>`).join('')}</fieldset>
      <div class="candidate-onboarding-field"><label>Specialization <b>*</b></label><input name="specialization" value="${escapeAccountHtml(education.specialization||saved.education_specialization||'')}" placeholder="Eg. Information Technology" required></div>
      <div class="candidate-onboarding-field"><label>University / Institute <b>*</b></label><input name="institution_name" value="${escapeAccountHtml(education.institution_name||'')}" placeholder="Enter university or institute" required></div>
      <div class="candidate-onboarding-field candidate-year-field"><label>Starting year <b>*</b></label><input name="start_year" type="number" min="1950" max="2100" value="${escapeAccountHtml(education.start_year||'')}" placeholder="Eg. ${currentYear-4}" required><div>${[currentYear,currentYear-1,currentYear-2,currentYear-3].map(year=>`<button type="button" data-year="start_year" data-value="${year}">${year}</button>`).join('')}</div></div>
      <div class="candidate-onboarding-field candidate-year-field"><label>Passing year <b>*</b></label><input name="end_year" type="number" min="1950" max="2100" value="${escapeAccountHtml(education.end_year||saved.graduation_year||'')}" placeholder="Eg. ${currentYear}" required><div>${[currentYear+3,currentYear+2,currentYear+1,currentYear].map(year=>`<button type="button" data-year="end_year" data-value="${year}">${year}</button>`).join('')}</div></div>
      <button class="btn btn-primary" id="save-education">Save and continue</button></form></section></main></div>`;
    const form = document.getElementById('candidate-education-form');
    form.querySelectorAll('[data-year]').forEach(button => button.onclick = () => { form.elements[button.dataset.year].value = button.dataset.value; });
    form.onsubmit = async event => {
      event.preventDefault(); if (!form.reportValidity()) return;
      const button = document.getElementById('save-education'), values = Object.fromEntries(new FormData(form));
      button.disabled = true; button.textContent = 'Saving…'; values.start_year = Number(values.start_year); values.end_year = Number(values.end_year);
      try { await api('/candidate/onboarding/education', {method:'PUT', body:JSON.stringify(values)}); route('/candidate/onboarding/preferences'); }
      catch (saveError) { showAccountError(saveError.message); button.disabled=false; button.textContent='Save and continue'; }
    };
  } catch (error) { toast(error.message, true); route('/candidate/dashboard'); }
}
async function candidatePreferencesPage() {
  try {
    const profile = await api('/candidate/profile'), saved = profile.country_specific_data || {}, education = saved.education_history?.[0] || {};
    const suggestion = [profile.current_title, education.course ? `with ${education.course}` : '', education.specialization ? `in ${education.specialization}` : '', profile.city ? `currently living in ${profile.city}` : ''].filter(Boolean).join(' ');
    const locationSuggestions = ['Bengaluru','Mumbai','Pune','Chennai','Hyderabad','Gurugram','Noida','Ahmedabad','Kolkata','Delhi / NCR','Remote'];
    app.innerHTML = `<div class="candidate-register-page"><header class="candidate-register-header"><a class="candidate-register-brand"><span>H</span>HireScoreAI</a><p>Welcome, ${escapeAccountHtml(profile.full_name)}</p></header><main class="candidate-employment-main">${onboardingSteps('last', true)}<section class="candidate-register-card candidate-employment-card candidate-preferences-card"><h1>Add headline & preferences</h1><p>Make your profile stronger to get more relevant job recommendations.</p><p id="account-error" role="alert" class="account-error" hidden></p><form id="candidate-preferences-form">
      <div class="candidate-onboarding-field"><label>Resume headline <b>*</b></label><textarea name="resume_headline" maxlength="300" placeholder="Add a concise headline that describes your career" required>${escapeAccountHtml(saved.resume_headline||'')}</textarea><small>Suggestion:</small><label class="candidate-headline-suggestion"><input type="radio" name="headline_suggestion" value="${escapeAccountHtml(suggestion)}"><span>${escapeAccountHtml(suggestion || 'Add your professional headline')}</span></label></div>
      <div data-preferences-extra ${saved.resume_headline?'':'hidden'}><div class="candidate-onboarding-field"><label>Preferred work locations <em>(Maximum 10)</em> <b>*</b></label><div class="candidate-location-editor"><div data-selected-locations></div><input data-location-input placeholder="Eg. Chennai, Bangalore, Mumbai"></div><small>Suggestions:</small><div class="candidate-location-suggestions">${locationSuggestions.map(value=>`<button type="button" data-location="${value}">${value} <span>＋</span></button>`).join('')}</div></div>
      <div class="candidate-onboarding-field"><label>Preferred salary <b>*</b></label><div class="candidate-salary"><span>₹</span><input name="preferred_salary" type="number" min="0" step="1000" value="${escapeAccountHtml(saved.expected_ctc||'')}" placeholder="Eg. 5,64,000" required></div><small>per year</small></div>
      <fieldset class="candidate-pill-field"><legend>Gender <b>*</b></legend>${['Male','Female','Transgender','Non-binary','Prefer not to say'].map(value=>`<label><input type="radio" name="gender" value="${value}" ${saved.gender===value?'checked':''} required><span>${value}</span></label>`).join('')}</fieldset></div>
      <button class="btn btn-primary" id="save-preferences">Submit</button></form></section></main></div>`;
    const form = document.getElementById('candidate-preferences-form'), headline = form.elements.resume_headline, extra = form.querySelector('[data-preferences-extra]');
    form.elements.headline_suggestion.onchange = () => { headline.value = form.elements.headline_suggestion.value; extra.hidden = false; };
    const selected = new Set(saved.preferred_locations || []), selectedHost = form.querySelector('[data-selected-locations]'), locationInput = form.querySelector('[data-location-input]');
    const renderLocations = () => { selectedHost.innerHTML = [...selected].map(value=>`<button type="button" data-remove-location="${escapeAccountHtml(value)}">${escapeAccountHtml(value)} ×</button>`).join(''); selectedHost.querySelectorAll('[data-remove-location]').forEach(button=>button.onclick=()=>{selected.delete(button.dataset.removeLocation);renderLocations();}); };
    const addLocation = value => { value=value.trim(); if(value && selected.size<10) { selected.add(value); renderLocations(); } };
    form.querySelectorAll('[data-location]').forEach(button=>button.onclick=()=>addLocation(button.dataset.location));
    locationInput.onkeydown = event => { if(event.key==='Enter'){event.preventDefault();addLocation(locationInput.value);locationInput.value='';} }; renderLocations();
    form.onsubmit = async event => {
      event.preventDefault(); if (extra.hidden) { form.elements.headline_suggestion.reportValidity(); return; } addLocation(locationInput.value);
      if (!selected.size) { locationInput.setCustomValidity('Add at least one preferred location'); locationInput.reportValidity(); return; } locationInput.setCustomValidity('');
      if (!form.reportValidity()) return; const button=document.getElementById('save-preferences'), values=Object.fromEntries(new FormData(form)); button.disabled=true;button.textContent='Submitting…';
      const body={resume_headline:headline.value.trim(),preferred_locations:[...selected],preferred_salary:Number(values.preferred_salary),gender:values.gender};
      try { await api('/candidate/onboarding/preferences',{method:'PUT',body:JSON.stringify(body)}); toast('Candidate profile created successfully'); route('/candidate/profile'); }
      catch(saveError){showAccountError(saveError.message);button.disabled=false;button.textContent='Submit';}
    };
  } catch(error){toast(error.message,true);route('/candidate/dashboard');}
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
      if (kind === 'register' && state.role === 'candidate') {
        state.step = 'details'; registerPage(); return;
      }
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
  if (onboarding.role === 'candidate') return candidateRegistrationPage();
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
const accountOnboardingRender = render;
render = function() {
  if (session?.user?.role === 'candidate' && session.user.phone_verified === false && location.pathname !== '/candidate/verify-mobile') return route('/candidate/verify-mobile');
  if (session?.user?.role === 'candidate' && location.pathname === '/candidate/verify-mobile') return restoreCandidateVerificationPage();
  if (session?.user?.role === 'candidate' && location.pathname === '/candidate/onboarding/employment') return candidateEmploymentPage();
  if (session?.user?.role === 'candidate' && location.pathname === '/candidate/onboarding/education') return candidateEducationPage();
  if (session?.user?.role === 'candidate' && location.pathname === '/candidate/onboarding/preferences') return candidatePreferencesPage();
  return accountOnboardingRender();
};
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
