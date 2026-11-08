/*
 * Complete FeatureJ batch workflow for the full 25-image dataset.
 *
 * Input  : data/raw/*.png
 * Config : config.yaml
 * Output : outputs/fiji/*.tif (32-bit float TIFF)
 * Runtime: append to outputs/metrics/fiji_runtime.csv
 *
 * Scope required by INSTRUCTIONS.md:
 *   Tier 1 (5 images, sigmas):
 *     gauss, lx, ly, lxx, lxy, lyy, grad, lap,
 *     hess-l1, hess-l2, st-l1, st-l2.
 *   Tier 2:
 *     BSDS : lx, ly, edge.
 *     DRIVE: hess-l1, hess-l2.
 *     Blob : lap at the dense blob sigma grid.
 *
 * Existing outputs are skipped, so this macro can safely resume an
 * interrupted or partially completed run.
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
blobSigmaText = readInlineList(configText, "sigmas_blob:");
pairText = readPairBlock(configText, "structure_pairs:");
tier1Set = readBlockListAsSet(configText, "tier1_images:");
eigenOrder = readScalar(configText, "eigen_order:");

if (sigmaText == "") exit("Cannot read 'sigmas' from config.yaml");
if (blobSigmaText == "") exit("Cannot read 'sigmas_blob' from config.yaml");
if (pairText == "") exit("Cannot read 'structure_pairs' from config.yaml");
if (tier1Set == "|") exit("Cannot read 'tier1_images' from config.yaml");
if (eigenOrder != "algebraic" && eigenOrder != "absolute")
    exit("Unsupported or missing eigen_order: " + eigenOrder);

sigmas = split(sigmaText, ",");
for (i = 0; i < sigmas.length; i++)
    sigmas[i] = String.trim(sigmas[i]);

blobSigmas = split(blobSigmaText, ",");
for (i = 0; i < blobSigmas.length; i++)
    blobSigmas[i] = String.trim(blobSigmas[i]);

structurePairs = split(pairText, "|");

if (!File.isDirectory(outputsDir)) File.makeDirectory(outputsDir);
if (!File.isDirectory(fijiDir)) File.makeDirectory(fijiDir);
if (!File.isDirectory(metricsDir)) File.makeDirectory(metricsDir);

if (!File.exists(runtimePath))
    File.saveString(
        "source,image,command,sigma,runtime_ms,output_files\n",
        runtimePath
    );

files = getFileList(rawDir);
processed = 0;

for (i = 0; i < files.length; i++) {
    fileName = files[i];
    if (!endsWith(toLowerCase(fileName), ".png"))
        continue;

    imageName = stripExtension(fileName);
    isTier1 = indexOf(tier1Set, "|" + imageName + "|") >= 0;
    isBsds = startsWith(imageName, "bsds_");
    isDrive = startsWith(imageName, "drive_");
    isBlob = startsWith(imageName, "blob_");

    if (!isBsds && !isDrive && !isBlob)
        continue;

    open(rawDir + fileName);
    // Required: Set Scale must be immediately after every open().
    run("Set Scale...", "distance=0 known=0 pixel=1 unit=pixel");
    run("32-bit");
    sourceTitle = getTitle();

    // Standard sigma grid.
    for (s = 0; s < sigmas.length; s++) {
        sigma = sigmas[s];

        if (isTier1) {
            runDerivative(sourceTitle, imageName, sigma, 0, 0,
                "gauss", fijiDir, runtimePath);
            runDerivative(sourceTitle, imageName, sigma, 1, 0,
                "lx", fijiDir, runtimePath);
            runDerivative(sourceTitle, imageName, sigma, 0, 1,
                "ly", fijiDir, runtimePath);
            runDerivative(sourceTitle, imageName, sigma, 2, 0,
                "lxx", fijiDir, runtimePath);
            runDerivative(sourceTitle, imageName, sigma, 1, 1,
                "lxy", fijiDir, runtimePath);
            runDerivative(sourceTitle, imageName, sigma, 0, 2,
                "lyy", fijiDir, runtimePath);
            runGradient(sourceTitle, imageName, sigma,
                fijiDir, runtimePath);
            runLaplacian(sourceTitle, imageName, sigma,
                fijiDir, runtimePath);
            runHessian(sourceTitle, imageName, sigma, eigenOrder,
                fijiDir, runtimePath);
        } else if (isBsds) {
            runDerivative(sourceTitle, imageName, sigma, 1, 0,
                "lx", fijiDir, runtimePath);
            runDerivative(sourceTitle, imageName, sigma, 0, 1,
                "ly", fijiDir, runtimePath);
        } else if (isDrive) {
            runHessian(sourceTitle, imageName, sigma, eigenOrder,
                fijiDir, runtimePath);
        }

        // FeatureJ Edges is the separate NMS reference for all BSDS images.
        if (isBsds)
            runEdge(sourceTitle, imageName, sigma, fijiDir, runtimePath);
    }

    // Dense scale grid for every blob image. Standard-scale Laplacian files
    // already created above are skipped automatically.
    if (isBlob) {
        for (s = 0; s < blobSigmas.length; s++)
            runLaplacian(sourceTitle, imageName, blobSigmas[s],
                fijiDir, runtimePath);
    }

    if (isTier1) {
        for (p = 0; p < structurePairs.length; p++) {
            pair = split(structurePairs[p], ",");
            if (pair.length != 2)
                exit("Invalid structure pair: " + structurePairs[p]);
            sd = String.trim(pair[0]);
            si = String.trim(pair[1]);
            runStructure(sourceTitle, imageName, sd, si,
                fijiDir, runtimePath);
        }
    }

    selectWindow(sourceTitle);
    close();
    processed++;
}

showMessage("FeatureJ full multi-sigma batch completed",
    "Processed " + processed + " input images.\n" +
    "Existing TIFF files were skipped.\n" +
    "TIFF outputs: " + fijiDir + "\n" +
    "Runtime CSV: " + runtimePath);


function runDerivative(sourceTitle, imageName, sigma, xOrder, yOrder,
        opCode, fijiDir, runtimePath) {
    outputName = "fiji_" + imageName + "_" + opCode +
        "_s" + sigma + ".tif";
    outputPath = fijiDir + outputName;
    if (File.exists(outputPath))
        return 0;

    selectWindow(sourceTitle);
    startMs = getTime();
    run("FeatureJ Derivatives",
        "x-order=" + xOrder + " y-order=" + yOrder +
        " z-order=0 smoothing=" + sigma);
    runtimeMs = getTime() - startMs;

    // The derivative result is the active image after the plugin returns.
    saveAs("tiff", outputPath);
    close();

    File.append("fiji," + imageName + "," + opCode + "," + sigma +
        "," + runtimeMs + "," + outputName + "\n", runtimePath);
}


function runGradient(sourceTitle, imageName, sigma, fijiDir, runtimePath) {
    outputName = "fiji_" + imageName + "_grad_s" + sigma + ".tif";
    outputPath = fijiDir + outputName;
    if (File.exists(outputPath))
        return 0;

    selectWindow(sourceTitle);
    startMs = getTime();
    // Raw gradient magnitude: NMS is deliberately not enabled.
    run("FeatureJ Edges",
        "compute smoothing=" + sigma + " lower=[] higher=[]");
    runtimeMs = getTime() - startMs;

    selectWindow(sourceTitle + " edges");
    saveAs("tiff", outputPath);
    close();

    File.append("fiji," + imageName + ",gradient," + sigma + "," +
        runtimeMs + "," + outputName + "\n", runtimePath);
}


function runEdge(sourceTitle, imageName, sigma, fijiDir, runtimePath) {
    outputName = "fiji_" + imageName + "_edge_s" + sigma + ".tif";
    outputPath = fijiDir + outputName;
    if (File.exists(outputPath))
        return 0;

    selectWindow(sourceTitle);
    startMs = getTime();
    run("FeatureJ Edges",
        "compute smoothing=" + sigma + " suppress lower=[] higher=[]");
    runtimeMs = getTime() - startMs;

    selectWindow(sourceTitle + " edges");
    saveAs("tiff", outputPath);
    close();

    File.append("fiji," + imageName + ",edge," + sigma + "," +
        runtimeMs + "," + outputName + "\n", runtimePath);
}


function runLaplacian(sourceTitle, imageName, sigma, fijiDir, runtimePath) {
    outputName = "fiji_" + imageName + "_lap_s" + sigma + ".tif";
    outputPath = fijiDir + outputName;
    if (File.exists(outputPath))
        return 0;

    selectWindow(sourceTitle);
    startMs = getTime();
    run("FeatureJ Laplacian", "compute smoothing=" + sigma);
    runtimeMs = getTime() - startMs;

    selectWindow(sourceTitle + " Laplacian");
    saveAs("tiff", outputPath);
    close();

    File.append("fiji," + imageName + ",laplacian," + sigma + "," +
        runtimeMs + "," + outputName + "\n", runtimePath);
}


function runHessian(sourceTitle, imageName, sigma, eigenOrder,
        fijiDir, runtimePath) {
    l1Name = "fiji_" + imageName + "_hess-l1_s" + sigma + ".tif";
    l2Name = "fiji_" + imageName + "_hess-l2_s" + sigma + ".tif";
    l1Path = fijiDir + l1Name;
    l2Path = fijiDir + l2Name;
    if (File.exists(l1Path) && File.exists(l2Path))
        return 0;

    selectWindow(sourceTitle);
    options = "largest smallest ";
    if (eigenOrder == "absolute")
        options = options + "absolute ";

    startMs = getTime();
    run("FeatureJ Hessian", options + "smoothing=" + sigma);
    runtimeMs = getTime() - startMs;

    selectWindow(sourceTitle + " largest Hessian eigenvalues");
    saveAs("tiff", l1Path);
    close();
    selectWindow(sourceTitle + " smallest Hessian eigenvalues");
    saveAs("tiff", l2Path);
    close();

    File.append("fiji," + imageName + ",hessian," + sigma + "," +
        runtimeMs + "," + l1Name + ";" + l2Name + "\n", runtimePath);
}


function runStructure(sourceTitle, imageName, sd, si,
        fijiDir, runtimePath) {
    l1Name = "fiji_" + imageName + "_st-l1_sd" + sd +
        "_si" + si + ".tif";
    l2Name = "fiji_" + imageName + "_st-l2_sd" + sd +
        "_si" + si + ".tif";
    l1Path = fijiDir + l1Name;
    l2Path = fijiDir + l2Name;
    if (File.exists(l1Path) && File.exists(l2Path))
        return 0;

    selectWindow(sourceTitle);
    startMs = getTime();
    run("FeatureJ Structure",
        "largest smallest smoothing=" + sd + " integration=" + si);
    runtimeMs = getTime() - startMs;

    selectWindow(sourceTitle + " largest structure eigenvalues");
    saveAs("tiff", l1Path);
    close();
    selectWindow(sourceTitle + " smallest structure eigenvalues");
    saveAs("tiff", l2Path);
    close();

    File.append("fiji," + imageName + ",structure,sd" + sd + "_si" +
        si + "," + runtimeMs + "," + l1Name + ";" + l2Name +
        "\n", runtimePath);
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


function readPairBlock(text, key) {
    lines = split(text, "\n");
    inBlock = false;
    result = "";
    for (j = 0; j < lines.length; j++) {
        line = String.trim(replace(lines[j], "\r", ""));
        if (!inBlock) {
            if (startsWith(line, key)) inBlock = true;
            continue;
        }
        if (line == "" || startsWith(line, "#")) continue;
        if (!startsWith(line, "-")) break;
        left = indexOf(line, "[");
        right = lastIndexOf(line, "]");
        if (left < 0 || right <= left) return "";
        pair = replace(substring(line, left + 1, right), " ", "");
        if (result != "") result = result + "|";
        result = result + pair;
    }
    return result;
}


function readBlockListAsSet(text, key) {
    lines = split(text, "\n");
    inBlock = false;
    result = "|";
    for (j = 0; j < lines.length; j++) {
        line = String.trim(replace(lines[j], "\r", ""));
        if (!inBlock) {
            if (startsWith(line, key)) inBlock = true;
            continue;
        }
        if (line == "" || startsWith(line, "#")) continue;
        if (!startsWith(line, "-")) break;
        item = String.trim(substring(line, 1));
        hash = indexOf(item, "#");
        if (hash >= 0)
            item = String.trim(substring(item, 0, hash));
        if (item != "") result = result + item + "|";
    }
    return result;
}


function containsNullValue(text) {
    lines = split(text, "\n");
    for (j = 0; j < lines.length; j++) {
        line = replace(lines[j], "\r", "");
        hash = indexOf(line, "#");
        if (hash >= 0) line = substring(line, 0, hash);
        line = String.trim(line);
        if (endsWith(line, ": null") || line == "null" ||
                startsWith(line, "- null"))
            return true;
    }
    return false;
}


function stripExtension(fileName) {
    dot = lastIndexOf(fileName, ".");
    if (dot < 0) return fileName;
    return substring(fileName, 0, dot);
}
