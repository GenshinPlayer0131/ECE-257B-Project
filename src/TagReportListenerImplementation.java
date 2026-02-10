import com.impinj.octane.Tag;
import com.impinj.octane.TagReport;
import com.impinj.octane.ImpinjReader;
import com.impinj.octane.TagReportListener;

import java.io.OutputStream;
import java.io.PrintWriter;

public class TagReportListenerImplementation implements TagReportListener {
    
    // private CallbackInterface callback;
    private PrintWriter writer;

    public TagReportListenerImplementation(OutputStream outputStream) {
        this.writer = new PrintWriter(outputStream, true);  // Auto-flush is enabled
    }

    @Override
    public void onTagReported(ImpinjReader reader, TagReport report) {
        for (Tag tag : report.getTags()) {
            String epc = tag.getEpc().toString();
            String timestamp = tag.getLastSeenTime().toString();
            int readCount = tag.getTagSeenCount();
            double phase = tag.getPhaseAngleInRadians();
            double channel = tag.getChannelInMhz();
            double rssi = tag.getPeakRssiInDbm();
            writer.println(epc + "," + timestamp + "," + channel + "," + phase + "," + rssi + "," + readCount);
        }
    }
}
