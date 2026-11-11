/*
 * FeatureJ calibration evidence for Pham Bao Loc.
 *
 * Input : data/calib/*.tif (float32)
 * Output: docs/fiji/calibration/{measurement_results.csv,
 *         kernel_profiles.csv,environment.csv,outputs/*.tif}
 *
 * This macro records measurements; it deliberately does not assert that the
 * current config values are correct. Review the measured values before filling
 * the conclusion column or changing config.yaml.
 */

requires("1.53");

projectDir = getDirectory("Choose the XLA project root");
calibInputDir = projectDir + "data" + File.separator + "calib" + File.separator;
calibDir = projectDir + "docs" + File.separator + "fiji" + File.separator +
    "calibration" + File.separator;
outputDir = calibDir + "outputs" + File.separator;
measurementPath = calibDir + "measurement_results.csv";
profilePath = calibDir + "kernel_profiles.csv";
environmentPath = calibDir + "environment.csv";

if (!File.isDirectory(calibInputDir))
    exit("Missing calibration input directory: " + calibInputDir);

required = newArray("ramp.tif", "parabola.tif", "saddle.tif",
    "dirac.tif", "bright_border.tif");
for (i = 0; i < required.length; i++) {
    if (!File.exists(calibInputDir + required[i]))
        exit("Missing calibration image: " + calibInputDir + required[i]);
}

if (!File.isDirectory(calibDir)) File.makeDirectory(calibDir);
if (!File.isDirectory(outputDir)) File.makeDirectory(outputDir);

File.saveString(
    "image,command,sigma,sigma_i,options,roi_x,roi_y,roi_width,roi_height," +
    "output_name,expected_raw,measured_mean,measured_min,measured_max," +
    "measured_stddev,measured_sum,conclusion\n", measurementPath);
File.saveString(
    "measurement_type,image,command,sigma,axis,offset,x,y,value," +
    "output_name,notes\n", profilePath);
File.saveString(
    "key,value,notes\n" +
    "measurement_status,MEASURED,Review CSV and screenshots before acceptance\n" +
    "imagej_version," + getVersion() + ",Recorded by reproduce.ijm\n" +
    "fiji_version,MANUAL_REQUIRED,Fill from Help About\n" +
    "featurej_version,MANUAL_REQUIRED,Fill from plugin or JAR metadata\n" +
    "imagescience_version,MANUAL_REQUIRED,Fill from plugin or JAR metadata\n" +
    "operator,Pham Bao Loc,Confirm operator name\n" +
    "measurement_date,MANUAL_REQUIRED,Use Asia Saigon date and time\n",
    environmentPath);

sigmas = newArray(1.0, 2.0, 4.0);

// Normalization and sign measurements.
for (i = 0; i < sigmas.length; i++) {
    s = sigmas[i];
    runDerivativeMeasurement("ramp.tif", "lx", s, 1, 0, "1",
        calibInputDir, outputDir, measurementPath);
    runDerivativeMeasurement("parabola.tif", "lxx", s, 2, 0, "1",
        calibInputDir, outputDir, measurementPath);
    runLaplacianMeasurement("parabola.tif", s, "1",
        calibInputDir, outputDir, measurementPath);
    runHessianMeasurement("saddle.tif", s, calibInputDir, outputDir,
        measurementPath);
    runEdgeMeasurement("ramp.tif", s, "1", calibInputDir, outputDir,
        measurementPath);
}

runStructureMeasurement("ramp.tif", 1.0, 3.0, calibInputDir, outputDir,
    measurementPath);
runStructureMeasurement("ramp.tif", 2.0, 6.0, calibInputDir, outputDir,
    measurementPath);

// Dirac responses: save images and record both derivative and smoothing axes.
for (i = 0; i < sigmas.length; i++) {
    s = sigmas[i];
    runProfileDerivative("dirac.tif", "gauss", s, 0, 0, "dirac",
        calibInputDir, outputDir, measurementPath, profilePath);
    runProfileDerivative("dirac.tif", "lx", s, 1, 0, "dirac",
        calibInputDir, outputDir, measurementPath, profilePath);
    runProfileDerivative("dirac.tif", "lxx", s, 2, 0, "dirac",
        calibInputDir, outputDir, measurementPath, profilePath);
}

// Border probes for the same three derivative orders.
for (i = 0; i < sigmas.length; i++) {
    s = sigmas[i];
    runProfileDerivative("bright_border.tif", "gauss", s, 0, 0, "border",
        calibInputDir, outputDir, measurementPath, profilePath);
    runProfileDerivative("bright_border.tif", "lx", s, 1, 0, "border",
        calibInputDir, outputDir, measurementPath, profilePath);
    runProfileDerivative("bright_border.tif", "lxx", s, 2, 0, "border",
        calibInputDir, outputDir, measurementPath, profilePath);
}

run("Close All");
showMessage("FeatureJ calibration evidence created",
    "Review the measured values before accepting conclusions.\n" +
    "Measurements: " + measurementPath + "\n" +
    "Profiles: " + profilePath + "\n" +
    "TIFF outputs: " + outputDir + "\n" +
    "Still required: plugin versions and screenshots.");


