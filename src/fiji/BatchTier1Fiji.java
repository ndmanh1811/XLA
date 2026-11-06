package src.fiji;

import ij.IJ;
import ij.ImagePlus;
import imagescience.image.Image;
import imagescience.feature.*;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.Locale;
import java.util.Vector;

public class BatchTier1Fiji {
    private static final String[] TIER1_IMAGES = {
        "bsds_01", "bsds_02", "drive_01", "blob_01", "blob_02"
    };
    private static final double[] SIGMAS = {1.0, 2.0, 4.0, 8.0};
    private static final double[][] ST_PAIRS = {{1.0, 3.0}, {2.0, 6.0}};

    public static void main(String[] args) {
        System.out.println("=================================================================");
        System.out.println("  BẮT ĐẦU BATCH EXPORTER FIJI / FEATUREJ (TIER 1 BENCHMARK)");
        System.out.println("=================================================================");

        File outDir = new File("outputs/fiji");
        if (!outDir.exists()) {
            outDir.mkdirs();
        }
        File metricsDir = new File("outputs/metrics");
        if (!metricsDir.exists()) {
            metricsDir.mkdirs();
        }

        File csvFile = new File("outputs/metrics/fiji_runtime.csv");

        try (PrintWriter pw = new PrintWriter(new FileWriter(csvFile))) {
            pw.println("image,operator,sigma,runtime_ms");

            Differentiator diff = new Differentiator();
            Laplacian lap = new Laplacian();
            Edges edges = new Edges();
            Hessian hess = new Hessian();
            Structure st = new Structure();

            for (String name : TIER1_IMAGES) {
                String inPath = "data/raw/" + name + ".png";
                File inFile = new File(inPath);
                if (!inFile.exists()) {
                    System.out.println("  [!] Không tìm thấy tệp: " + inPath);
                    continue;
                }

                System.out.println("-> Đang xử lý FeatureJ cho ảnh: " + name + "...");
                ImagePlus imp = IJ.openImage(inPath);
                Image baseImg = Image.wrap(imp);

                // 1. Các bản đồ vi phân ở 4 tỷ lệ chuẩn
                for (double s : SIGMAS) {
                    String sStr = String.format(Locale.US, "%.1f", s);

                    // Gauss
                    long t0 = System.currentTimeMillis();
                    Image g = diff.run(baseImg.duplicate(), s, 0, 0, 0);
                    long dt = System.currentTimeMillis() - t0;
                    saveTif("outputs/fiji/fj_" + name + "_gauss_s" + sStr + ".tif", g);
                    pw.println(name + ",gauss," + sStr + "," + dt);

                    // Lx, Ly
                    t0 = System.currentTimeMillis();
                    Image lx = diff.run(baseImg.duplicate(), s, 1, 0, 0);
                    dt = System.currentTimeMillis() - t0;
                    saveTif("outputs/fiji/fj_" + name + "_lx_s" + sStr + ".tif", lx);
                    pw.println(name + ",lx," + sStr + "," + dt);

                    t0 = System.currentTimeMillis();
                    Image ly = diff.run(baseImg.duplicate(), s, 0, 1, 0);
                    dt = System.currentTimeMillis() - t0;
                    saveTif("outputs/fiji/fj_" + name + "_ly_s" + sStr + ".tif", ly);
                    pw.println(name + ",ly," + sStr + "," + dt);

                    // Grad
                    t0 = System.currentTimeMillis();
                    Image grad = edges.run(baseImg.duplicate(), s, false);
                    dt = System.currentTimeMillis() - t0;
                    saveTif("outputs/fiji/fj_" + name + "_grad_s" + sStr + ".tif", grad);
                    pw.println(name + ",grad," + sStr + "," + dt);

                    // Lxx, Lyy, Lxy
                    t0 = System.currentTimeMillis();
                    Image lxx = diff.run(baseImg.duplicate(), s, 2, 0, 0);
                    dt = System.currentTimeMillis() - t0;
                    saveTif("outputs/fiji/fj_" + name + "_lxx_s" + sStr + ".tif", lxx);
                    pw.println(name + ",lxx," + sStr + "," + dt);

                    t0 = System.currentTimeMillis();
                    Image lyy = diff.run(baseImg.duplicate(), s, 0, 2, 0);
                    dt = System.currentTimeMillis() - t0;
                    saveTif("outputs/fiji/fj_" + name + "_lyy_s" + sStr + ".tif", lyy);
                    pw.println(name + ",lyy," + sStr + "," + dt);

                    t0 = System.currentTimeMillis();
                    Image lxy = diff.run(baseImg.duplicate(), s, 1, 1, 0);
                    dt = System.currentTimeMillis() - t0;
                    saveTif("outputs/fiji/fj_" + name + "_lxy_s" + sStr + ".tif", lxy);
                    pw.println(name + ",lxy," + sStr + "," + dt);

                    // Laplacian
                    t0 = System.currentTimeMillis();
                    Image lp = lap.run(baseImg.duplicate(), s);
                    dt = System.currentTimeMillis() - t0;
                    saveTif("outputs/fiji/fj_" + name + "_lap_s" + sStr + ".tif", lp);
                    pw.println(name + ",lap," + sStr + "," + dt);

                    // Hessian eigenvalues (algebraic: absolute=false)
                    t0 = System.currentTimeMillis();
                    Vector<Image> h = hess.run(baseImg.duplicate(), s, false);
                    dt = System.currentTimeMillis() - t0;
                    saveTif("outputs/fiji/fj_" + name + "_hess-l1_s" + sStr + ".tif", h.get(0));
                    saveTif("outputs/fiji/fj_" + name + "_hess-l2_s" + sStr + ".tif", h.get(1));
                    pw.println(name + ",hess-l1," + sStr + "," + dt);
                    pw.println(name + ",hess-l2," + sStr + "," + dt);
                }

                // 2. Structure Tensor
                for (double[] pair : ST_PAIRS) {
                    double sd = pair[0];
                    double si = pair[1];
                    String sdStr = String.format(Locale.US, "%.1f", sd);
                    String siStr = String.format(Locale.US, "%.1f", si);

                    long t0 = System.currentTimeMillis();
                    Vector<Image> svec = st.run(baseImg.duplicate(), sd, si);
                    long dt = System.currentTimeMillis() - t0;
                    saveTif("outputs/fiji/fj_" + name + "_st-l1_sd" + sdStr + "_si" + siStr + ".tif", svec.get(0));
                    saveTif("outputs/fiji/fj_" + name + "_st-l2_sd" + sdStr + "_si" + siStr + ".tif", svec.get(1));
                    pw.println(name + ",st-l1," + sdStr + "_" + siStr + "," + dt);
                    pw.println(name + ",st-l2," + sdStr + "_" + siStr + "," + dt);
                }

                System.out.println("   ✓ Hoàn tất xuất đầy đủ 44 bản đồ FeatureJ cho " + name);
            }

            pw.flush();
            System.out.println("=================================================================");
            System.out.println("  HOÀN THÀNH XUẤT TOÀN BỘ BẢN ĐỒ FEATUREJ (outputs/fiji/)!");
            System.out.println("  -> Đã lưu thời gian thực thi: outputs/metrics/fiji_runtime.csv");
            System.out.println("=================================================================");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void saveTif(String path, Image img) {
        IJ.saveAsTiff(img.imageplus(), path);
    }
}
