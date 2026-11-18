"""Capture real FeatureJ dialog/result windows; no synthetic UI images."""
import argparse,os,shutil,subprocess,sys
from pathlib import Path
import yaml

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repo",required=True,type=Path)
parser.add_argument("--fiji",required=True,type=Path)
args=parser.parse_args()
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
base=Path(__file__).resolve().parent
argdir=Path(os.environ["LOCALAPPDATA"])/"Temp/xla_java_build"
argdir.mkdir(parents=True,exist_ok=True)
classes=argdir/"gui_classes"
classes.mkdir(exist_ok=True)
runtime=argdir/"runtime_jars"
runtime.mkdir(exist_ok=True)
jars=[]
for folder in (args.fiji/"jars",args.fiji/"plugins"):
    for p in folder.rglob("*.jar"):
        if p.name.startswith(("ij-","imagescience-","FeatureJ_","Image_5D-")) or "vecmath" in p.name.lower():
            dest=runtime/p.name
            shutil.copy2(p,dest)
            jars.append(dest)
cp=";".join(str(p) for p in [classes,*jars])
def launch(tool,arguments,label):
    file=argdir/(label+".args")
    file.write_text("\n".join('"'+str(a).replace("\\","/")+'"' for a in arguments)+"\n",encoding="utf8")
    r=subprocess.run([shutil.which(tool),"@"+str(file)],capture_output=True,text=True,encoding="utf8",errors="replace")
    print(r.stdout)
    print(r.stderr)
    r.check_returncode()
    return r
launch("javac",["-encoding","UTF-8","-proc:none","-cp",cp,"-d",classes,base/"GuiEvidence.java"],"gui-compile")
cfg=yaml.safe_load((args.repo/"config.yaml").read_text(encoding="utf8"))
scale=next(float(x) for x in cfg["sigmas"] if float(x)==2)
sd,si=cfg["structure_pairs"][0]
captures=base.parent/"figures/gui"
job=argdir/"gui-job.properties"
job.write_text("repo="+args.repo.resolve().as_posix()+"\ncaptures="+captures.as_posix()+
               "\npython="+Path(sys.executable).as_posix()+
               "\nnative_capture="+(base/"capture_native_window.py").as_posix()+
               f"\nsigma={scale:.1f}\nsd={sd:.1f}\nsi={si:.1f}\n",encoding="utf8")
# The installed runtime jars are copied to an ASCII temp path for the Windows launcher.
r=launch("java",["-Djava.awt.headless=false","-cp",cp,"GuiEvidence",job],"gui-run")
(args.repo/"experiments/gui_evidence/gui_session.txt").write_text(r.stdout+r.stderr,encoding="utf8")