function runDerivativeMeasurement(fileName, command, sigma, xOrder, yOrder,
        expectedRaw, inputDir, outputDir, measurementPath) {
    sourceTitle = openFloatCalibration(inputDir + fileName);
    sText = d2s(sigma, 1);
    options = "x-order=" + xOrder + " y-order=" + yOrder +
        " z-order=0 smoothing=" + sText;
    run("FeatureJ Derivatives", options);
    resultTitle = getTitle();
    outputName = "calib_" + stripExtension(fileName) + "_" + command +
        "_s" + sText + ".tif";
    saveAs("tiff", outputDir + outputName);
    recordCentralRoi(fileName, command, sigma, "", options, outputName,
        expectedRaw, measurementPath);
    close();
    selectWindow(sourceTitle);
    close();
}


function runLaplacianMeasurement(fileName, sigma, expectedRaw,
        inputDir, outputDir, measurementPath) {
    sourceTitle = openFloatCalibration(inputDir + fileName);
    sText = d2s(sigma, 1);
    options = "compute smoothing=" + sText;
    run("FeatureJ Laplacian", options);
    outputName = "calib_" + stripExtension(fileName) + "_lap_s" + sText +
        ".tif";
    saveAs("tiff", outputDir + outputName);
    recordCentralRoi(fileName, "lap", sigma, "", options, outputName,
        expectedRaw, measurementPath);
    close();
    selectWindow(sourceTitle);
    close();
}


function runHessianMeasurement(fileName, sigma, inputDir, outputDir,
        measurementPath) {
    sourceTitle = openFloatCalibration(inputDir + fileName);
    sText = d2s(sigma, 1);
    // Do not add "absolute": signed algebraic Largest/Smallest are required.
    options = "largest smallest smoothing=" + sText;
    run("FeatureJ Hessian", options);

    selectWindow(sourceTitle + " largest Hessian eigenvalues");
    outputName = "calib_" + stripExtension(fileName) +
        "_hess-l1_s" + sText + ".tif";
    saveAs("tiff", outputDir + outputName);
    recordCentralRoi(fileName, "hess-l1", sigma, "", options, outputName,
        "1", measurementPath);
    close();

    selectWindow(sourceTitle + " smallest Hessian eigenvalues");
    outputName = "calib_" + stripExtension(fileName) +
        "_hess-l2_s" + sText + ".tif";
    saveAs("tiff", outputDir + outputName);
    recordCentralRoi(fileName, "hess-l2", sigma, "", options, outputName,
        "-2", measurementPath);
    close();

    selectWindow(sourceTitle);
    close();
}


function runEdgeMeasurement(fileName, sigma, expectedRaw, inputDir,
        outputDir, measurementPath) {
    sourceTitle = openFloatCalibration(inputDir + fileName);
    sText = d2s(sigma, 1);
    // NMS is intentionally off; thresholds are blank.
    options = "compute smoothing=" + sText + " lower=[] higher=[]";
    run("FeatureJ Edges", options);
    selectWindow(sourceTitle + " edges");
    outputName = "calib_" + stripExtension(fileName) + "_grad_s" + sText +
        ".tif";
    saveAs("tiff", outputDir + outputName);
    recordCentralRoi(fileName, "grad", sigma, "", options, outputName,
        expectedRaw, measurementPath);
    close();
    selectWindow(sourceTitle);
    close();
}


function runStructureMeasurement(fileName, sd, si, inputDir, outputDir,
        measurementPath) {
    sourceTitle = openFloatCalibration(inputDir + fileName);
    sdText = d2s(sd, 1);
    siText = d2s(si, 1);
    options = "largest smallest smoothing=" + sdText +
        " integration=" + siText;
    run("FeatureJ Structure", options);

    selectWindow(sourceTitle + " largest structure eigenvalues");
    outputName = "calib_" + stripExtension(fileName) +
        "_st-l1_sd" + sdText + "_si" + siText + ".tif";
    saveAs("tiff", outputDir + outputName);
    recordCentralRoi(fileName, "st-l1", sd, si, options, outputName, "1",
        measurementPath);
    close();

    selectWindow(sourceTitle + " smallest structure eigenvalues");
    outputName = "calib_" + stripExtension(fileName) +
        "_st-l2_sd" + sdText + "_si" + siText + ".tif";
    saveAs("tiff", outputDir + outputName);
    recordCentralRoi(fileName, "st-l2", sd, si, options, outputName, "0",
        measurementPath);
    close();

    selectWindow(sourceTitle);
    close();
}


