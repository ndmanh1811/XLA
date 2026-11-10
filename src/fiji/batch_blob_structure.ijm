/*
 * Batch FeatureJ workflow for the Blob/Structure assignment.
 *
 * Inputs : data/raw/*.png
 * Config : config.yaml (sigmas, sigmas_blob, structure_pairs, tier1_images)
 * Outputs: outputs/fiji/*.tif (32-bit float, uncompressed TIFF)
 * Runtime: appends to outputs/metrics/fiji_runtime.csv
 *
 * Scope:
 *   - Laplacian for every blob image at sigmas_blob.
 *   - Laplacian for non-blob Tier-1 images at sigmas.
 *   - Structure eigenvalues for every Tier-1 image at structure_pairs.
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

if (sigmaText == "") exit("Cannot read 'sigmas' from config.yaml");
if (blobSigmaText == "") exit("Cannot read 'sigmas_blob' from config.yaml");
if (pairText == "") exit("Cannot read 'structure_pairs' from config.yaml");
if (tier1Set == "|") exit("Cannot read 'tier1_images' from config.yaml");

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

// Preserve the Edge/Hessian runtime rows from the previous assignment.
if (!File.exists(runtimePath))
    File.saveString("source,image,command,sigma,runtime_ms,output_files\n", runtimePath);

files = getFileList(rawDir);
processed = 0;

for (i = 0; i < files.length; i++) {
    fileName = files[i];
    if (!endsWith(toLowerCase(fileName), ".png"))
        continue;

    imageName = stripExtension(fileName);
    isTier1 = indexOf(tier1Set, "|" + imageName + "|") >= 0;
    isBlob = startsWith(imageName, "blob_");
    doLaplacian = isBlob || isTier1;
    doStructure = isTier1;

    if (!doLaplacian && !doStructure)
        continue;

    open(rawDir + fileName);
    // Required by INSTRUCTIONS.md: this must be immediately after open().
    run("Set Scale...", "distance=0 known=0 pixel=1 unit=pixel");
    run("32-bit");
    sourceTitle = getTitle();

    if (doLaplacian) {
        if (isBlob) {
            for (s = 0; s < blobSigmas.length; s++)
                runLaplacian(sourceTitle, imageName, blobSigmas[s],
                    fijiDir, runtimePath);
        } else {
            for (s = 0; s < sigmas.length; s++)
                runLaplacian(sourceTitle, imageName, sigmas[s],
                    fijiDir, runtimePath);
        }
    }

    if (doStructure) {
        for (p = 0; p < structurePairs.length; p++) {
            pair = split(structurePairs[p], ",");
            if (pair.length != 2)
                exit("Invalid structure pair in config.yaml: " + structurePairs[p]);
            pair[0] = String.trim(pair[0]);
            pair[1] = String.trim(pair[1]);
            runStructure(sourceTitle, imageName, pair[0], pair[1],
                fijiDir, runtimePath);
        }
    }

    selectWindow(sourceTitle);
    close();
    processed++;
}

showMessage("FeatureJ Blob/Structure batch completed",
    "Processed " + processed + " input images.\n" +
    "New TIFF outputs were saved in: " + fijiDir + "\n" +
    "Runtime rows were appended to: " + runtimePath);


function runLaplacian(sourceTitle, imageName, sigma, fijiDir, runtimePath) {
    selectWindow(sourceTitle);
    startMs = getTime();
    // Compute the continuous Laplacian map; do not enable zero-crossings.
    run("FeatureJ Laplacian", "compute smoothing=" + sigma);
    runtimeMs = getTime() - startMs;

    resultTitle = sourceTitle + " Laplacian";
    outputName = "fiji_" + imageName + "_lap_s" + sigma + ".tif";

    selectWindow(resultTitle);
    saveAs("tiff", fijiDir + outputName);
    close();

    File.append("fiji," + imageName + ",laplacian," + sigma + "," +
        runtimeMs + "," + outputName + "\n", runtimePath);
}


function runStructure(sourceTitle, imageName, sd, si, fijiDir, runtimePath) {
    selectWindow(sourceTitle);
    startMs = getTime();
    run("FeatureJ Structure",
        "largest smallest smoothing=" + sd + " integration=" + si);
    runtimeMs = getTime() - startMs;

    largestTitle = sourceTitle + " largest structure eigenvalues";
    smallestTitle = sourceTitle + " smallest structure eigenvalues";
    l1Name = "fiji_" + imageName + "_st-l1_sd" + sd + "_si" + si + ".tif";
    l2Name = "fiji_" + imageName + "_st-l2_sd" + sd + "_si" + si + ".tif";

    selectWindow(largestTitle);
    saveAs("tiff", fijiDir + l1Name);
    close();

    selectWindow(smallestTitle);
    saveAs("tiff", fijiDir + l2Name);
    close();

    File.append("fiji," + imageName + ",structure,sd" + sd + "_si" + si +
        "," + runtimeMs + "," + l1Name + ";" + l2Name + "\n", runtimePath);
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


function readPairBlock(text, key) {
    lines = split(text, "\n");
    inBlock = false;
    result = "";

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

        left = indexOf(line, "[");
        right = lastIndexOf(line, "]");
        if (left < 0 || right <= left)
            return "";
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
