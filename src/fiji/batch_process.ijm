/*
 * Batch FeatureJ workflow for the Edge/Ridge assignment.
 *
 * Inputs : data/raw/*.png
 * Config : config.yaml (sigmas and tier1_images)
 * Outputs: outputs/fiji/*.tif (32-bit float, uncompressed TIFF)
 * Runtime: outputs/metrics/fiji_runtime.csv
 *
 * Processing scope for this assignment:
 *   - Every Tier-1 image: FeatureJ Edges and FeatureJ Hessian.
 *   - Remaining BSDS images: FeatureJ Edges.
 *   - Remaining DRIVE images: FeatureJ Hessian (inputs for Ridge detection).
 */

requires("1.54");

projectDir = getDirectory("Choose the XLA project root");
configPath = projectDir + "config.yaml";
rawDir = projectDir + "data" + File.separator + "raw" + File.separator;
outputsDir = projectDir + "outputs" + File.separator;
fijiDir = outputsDir + "fiji" + File.separator;
metricsDir = outputsDir + "metrics" + File.separator;
runtimePath = metricsDir + "fiji_runtime.csv";

if (!File.exists(configPath))
    exit("Missing config file: " + configPath);
if (!File.isDirectory(rawDir))
    exit("Missing input directory: " + rawDir);

configText = File.openAsString(configPath);
if (indexOf(configText, "<Error:") == 0)
    exit("Cannot read config file: " + configPath);
if (containsNullValue(configText))
    exit("config.yaml still contains a null value. Fill it before running Fiji.");

sigmaText = readInlineList(configText, "sigmas:");
if (sigmaText == "")
    exit("Cannot read 'sigmas' from config.yaml");
sigmas = split(sigmaText, ",");
for (i = 0; i < sigmas.length; i++)
    sigmas[i] = String.trim(sigmas[i]);

tier1Set = readBlockListAsSet(configText, "tier1_images:");
if (tier1Set == "|")
    exit("Cannot read 'tier1_images' from config.yaml");

eigenOrder = readScalar(configText, "eigen_order:");
if (eigenOrder != "algebraic" && eigenOrder != "absolute")
    exit("Unsupported or missing eigen_order in config.yaml: " + eigenOrder);

if (!File.isDirectory(outputsDir)) File.makeDirectory(outputsDir);
if (!File.isDirectory(fijiDir)) File.makeDirectory(fijiDir);
if (!File.isDirectory(metricsDir)) File.makeDirectory(metricsDir);

// Start a clean runtime table for this batch invocation.
File.saveString("source,image,command,sigma,runtime_ms,output_files\n", runtimePath);

files = getFileList(rawDir);
processed = 0;

for (i = 0; i < files.length; i++) {
    fileName = files[i];
    lowerName = toLowerCase(fileName);
    if (!endsWith(lowerName, ".png"))
        continue;

    imageName = stripExtension(fileName);
    isTier1 = indexOf(tier1Set, "|" + imageName + "|") >= 0;
    doEdge = isTier1 || startsWith(imageName, "bsds_");
    doHessian = isTier1 || startsWith(imageName, "drive_");

    if (!doEdge && !doHessian)
        continue;

    open(rawDir + fileName);
    // Required by INSTRUCTIONS.md: this must be immediately after open().
    run("Set Scale...", "distance=0 known=0 pixel=1 unit=pixel");
    run("32-bit");
    sourceTitle = getTitle();

    for (s = 0; s < sigmas.length; s++) {
        sigma = sigmas[s];

        if (doEdge)
            runEdge(sourceTitle, imageName, sigma, fijiDir, runtimePath);

        if (doHessian)
            runHessian(sourceTitle, imageName, sigma, eigenOrder,
                fijiDir, runtimePath);
    }

    selectWindow(sourceTitle);
    close();
    processed++;
}

showMessage("FeatureJ batch completed",
    "Processed " + processed + " input images.\n" +
    "TIFF outputs: " + fijiDir + "\n" +
    "Runtime CSV: " + runtimePath);


