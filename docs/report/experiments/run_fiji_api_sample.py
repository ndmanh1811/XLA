"""Run the actual Fiji ImageScience API using an installed Java JDK."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import os

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",required=True,type=Path)
    parser.add_argument("--fiji",required=True,type=Path)
    parser.add_argument("--arg-dir",type=Path,
                        default=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/"AppData/Local")))/"Temp/xla_java_build")
    args=parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8",errors="replace")
    javac=shutil.which("javac")
    java=shutil.which("java")
    if not javac or not java: parser.error("A Java JDK with java and javac is required.")
    base=Path(__file__).resolve().parent
    arg_dir=args.arg_dir
    arg_dir.mkdir(parents=True,exist_ok=True)
    classes=arg_dir/"sample_classes"
    classes.mkdir(exist_ok=True)
    source_jars=[p for directory in (args.fiji/"jars",args.fiji/"plugins") for p in directory.rglob("*.jar")
                 if p.name.startswith(("ij-","imagescience-","FeatureJ_","Image_5D-"))
                 or "vecmath" in p.name.lower()]
    runtime=arg_dir/"runtime_jars"
    runtime.mkdir(exist_ok=True)
    jars=[]
    for p in source_jars:
        dest=runtime/p.name
        shutil.copy2(p,dest)
        jars.append(str(dest))
    if not any("imagescience" in p.lower() for p in jars):
        parser.error("ImageScience is not installed in this Fiji.")
    cp=";".join([str(classes),*jars])
    # ASCII argument-file location avoids Windows native command-line encoding loss.
    def launch(executable,arguments,name):
        file=arg_dir/(name+".args")
        file.write_text("\n".join('"'+str(x).replace("\\","/")+'"' for x in arguments)+"\n",encoding="utf-8")
        r=subprocess.run([executable,"@"+str(file)],capture_output=True,text=True,encoding="utf-8",errors="replace")
        if r.stdout: print(r.stdout)
        if r.stderr: print(r.stderr)
        r.check_returncode()
        return r
    launch(javac,["-encoding","UTF-8","-proc:none","-cp",cp,"-d",classes,base/"SampleFeatureJ.java"],"sample-compile")
    properties=arg_dir/"sample-job.properties"
    properties.write_text("repo="+args.repo.resolve().as_posix()+"\n",encoding="utf-8")
    result=launch(java,["-Djava.awt.headless=true","-cp",cp,"SampleFeatureJ",properties],"sample-run")
    out=args.repo/"experiments/sample_local"
    (out/"fiji_api_run.txt").write_text(result.stdout+"\n"+result.stderr,encoding="utf-8")
    (out/"java_runtime.txt").write_text(subprocess.run([java,"-version"],capture_output=True,text=True).stderr,encoding="utf-8")

if __name__=="__main__":
    main()
