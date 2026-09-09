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
function setupCareerWizard(form, host) {
  form.noValidate = true;
  form.classList.add('career-wizard');
  const skillChips = setupCareerSkillChips(form);
  const base = [...form.children].filter(node => node.classList.contains('profile-form-card'));
  const section = key => host.querySelector(`#career-section-${key}`);
  const overview = section('career');
  base[1].append(...overview.querySelectorAll('.profile-form-grid'));
  overview.remove();
  const steps = [base[0], base[1], section('education_history'), section('work_experiences'), base[2],
    section('preferences'), section('it_skills'), section('projects'), section('accomplishments'), section('languages'), section('personal')];
  steps.forEach(step => host.append(step));
  const titles = steps.map(step => step.querySelector('h2').textContent);
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
    if (step === section('work_experiences') && form.elements.extra_career_stage.value === 'experienced' && !form.elements.current_employer.value.trim() && !step.querySelector('.career-record')) { show(index); toast('Add your employment experience.',true); return false; }
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
  show(0, false);
  return {next:advance, isLast:()=>current === steps.length - 1, validateAll:()=>steps.every((_,index)=>validate(index))};
}

/* Structured career evidence, saved with the existing candidate profile. */
const careerBaseProfilePage = profilePage;
profilePage = async function() {
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
    const stage = form.elements.extra_career_stage;
    if (!stage.value) stage.value = profile.total_experience > 0 ? 'experienced' : 'fresher';
    const updateStage = () => { const input = form.elements.total_experience; input.readOnly = stage.value === 'fresher'; if (input.readOnly) input.value = '0'; };
    stage.onchange = updateStage; updateStage();
    const wizard = setupCareerWizard(form, host);
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
      data.education_specialization = data.education_history[0].specialization;
      data.graduation_year = data.education_history[0].end_year;
      const body = {country_specific_data:data};
      ['full_name','email','phone','country','city','current_title','linkedin_url','current_employer'].forEach(key=>body[key]=String(f.get(key)||'').trim());
      body.total_experience = Number(f.get('total_experience'));
      body.skills = [...new Set(String(f.get('skills')).split(',').map(x=>x.trim()).filter(Boolean))];
      button.disabled = true;
      const original = button.textContent; button.textContent = 'Saving profile…';
      try { await api('/candidate/profile',{method:'PUT',body:JSON.stringify(body)}); toast('Career profile saved'); await profilePage(); }
      catch(error) { toast(error.message,true); }
      finally {button.disabled=false;button.textContent=original;}
    };
  } catch(error) { toast(error.message,true); }
};
