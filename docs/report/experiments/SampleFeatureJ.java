import ij.IJ;
import ij.ImagePlus;
import ij.io.FileSaver;
import imagescience.ImageScience;
import imagescience.feature.Differentiator;
import imagescience.image.FloatImage;
import imagescience.image.Image;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import java.util.regex.*;

/** Direct ImageScience API sample using the Fiji libraries, not a GUI screenshot. */
public class SampleFeatureJ {
    public static void main(String[] args) throws Exception {
        Properties job = new Properties();
        try (Reader r = Files.newBufferedReader(Paths.get(args[0]),StandardCharsets.UTF_8)) {
            job.load(r);
        }
        Path repo = Paths.get(job.getProperty("repo"));
        String config = new String(Files.readAllBytes(repo.resolve("config.yaml")),StandardCharsets.UTF_8);
        if (Pattern.compile("(?m)^\\s*[^#\\n]+:\\s*null\\s*(?:#.*)?$").matcher(config).find())
            throw new IllegalArgumentException("Uncalibrated null in config.yaml");
        Matcher scales = Pattern.compile("(?m)^sigmas:\\s*\\[([^\\]]+)\\]").matcher(config);
        if (!scales.find()) throw new IllegalArgumentException("Missing sigmas in config.yaml");
        String[] sigmaStrings = scales.group(1).split(",");
        Path out = repo.resolve("experiments/sample_local/fiji");
        Files.createDirectories(out);
        String[] names = {"bsds_01","drive_01","blob_01"};
        String[] codes = {"gauss","lx","ly","lxx","lxy","lyy"};
        int[] xs={0,1,0,2,1,0}, ys={0,0,1,0,1,2};
        Path log=out.getParent().resolve("fiji_api_sample_log.csv");
        int count=0;
        try(PrintWriter writer=new PrintWriter(Files.newBufferedWriter(log,StandardCharsets.UTF_8))){
            writer.println("image,operator,sigma,runtime_ms,producer,timestamp_utc");
            for(String name:names){
                ImagePlus input=IJ.openImage(repo.resolve("data/raw/"+name+".png").toString());
                if(input==null || input.getBitDepth()!=8)
                    throw new IllegalArgumentException("Missing or non-8-bit input: "+name);
                input.getCalibration().pixelWidth=1;
                input.getCalibration().pixelHeight=1;
                input.getCalibration().pixelDepth=1;
                input.getCalibration().setUnit("pixel");
                Image original=new FloatImage(Image.wrap(input));
                for(String scale:sigmaStrings){
                    double sigma=Double.parseDouble(scale.trim());
                    for(int k=0;k<codes.length;k++){
                        long start=System.nanoTime();
                        Image result=new Differentiator().run(original.duplicate(),sigma,xs[k],ys[k],0);
                        double duration=(System.nanoTime()-start)/1e6;
                        ImagePlus image=result.imageplus();
                        if(image.getBitDepth()!=32) throw new IllegalStateException("Not float32");
                        String file=String.format(Locale.US,"fiji_%s_%s_s%.1f.tif",name,codes[k],sigma);
                        if(!new FileSaver(image).saveAsTiff(out.resolve(file).toString()))
                            throw new IOException("Could not save "+file);
                        writer.printf(Locale.US,"%s,%s,%.1f,%.3f,ImageScience-%s-API,%s%n",
                            name,codes[k],sigma,duration,ImageScience.version(),Instant.now().toString());
                        count++;
                    }
                }
                input.close();
            }
        }
        System.out.println("ImageJ "+IJ.getVersion()+", ImageScience "+ImageScience.version());
        System.out.println("Computed "+count+" fresh maps via direct ImageScience API.");
        System.out.println("Producer is API export; no GUI screenshots were captured.");
    }
}
