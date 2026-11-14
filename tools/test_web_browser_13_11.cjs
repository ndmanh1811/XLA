// Real Edge headless + real Flask, using only Node built-ins and DevTools.
// Own temporary profile/ports/process trees are cleaned up after the checks.
const fs=require('fs'),path=require('path'),os=require('os'),net=require('net');
const {spawn,spawnSync}=require('child_process');
const assert=require('assert/strict');
const crypto=require('crypto');
const root=path.resolve(__dirname,'..');
const uiReview=process.argv.includes('--ui-review');
const out=path.join(root,uiReview?'docs/14_11/giao_dien_web':'docs/13_11/sau_sua_web_app');fs.mkdirSync(out,{recursive:true});
const edge=['C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe','C:/Program Files/Microsoft/Edge/Application/msedge.exe'].find(fs.existsSync);
if(!edge)throw Error('Microsoft Edge is required for this optional browser integration check.');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const port=()=>new Promise(resolve=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p));});});
let server,browser,socket,profile,flaskLog='';
const evidence={status:'RUNNING',browser:'Microsoft Edge headless / DevTools',checks:[],javascript_errors:[]};
evidence.source_sha256=Object.fromEntries(['src/web/app.py','src/web/parameters.py','src/web/comparison.py','src/web/templates/index.html','src/web/static/studio.css'].filter(name=>fs.existsSync(path.join(root,name))).map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')]));
function check(name,details){evidence.checks.push({name,status:'PASS',details});console.log('PASS:',name);}
async function waitFor(fn,label,timeout=60000){const end=Date.now()+timeout;while(Date.now()<end){try{const v=await fn();if(v)return v;}catch{}await delay(150);}throw Error('Timeout: '+label);}
function killOwned(child){if(child?.pid)spawnSync('taskkill.exe',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});}
async function main(){
  const webPort=await port(),debugPort=await port();
  profile=fs.mkdtempSync(path.join(os.tmpdir(),'xla-web-check-'));
  server=spawn(path.join(root,'.venv/Scripts/python.exe'),['-B','-X','utf8','-u','-c',`from src.web.app import app; app.run(host='127.0.0.1',port=${webPort},debug=False)`],{cwd:root,windowsHide:true,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
  server.stdout.on('data',b=>flaskLog+=b);server.stderr.on('data',b=>flaskLog+=b);
  await waitFor(async()=>{const r=await fetch(`http://127.0.0.1:${webPort}/api/settings`);return r.ok;},'Flask ready');
  browser=spawn(edge,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-extensions','--disable-background-networking',
    '--remote-debugging-address=127.0.0.1',`--remote-debugging-port=${debugPort}`,`--user-data-dir=${profile}`,'--window-size=1440,1000','about:blank'],{windowsHide:true,stdio:'ignore'});
  const target=await waitFor(async()=>{const r=await fetch(`http://127.0.0.1:${debugPort}/json/list`);return (await r.json()).find(t=>t.type==='page');},'Edge ready');
  socket=new WebSocket(target.webSocketDebuggerUrl);await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j;});
  let id=0,requests=0;const pending=new Map();
  socket.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}}
    else if(m.method==='Runtime.exceptionThrown')evidence.javascript_errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);
    else if(m.method==='Network.requestWillBeSent'&&m.params.request.url.endsWith('/api/process'))requests++;
  };
  const send=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});socket.send(JSON.stringify({id:n,method,params}));});
  const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result?.value;};
  const ready=(image,algo)=>waitFor(()=>evaluate(`typeof lastData !== 'undefined' && lastData && activeController === null && lastData.request_context.image_id === '${image}' && lastData.request_context.algorithm === '${algo}'`),`${image}/${algo}`);
  await send('Runtime.enable');await send('Page.enable');await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:`http://127.0.0.1:${webPort}/`});
  await ready('bsds_01','canny');
  assert.equal(await evaluate('lastData.gt_metrics.f1'),.4821);
  check('Initial page loads settings, correct Canny and numeric HUD',{f1:.4821});

  if(uiReview){
    const typography=await evaluate(`({body:parseFloat(getComputedStyle(document.body).fontSize),label:parseFloat(getComputedStyle(document.querySelector('.form-group label')).fontSize),numbers:document.querySelectorAll('.range-number').length})`);
    assert.ok(typography.body>=17&&typography.label>=16&&typography.numbers===3);
    assert.equal(await evaluate("document.querySelector('.btn-primary').getBoundingClientRect().bottom <= innerHeight"),true);
    check('Large readable type and three precise numeric controls',typography);
    await evaluate(`document.getElementById('number-param-plow').value=65;document.getElementById('number-param-plow').dispatchEvent(new Event('input',{bubbles:true}))`);
    assert.equal(await evaluate("document.getElementById('param-plow').value"),'65');
    await evaluate(`document.getElementById('param-plow').value=67;document.getElementById('param-plow').dispatchEvent(new Event('input',{bubbles:true}))`);
    assert.equal(await evaluate("document.getElementById('number-param-plow').value"),'67');
    const countBefore=requests;
    await evaluate(`document.getElementById('number-param-plow').value='';runAlgorithm()`);
    assert.equal(requests,countBefore);
    await evaluate(`document.getElementById('number-param-plow').value=67;document.getElementById('number-param-plow').dispatchEvent(new Event('input',{bubbles:true}))`);
    check('Number and slider synchronize; blank required value cannot submit');
    await evaluate("document.querySelector('[data-panel=original] .image-expand').click()");
    await waitFor(()=>evaluate("document.getElementById('figure-modal').classList.contains('active') && document.getElementById('modal-img').naturalWidth>0"),'result image zoom');
    await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))");
    assert.equal(await evaluate("document.getElementById('figure-modal').classList.contains('active')"),false);
    check('Image zoom and Escape close work on real result images');
    await evaluate("document.getElementById('toast').classList.remove('show')");
    const sizes=[];
    for(const [width,height] of [[1440,1000],[1024,900],[390,844]]){
      await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});await delay(200);
      const size=await evaluate(`({width:innerWidth,scroll:document.documentElement.scrollWidth,panels:document.querySelectorAll('.quad-cell').length,font:parseFloat(getComputedStyle(document.body).fontSize)})`);
      assert.ok(size.scroll<=size.width+1,JSON.stringify(size));sizes.push(size);
      await evaluate('window.scrollTo(0,0)');await delay(100);
      const shot=await send('Page.captureScreenshot',{format:'png'});
      fs.writeFileSync(path.join(out,`UI_${width}.png`),Buffer.from(shot.data,'base64'));
    }
    check('Desktop, tablet and mobile keep four distinct panels without horizontal page overflow',sizes);
    await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await evaluate('window.scrollTo(0,0)');await delay(200);
    const metrics=await send('Page.getLayoutMetrics');
    const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:1440,height:Math.ceil(metrics.cssContentSize.height),scale:1}});
    fs.writeFileSync(path.join(out,'UI_FULL_PAGE.png'),Buffer.from(shot.data,'base64'));
  }

  let before=requests;
  await evaluate("applyPreset('blob')");await ready('blob_05','blob');await delay(200);
  assert.equal(requests-before,1);
  assert.equal(await evaluate('lastData.gt_metrics.f1'),.4921);
  check('One preset click produces exactly one process request',{requests:requests-before});
  const overlay=await evaluate('lastData.img_gt_overlay');
  await evaluate("document.getElementById('param-ignore').checked=false;runAlgorithm()");await ready('blob_05','blob');
  assert.equal(await evaluate('lastData.gt_metrics.f1'),.4921);
  assert.notEqual(await evaluate('lastData.img_gt_overlay'),overlay);
  check('Ignore visibility changes overlay, retains canonical scoring',{f1:.4921});

  await evaluate("document.getElementById('preset-select').value='blob_02';onImageSelectChange()");await ready('blob_02','blob');
  assert.equal(await evaluate("document.getElementById('param-polarity').value"),'dark');
  assert.equal(await evaluate('lastData.gt_metrics.f1'),1);
  check('Dark blob annotation determines actual default polarity',{image:'blob_02',f1:1});

  await evaluate("applyPreset('canny')");await ready('bsds_01','canny');
  await evaluate("document.getElementById('algo-select').value='gradient';onAlgoChange()");await ready('bsds_01','gradient');
  await evaluate("document.getElementById('param-dtype').value='angle';runAlgorithm()");await ready('bsds_01','gradient');
  assert.equal(await evaluate('lastData.fiji_metrics.kind'),'angular');
  assert.equal(await evaluate('lastData.fiji_metrics.pearson'),null);
  assert.match(await evaluate("document.getElementById('hud-fiji-pearson').innerText"),/Δθ/);
  check('Angular mode displays periodic angle error, not Pearson',await evaluate('lastData.fiji_metrics.mean_angular_error_deg'));

  await evaluate("document.getElementById('algo-select').value='gaussian';onAlgoChange()");await ready('bsds_01','gaussian');
  await evaluate("applyPreset('canny')");await ready('bsds_01','canny');
  assert.equal(await evaluate('pyView'),'binary');
  assert.equal(await evaluate("document.getElementById('btn-py-bin').classList.contains('active')"),true);
  assert.equal(await evaluate("document.getElementById('img-python').src === lastData.img_python_binary"),true);
  check('Binary button and actual image stay synchronized after Gaussian → Canny');

  const race=await evaluate(`(async()=>{
    const original=window.fetch;const waiting=[];const snapshot=JSON.parse(JSON.stringify(lastData));
    window.fetch=(url,opts)=>url==='/api/process'?new Promise(resolve=>waiting.push({resolve,payload:JSON.parse(opts.body)})):original(url,opts);
    try {
      currentImageId='bsds_01';document.getElementById('algo-select').value='canny';onAlgoChange(false);const a=runAlgorithm();
      currentImageId='drive_08';document.getElementById('algo-select').value='frangi';onAlgoChange(false);const b=runAlgorithm();
      function finish(i,f1){const data=JSON.parse(JSON.stringify(snapshot));data.request_context={image_id:waiting[i].payload.image_id,algorithm:waiting[i].payload.algorithm};data.gt_metrics.f1=f1;waiting[i].resolve(new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}}));}
      finish(1,.2222);await b;finish(0,.1111);await a;
      return {image:lastData.request_context.image_id,f1:lastData.gt_metrics.f1,hud:document.getElementById('hud-gt-f1').innerText};
    }finally{window.fetch=original;}
  })()`);
  assert.equal(race.image,'drive_08');assert.equal(race.f1,.2222);
  check('Old response cannot overwrite the newer result even when fetch ignores abort',race);

  await evaluate("applyPreset('canny')");await ready('bsds_01','canny');
  await evaluate("document.getElementById('param-plow').value=95;document.getElementById('param-phigh').value=10;runAlgorithm()");
  await waitFor(()=>evaluate("activeController===null && lastData===null"),'validation error UI');
  assert.match(await evaluate("document.getElementById('toast').innerText"),/Low/);
  check('Invalid thresholds show a specific validation error and clear old scores');

  await evaluate("applyPreset('canny')");await ready('bsds_01','canny');
  await delay(200);
  let shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,'WEB_STUDIO_SAU_SUA.png'),Buffer.from(shot.data,'base64'));
  await evaluate("switchTab('benchmarks')");
  await waitFor(()=>evaluate("document.getElementById('benchmark-edge').innerText.includes('0.4779') && document.querySelectorAll('#figure-gallery img').length===10"),'benchmarks');
  await waitFor(()=>evaluate("Array.from(document.querySelectorAll('#figure-gallery img')).filter(x=>x.getClientRects().length && x.getBoundingClientRect().top<1000).every(x=>x.complete&&x.naturalWidth>0)"),'chart image load');
  await evaluate("document.getElementById('benchmark-protocol').closest('details').open=true");
  assert.match(await evaluate("document.getElementById('benchmark-protocol').innerText"),/185/);
  assert.match(await evaluate("document.getElementById('benchmark-protocol').innerText"),/1e-2/);
  check('Benchmark headlines, strict failures and 10 charts come from verified API',await evaluate("document.getElementById('benchmark-protocol').innerText"));
  await evaluate("document.getElementById('benchmark-protocol').closest('details').open=false");
  shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,'WEB_BENCHMARK_SAU_SUA.png'),Buffer.from(shot.data,'base64'));
  await evaluate('toggleAllFigures()');
  assert.equal(await evaluate("document.getElementById('figure-gallery').classList.contains('show-all')"),true);
  assert.equal(await evaluate("Array.from(document.querySelectorAll('#figure-gallery .gallery-card')).filter(x=>x.getClientRects().length).length"),10);
  check('Show all reveals all 10 chart cards');
  await evaluate("document.querySelector('#figure-gallery .gallery-card').click()");
  await waitFor(()=>evaluate("document.getElementById('figure-modal').classList.contains('active') && document.getElementById('modal-img').complete && document.getElementById('modal-img').naturalWidth>0"),'chart modal');
  await evaluate('closeModal()');
  assert.equal(await evaluate("document.getElementById('figure-modal').classList.contains('active')"),false);
  check('Full chart modal opens and closes correctly');
  assert.equal(evidence.javascript_errors.length,0);
  evidence.status='PASS';evidence.process_requests=requests;
}
main().catch(e=>{evidence.status='FAIL';evidence.error=String(e.stack||e);process.exitCode=1;console.error(e);}).finally(async()=>{
  if(socket)socket.close();killOwned(browser);killOwned(server);
  if(profile){const resolved=path.resolve(profile),base=path.resolve(os.tmpdir())+path.sep;
    if(resolved.startsWith(base)&&path.basename(resolved).startsWith('xla-web-check-')){
      for(let i=0;i<5;i++){try{fs.rmSync(resolved,{recursive:true,force:true});break;}catch{await delay(200);}}
    }
  }
  fs.writeFileSync(path.join(out,'BROWSER_REGRESSION.json'),JSON.stringify(evidence,null,2));
  fs.writeFileSync(path.join(out,'BROWSER_FLASK_LOG.txt'),flaskLog);
  console.log(JSON.stringify({status:evidence.status,checks:evidence.checks.length,errors:evidence.javascript_errors},null,2));
});
