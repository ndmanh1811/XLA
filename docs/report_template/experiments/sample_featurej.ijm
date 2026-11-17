// Sample run only. Output is separate from the official repo outputs.
requires("1.54");
projectDir = getArgument();
if (projectDir == "")
    projectDir = getDirectory("Choose the XLA repo root containing config.yaml");
if (!endsWith(projectDir, File.separator)) projectDir = projectDir + File.separator;
configPath = projectDir + "config.yaml";
if (!File.exists(configPath)) exit("Missing config.yaml");
configText = File.openAsString(configPath);
if (indexOf(configText, ": null") >= 0) exit("config.yaml contains null");
rawDir = projectDir + "data" + File.separator + "raw" + File.separator;
expDir = projectDir + "experiments" + File.separator;
if (!File.exists(expDir)) File.makeDirectory(expDir);
sampleDir = expDir + "sample_gui_local" + File.separator;
if (!File.exists(sampleDir)) File.makeDirectory(sampleDir);
outDir = sampleDir + "fiji" + File.separator;
if (!File.exists(outDir)) File.makeDirectory(outDir);
logPath = sampleDir + "fiji_sample_log.csv";
if (!File.exists(logPath))
    File.saveString("image,operator,sigma,runtime_ms,state\n", logPath);
names = newArray("bsds_01", "drive_01", "blob_01");
configLines = split(configText, "\n");
sigmaTextList = "";
for (lineIndex=0; lineIndex<configLines.length; lineIndex++) {
    configLine = String.trim(configLines[lineIndex]);
    if (startsWith(configLine, "sigmas:")) {
        sigmaTextList = substring(configLine,indexOf(configLine,"[")+1,indexOf(configLine,"]"));
    }
}
if (sigmaTextList == "") exit("Missing sigmas list in config.yaml");
sigmas = split(sigmaTextList,",");
codes = newArray("gauss", "lx", "ly", "lxx", "lxy", "lyy");
xo = newArray(0, 1, 0, 2, 1, 0);
yo = newArray(0, 0, 1, 0, 1, 2);
for (i=0; i<names.length; i++) {
    path = rawDir + names[i] + ".png";
    if (!File.exists(path)) exit("Missing input: " + path);
    open(path);
    run("Set Scale...", "distance=0 known=0 pixel=1 unit=pixel");
    run("32-bit");
    sourceTitle = getTitle();
    for (j=0; j<sigmas.length; j++) {
        sigmaText = d2s(parseFloat(String.trim(sigmas[j])),1);
        for (k=0; k<codes.length; k++) {
            target = outDir + "fiji_" + names[i] + "_" + codes[k] +
                "_s" + sigmaText + ".tif";
            if (File.exists(target)) {
                File.append(names[i]+","+codes[k]+","+sigmaText+",,SKIPPED_EXISTS\n",logPath);
            } else {
                selectWindow(sourceTitle);
                startMs = getTime();
                run("FeatureJ Derivatives", "x-order="+xo[k]+
                    " y-order="+yo[k]+" z-order=0 smoothing="+sigmaText);
                elapsedMs = getTime()-startMs;
                saveAs("tiff",target);
                close();
                File.append(names[i]+","+codes[k]+","+sigmaText+","+
                    elapsedMs+",COMPUTED\n",logPath);
            }
        }
    }
    selectWindow(sourceTitle);
    close();
}
showMessage("Sample export complete",
    "Expected scope: "+(names.length*sigmas.length*codes.length)+" maps.\nOutput: "+outDir+
    "\nRead the log to distinguish computed and skipped files.");
