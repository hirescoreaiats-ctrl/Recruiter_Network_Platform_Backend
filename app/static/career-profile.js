function setupCareerSkillChips(form) {
  const value = form.querySelector('[name="skills"]');
  const skills = [];
  value.value.split(',').map(skill => skill.trim()).filter(Boolean).forEach(skill => {
    if (!skills.some(existing => existing.toLowerCase() === skill.toLowerCase())) skills.push(skill);
  });
  const box = document.createElement('div');
  box.className = 'career-skill-editor';
  const chips = document.createElement('div');
  chips.className = 'career-skill-chips';
  const input = document.createElement('input');
  input.type = 'text';
  input.id = value.id || 'career-skills';
  input.placeholder = 'Type a skill';
  input.setAttribute('aria-label', 'Add a skill');
  input.setAttribute('aria-describedby', 'career-skills-help');
  const add = document.createElement('button');
  add.type = 'button';
  add.className = 'btn btn-secondary';
  add.textContent = '+ Add';
  const help = document.createElement('small');
  help.id = 'career-skills-help';
  help.textContent = 'Press Enter or click Add for each skill. Add at least 3 different skills.';
  value.removeAttribute('id');
  value.required = false;
  value.type = 'hidden';
  value.after(box, help);
  box.append(chips, input, add);
  function render() {
    value.value = skills.join(',');
    chips.replaceChildren();
    skills.forEach((skill, index) => {
      const chip = document.createElement('span');
      chip.className = 'career-skill-chip';
      chip.append(document.createTextNode(skill));
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.textContent = '×';
      remove.setAttribute('aria-label', `Remove ${skill}`);
      remove.onclick = () => { skills.splice(index, 1); input.setCustomValidity(''); render(); input.focus(); };
      chip.append(remove);
      chips.append(chip);
    });
  }
  function commit() {
    input.value.split(',').map(skill => skill.trim()).filter(Boolean).forEach(skill => {
      if (!skills.some(existing => existing.toLowerCase() === skill.toLowerCase())) skills.push(skill);
    });
    input.value = '';
    input.setCustomValidity('');
    render();
  }
  add.onclick = () => { commit(); input.focus(); };
  input.onkeydown = event => {
    if (event.key === 'Enter' && !event.isComposing) { event.preventDefault(); commit(); }
  };
  input.onblur = commit;
  input.oninput = () => input.setCustomValidity('');
  render();
  return {input, commit, count: () => skills.length};
}

