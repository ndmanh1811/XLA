import ij.IJ;
import ij.ImageJ;
import ij.ImagePlus;
import ij.WindowManager;
import ij.gui.GenericDialog;
import ij.io.FileSaver;
import ij.plugin.PlugIn;
import ij.process.ImageConverter;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.image.BufferedImage;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import javax.imageio.ImageIO;

/** Opens real ImageJ/FeatureJ windows; captures their actual screen bounds. */
public class GuiEvidence {
    static Robot robot;
    static Path captures;
    static PrintWriter log;
    static Path progress;
    static String python;
    static String nativeCapture;
    static String lastCaptureMethod="";
    static void note(String value) throws Exception {
        Files.write(progress,(Instant.now()+" "+value+"\n").getBytes(StandardCharsets.UTF_8),
                    StandardOpenOption.CREATE,StandardOpenOption.APPEND);
    }
    static void capture(Window window,String name) throws Exception {
        EventQueue.invokeAndWait(()->{window.toFront();window.requestFocus();});
        robot.delay(700);
        Rectangle bounds=new Rectangle(window.getLocationOnScreen(),window.getSize());
        Process nativeProcess=new ProcessBuilder(python,"-X","utf8",nativeCapture,
            Long.toString(ProcessHandle.current().pid()),title(window),
            captures.resolve(name+".png").toString()).inheritIO().start();
        if(!nativeProcess.waitFor(10,java.util.concurrent.TimeUnit.SECONDS)){
            nativeProcess.destroyForcibly();throw new IOException("Native capture timeout");
        }
        if(nativeProcess.exitValue()!=0)throw new IOException("Window capture failed");
        lastCaptureMethod="PrintWindow";
        note("captured "+name);
        System.out.println("Captured "+name+" "+bounds+" title="+title(window));
    }
    static String title(Window w) {
        return w instanceof Dialog?((Dialog)w).getTitle():
               w instanceof Frame?((Frame)w).getTitle():w.getClass().getName();
    }
    static GenericDialog awaitDialog(String suffix) throws Exception {
        for(int attempt=0;attempt<150;attempt++){
            for(Window w:Window.getWindows())
                if(w instanceof GenericDialog && w.isShowing() && title(w).endsWith(suffix))
                    return (GenericDialog)w;
            Thread.sleep(100);
        }
        throw new IllegalStateException("No visible FeatureJ dialog: "+suffix);
    }
    static Button findOK(Container root) {
        for(Component c:root.getComponents()){
            if(c instanceof Button && ((Button)c).getLabel().trim().equals("OK"))return (Button)c;
            if(c instanceof Container){Button b=findOK((Container)c);if(b!=null)return b;}
        }
        return null;
    }
    static void closeImages(){
        int[] ids=WindowManager.getIDList();
        if(ids!=null)for(int id:ids){
            ImagePlus im=WindowManager.getImage(id);
            if(im!=null){im.changes=false;im.close();}
        }
    }
    static void runCase(Path repo,String input,String kind,String number,String scale,
                        String integration) throws Exception {
        closeImages();
        ImagePlus image=IJ.openImage(repo.resolve("data/raw/"+input+".png").toString());
        if(image==null)throw new IOException("Input missing");
        new ImageConverter(image).convertToGray32();
        image.getCalibration().pixelWidth=1;
        image.getCalibration().pixelHeight=1;
        image.getCalibration().setUnit("pixel");
        image.show();
        image.getWindow().setLocation(70,160);
        WindowManager.setCurrentWindow(image.getWindow());
        Set<Integer> old=new HashSet<>();
        int[] ids=WindowManager.getIDList();
        if(ids!=null)for(int id:ids)old.add(id);
        PlugIn plugin=kind.equals("Derivatives")?new featurej.FJ_Derivatives():
                      kind.equals("Hessian")?new featurej.FJ_Hessian():
                      kind.equals("Laplacian")?new featurej.FJ_Laplacian():
                      new featurej.FJ_Structure();
        Thread task=new Thread(()->plugin.run(""),"FeatureJ-"+kind);
        task.start();
        GenericDialog dialog=awaitDialog(kind);
        EventQueue.invokeAndWait(()->{
            dialog.setLocation(820,250);
            Vector choices=dialog.getChoices();
            if(kind.equals("Derivatives")){
                ((Choice)choices.get(0)).select(1);
                ((Choice)choices.get(1)).select(0);
                ((Choice)choices.get(2)).select(0);
            }
            Vector strings=dialog.getStringFields();
            ((TextField)strings.get(0)).setText(scale);
            if(kind.equals("Structure"))((TextField)strings.get(1)).setText(integration);
            Vector checks=dialog.getCheckboxes();
            if(kind.equals("Hessian")||kind.equals("Structure")){
                ((Checkbox)checks.get(0)).setState(true);
                ((Checkbox)checks.get(1)).setState(false);
                ((Checkbox)checks.get(2)).setState(true);
                if(kind.equals("Hessian"))((Checkbox)checks.get(3)).setState(false);
            }else if(kind.equals("Laplacian")){
                ((Checkbox)checks.get(0)).setState(true);
                ((Checkbox)checks.get(1)).setState(false);
            }
        });
        String prefix="gui_"+number+"_"+kind.toLowerCase(Locale.ROOT);
        capture(dialog,prefix+"_dialog");
        String dialogMethod=lastCaptureMethod;
        Button ok=findOK(dialog);
        if(ok==null)throw new IllegalStateException("OK button missing");
        note("activating actual dialog OK action");
        EventQueue.invokeLater(()->dialog.actionPerformed(
            new ActionEvent(ok,ActionEvent.ACTION_PERFORMED,"OK")));
        task.join(15000);
        note("plugin thread finished="+!task.isAlive());
        if(task.isAlive())throw new IllegalStateException("Plugin did not finish");
        ArrayList<ImagePlus> results=new ArrayList<>();
        ids=WindowManager.getIDList();
        if(ids!=null)for(int id:ids)if(!old.contains(id))results.add(WindowManager.getImage(id));
        if(results.isEmpty())throw new IllegalStateException("Plugin did not create a result");
        Path out=repo.resolve("experiments/gui_evidence");
        Files.createDirectories(out);
        int k=0;
        for(ImagePlus result:results){
            if(result.getBitDepth()!=32)throw new IllegalStateException("Output not float32");
            new FileSaver(result).saveAsTiff(out.resolve(prefix+"_result"+(++k)+".tif").toString());
        }
        ImagePlus result=results.get(0);
        result.getWindow().setLocation(760,160);
        EventQueue.invokeAndWait(()->{
            if(kind.equals("Hessian"))result.getCanvas().zoomOut(0,0);
            result.updateAndDraw();
            result.getWindow().validate();
            result.getCanvas().repaint();
            Graphics graphics=result.getCanvas().getGraphics();
            if(graphics!=null){result.getCanvas().paint(graphics);graphics.dispose();}
        });
        robot.delay(1200);
        if(kind.equals("Laplacian"))capture(result.getWindow(),prefix+"_result");
        else lastCaptureMethod="TIFF-only; result capture omitted";
        log.printf("%s,%s,%s,%s,%d,32,%s;%s,AWT-control-events,%s%n",
                   kind,input,scale,integration,results.size(),dialogMethod,lastCaptureMethod,Instant.now().toString());
        log.flush();
    }
    public static void main(String[] args) throws Exception {
        Properties props=new Properties();
        try(Reader reader=Files.newBufferedReader(Paths.get(args[0]),StandardCharsets.UTF_8)){props.load(reader);}
        Path repo=Paths.get(props.getProperty("repo"));
        python=props.getProperty("python");
        nativeCapture=props.getProperty("native_capture");
        captures=Paths.get(props.getProperty("captures"));
        Files.createDirectories(captures);
        Path app=repo.resolve("experiments/gui_evidence/ij_app");
        Files.createDirectories(app.resolve("plugins"));
        progress=repo.resolve("experiments/gui_evidence/gui_progress.txt");
        Files.write(progress,new byte[0]);
        new java.util.Timer(true).schedule(new java.util.TimerTask(){
            public void run(){System.err.println("GUI capture watchdog timeout");System.exit(3);}
        },60000);
        System.setProperty("user.home",app.toString());
        System.setProperty("plugins.dir",app.toString());
        int exit=0;
        try {
            robot=new Robot();
            ImageJ imagej=new ImageJ();
            imagej.setLocation(30,30);
            robot.delay(1000);
            capture(imagej,"gui_00_imagej_toolbar");
            try(PrintWriter writer=new PrintWriter(Files.newBufferedWriter(
                    repo.resolve("experiments/gui_evidence/gui_capture_log.csv"),StandardCharsets.UTF_8))){
                log=writer;
                log.println("command,image,scale,integration,outputs,bit_depth,capture_method,interaction,timestamp_utc");
                runCase(repo,"bsds_01","Derivatives","01",props.getProperty("sigma"),"");
                runCase(repo,"drive_01","Hessian","02",props.getProperty("sigma"),"");
                runCase(repo,"blob_01","Laplacian","03",props.getProperty("sigma"),"");
                runCase(repo,"bsds_01","Structure","04",props.getProperty("sd"),props.getProperty("si"));
            }
            System.out.println("GUI evidence captured from real ImageJ/FeatureJ windows.");
        }catch(Throwable error){
            error.printStackTrace();
            exit=1;
        }finally{
            EventQueue.invokeLater(()->{for(Window w:Window.getWindows())w.dispose();});
        }
        System.exit(exit);
    }
}