function runProfileDerivative(fileName, command, sigma, xOrder, yOrder,
        profileType, inputDir, outputDir, measurementPath, profilePath) {
    sourceTitle = openFloatCalibration(inputDir + fileName);
    sText = d2s(sigma, 1);
    options = "x-order=" + xOrder + " y-order=" + yOrder +
        " z-order=0 smoothing=" + sText;
    run("FeatureJ Derivatives", options);
    outputName = "calib_" + stripExtension(fileName) + "_" + command +
        "_s" + sText + ".tif";
    saveAs("tiff", outputDir + outputName);

    if (profileType == "dirac") {
        recordFullImage(fileName, command, sigma, options, outputName,
            measurementPath);
        appendCenterProfiles(profileType, fileName, command, sigma,
            outputName, profilePath);
    } else {
        recordCentralRoi(fileName, command, sigma, "", options, outputName,
            "border probe", measurementPath);
        appendBorderProfiles(fileName, command, sigma, outputName,
            profilePath);
    }

    close();
    selectWindow(sourceTitle);
    close();
}


function openFloatCalibration(path) {
    open(path);
    // Required immediately after every open: sigma is measured in pixels.
    run("Set Scale...", "distance=0 known=0 pixel=1 unit=pixel");
    if (bitDepth() != 32)
        exit("Calibration input must be 32-bit float: " + path);
    return getTitle();
}


function recordCentralRoi(imageName, command, sigma, sigmaI, options,
        outputName, expectedRaw, measurementPath) {
    getDimensions(w, h, channels, slices, frames);
    roiW = minOf(64, w - 2);
    roiH = minOf(64, h - 2);
    roiX = floor((w - roiW) / 2);
    roiY = floor((h - roiH) / 2);
    makeRectangle(roiX, roiY, roiW, roiH);
    getStatistics(area, mean, min, max, stddev);
    appendMeasurement(imageName, command, sigma, sigmaI, options, roiX,
        roiY, roiW, roiH, outputName, expectedRaw, mean, min, max, stddev,
        "REVIEW_MEASURED_VALUE", measurementPath);
    run("Select None");
}


function recordFullImage(imageName, command, sigma, options, outputName,
        measurementPath) {
    getDimensions(w, h, channels, slices, frames);
    run("Select All");
    getStatistics(area, mean, min, max, stddev);
    appendMeasurement(imageName, command, sigma, "", options, 0, 0, w, h,
        outputName, "Dirac response; review sum and support", mean, min, max,
        stddev, "REVIEW_PROFILE", measurementPath);
    run("Select None");
}


function appendMeasurement(imageName, command, sigma, sigmaI, options,
        roiX, roiY, roiW, roiH, outputName, expectedRaw, mean, min, max,
        stddev, conclusion, path) {
    row = "" + imageName + "," + command + "," + d2s(sigma, 1) +
        "," + sigmaI + "," + options + "," + roiX + "," +
        roiY + "," + roiW + "," + roiH + "," + outputName + "," +
        expectedRaw + "," + d2s(mean, 10) + "," + d2s(min, 10) +
        "," + d2s(max, 10) + "," + d2s(stddev, 10) + "," +
        d2s(mean * roiW * roiH, 12) + "," + conclusion + "\n";
    File.append(row, path);
}


function appendCenterProfiles(profileType, imageName, command, sigma,
        outputName, path) {
    getDimensions(w, h, channels, slices, frames);
    cx = floor(w / 2);
    cy = floor(h / 2);
    for (x = 0; x < w; x++) {
        value = getPixel(x, cy);
        appendProfile(profileType, imageName, command, sigma, "x", x - cx,
            x, cy, value, outputName, "center row", path);
    }
    for (y = 0; y < h; y++) {
        value = getPixel(cx, y);
        appendProfile(profileType, imageName, command, sigma, "y", y - cy,
            cx, y, value, outputName, "center column", path);
    }
}


function appendBorderProfiles(imageName, command, sigma, outputName, path) {
    getDimensions(w, h, channels, slices, frames);
    cx = floor(w / 2);
    cy = floor(h / 2);
    depth = minOf(24, floor(minOf(w, h) / 2));
    for (d = 0; d < depth; d++) {
        appendProfile("border", imageName, command, sigma, "x-left", d,
            d, cy, getPixel(d, cy), outputName, "distance from left", path);
        appendProfile("border", imageName, command, sigma, "x-right", d,
            w - 1 - d, cy, getPixel(w - 1 - d, cy), outputName,
            "distance from right", path);
        appendProfile("border", imageName, command, sigma, "y-top", d,
            cx, d, getPixel(cx, d), outputName, "distance from top", path);
        appendProfile("border", imageName, command, sigma, "y-bottom", d,
            cx, h - 1 - d, getPixel(cx, h - 1 - d), outputName,
            "distance from bottom", path);
    }
}


function appendProfile(measurementType, imageName, command, sigma, axis,
        offset, x, y, value, outputName, notes, path) {
    row = "" + measurementType + "," + imageName + "," + command +
        "," + d2s(sigma, 1) + "," + axis + "," + offset + "," + x +
        "," + y + "," + d2s(value, 12) + "," + outputName + "," +
        notes + "\n";
    File.append(row, path);
}


function stripExtension(fileName) {
    dot = lastIndexOf(fileName, ".");
    if (dot < 0) return fileName;
    return substring(fileName, 0, dot);
}