/* Only the current step is shown; all controls remain mounted to preserve edits. */
function setupCareerWizard(form, host, initialStep = 0) {
  form.noValidate = true;
  form.classList.add('career-wizard');
  const skillChips = setupCareerSkillChips(form);
  const base = [...form.children].filter(node => node.classList.contains('profile-form-card'));
  const section = key => host.querySelector(`#career-section-${key}`);
  const overview = section('career');
  base[1].append(...overview.querySelectorAll('.profile-form-grid'));
  overview.remove();
  const groups = [
    ['Identity & contact', [base[0]]],
    ['Career & skills', [base[1], section('it_skills')]],
    ['Education', [section('education_history')]],
    ['Employment & projects', [section('work_experiences'), section('projects')]],
    ['Location & job preferences', [base[2], section('preferences')]],
    ['Personal details & accomplishments', [section('personal'), section('languages'), section('accomplishments')]]
  ];
  const steps = groups.map(([, cards]) => {
    const group = document.createElement('div');
    group.className = 'career-step'; group.append(...cards); host.append(group); return group;
  });
  const titles = groups.map(([title]) => title);
  const progress = document.createElement('div');
  progress.className = 'career-progress';
  progress.innerHTML = '<p data-step-status role="status" aria-live="polite"></p><progress aria-label="Profile setup progress"></progress><p data-step-help></p>';
  form.prepend(progress);
  const bar = form.querySelector('.profile-save-bar');
  bar.innerHTML = '<button type="button" class="btn btn-secondary" data-career-back>← Back</button><span class="career-save-note">Details are saved when you finish.</span><button type="button" class="btn btn-primary" data-career-next>Next →</button><button type="submit" class="btn btn-primary" data-career-save>Save profile</button>';
  const back = bar.querySelector('[data-career-back]'), next = bar.querySelector('[data-career-next]'), save = bar.querySelector('[data-career-save]');
  let current = 0;
  function show(index, focus = true) {
    current = index;
    steps.forEach((step, i) => { step.hidden = i !== index; });
    progress.querySelector('[data-step-status]').textContent = `Step ${index + 1} of ${steps.length} · ${titles[index]}`;
    const meter = progress.querySelector('progress'); meter.max = steps.length; meter.value = index + 1;
    progress.querySelector('[data-step-help]').textContent = index === steps.length - 1 ? 'Last step. Add any optional details, then save your profile.' : 'Complete this section, then continue. You can go back to edit your answers.';
    back.disabled = index === 0;
    next.hidden = index === steps.length - 1;
    save.hidden = index !== steps.length - 1;
    if (focus) { const heading = steps[index].querySelector('h2'); heading.tabIndex = -1; heading.focus({preventScroll:true}); progress.scrollIntoView({block:'start',behavior:'smooth'}); }
  }
  function validate(index) {
    const step = steps[index];
    const inputs = [...step.querySelectorAll('input,select,textarea')];
    inputs.forEach(input => input.setCustomValidity(''));
    const skills = step.querySelector('[name="skills"]');
    if (skills) {
      skillChips.commit();
      if (skillChips.count() < 3) skillChips.input.setCustomValidity('Add at least 3 different skills.');
    }
    const records = step.querySelector('[data-records="education_history"]');
    if (records && !records.children.length) { show(index); toast('Add at least one education record.',true); return false; }
    if (step.contains(section('work_experiences')) && form.elements.extra_career_stage.value === 'experienced' && !form.elements.current_employer.value.trim() && !section('work_experiences').querySelector('.career-record')) { show(index); toast('Add your employment experience.',true); return false; }
    for (const row of step.querySelectorAll('.career-record')) {
      for (const [start, end] of [['start_date','end_date'],['start_year','end_year']]) {
        const from = row.querySelector(`[name$="_${start}"]`), to = row.querySelector(`[name$="_${end}"]`);
        if (from?.value && to?.value && (start === 'start_year' ? Number(to.value) < Number(from.value) : to.value < from.value)) to.setCustomValidity('End date must be after the start date.');
      }
    }
    const invalid = inputs.find(input => !input.checkValidity());
    if (invalid) { show(index); invalid.reportValidity(); return false; }
    return true;
  }
  const advance = () => { if (validate(current) && current < steps.length - 1) show(current + 1); };
  back.onclick = () => show(current - 1);
  next.onclick = advance;
  form.addEventListener('input', event => event.target.setCustomValidity?.(''));
  show(initialStep, false);
  return {next:advance, isLast:()=>current === steps.length - 1, validateAll:()=>steps.every((_,index)=>validate(index))};
}