function runEdge(sourceTitle, imageName, sigma, fijiDir, runtimePath) {
    selectWindow(sourceTitle);
    startMs = getTime();
    run("FeatureJ Edges",
        "compute smoothing=" + sigma + " suppress lower=[] higher=[]");
    runtimeMs = getTime() - startMs;

    resultTitle = sourceTitle + " edges";
    outputName = "fiji_" + imageName + "_edge_s" + sigma + ".tif";
    outputPath = fijiDir + outputName;

    selectWindow(resultTitle);
    saveAs("tiff", outputPath);
    close();

    File.append("fiji," + imageName + ",edge," + sigma + "," +
        runtimeMs + "," + outputName + "\n", runtimePath);
}


function runHessian(sourceTitle, imageName, sigma, eigenOrder,
        fijiDir, runtimePath) {
    selectWindow(sourceTitle);
    startMs = getTime();
    hessianOptions = "largest smallest ";
    if (eigenOrder == "absolute")
        hessianOptions = hessianOptions + "absolute ";
    run("FeatureJ Hessian", hessianOptions + "smoothing=" + sigma);
    runtimeMs = getTime() - startMs;

    largestTitle = sourceTitle + " largest Hessian eigenvalues";
    smallestTitle = sourceTitle + " smallest Hessian eigenvalues";
    l1Name = "fiji_" + imageName + "_hess-l1_s" + sigma + ".tif";
    l2Name = "fiji_" + imageName + "_hess-l2_s" + sigma + ".tif";

    selectWindow(largestTitle);
    saveAs("tiff", fijiDir + l1Name);
    close();

    selectWindow(smallestTitle);
    saveAs("tiff", fijiDir + l2Name);
    close();

    File.append("fiji," + imageName + ",hessian," + sigma + "," +
        runtimeMs + "," + l1Name + ";" + l2Name + "\n", runtimePath);
}


function readInlineList(text, key) {
    lines = split(text, "\n");
    for (j = 0; j < lines.length; j++) {
        line = String.trim(replace(lines[j], "\r", ""));
        if (startsWith(line, key)) {
            left = indexOf(line, "[");
            right = lastIndexOf(line, "]");
            if (left < 0 || right <= left)
                return "";
            return substring(line, left + 1, right);
        }
    }
    return "";
}


function readScalar(text, key) {
    lines = split(text, "\n");
    for (j = 0; j < lines.length; j++) {
        line = String.trim(replace(lines[j], "\r", ""));
        if (startsWith(line, key)) {
            value = String.trim(substring(line, lengthOf(key)));
            hash = indexOf(value, "#");
            if (hash >= 0)
                value = String.trim(substring(value, 0, hash));
            return value;
        }
    }
    return "";
}


function readBlockListAsSet(text, key) {
    lines = split(text, "\n");
    inBlock = false;
    result = "|";

    for (j = 0; j < lines.length; j++) {
        line = String.trim(replace(lines[j], "\r", ""));

        if (!inBlock) {
            if (startsWith(line, key))
                inBlock = true;
            continue;
        }

        if (line == "" || startsWith(line, "#"))
            continue;
        if (!startsWith(line, "-"))
            break;

        item = String.trim(substring(line, 1));
        hash = indexOf(item, "#");
        if (hash >= 0)
            item = String.trim(substring(item, 0, hash));
        if (item != "")
            result = result + item + "|";
    }

    return result;
}


function containsNullValue(text) {
    lines = split(text, "\n");
    for (j = 0; j < lines.length; j++) {
        line = replace(lines[j], "\r", "");
        hash = indexOf(line, "#");
        if (hash >= 0)
            line = substring(line, 0, hash);
        line = String.trim(line);
        if (endsWith(line, ": null") || line == "null" || startsWith(line, "- null"))
            return true;
    }
    return false;
}


function stripExtension(fileName) {
    dot = lastIndexOf(fileName, ".");
    if (dot < 0)
        return fileName;
    return substring(fileName, 0, dot);
}
