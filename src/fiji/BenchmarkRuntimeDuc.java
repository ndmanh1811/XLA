import ij.IJ;
import imagescience.ImageScience;
import imagescience.image.Coordinates;
import imagescience.image.Image;
import imagescience.image.FloatImage;
import imagescience.image.Dimensions;
import imagescience.image.Axes;
import imagescience.feature.Differentiator;
import imagescience.feature.Edges;
import imagescience.feature.Hessian;
import imagescience.feature.Laplacian;
import imagescience.feature.Structure;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;

/** Task 24: repeated, headless ImageScience engine timings, no output TIFFs.
 * Cases and eigenvalue order are supplied by the validated Python driver.
 * Input reading and duplication are outside the timer. Kernel/filter work is
 * inside it. Each case has one discarded warm-up then all recorded repeats.
 */
public final class BenchmarkRuntimeDuc {
    private static volatile double sink;
    private final Differentiator diff = new Differentiator();
    private final Edges edges = new Edges();
    private final Hessian hessian = new Hessian();
    private final Laplacian lap = new Laplacian();
    private final Structure structure = new Structure();

    private Image run(String cmd, Image input, String scale, boolean absolute) {
        if (cmd.equals("structure")) {
            String[] pair = scale.replace("sd", "").split("_si");
            return structure.run(input, Double.parseDouble(pair[0]), Double.parseDouble(pair[1])).get(0);
        }
        double s = Double.parseDouble(scale);
        switch (cmd) {
            case "gauss": return diff.run(input, s, 0, 0, 0);
            case "lx": return diff.run(input, s, 1, 0, 0);
            case "ly": return diff.run(input, s, 0, 1, 0);
            case "lxx": return diff.run(input, s, 2, 0, 0);
            case "lyy": return diff.run(input, s, 0, 2, 0);
            case "lxy": return diff.run(input, s, 1, 1, 0);
            case "gradient": return edges.run(input, s, false);
            case "edge": return edges.run(input, s, true);
            case "laplacian": return lap.run(input, s);
            case "hessian": return hessian.run(input, s, absolute).get(0);
            default: throw new IllegalArgumentException("Unknown operation: " + cmd);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 5) throw new IllegalArgumentException("cases.csv rawDir samples.csv repeats eigen_order");
        int repeats = Integer.parseInt(args[3]);
        if (repeats < 3) throw new IllegalArgumentException("Need at least 3 repeats");
        boolean absolute = args[4].equals("absolute");
        if (!absolute && !args[4].equals("algebraic")) throw new IllegalArgumentException("eigen_order");
        BenchmarkRuntimeDuc bench = new BenchmarkRuntimeDuc();
        Map<String,Image> inputs = new HashMap<>();
        System.out.println("ImageJ=" + IJ.getVersion() + " ImageScience=" + ImageScience.version());
        System.out.println("Java=" + System.getProperty("java.version") + " VM=" + System.getProperty("java.vm.name"));
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(args[0]), StandardCharsets.UTF_8));
             PrintWriter writer = new PrintWriter(new OutputStreamWriter(new FileOutputStream(args[2]), StandardCharsets.UTF_8))) {
            reader.readLine();
            writer.println("source,image,command,sigma,iteration,warmup,runtime_ms");
            String line;
            int count = 0;
            while ((line = reader.readLine()) != null) {
                if (line.trim().isEmpty()) continue;
                String[] c = line.split(",");
                String name = c[0], cmd = c[1], sigma = c[2];
                if (!inputs.containsKey(name)) {
                    // ImageIO avoids ImageJ 1.53k Opener's AWT menu initializer,
                    // which cannot run headless. Raster samples preserve uint8
                    // grayscale exactly; convert before timing, like Python.
                    BufferedImage png = ImageIO.read(new File(args[1], name + ".png"));
                    if (png == null) throw new IOException("Cannot open " + name);
                    int w = png.getWidth(), h = png.getHeight();
                    float[][] values = new float[h][w];
                    for (int y = 0; y < h; y++)
                        for (int x = 0; x < w; x++) values[y][x] = png.getRaster().getSample(x,y,0);
                    Image image = new FloatImage(new Dimensions(w,h));
                    image.axes(Axes.X | Axes.Y);
                    image.set(new Coordinates(), values);
                    inputs.put(name, image);
                }
                for (int iteration = 0; iteration <= repeats; iteration++) {
                    Image input = inputs.get(name).duplicate();
                    long start = System.nanoTime();
                    Image result = bench.run(cmd, input, sigma, absolute);
                    long elapsed = System.nanoTime() - start;
                    sink = result.get(new Coordinates()); // Consume outside the timed region.
                    writer.printf(Locale.ROOT, "fiji_engine,%s,%s,%s,%d,%s,%.9f%n",
                        name, cmd, sigma, iteration, iteration == 0, elapsed / 1e6);
                }
                count++;
                if (count % 40 == 0) {
                    writer.flush();
                    System.out.println("ImageScience cases complete: " + count);
                }
            }
            System.out.println("ImageScience complete: " + count + " cases, " + repeats + " measured repeats each");
        }
    }
}
