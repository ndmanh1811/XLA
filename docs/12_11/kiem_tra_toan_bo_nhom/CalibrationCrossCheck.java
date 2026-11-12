import imagescience.ImageScience;
import imagescience.feature.*;
import imagescience.image.*;
import java.nio.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.io.*;
import java.util.*;

/** Compare the existing timing library with Loc's 40 calibration outputs. */
public class CalibrationCrossCheck {
    static Image input(Path path,int width,int height) throws Exception {
        float[][] values=read(path,width,height);
        Image image=new FloatImage(new Dimensions(width,height));
        image.axes(Axes.X|Axes.Y); image.set(new Coordinates(),values);
        return image;
    }
    static float[][] read(Path path,int w,int h) throws Exception {
        FloatBuffer buffer=ByteBuffer.wrap(Files.readAllBytes(path)).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer();
        float[][] values=new float[h][w];
        for(int y=0;y<h;y++) buffer.get(values[y]);
        return values;
    }
    public static void main(String[] args) throws Exception {
        Path data=Paths.get(args[0]);
        Differentiator diff=new Differentiator();
        Laplacian lap=new Laplacian(); Hessian hess=new Hessian();
        Edges edges=new Edges(); Structure st=new Structure();
        System.out.println("Timing-library ImageScience="+ImageScience.version());
        try(BufferedReader reader=Files.newBufferedReader(data.resolve("cases.csv"),StandardCharsets.UTF_8);
            PrintWriter writer=new PrintWriter(args[1],"UTF-8")) {
            writer.println("output,command,sigma,max_abs_error,relative_max_error");
            reader.readLine(); String line;
            while((line=reader.readLine())!=null) {
                String[] c=line.split(",",-1);
                int w=Integer.parseInt(c[5]),h=Integer.parseInt(c[6]);
                Image base=input(data.resolve(c[1]+".bin"),w,h);
                double s=Double.parseDouble(c[3]); Image result;
                switch(c[2]) {
                    case "gauss": result=diff.run(base,s,0,0,0);break;
                    case "lx": result=diff.run(base,s,1,0,0);break;
                    case "lxx": result=diff.run(base,s,2,0,0);break;
                    case "lap": result=lap.run(base,s);break;
                    case "grad": result=edges.run(base,s,false);break;
                    case "hess-l1": result=hess.run(base,s,false).get(0);break;
                    case "hess-l2": result=hess.run(base,s,false).get(1);break;
                    case "st-l1": result=st.run(base,s,Double.parseDouble(c[4])).get(0);break;
                    case "st-l2": result=st.run(base,s,Double.parseDouble(c[4])).get(1);break;
                    default:throw new IllegalArgumentException(c[2]);
                }
                float[][] target=read(data.resolve(c[0]+".bin"),w,h);
                float[][] actual=new float[h][w];
                result.axes(Axes.X|Axes.Y); result.get(new Coordinates(),actual);
                double maximum=0,peak=0;
                for(int y=0;y<h;y++)for(int x=0;x<w;x++) {
                    maximum=Math.max(maximum,Math.abs((double)actual[y][x]-target[y][x]));
                    peak=Math.max(peak,Math.abs((double)target[y][x]));
                }
                writer.printf(Locale.ROOT,"%s,%s,%s,%.12g,%.12g%n",c[0],c[2],c[3],maximum,peak==0?maximum:maximum/peak);
            }
        }
    }
}
