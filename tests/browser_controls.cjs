// UI tests with simulated TV API responses. Not a real-TV test.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.SAMY_CHROMIUM_PATH||undefined});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000}}), writes=[], errors=[];
    page.on('pageerror',e=>errors.push(String(e)));
    await page.route('**/api/**',async route=>{
      const req=route.request(), path=new URL(req.url()).pathname;
      let body={ok:true,data:{}};
      if(req.method()==='POST') {
        assert.equal(req.headers()['x-samy-csrf'],'simulated-session-only');
        writes.push({path,data:req.postDataJSON()});
        if(req.postDataJSON().key==='mute') {await route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({ok:false})});return;}
        body={ok:true,result:'SUCCESS'};
      } else if(path==='/api/session') body={ok:true,csrf:'simulated-session-only',offline:false};
      else if(path==='/api/inputs') body={ok:true,data:[{id:'HDMI-2',name:'Google TV (simulated)',writable:true},{id:'HDMI-1',name:'HDMI 1 (read-only)',writable:false}]};
      else if(path==='/api/settings/picture') body={ok:true,data:[{id:'brightness',name:'Brightness',value:50,spec:{kind:'integer',min:0,max:100,step:1}},{id:'contrast',name:'Contrast',value:50,spec:null}]};
      else if(path==='/api/watchfree/status') body={ok:true,data:{matches_legacy_id:true,screen_verified:false,playback_verified:false}};
      else if(path==='/api/status') body={ok:true,data:{model:'D40f-G9',firmware:'SIMULATED'}};
      await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
    });
    await page.goto('http://127.0.0.1:8766/');
    await page.waitForFunction(()=>document.querySelector('#connection').textContent.includes('Local control session'));
    await page.locator('[data-key="volume_up"]').click();
    await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('The API accepted'));
    await page.locator('[data-key="mute"]').click();
    await page.waitForFunction(()=>document.querySelector('#notice').classList.contains('error'));
    await page.locator('#load-inputs').click();
    await page.getByRole('button',{name:'Google TV (simulated)',exact:true}).click();
    assert.equal(await page.getByRole('button',{name:'HDMI 1 (read-only)',exact:true}).isDisabled(),true);
    await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('The API accepted'));
    await page.locator('[data-settings="picture"]').click();
    await page.locator('#setting-picture-0').fill('55');
    await page.getByRole('button',{name:'Apply',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('The API accepted'));
    await page.locator('.app-card.app-netflix .app-launch').click();
    await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('The API accepted'));
    await page.locator('#watchfree-launch').click();
    await page.waitForFunction(()=>document.querySelector('#watchfree-status').textContent.includes('legacy WatchFree ID'));
    assert.match(await page.locator('#watchfree-status').innerText(),/does not confirm/);
    assert.deepEqual(writes,[
      {path:'/api/key',data:{key:'volume_up'}},{path:'/api/key',data:{key:'mute'}},
      {path:'/api/input',data:{input:'HDMI-2'}},{path:'/api/setting',data:{group:'picture',name:'brightness',value:55}},
      {path:'/api/app',data:{app:'netflix'}},{path:'/api/app',data:{app:'watchfree'}}]);
    assert.equal(await page.locator('.setting-row button').count(),1);
    assert.doesNotMatch(await page.locator('body').innerText(),/[\u0600-\u06ff]/);
    assert.deepEqual(errors,[]);
    console.log('PASS: simulated controller UI — volume, failure feedback, discovered input, metadata-gated setting, native app, WatchFree legacy identity without playback claims, CSRF header. No real TV used.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
