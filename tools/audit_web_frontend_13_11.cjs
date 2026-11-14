// Execute the actual page script with a controlled DOM/fetch stub.
// This tests state transitions, not browser rendering or CSS layout.
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const root = path.resolve(__dirname, '..');
const template = fs.readFileSync(path.join(root, 'src/web/templates/index.html'), 'utf8');
const source = template.match(/<script>([\s\S]*?)<\/script>/)[1];
const nodes = new Map();
const controls = new Map([
  ['param-sigma', { value: '2' }], ['param-plow', { value: '67' }],
  ['param-phigh', { value: '91' }], ['param-nms', { checked: true }],
]);
function node(id) {
  if (id.startsWith('param-')) return controls.get(id) || null;
  if (!nodes.has(id)) nodes.set(id, {
    value: id === 'colormap-select' ? 'inferno' : '', style: {}, innerText: '', innerHTML: '', src: '',
    classList: { add() {}, remove() {}, toggle() {} },
  });
  return nodes.get(id);
}
const requests = [];
const sandbox = { console, setTimeout, window: { addEventListener() {} },
  document: { getElementById: node, querySelectorAll: () => [], querySelector: () => node('query') },
  fetch: (url, options) => new Promise(resolve => requests.push({ url, payload: JSON.parse(options.body), resolve })) };
vm.createContext(sandbox);
vm.runInContext(source, sandbox);
const tick = () => new Promise(resolve => setImmediate(resolve));
function response(id, f1) {
  return { img_original: id, img_python_binary: id+'_BINARY', img_python_response: id+'_RESPONSE',
    img_fiji: id, img_gt_overlay: id, img_gt_raw: id, img_diff: id,
    has_gt: true, image_size: [100,100], timing: {total_ms: 10},
    gt_metrics: {has_gt:true,f1}, fiji_metrics: {pearson:.99,mae:.01,fiji_file:id} };
}
async function main() {
  vm.runInContext("currentImageId='bsds_01';currentAlgo='canny';runAlgorithm()",sandbox);
  vm.runInContext("currentImageId='drive_08';currentAlgo='frangi';runAlgorithm()",sandbox);
  requests[1].resolve({json:async()=>response('NEW_DRIVE_RESULT',.4444)});
  await tick();
  const afterNew = { image:node('img-original').src, label:node('tag-fiji-title').innerText };
  requests[0].resolve({json:async()=>response('OLD_BSDS_RESULT',.1111)});
  await tick();
  const afterOld = { image:node('img-original').src, label:node('tag-fiji-title').innerText,
    f1:node('hud-gt-f1').innerText, selectedImage:vm.runInContext('currentImageId',sandbox),
    selectedAlgorithm:vm.runInContext('currentAlgo',sandbox) };
  let index=requests.length;
  vm.runInContext("currentAlgo='gaussian';runAlgorithm()",sandbox);
  const continuous=response('GAUSSIAN',0);continuous.img_python_binary=null;
  requests[index].resolve({json:async()=>continuous});await tick();
  index=requests.length;
  vm.runInContext("currentAlgo='canny';runAlgorithm()",sandbox);
  requests[index].resolve({json:async()=>response('CANNY_AFTER_GAUSSIAN',.4)});await tick();
  const viewAfterContinuous={view:vm.runInContext('pyView',sandbox),shown:node('img-python').src,
    note:'runAlgorithm changes pyView to response but never synchronizes the binary/response active classes'};
  const requestCount=requests.length;
  vm.runInContext("applyPreset('canny')",sandbox);
  const results = { scope:'Node VM with controlled DOM/fetch; real inline JS; no browser CSS/layout test',
    requests_complete_out_of_order:{ after_new_response:afterNew, after_old_response:afterOld,
      stale_overwrite_confirmed:afterOld.image==='OLD_BSDS_RESULT'&&afterOld.selectedImage==='drive_08' },
    preset_api_requests_for_one_click:requests.length-requestCount,
    binary_view_after_continuous_algorithm:viewAfterContinuous,
    issue:'runAlgorithm has no request sequence, cancellation or response-to-selection check; preset calls twice' };
  const out=path.join(root,'docs/13_11/kiem_tra_web_app');fs.mkdirSync(out,{recursive:true});
  fs.writeFileSync(path.join(out,'FRONTEND_STATE_AUDIT.json'),JSON.stringify(results,null,2));
  console.log(JSON.stringify(results,null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
