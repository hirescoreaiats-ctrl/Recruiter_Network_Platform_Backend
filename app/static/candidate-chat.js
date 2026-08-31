// Conversation state lives only in this tab and is isolated by signed-in user.
const candidateConversations = new Map();

function initializeCandidateChat(panel, status) {
  panel.classList.add('conversation-panel');
  panel.innerHTML = `
    <header><div><span class="ai-mark" aria-hidden="true">✦</span><div><b>Career assistant</b><small>Your career conversation</small></div></div></header>
    <div class="agent-thread" role="log" aria-label="Career conversation" aria-live="polite" aria-relevant="additions text"></div>
    <form class="chat-composer" id="candidate-agent-form">
      <label class="chat-input-label" for="career-message">Message your career assistant</label>
      <div class="chat-input-row"><textarea id="career-message" rows="2" maxlength="500" placeholder="Type your message…"></textarea><button type="submit" aria-label="Send message" disabled><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 7-7 7 7M12 5v14"/></svg></button></div>
      <small>Local preview · Replies use workspace data</small>
    </form>`;
  const thread = panel.querySelector('.agent-thread');
  const form = panel.querySelector('form');
  const input = panel.querySelector('textarea');
  const send = panel.querySelector('button');
  const userKey = session.user.id || session.user.email;
  let messages = candidateConversations.get(userKey);
  if (!messages) {
    const name = status.candidate.name.split(' ')[0];
    messages = [{role: 'assistant', text: `Hi ${name}! What would you like help with today? Tell me about the role you’re looking for, or ask me about your profile.`}];
    candidateConversations.set(userKey, messages);
  }
  const append = (role, text, pending = false) => {
    const bubble = document.createElement('div');
    bubble.className = `agent-bubble ${role}${pending ? ' agent-thinking' : ''}`;
    bubble.setAttribute('aria-label', role === 'user' ? 'You' : 'Career assistant');
    const copy = document.createElement('p');
    copy.textContent = text;
    bubble.append(copy);
    thread.append(bubble);
    thread.scrollTop = thread.scrollHeight;
    return copy;
  };
  messages.forEach(message => append(message.role, message.text));
  let busy = false;
  input.oninput = () => { send.disabled = busy || !input.value.trim(); };
  input.onkeydown = event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      if (!send.disabled) form.requestSubmit();
    }
  };
  form.onsubmit = async event => {
    event.preventDefault();
    const prompt = input.value.trim();
    if (!prompt || busy) return;
    busy = true;
    send.disabled = true;
    messages.push({role: 'user', text: prompt});
    append('user', prompt);
    input.value = '';
    const reply = append('assistant', 'Thinking…', true);
    try {
      const q = prompt.toLowerCase();
      let answer;
      if (/^(hi|hello|hey|hii|namaste|bhai)[.!\s]*$/i.test(prompt)) {
        answer = 'Hi! What kind of role are you looking for? You can tell me a job title or ask what’s missing from your profile.';
      } else if (/^(thanks|thank you|thankyou|shukriya)[.!\s]*$/i.test(prompt)) {
        answer = 'You’re welcome! What else would you like to check?';
      } else if (/\b(email|mail|alerts?|notifications?)\b/.test(q)) {
        answer = 'Email delivery isn’t connected in this local preview. Match notifications can be previewed here, but no real emails are being sent.';
      } else if (/\b(profile|resume|cv|availability|ready|missing|next step)\b/.test(q)) {
        const current = await api('/candidate/matching-status');
        if (/\b(availability)\b/.test(q)) {
          const labels = {actively_looking: 'actively looking', open_to_right_opportunity: 'open to the right opportunity', not_looking: 'not looking', joined_elsewhere: 'joined another role'};
          answer = `Your availability is ${labels[current.availability?.status] || 'not set'}. You can update it from Availability in the sidebar.`;
        } else if (/\b(resume|cv)\b/.test(q)) {
          answer = current.profile_checks.resume
            ? 'Your resume is uploaded. You can review or replace it from My Resume. Matching currently uses your structured profile details.'
            : 'You haven’t uploaded a resume yet. Open My Resume and add a PDF, DOC or DOCX file.';
        } else {
          const nextSteps = [];
          if (!current.profile_checks.profile) nextSteps.push('Open My Profile and complete the required career details.');
          if (!current.profile_checks.availability) nextSteps.push('Review Availability and confirm whether you’re open to opportunities.');
          if (!current.profile_checks.resume) nextSteps.push('Upload your resume from My Resume.');
          answer = nextSteps.length
            ? `Here’s what’s left before your profile is ready for matching:\n\n${nextSteps.join('\n\n')}\n\nThe other setup steps are complete.`
            : 'Your profile, resume and availability are all set. Tell me what kind of job you’d like me to check for you.';
          if (nextSteps.length === 3) answer = `Let’s get your profile ready:\n\n${nextSteps.join('\n\n')}`;
        }
      } else if (/\b(find|search|jobs?|roles?|match(?:es)?|dhundo)\b/.test(q)) {
        reply.textContent = 'Checking recruiter requirements for you…';
        const result = await api('/candidate/agent/search', {method: 'POST', body: JSON.stringify({query: prompt})});
        answer = result.message;
        if (result.matches.length) {
          answer += '\n\n' + result.matches.slice(0, 3).map(match => `${match.title} at ${match.company}\n${match.city} · ${Math.round(match.match_score)}% structured match`).join('\n\n');
          answer += '\n\nNo application has been sent and your profile has not been shared.';
        }
      } else {
        answer = 'I can check your profile, resume, availability, email status or matching roles using this workspace. What would you like to look at?';
      }
      reply.textContent = answer;
      messages.push({role: 'assistant', text: answer});
    } catch (error) {
      reply.textContent = `I couldn’t complete that request. ${error.message} Please try again.`;
      messages.push({role: 'assistant', text: reply.textContent});
    } finally {
      reply.parentElement.classList.remove('agent-thinking');
      busy = false;
      send.disabled = !input.value.trim();
      thread.scrollTop = thread.scrollHeight;
    }
  };
}
