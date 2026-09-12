const { chromium } = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({channel:'msedge', headless:true});
  const page = await browser.newPage();
  await page.route('http://profile.test/**', route => route.fulfill({contentType:'text/html',body:'<main id="app"></main>'}));
  await page.goto('http://profile.test/candidate/profile/edit');
  const source = fs.readFileSync('app/static/app.js','utf8');
  await page.evaluate(() => {
    window.$ = s => document.querySelector(s);
    window.session = {user:{role:'candidate'}};
    window.countryConfig = {IN:{name:'India'}};
    window.profilePage = async () => {};
    window.profileCountryFields = () => '';
    window.layout = html => document.querySelector('#app').innerHTML = html;
    window.candidateEscape = value => String(value ?? '');
    window.render = () => {};
    window.toast = message => window.lastToast = message;
    window.route = path => window.lastRoute = path;
    window.wireDownloads = () => {};
    window.fixture = {id:1,full_name:'Test User',email:'test@example.com',phone:'9999999999',country:'IN',city:'Delhi',current_title:'Developer',total_experience:2,current_employer:'Example',linkedin_url:'',skills:['Python','SQL','Git'],created_at:'2026-09-12',country_specific_data:{onboarding_step:'complete',career_stage:'experienced',highest_qualification:'Graduation',preferred_locations:['Delhi','Pune'],projects:[{title:'Original', custom:'preserve'}],profile_summary:'Original summary'}};
    window.api = async (url, options) => { if(options) { window.savedBody=JSON.parse(options.body); return {}; } return structuredClone(window.fixture); };
  });
  await page.addScriptTag({content:source.slice(source.indexOf('const readOnlyProfilePage='),source.indexOf('function candidateAgentReply'))});
  await page.addScriptTag({content:fs.readFileSync('app/static/career-profile.js','utf8')});
  for (const section of ['identity','headline','skills','employment','education','it-skills','projects','summary','accomplishments','career','personal','diversity']) {
    await page.evaluate(async section => { history.replaceState({},'',`/candidate/profile/edit?section=${section}`); await profilePage(); }, section);
    assert.equal(await page.locator('[data-career-save]').isVisible(),true,section + ': ' + await page.evaluate(()=>window.lastToast));
    assert.equal(await page.locator('[data-career-next]').isVisible(),false,section);
    if(section === 'summary') {
      await page.locator('[name=extra_profile_summary]').fill('Changed summary');
      await page.locator('[data-career-save]').click();
      const result=await page.evaluate(()=>({body:savedBody,route:lastRoute}));
      assert.equal(result.route,'/candidate/profile');
      assert.equal(result.body.country_specific_data.profile_summary,'Changed summary');
      assert.deepEqual(result.body.country_specific_data.projects,[{title:'Original',custom:'preserve'}]);
      assert.deepEqual(result.body.country_specific_data.preferred_locations,['Delhi','Pune']);
      assert.equal(result.body.total_experience,2);
    }
  }
  await page.evaluate(()=>renderCandidateProfileOverview(fixture));
  assert.equal(await page.locator('.candidate-profile-promo').count(),0);
  await page.locator('#profile-projects [data-profile-edit]').click();
  assert.equal(await page.evaluate(()=>lastRoute),'/candidate/profile/edit?section=projects');
  await browser.close();
  console.log('Profile sections: 12 direct editors, isolated save, return navigation and promo removal passed.');
})().catch(error => { console.error(error); process.exit(1); });