/* Structured career evidence, saved with the existing candidate profile. */
const careerBaseProfilePage = profilePage;
function renderCandidateProfileOverview(profile) {
  const saved = profile.country_specific_data || {}, esc = candidateEscape;
  const work = Array.isArray(saved.work_experiences) ? saved.work_experiences : [];
  const education = Array.isArray(saved.education_history) ? saved.education_history : [];
  const itSkills = Array.isArray(saved.it_skills) ? saved.it_skills : [];
  const projects = Array.isArray(saved.projects) ? saved.projects : [];
  const accomplishments = Array.isArray(saved.accomplishments) ? saved.accomplishments : [];
  const languages = Array.isArray(saved.languages) ? saved.languages : [];
  const checks = [profile.full_name, profile.phone, profile.email, profile.city, profile.current_title, profile.resume_file_id,
    saved.resume_headline, profile.skills.length >= 3, work.length || saved.career_stage === 'fresher', education.length,
    saved.profile_summary, saved.preferred_locations?.length, saved.gender, saved.date_of_birth];
  const completion = Math.round(checks.filter(Boolean).length / checks.length * 100);
  const initials = profile.full_name.split(/\s+/).map(word=>word[0]).slice(0,2).join('').toUpperCase();
  const updated = new Date(profile.created_at).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});
  const salary = value => value && Number.isFinite(Number(value)) ? Number(value).toLocaleString('en-IN') : value;
  const add = label => `<button class="candidate-profile-add" data-profile-edit>＋ ${label}</button>`;
  const edit = '<button class="candidate-profile-edit" data-profile-edit aria-label="Edit profile">✎</button>';
  const recordDetails = item => `<div class="candidate-profile-details">${Object.entries(item).filter(([key,value]) => value !== '' && value != null && key !== 'is_current').map(([key,value]) => `<div><small>${esc(key.replaceAll('_',' '))}</small><b>${esc(Array.isArray(value) ? value.join(', ') : value)}</b></div>`).join('')}</div>`;
  const listCards = (items, renderer, emptyLabel) => items.length ? items.map(item => `<article class="candidate-profile-record">${recordDetails(item)}</article>`).join('') : add(emptyLabel);
  const sections = [
    ['contact','Contact & work details',`<div class="candidate-profile-details">${[['Name',profile.full_name],['Email',profile.email],['Phone',profile.phone],['Location',profile.city],['Country',countryConfig[profile.country]?.name||profile.country],['Job title',profile.current_title],['Current employer',profile.current_employer],['Experience (years)',profile.total_experience],['LinkedIn',profile.linkedin_url],['Career stage',saved.career_stage],['Highest qualification',saved.highest_qualification]].map(([label,value])=>`<div><small>${esc(label)}</small><b>${esc(value ?? 'Not added')}</b></div>`).join('')}</div>`],
    ['resume','Resume',profile.resume_file?`<div class="candidate-resume-row"><span>▤</span><div><b>${esc(profile.resume_file.original_name)}</b><small>Uploaded on ${new Date(profile.resume_file.created_at).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'})}</small></div><button data-resume="${profile.resume_file.id}">Download</button></div>`:add('Upload resume')],
    ['headline','Resume headline',saved.resume_headline?`<p>${esc(saved.resume_headline)}</p>`:add('Add resume headline')],
    ['skills','Key skills',profile.skills.length?`<div class="candidate-profile-chips">${profile.skills.map(skill=>`<span>${esc(skill)}</span>`).join('')}</div>`:add('Add key skills')],
    ['employment','Employment',listCards(work,item=>`<article class="candidate-profile-record"><b>${esc(item.job_title||'Job title')}</b><strong>${esc(item.company_name||'Company')}</strong><small>${esc(item.employment_type||'')} · ${esc(item.start_date||'')} to ${item.is_current?'Present':esc(item.end_date||'')}</small></article>`,'Add employment')],
    ['education','Education',listCards(education,item=>`<article class="candidate-profile-record"><b>${esc(item.course||item.qualification||'Qualification')} <span>${esc(item.specialization||'')}</span></b><strong>${esc(item.institution_name||'Institute')}</strong><small>${esc(item.start_year||'')} – ${esc(item.end_year||'')} · ${esc(item.course_type||'')}</small></article>`,'Add education')],
    ['it-skills','IT skills',itSkills.length?listCards(itSkills,null,'Add IT skills'):'<p class="candidate-profile-empty">Show your technical expertise by mentioning software and skills you know.</p>'+add('Add details')],
    ['projects','Projects',projects.length?listCards(projects,item=>`<article class="candidate-profile-record"><b>${esc(item.title)}</b><small>${esc(item.description||'')}</small></article>`,'Add project'):'<p class="candidate-profile-empty">Stand out by adding projects you have completed.</p>'+add('Add project')],
    ['summary','Profile summary',saved.profile_summary?`<p>${esc(saved.profile_summary)}</p>`:'<p class="candidate-profile-empty">Highlight your key career achievements and potential.</p>'+add('Add profile summary')],
    ['accomplishments','Accomplishments',accomplishments.length?listCards(accomplishments,item=>`<article class="candidate-profile-record"><b>${esc(item.title)}</b><small>${esc(item.type||'')}</small></article>`,'Add accomplishment'):`<div class="candidate-accomplishment-grid">${['Online profile','Work sample','Research publication','Presentation','Patent','Certification'].map(label=>`<button data-profile-edit><span>＋</span><b>${label}</b><small>Add relevant details</small></button>`).join('')}</div>`],
    ['career','Career profile',`<div class="candidate-profile-details">${[['Current industry',saved.industry],['Department',saved.department],['Role category',saved.role_category],['Job role',saved.desired_role],['Availability',saved.availability],['Notice period',saved.notice_period],['Current salary',saved.current_ctc],['Work mode',saved.work_mode],['Work authorization',saved.work_authorization],['Preferred shift',saved.preferred_shift],['Relocation',saved.willing_to_relocate],['Salary currency',saved.salary_currency],['Desired job type',saved.job_type],['Desired employment type',saved.employment_type],['Preferred work location',(saved.preferred_locations||[]).join(', ')],['Preferred annual salary',saved.expected_ctc?`₹${salary(saved.expected_ctc)}`:'']].map(([label,value])=>`<div><small>${label}</small><b>${esc(value||'Add '+label.toLowerCase())}</b></div>`).join('')}</div>`],
    ['personal','Personal details',`<div class="candidate-profile-details">${[['Gender',saved.gender],['Date of birth',saved.date_of_birth],['Marital status',saved.marital_status],['Work permit',saved.work_permit],['Address',saved.address],['Languages',languages.map(item=>[item.language,item.proficiency,item.abilities].filter(Boolean).join(' · ')).join(', ')],['Postal code',saved.postal_code],['Career break',saved.career_break],['Portfolio',saved.portfolio_url]].map(([label,value])=>`<div><small>${label}</small><b>${esc(value||'Add '+label.toLowerCase())}</b></div>`).join('')}</div>`],
    ['diversity','Diversity & inclusion',saved.disability ? `<p>Disability status: ${esc(saved.disability)}</p>` : add('Add disability status')]
  ];
  layout(`<div class="candidate-profile-overview"><section class="candidate-profile-hero"><div class="candidate-profile-avatar">${initials}</div><div><span class="candidate-profile-completion">${completion}%</span><h1>${esc(profile.full_name)} ${edit}</h1><small>Profile last updated · ${updated}</small><div class="candidate-profile-meta"><span>⌖ ${esc(profile.city||'Add location')}, ${esc(countryConfig[profile.country]?.name || profile.country)}</span><span>◷ ${profile.total_experience?`${Math.floor(profile.total_experience)} Years ${Math.round(profile.total_experience%1*12)} Months`:'Add experience'}</span><span>₹ ${saved.current_ctc?salary(saved.current_ctc):'Add salary'}</span><span>☎ ${esc(profile.phone)}</span><span>✉ ${esc(profile.email)}</span></div></div><button class="btn btn-primary" data-profile-edit>Edit profile</button></section><div class="candidate-profile-columns"><aside><section class="candidate-quick-links"><h2>Quick links</h2>${sections.map(([id,title])=>`<a href="#profile-${id}">${title}</a>`).join('')}</section><section class="candidate-profile-promo"><span>PRO</span><h3>Power up your profile</h3><p>Complete every section to improve recruiter visibility.</p></section></aside><main>${sections.map(([id,title,body])=>`<section id="profile-${id}" class="candidate-profile-section"><header><h2>${title}</h2>${edit}</header>${body}</section>`).join('')}</main></div></div>`,'My Profile');
  document.querySelectorAll('[data-profile-edit]').forEach(button=>button.onclick=()=>{
    const section = button.closest('.candidate-profile-section')?.id.replace('profile-', '') || '';
    route(section === 'resume' ? '/candidate/resume' : '/candidate/profile/edit' + (section ? '#' + section : ''));
  });
  wireDownloads();
}
profilePage = async function() {
  if (session?.user.role === 'candidate' && location.pathname === '/candidate/profile') {
    try {
      const overviewProfile = await api('/candidate/profile');
      return renderCandidateProfileOverview(overviewProfile);
    } catch (error) { toast(error.message,true); return; }
  }
  await careerBaseProfilePage();
  if (session?.user.role !== 'candidate') return;
  const form = document.querySelector('#candidate-profile-form');
  if (!form) return;
  try {
    const profile = await api('/candidate/profile');
    const saved = profile.country_specific_data || {};
    const esc = candidateEscape;
    const field = ([key, label, type = 'text', required = false], value = '', prefix = 'extra_') => {
      const id = `career-${prefix}${key}`;
      const attrs = `id="${esc(id)}" name="${esc(prefix + key)}" ${required ? 'required' : ''}`;
      const control = Array.isArray(type) ? `<select ${attrs}><option value="">Select ${esc(label.toLowerCase())}</option>${[...new Set([...type, ...(value && !type.includes(value) ? [value] : [])])].map(x => `<option ${x === value ? 'selected' : ''}>${esc(x)}</option>`).join('')}</select>` : type === 'textarea' ? `<textarea ${attrs} rows="3" maxlength="4000">${esc(value)}</textarea>` : `<input ${attrs} type="${type}" value="${esc(value)}" ${type === 'number' ? 'min="0" max="2100"' : ''} ${type === 'text' ? 'maxlength="500"' : ''}>`;
      return `<div class="field"><label for="${esc(id)}">${esc(label)}${required ? ' *' : ''}</label>${control}</div>`;
    };
    const sections = [
      ['career', 'Career overview', [['career_stage','Career stage',['fresher','experienced'],true],['highest_qualification','Highest qualification',['Doctorate / PhD','Post graduation','Graduation','Diploma','12th','10th','Below 10th'],true],['resume_headline','Resume headline'],['profile_summary','Profile summary','textarea']]],
      ['preferences','Desired career profile', [['industry','Industry',['IT Services & Consulting','Software Product','Banking','Financial Services','Healthcare','Education','Manufacturing','Retail','Telecom','Other']],['department','Department'],['role_category','Role category'],['desired_role','Desired job role'],['job_type','Job type',['Permanent','Contractual','Both']],['employment_type','Employment type',['Full time','Part time','Internship','Freelance']],['preferred_shift','Preferred shift',['Day','Night','Flexible']],['preferred_locations','Preferred locations (comma separated)'],['salary_currency','Salary currency',['INR','USD','GBP','EUR','AED','CAD','AUD']],['willing_to_relocate','Willing to relocate',['Yes','No','Depends on opportunity']]]],
      ['personal','Personal details (optional)', [['date_of_birth','Date of birth','date'],['gender','Gender',['Female','Male','Non-binary','Prefer to self-describe','Prefer not to say']],['marital_status','Marital status',['Single','Married','Other','Prefer not to say']],['address','Address','textarea'],['postal_code','Postal code'],['disability','Disability',['Yes','No','Prefer not to say']],['career_break','Career break details','textarea'],['work_permit','Work permit countries'],['portfolio_url','Portfolio website','url']]]
    ];
    const collections = [
      ['education_history','Education', [['qualification','Qualification','text',true],['institution_name','University / institute / school','text',true],['course','Course','text',true],['specialization','Specialization / stream','text',true],['course_type','Course type',['Full time','Part time','Correspondence / Distance']],['start_year','Starting year','number'],['end_year','Completion year','number',true],['grading_system','Grading system',['Percentage','CGPA out of 10','GPA out of 4','Pass / fail']],['grade','Marks / grade']]],
      ['work_experiences','Employment & internships', [['company_name','Company','text',true],['job_title','Job title','text',true],['employment_type','Employment type',['Full time','Part time','Internship','Contract','Freelance']],['start_date','Joining date','date',true],['end_date','Leaving date (blank for current job)','date'],['description','Job responsibilities','textarea'],['skills_used','Skills used']]],
      ['it_skills','IT skills', [['name','Skill / software','text',true],['version','Version'],['last_used','Last used year','number'],['experience_years','Experience in years','number']]],
      ['projects','Projects', [['title','Project title','text',true],['client','Client'],['status','Status',['In progress','Completed']],['start_date','Start date','date'],['end_date','End date','date'],['role','Your role'],['description','Project details','textarea'],['skills','Skills used'],['url','Project URL','url']]],
      ['accomplishments','Accomplishments', [['type','Type',['Certification','Online profile','Work sample','Publication / research paper','Presentation','Patent','Award'],true],['title','Title','text',true],['organization','Issuing organization'],['url','URL','url'],['issue_date','Issue date','date'],['expiry_date','Expiry date (optional)','date'],['description','Description','textarea']]],
      ['languages','Languages', [['language','Language','text',true],['proficiency','Proficiency',['Beginner','Proficient','Expert','Native']],['abilities','Can',['Read','Write','Speak','Read and write','Read and speak','Write and speak','Read, write and speak']]]]
    ];
    const block = (id, title, body) => `<section id="career-section-${id}" class="profile-form-card career-section"><header><div><h2>${title}</h2></div></header>${body}</section>`;
    const host = document.createElement('div');
    host.className = 'career-sections';
    host.innerHTML = sections.map(([id,title,fields]) => block(id,title,`<div class="profile-form-grid">${fields.map(f=>field(f,saved[f[0]] ?? '')).join('')}</div>`)).join('') + collections.map(([id,title])=>block(id,title,`<div data-records="${id}"></div><button type="button" class="btn btn-secondary" data-add="${id}">+ Add ${title.toLowerCase()}</button>`)).join('');
    form.querySelector('.profile-save-bar').before(host);
    let serial = 0;
    const addRecord = (key, fields, record = {}) => {
      const row = document.createElement('fieldset');
      row.className = 'career-record';
      row.innerHTML = `<legend>${esc(collections.find(x=>x[0]===key)[1])} entry</legend><div class="profile-form-grid">${fields.map(f=>field(f,record[f[0]] ?? '',`record_${serial}_`)).join('')}</div><button type="button" class="btn btn-secondary career-remove">Remove entry</button>`;
      serial++;
      row.querySelector('.career-remove').onclick = () => row.remove();
      row.dataset.original = JSON.stringify(record);
      host.querySelector(`[data-records="${key}"]`).append(row);
    };
    collections.forEach(([key,,fields]) => {
      const records = Array.isArray(saved[key]) ? saved[key] : [];
      records.forEach(record=>addRecord(key,fields,record));
      if (key === 'education_history' && !records.length) addRecord(key,fields,{qualification:saved.highest_qualification, specialization:saved.education_specialization,end_year:saved.graduation_year});
      host.querySelector(`[data-add="${key}"]`).onclick = () => addRecord(key,fields);
    });
    const resumeField = document.createElement('div');
    resumeField.className = 'field';
    resumeField.innerHTML = `<label for="onboarding-resume">Resume (optional)</label><input id="onboarding-resume" type="file" accept=".pdf,.doc,.docx"><small>${esc(profile.resume_file?.original_name || 'Upload a resume to help recruiters review your profile.')} · PDF, DOC or DOCX, up to 5 MB</small>`;
    host.querySelector('#career-section-personal .profile-form-grid').append(resumeField);
    const stage = form.elements.extra_career_stage;
    if (!stage.value) stage.value = profile.total_experience > 0 ? 'experienced' : 'fresher';
    const updateStage = () => { const input = form.elements.total_experience; input.readOnly = stage.value === 'fresher'; if (input.readOnly) input.value = '0'; };
    stage.onchange = updateStage; updateStage();
    const editing = location.pathname === '/candidate/profile/edit';
    const sectionSteps = {headline:1, skills:1, 'it-skills':1, summary:1, education:2, employment:3, projects:3, career:4, personal:5, accomplishments:5, diversity:5};
    const requestedSection = location.hash.replace('#', '');
    const wizard = setupCareerWizard(form, host, editing ? (sectionSteps[requestedSection] ?? 0) : 0);
    const builder = form.closest('.profile-builder');
    builder.classList.add('candidate-onboarding-builder');
    builder.querySelector('.profile-hero h1').textContent = editing ? 'Edit your profile' : 'Let’s build your profile';
    builder.querySelector('.profile-hero p').textContent = 'Complete these six steps so recruiters can discover your experience, skills and preferences.';
    if (!editing) {
      const page = document.createElement('div'); page.className = 'candidate-register-page';
      page.innerHTML = '<header class="candidate-register-header"><a class="candidate-register-brand"><span>H</span>HireScoreAI</a><p>Candidate profile setup</p></header>';
      page.append(builder); app.replaceChildren(page);
    }
    const cancel = document.createElement('button'); cancel.type = 'button'; cancel.className = 'btn btn-secondary';
    cancel.textContent = editing ? 'Back to profile' : 'Sign out';
    cancel.onclick = () => { if (editing) route('/candidate/profile'); else { localStorage.removeItem('tb_session'); session = null; route('/auth/login'); } };
    builder.querySelector('.profile-hero').append(cancel);
    form.onsubmit = async event => {
      event.preventDefault();
      if (!wizard.isLast()) { wizard.next(); return; }
      if (!wizard.validateAll()) return;
      const button = form.querySelector('[data-career-save]');
      if (button.disabled) return;
      const f = new FormData(form), data = {...saved};
      for (const [key,value] of f) if (key.startsWith('extra_')) data[key.slice(6)] = value.trim();
      for (const [key,,fields] of collections) {
        data[key] = [...host.querySelector(`[data-records="${key}"]`).children].map(row => {
          const record = JSON.parse(row.dataset.original);
          fields.forEach(([name],index)=>{record[name]=row.querySelectorAll('input,select,textarea')[index].value.trim();});
          if (key === 'work_experiences') record.is_current = !record.end_date;
          return record;
        });
        for (const record of data[key]) {
          if (record.start_date && record.end_date && record.end_date < record.start_date || record.start_year && record.end_year && Number(record.end_year) < Number(record.start_year)) { toast('End date must be after the start date.',true); return; }
        }
      }
      if (!data.education_history.length) { toast('Add at least one education record.',true); return; }
      data.preferred_locations = String(data.preferred_locations || '').split(',').map(value => value.trim()).filter(Boolean);
      data.education_specialization = data.education_history[0].specialization;
      data.graduation_year = data.education_history[0].end_year;
      data.onboarding_step = 'complete';
      const body = {country_specific_data:data};
      ['full_name','email','phone','country','city','current_title','linkedin_url','current_employer'].forEach(key=>body[key]=String(f.get(key)||'').trim());
      body.total_experience = Number(f.get('total_experience'));
      body.skills = [...new Set(String(f.get('skills')).split(',').map(x=>x.trim()).filter(Boolean))];
      button.disabled = true;
      const original = button.textContent; button.textContent = 'Saving profile…';
      try {
        const resume = resumeField.querySelector('input').files[0];
        if (resume) {
          if (resume.size > 5 * 1024 * 1024) throw new Error('Resume must be 5 MB or smaller.');
          const upload = new FormData(); upload.append('file', resume);
          await api(`/candidates/${profile.id}/resume`, {method:'POST',body:upload});
        }
        await api('/candidate/profile',{method:'PUT',body:JSON.stringify(body)}); toast('Career profile saved'); route('/candidate/profile'); }
      catch(error) { toast(error.message,true); }
      finally {button.disabled=false;button.textContent=original;}
    };
  } catch(error) { toast(error.message,true); }
};

const careerProfileRender = render;
render = async function() {
  if (session?.user?.role === 'candidate') {
    if (session.user.phone_verified === false) return careerProfileRender();
    const path = location.pathname;
    if (path.startsWith('/candidate/onboarding')) return profilePage();
    if (path === '/candidate/profile/edit') return profilePage();
    if (path.startsWith('/candidate') || path.startsWith('/auth')) {
      try {
        const profile = await api('/candidate/profile');
        if (path !== location.pathname) return;
        const saved = profile.country_specific_data || {};
        if (saved.onboarding_step !== 'complete' && !saved._profile_completed) return route('/candidate/onboarding');
      } catch (error) { toast(error.message, true); return; }
    }
  }
  return careerProfileRender();
};
window.onpopstate = () => render();
