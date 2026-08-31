/* Candidate-only navigation and resume page. Other role workspaces stay intact. */
const candidateUiIcons = {
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',
  profile: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  file: '<path d="M14 2H5v20h14V7zM14 2v6h5M8 12h8M8 16h6"/>',
  upload: '<path d="M12 16V3m-5 5 5-5 5 5M3 15v6h18v-6"/>',
  download: '<path d="M12 3v13m-5-5 5 5 5-5M3 17v4h18v-4"/>',
  arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  logout: '<path d="M10 3H4v18h6M9 12h12m-5-5 5 5-5 5"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 14v3"/>',
  spark: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>'
};
const candidateIcon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${candidateUiIcons[name] || candidateUiIcons.file}</svg>`;
const candidateEscape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const candidateFileSize = bytes => bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
async function openCandidateConversation() {
  if (location.pathname !== '/candidate/dashboard') {
    history.pushState({}, '', '/candidate/dashboard');
    await dashboard();
  }
  const input = document.querySelector('#career-message');
  if (input) {
    input.scrollIntoView({behavior: 'smooth', block: 'center'});
    input.focus({preventScroll: true});
  }
}

const candidateBaseLayout = layout;
layout = function(content, title) {
  candidateBaseLayout(content, title);
  if (session?.user.role !== 'candidate') return;
  window.scrollTo(0, 0);
  const shell = document.querySelector('.shell');
  shell.classList.add('candidate-workspace-shell');
  const sidebar = shell.querySelector('.sidebar');
  const logoutAction = document.querySelector('#logout').onclick;
  const sections = [ ['Home', '/candidate/dashboard', 'home'], ['My Profile', '/candidate/profile', 'profile'], ['Availability', '/candidate/availability', 'clock'], ['My Resume', '/candidate/resume', 'file'] ];
  sidebar.id = 'candidate-navigation';
  sidebar.innerHTML = `
    <a class="cw-brand" href="/candidate/dashboard" data-link aria-label="HireScore AI home"><span class="cw-logo"><svg viewBox="0 0 30 30" aria-hidden="true"><path d="M5 22V13h5v9zm8 0V8h5v14zm8 0V3h5v19z" fill="currentColor"/><path d="m5 26 21-8" stroke="#9c91ff" stroke-width="2"/></svg></span><span><strong>HireScore AI</strong><small>CANDIDATE WORKSPACE</small></span></a>
    <div class="cw-nav-body"><span class="cw-section-label">WORKSPACE</span><nav class="nav cw-nav" aria-label="Candidate workspace">${sections.map(([label,path,icon]) => `<a href="${path}" data-link class="${location.pathname===path?'active':''}" ${location.pathname===path?'aria-current="page"':''}><span class="cw-nav-icon">${candidateIcon(icon)}</span><span>${label}</span></a>`).join('')}</nav></div>
    <div class="cw-sidebar-bottom"><button type="button" id="logout" class="cw-logout">${candidateIcon('logout')}<span>Logout</span></button></div>`;
  sidebar.querySelector('#logout').onclick = logoutAction;
  const pageLabel = sections.find(([,path]) => path === location.pathname)?.[0] || title;
  const initials = session.user.name.split(/\s+/).map(word => word[0]).slice(0,2).join('').toUpperCase();
  shell.querySelector('.topbar').innerHTML = `<div class="cw-breadcrumb"><button type="button" class="cw-menu" aria-label="Open navigation" aria-controls="candidate-navigation" aria-expanded="false">${candidateIcon('menu')}</button><span>Workspace</span><i>/</i><b>${candidateEscape(pageLabel)}</b></div><div class="cw-top-actions"><span class="cw-local">Local workspace</span><button type="button" class="cw-top-agent">${candidateIcon('spark')}<span>Ask your agent</span></button><a href="/candidate/profile" data-link class="cw-top-avatar" aria-label="My profile">${candidateEscape(initials)}</a></div>`;
  const overlay = document.createElement('button');
  overlay.className = 'cw-nav-backdrop';
  overlay.setAttribute('aria-label', 'Close navigation');
  shell.append(overlay);
  const menu = shell.querySelector('.cw-menu');
  const setOpen = open => {
    sidebar.classList.toggle('open', open);
    shell.classList.toggle('navigation-open', open);
    menu.setAttribute('aria-expanded', String(open));
    menu.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
  };
  menu.onclick = () => setOpen(!sidebar.classList.contains('open'));
  overlay.onclick = () => { setOpen(false); menu.focus(); };
  shell.onkeydown = event => { if (event.key === 'Escape') { setOpen(false); menu.focus(); } };
  shell.querySelector('.cw-top-agent').onclick = openCandidateConversation;
};

resumePage = async function() {
  try {
    const profile = await api('/candidate/profile');
    const resume = profile.resume_file;
    const hasResume = Boolean(profile.resume_file_id);
    const maxBytes = profile.max_resume_bytes || 5 * 1024 * 1024;
    const maxSize = candidateFileSize(maxBytes);
    const uploadedDate = resume?.created_at ? new Date(resume.created_at + (/[Z+]/.test(resume.created_at) ? '' : 'Z')).toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric'}) : '';
    layout(`<div class="resume-studio"><header class="rs-page-head"><div><span class="rs-eyebrow">YOUR CAREER DOCUMENTS</span><h1>My resume</h1><p>Keep your experience up to date. Be ready for your next opportunity.</p></div><span class="rs-status ${hasResume?'uploaded':''}"><i></i>${hasResume?'Resume uploaded':'No resume yet'}</span></header>
      <section class="rs-current" aria-labelledby="current-resume-title"><div class="rs-document-icon">${candidateIcon('file')}</div><div class="rs-current-copy"><span id="current-resume-title">${hasResume?'CURRENT RESUME':'YOUR RESUME'}</span><h2>${candidateEscape(resume?.original_name || (hasResume?'Current resume':'Add your first resume'))}</h2><p>${hasResume ? [resume ? candidateFileSize(resume.size_bytes) : '', uploadedDate ? `Uploaded ${uploadedDate}` : '', 'Saved to your profile'].filter(Boolean).join('<i>·</i>') : 'Your uploaded document will appear here.'}</p></div>${hasResume?`<button type="button" class="rs-download" data-resume="${profile.resume_file_id}">${candidateIcon('download')}<span>Download resume</span></button>`:''}</section>
      <div class="rs-columns"><section class="rs-upload-card"><header><h2>${hasResume?'Update your resume':'Upload your resume'}</h2><p>${hasResume?'Add your latest version when your experience changes.':'Start with a document that tells your career story.'}</p></header><form id="resume"><div class="rs-dropzone"><span class="rs-upload-icon">${candidateIcon('upload')}</span><h3>Drag & drop your resume here</h3><p>or <span>browse files</span> from your computer</p><div class="rs-file-types"><span>PDF</span><span>DOC</span><span>DOCX</span><small>Up to ${maxSize}</small></div><input id="resume-file" name="file" type="file" accept=".pdf,.doc,.docx" aria-label="Choose a resume file" aria-describedby="resume-upload-help resume-feedback"></div><div class="rs-selection" hidden><span class="rs-selected-icon">${candidateIcon('file')}</span><div><b></b><small></small></div><button type="button" class="rs-clear-file" aria-label="Remove selected file">×</button></div><p id="resume-feedback" role="status" aria-live="polite"></p><div class="rs-upload-footer"><p id="resume-upload-help">${candidateIcon('lock')}<span>${hasResume?'Your current file stays until the new upload succeeds.':'Only upload a document you want linked to your profile.'}</span></p><button type="submit" class="rs-upload-submit" disabled>${candidateIcon('upload')}<span>${hasResume?'Replace resume':'Upload resume'}</span></button></div></form></section>
      <aside class="rs-guidance"><section><span class="rs-guide-icon">${candidateIcon('spark')}</span><h2>Make a strong<br>first impression.</h2><p>A clear, current resume helps recruiters understand what you bring.</p><ul><li>${candidateIcon('check')}<span>Lead with your recent experience.</span></li><li>${candidateIcon('check')}<span>Highlight skills and measurable results.</span></li><li>${candidateIcon('check')}<span>Keep contact details up to date.</span></li></ul></section><div class="rs-profile-tip"><b>Your profile matters, too</b><p>Matching uses the skills, experience and preferences saved in your profile.</p><a href="/candidate/profile" data-link>Review my profile ${candidateIcon('arrow')}</a></div></aside></div>
      <p class="rs-security-note">${candidateIcon('lock')} Resume access follows your workspace permissions. Uploading does not submit a job application.</p></div>`, 'My Resume');
    wireDownloads();
    const form = document.querySelector('#resume');
    const fileInput = form.querySelector('input[type=file]');
    const zone = form.querySelector('.rs-dropzone');
    const selection = form.querySelector('.rs-selection');
    const feedback = form.querySelector('#resume-feedback');
    const submit = form.querySelector('[type=submit]');
    let selectedFile = null;
    let uploading = false;
    const selectFile = file => {
      if (uploading) return;
      selectedFile = null;
      selection.hidden = true;
      submit.disabled = true;
      feedback.textContent = '';
      feedback.className = '';
      if (!file) return;
      const error = !/\.(pdf|doc|docx)$/i.test(file.name) ? 'Choose a PDF, DOC or DOCX file.' : !file.size ? 'This file is empty. Please choose another file.' : file.size > maxBytes ? `This file exceeds ${maxSize}. Please choose a smaller file.` : '';
      if (error) { feedback.textContent = error; feedback.className = 'rs-error'; fileInput.value = ''; return; }
      selectedFile = file;
      selection.querySelector('b').textContent = file.name;
      selection.querySelector('small').textContent = `${candidateFileSize(file.size)} · Ready to upload`;
      selection.hidden = false;
      submit.disabled = false;
    };
    fileInput.onchange = () => selectFile(fileInput.files[0]);
    form.querySelector('.rs-clear-file').onclick = () => { fileInput.value = ''; selectFile(null); fileInput.focus(); };
    zone.ondragover = event => { event.preventDefault(); if (!uploading) zone.classList.add('drag-over'); };
    zone.ondragleave = () => zone.classList.remove('drag-over');
    zone.ondrop = event => {
      event.preventDefault(); zone.classList.remove('drag-over');
      if (uploading) return;
      if (event.dataTransfer.files.length > 1) { selectFile(null); feedback.textContent = 'Choose one resume at a time.'; feedback.className = 'rs-error'; return; }
      fileInput.value = ''; selectFile(event.dataTransfer.files[0]);
    };
    form.onsubmit = async event => {
      event.preventDefault();
      if (!selectedFile || uploading) return;
      uploading = true;
      submit.disabled = true;
      fileInput.disabled = true;
      form.querySelector('.rs-clear-file').disabled = true;
      submit.querySelector('span').textContent = 'Uploading…';
      feedback.textContent = 'Uploading your resume. Please keep this page open.';
      const data = new FormData(); data.append('file', selectedFile);
      try {
        await api(`/candidates/${profile.id}/resume`, {method: 'POST', body: data});
        if (location.pathname === '/candidate/resume') await resumePage();
        toast('Resume updated successfully');
      } catch (error) {
        feedback.textContent = error.message; feedback.className = 'rs-error';
        uploading = false; submit.disabled = false; fileInput.disabled = false;
        form.querySelector('.rs-clear-file').disabled = false;
        submit.querySelector('span').textContent = hasResume ? 'Replace resume' : 'Upload resume';
      }
    };
  } catch (error) { toast(error.message, true); }
};
if (session?.user.role === 'candidate') render();
