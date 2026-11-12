"""Compare measured calibration TIFFs with the currently available timing JAR."""
from pathlib import Path
import csv
import json
import os
import shutil
import subprocess
import tempfile
import numpy as np
import tifffile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/12_11/kiem_tra_toan_bo_nhom'
CAL=ROOT/'docs/fiji/calibration'


def main():
    env=json.loads((ROOT/'outputs/analysis/duc_task5_10_11/runtime/runtime_environment.json').read_text(encoding='utf-8'))
    jars=list(env['jars'])
    if not all(Path(p).is_file() for p in jars): raise FileNotFoundError('Timing library unavailable')
    javac=Path(shutil.which('javac'))
    java=javac.with_name('java.exe' if os.name=='nt' else 'java')
    cp=os.pathsep.join(jars)
    with tempfile.TemporaryDirectory(prefix='calibration_crosscheck_',dir=OUT) as tmp:
        folder=Path(tmp).resolve()
        assert folder.is_relative_to(OUT.resolve())
        with (CAL/'measurement_results.csv').open(encoding='utf-8-sig',newline='') as f: measured=list(csv.DictReader(f))
        for p in (ROOT/'data/calib').glob('*.tif'):
            np.asarray(tifffile.imread(p),dtype='<f4').tofile(folder/(p.name+'.bin'))
        with (folder/'cases.csv').open('w',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(['output','input','command','sigma','si','width','height'])
            for r in measured:
                a=np.asarray(tifffile.imread(CAL/'outputs'/r['output_name']),dtype='<f4')
                a.tofile(folder/(r['output_name']+'.bin'))
                writer.writerow([r['output_name'],r['image'],r['command'],r['sigma'],r['sigma_i'],a.shape[1],a.shape[0]])
        p=subprocess.run([str(javac),'-encoding','UTF-8','-cp',cp,'-d',str(folder),str(OUT/'CalibrationCrossCheck.java')],capture_output=True,text=True)
        if p.returncode: raise RuntimeError(p.stderr)
        p=subprocess.run([str(java),'-Djava.awt.headless=true','-cp',str(folder)+os.pathsep+cp,
                          'CalibrationCrossCheck',str(folder),str(OUT/'TIMING_LIBRARY_CALIBRATION.csv')],capture_output=True,text=True,timeout=90)
        (OUT/'TIMING_LIBRARY_CALIBRATION_LOG.txt').write_text(p.stdout+p.stderr,encoding='utf-8')
        if p.returncode: raise RuntimeError(p.stderr)
    with (OUT/'TIMING_LIBRARY_CALIBRATION.csv').open(encoding='utf-8') as f: rows=list(csv.DictReader(f))
    summary=dict(cases=len(rows),identical_arrays=sum(float(r['max_abs_error'])==0 for r in rows),
                 max_abs_error=max(float(r['max_abs_error']) for r in rows),
                 max_relative_error=max(float(r['relative_max_error']) for r in rows))
    (OUT/'TIMING_LIBRARY_CALIBRATION.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__': main()
