/*
 * Validate every Fiji TIFF output against the shared project convention.
 *
 * Checks:
 *   1. File name starts with fiji_{bsds|drive|blob}_
 *   2. One-scale outputs use _{algorithm}_s{sigma}.tif
 *   3. Structure outputs use _st-l{1|2}_sd{sd}_si{si}.tif
 *   4. Every TIFF opens as a 32-bit image in ImageJ/Fiji
 *
 * Result:
 *   outputs/metrics/fiji_output_manifest.csv
 */

requires("1.54");

projectDir = getDirectory("Choose the XLA project root");
fijiDir = projectDir + "outputs" + File.separator +
    "fiji" + File.separator;
metricsDir = projectDir + "outputs" + File.separator +
    "metrics" + File.separator;
manifestPath = metricsDir + "fiji_output_manifest.csv";

if (!File.isDirectory(fijiDir))
    exit("Missing Fiji output directory: " + fijiDir);
if (!File.isDirectory(metricsDir))
    File.makeDirectory(metricsDir);

File.saveString(
    "file,width,height,channels,slices,frames,bit_depth,name_ok,depth_ok\n",
    manifestPath
);

files = getFileList(fijiDir);
total = 0;
validNames = 0;
validDepths = 0;
invalid = 0;

setBatchMode(true);

for (i = 0; i < files.length; i++) {
    fileName = files[i];
    if (!endsWith(toLowerCase(fileName), ".tif"))
        continue;

    nameOk = isValidFijiName(fileName);

    open(fijiDir + fileName);
    getDimensions(width, height, channels, slices, frames);
    depth = bitDepth();
    depthOk = depth == 32;

    if (nameOk) validNames++;
    if (depthOk) validDepths++;
    if (!nameOk || !depthOk) invalid++;

    File.append(
        fileName + "," + width + "," + height + "," +
        channels + "," + slices + "," + frames + "," +
        depth + "," + nameOk + "," + depthOk + "\n",
        manifestPath
    );

    close();
    total++;
}

setBatchMode(false);

showMessage("Fiji output validation completed",
    "Total TIFF files: " + total + "\n" +
    "Valid names: " + validNames + "\n" +
    "32-bit TIFF files: " + validDepths + "\n" +
    "Invalid files: " + invalid + "\n" +
    "Manifest: " + manifestPath);


function isValidFijiName(fileName) {
    lowerName = toLowerCase(fileName);

    if (!endsWith(lowerName, ".tif"))
        return 0;

    sourceOk = startsWith(lowerName, "fiji_bsds_") ||
        startsWith(lowerName, "fiji_drive_") ||
        startsWith(lowerName, "fiji_blob_");
    if (!sourceOk)
        return 0;

    // Two-scale Structure Tensor convention.
    structureOk = indexOf(lowerName, "_st-l1_sd") >= 0 ||
        indexOf(lowerName, "_st-l2_sd") >= 0;
    if (structureOk && indexOf(lowerName, "_si") >= 0)
        return 1;

    // One-scale convention.
    markers = newArray(
        "_gauss_s", "_lx_s", "_ly_s", "_lxx_s", "_lxy_s",
        "_lyy_s", "_grad_s", "_lap_s", "_edge_s",
        "_hess-l1_s", "_hess-l2_s"
    );

    for (j = 0; j < markers.length; j++) {
        if (indexOf(lowerName, markers[j]) >= 0)
            return 1;
    }

    return 0;
}
