package gui;

import com.dtw.FastDTW;
import com.timeseries.TimeSeries;
import com.util.DistanceFunction;
import com.util.EuclideanDistance;
import com.dtw.WarpPath;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import java.io.FileWriter;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.stream.Collectors;

import org.jfree.data.json.impl.JSONArray;

public class TagData {

    private final List<Map<String, Object>> tagRecords;
    private final int bufferSize;
    private final int windowSize;
    private Configs config;
    
    private Set<String> epcs;
    private Map<String, Object> sensorConfig;

    private List<Double> phaseDifferences = new ArrayList<>();
    private List<Double> rssiDifferences = new ArrayList<>();
    
    // // Non-parameterized constructor (uses default sensorDef from configs)
    // public TagData() {
    //     this(new Configs().getSensorDef());  // Get default sensor from the config and call the parameterized constructor
    // }

    public TagData() {
        this.config = Configs.getCfgInstance();
        
        this.bufferSize = config.getMaxTagHistory();
        
        // Load EPCs from the configuration based on the sensor definition
        refreshSensorConfigs();
        System.out.println(config.getSensorDef() + " with epcs to capture:" + epcs);

        // Load the window size from the config and calculate windowSize = sensor.window * read_rate
        double window = (Double) sensorConfig.get("window");  // Read `window` from the config
        int readRate = config.getReadRate(); // Fetch the read rate from config
        this.windowSize = (int) (window * readRate);  // Calculate windowSize = window * read_rate
        
        this.tagRecords = Collections.synchronizedList(new ArrayList<>());
    }

    // Method to refresh both sensorConfig and EPCs from the configuration
    private void refreshSensorConfigs() {
        String sensorDef = config.getSensorDef();  // Get current sensor definition
        this.sensorConfig = config.getSensorConfig(sensorDef);  // Refresh sensor configuration
        List<String> epcList = (List<String>) sensorConfig.get("epcs");  // Get updated EPC list
        this.epcs = new HashSet<>(epcList);  // Update the EPC set
    }

    // Add a tag to the records
    public void addTag(String epc, String timestamp, double channel, double phase, double rssi) {
        
        Map<String, Object> tagRecord = new HashMap<>();
        tagRecord.put("epc", epc);
        tagRecord.put("timestamp", timestamp);  // String timestamp
        tagRecord.put("channel", channel);
        tagRecord.put("phase", phase);
        tagRecord.put("rssi", rssi);
        this.tagRecords.add(tagRecord);

        // Check if tagRecords exceeds the buffer size, and clear/remove records if necessary
        if (tagRecords.size() > bufferSize) {
            // Clear the oldest record(s) or trim the list to fit the buffer size
            this.tagRecords.remove(0); // Removes the oldest entry (FIFO)
        }
    }

    // Helper method to convert double[] to TimeSeries
    private TimeSeries createTimeSeries(double[] sequence) {
        return new TimeSeries(sequence);
    }

    // Performs dynamic time warping (DTW) matching between two sequences
    private double[][] dtwMatching(double[] sequence1, double[] sequence2) {
        DistanceFunction distFunc = new EuclideanDistance();
        WarpPath warpPath = FastDTW.getWarpPathBetween(createTimeSeries(sequence1), createTimeSeries(sequence2), windowSize, distFunc);

        double[] warpedSeq1 = new double[warpPath.size()];
        double[] warpedSeq2 = new double[warpPath.size()];

        for (int i = 0; i < warpPath.size(); i++) {
            warpedSeq1[i] = sequence1[warpPath.get(i).getCol()];
            warpedSeq2[i] = sequence2[warpPath.get(i).getRow()];
        }

        return new double[][]{warpedSeq1, warpedSeq2};
    }

    // Calculate the average phase difference across all channels using FastDTW and phase matching
    public double calculateAvgPhaseDifference() {
        // Ensure there are enough records to calculate
        if (this.tagRecords.size() < 2) {
            return -1000;
        }

        // Get the last windowSize tag records, or all records if fewer are available
        try {
            List<Map<String, Object>> tagRecordsSubset;
            if (this.tagRecords.size() <= windowSize) {
                tagRecordsSubset = new ArrayList<>(this.tagRecords);
            } else {
                tagRecordsSubset = tagRecords.subList(this.tagRecords.size() - windowSize, this.tagRecords.size());
            }
            // EPC selection
            Iterator<String> epcIterator = epcs.iterator();
            if (epcs.size() < 2) {
                throw new IllegalArgumentException("At least two EPCs are required to calculate phase differences.");
            }
        
            String epc1 = epcIterator.next();
            String epc2 = epcIterator.next();
        
            Map<Double, List<Double>> phasesByChannelEpc1 = new HashMap<>();
            Map<Double, List<Double>> phasesByChannelEpc2 = new HashMap<>();
        
            // Group phases by channels for both EPCs
            for (Map<String, Object> tagRecord : tagRecordsSubset) {
                double channel = (Double) tagRecord.get("channel");
                double phase = (Double) tagRecord.get("phase");
        
                if (epc1.equals(tagRecord.get("epc"))) {
                    phasesByChannelEpc1.computeIfAbsent(channel, k -> new ArrayList<>()).add(phase);
                }
                if (epc2.equals(tagRecord.get("epc"))) {
                    phasesByChannelEpc2.computeIfAbsent(channel, k -> new ArrayList<>()).add(phase);
                }
            }
        
            double totalPhaseDiff = 0.0;
            int totalMatches = 0;
        
            // Iterate over all channels present in both EPCs
            for (double channel : phasesByChannelEpc1.keySet()) {
                if (phasesByChannelEpc2.containsKey(channel)) {
                    List<Double> phaseList1 = phasesByChannelEpc1.get(channel);
                    List<Double> phaseList2 = phasesByChannelEpc2.get(channel);
        
                    // Convert phase lists to arrays
                    double[] phases1 = phaseList1.stream().mapToDouble(Double::doubleValue).toArray();
                    double[] phases2 = phaseList2.stream().mapToDouble(Double::doubleValue).toArray();

                    boolean isDtw = config.isDtw();
                    double[] warpedSeq1 = new double[0];
                    double[] warpedSeq2 = new double[0];
                    // Perform DTW matching between the two phase sequences
                    if (isDtw) {
                        double[][] warpedPhases = dtwMatching(phases1, phases2);
                        warpedSeq1 = warpedPhases[0];
                        warpedSeq2 = warpedPhases[1];
                    }
                    else {
                        int targetLength = Math.min(phases1.length, phases2.length);
                        warpedSeq1 = Arrays.copyOf(phases1, targetLength);
                        warpedSeq2 = Arrays.copyOf(phases2, targetLength);
                    }
        
                    // Calculate phase differences after alignment
                    for (int i = 0; i < warpedSeq1.length; i++) {
                        double diff = Math.abs(warpedSeq1[i] - warpedSeq2[i]);
                        // if (diff > 270) {
                        //     diff = Math.abs(diff - 360);
                        // } else if (diff > 135) {
                        //     diff = Math.abs(diff - 180);
                        // }
                        totalPhaseDiff += phaseNormalization(diff);
                        totalMatches++;
                    }
                }
            }
        
            // Return the average phase difference across all channels
            Double avgPhaseDiff = totalMatches > 0 ? totalPhaseDiff / totalMatches : 0;
            phaseDifferences.add(avgPhaseDiff);

            return avgPhaseDiff;
        } catch (Exception e) {
            // Do nothing
            return -1000;
        }
    }

    // Clear all stored tag records
    public void clearData() {
        this.tagRecords.clear();
    }

    // Get all tag records
    public List<Map<String, Object>> getAllTags() {
        return this.tagRecords;
    }

    private static double phaseNormalization(double phaseDeg) {
        double phaseNorm = phaseDeg % 180.0;

        // If phiNorm is negative (e.g., -5 % 180 in Java is -5), add 180 to bring it into [0, 180).
        if (phaseDeg < 0) {
            phaseNorm += 180.0;
        }
        return Math.min(phaseNorm, 180.0 - phaseNorm);
    }

    // =================================================================================
    // == CHANNEL-AWARE METHOD FOR INTERPOLATION-BASED PHASE DIFFERENCE CALCULATION   ==
    // =================================================================================

    /**
     * A private record to temporarily hold strongly-typed tag data for interpolation.
     * Includes channel information, which is critical for correct processing.
     */
    private record InterpolationRecord(String epc, long timestamp, double phase, double channel) {}

    /**
     * Reconstructs the continuous phase signal from wrapped phase data (0-360 degrees).
     * This must be performed on a list of records from a SINGLE tag on a SINGLE channel.
     *
     * @param records A list of records for a single tag on a single channel, sorted by timestamp.
     * @return A new list of records with the phase values unwrapped.
     */
    private List<InterpolationRecord> unwrapPhase(List<InterpolationRecord> records) {
        if (records.isEmpty()) {
            return records;
        }
        List<InterpolationRecord> unwrappedRecords = new ArrayList<>();
        double phaseOffset = 0.0;
        double lastPhase = records.get(0).phase();
        unwrappedRecords.add(records.get(0));

        for (int i = 1; i < records.size(); i++) {
            InterpolationRecord current = records.get(i);
            double currentPhase = current.phase();
            double phaseDiff = currentPhase - lastPhase;

            if (phaseDiff > 180) {      // A jump down (e.g., from 350 to 10 degrees)
                phaseOffset -= 360.0;
            } else if (phaseDiff < -180) { // A jump up (e.g., from 10 to 350 degrees)
                phaseOffset += 360.0;
            }
            
            lastPhase = currentPhase;
            unwrappedRecords.add(new InterpolationRecord(
                current.epc(),
                current.timestamp(),
                currentPhase + phaseOffset,
                current.channel()
            ));
        }
        return unwrappedRecords;
    }

    /**
     * Calculates the channel-aware average phase difference using time-based linear interpolation.
     * This method first separates data by channel, then performs unwrapping and interpolation
     * independently for each channel before averaging the results. This is the most physically
     * accurate method for mobile, asynchronous sensing.
     *
     * @return The calculated average phase difference in degrees, or -1000.0 if calculation is impossible.
     */
    public double calculateInterpolatedAvgPhaseDifference() {
        // Step 1: Get the last 'windowSize' records for analysis
        List<Map<String, Object>> tagRecordsSubset;
        synchronized (this.tagRecords) {
            if (this.tagRecords.size() <= windowSize) {
                tagRecordsSubset = new ArrayList<>(this.tagRecords);
            } else {
                tagRecordsSubset = new ArrayList<>(this.tagRecords.subList(this.tagRecords.size() - windowSize, this.tagRecords.size()));
            }
        }
        
        if (tagRecordsSubset.size() < 4 || this.epcs.size() < 2) {
            return -1000.0;
        }

        Iterator<String> epcIterator = epcs.iterator();
        String epc1 = epcIterator.next();
        String epc2 = epcIterator.next();

        // Step 2: Group records by channel for each EPC
        Map<Double, List<InterpolationRecord>> channelMap1 = new HashMap<>();
        Map<Double, List<InterpolationRecord>> channelMap2 = new HashMap<>();

        for (Map<String, Object> record : tagRecordsSubset) {
            try {
                String epc = (String) record.get("epc");
                if (epc.equals(epc1) || epc.equals(epc2)) {
                    long timestamp = Long.parseLong((String) record.get("timestamp"));
                    double phase = (Double) record.get("phase");
                    double channel = (Double) record.get("channel");
                    InterpolationRecord ir = new InterpolationRecord(epc, timestamp, phase, channel);

                    if (epc.equals(epc1)) {
                        channelMap1.computeIfAbsent(channel, k -> new ArrayList<>()).add(ir);
                    } else {
                        channelMap2.computeIfAbsent(channel, k -> new ArrayList<>()).add(ir);
                    }
                }
            } catch (Exception e) {
                System.err.println("Skipping record in window due to parsing error: " + e.getMessage());
            }
        }

        List<Double> allDifferences = new ArrayList<>();

        // Step 3: Iterate over common channels and perform interpolation for each
        for (Double channel : channelMap1.keySet()) {
            if (channelMap2.containsKey(channel)) {
                List<InterpolationRecord> records1 = channelMap1.get(channel);
                List<InterpolationRecord> records2 = channelMap2.get(channel);

                // Need at least 2 points per tag on this specific channel to interpolate
                if (records1.size() < 2 || records2.size() < 2) {
                    continue; // Skip this channel, not enough data
                }

                // --- Perform per-channel processing ---
                records1.sort(Comparator.comparingLong(InterpolationRecord::timestamp));
                records2.sort(Comparator.comparingLong(InterpolationRecord::timestamp));

                List<InterpolationRecord> unwrappedRecords1 = unwrapPhase(records1);
                List<InterpolationRecord> unwrappedRecords2 = unwrapPhase(records2);
                
                List<InterpolationRecord> recordsA = unwrappedRecords1; // Reference tag
                List<InterpolationRecord> recordsB = unwrappedRecords2; // Tag to interpolate

                List<Double> differencesOnThisChannel = new ArrayList<>();
                int searchIndexForB = 0;

                for (InterpolationRecord recordA : recordsA) {
                    long timestampA = recordA.timestamp();

                    while (searchIndexForB < recordsB.size() && recordsB.get(searchIndexForB).timestamp() < timestampA) {
                        searchIndexForB++;
                    }

                    if (searchIndexForB == 0 || searchIndexForB >= recordsB.size()) continue;

                    InterpolationRecord beforeB = recordsB.get(searchIndexForB - 1);
                    InterpolationRecord afterB = recordsB.get(searchIndexForB);

                    long t_before = beforeB.timestamp();
                    double p_before = beforeB.phase();
                    long t_after = afterB.timestamp();
                    double p_after = afterB.phase();

                    if (t_after == t_before) continue;

                    double interpolatedPhaseB = p_before + (p_after - p_before) * ((double)(timestampA - t_before) / (double)(t_after - t_before));
                    double difference = recordA.phase() - interpolatedPhaseB;
                    differencesOnThisChannel.add(difference);
                }
                
                // Add all successfully calculated differences from this channel to the master list
                allDifferences.addAll(differencesOnThisChannel);
            }
        }

        // Step 4: Aggregate final result from all channel calculations
        if (allDifferences.isEmpty()) {
            return -1000.0; // No overlapping data found on any common channel
        }

        double avgDifference = allDifferences.stream()
                .mapToDouble(d -> d)
                .average()
                .orElse(-1000.0);
        
        // Add final result to the class-level list for logging
        phaseDifferences.add(phaseNormalization(avgDifference));

        return phaseNormalization(avgDifference);
    }

    // =================================================================================
    // == CHANNEL-AWARE METHOD FOR INTERPOLATION-BASED RSSI DIFFERENCE CALCULATION    ==
    // =================================================================================

    /**
     * A private record to temporarily hold strongly-typed tag data for interpolation.
     * Includes RSSI and channel information.
     */
    private record InterpolationRssiRecord(String epc, long timestamp, double rssi, double channel) {}

    /**
     * Calculates the channel-aware average RSSI difference using time-based linear interpolation.
     * This method separates data by channel and performs interpolation independently 
     * for each channel before averaging.
     *
     * @return The calculated average RSSI difference in dBm, or -1000.0 if calculation is impossible.
     */
    public double calculateInterpolatedAvgRssiDifference() {
        // Step 1: Get the last 'windowSize' records for analysis
        List<Map<String, Object>> tagRecordsSubset;
        synchronized (this.tagRecords) {
            if (this.tagRecords.size() <= windowSize) {
                tagRecordsSubset = new ArrayList<>(this.tagRecords);
            } else {
                tagRecordsSubset = new ArrayList<>(this.tagRecords.subList(this.tagRecords.size() - windowSize, this.tagRecords.size()));
            }
        }
        
        if (tagRecordsSubset.size() < 4 || this.epcs.size() < 2) {
            return -1000.0;
        }

        Iterator<String> epcIterator = epcs.iterator();
        String epc1 = epcIterator.next();
        String epc2 = epcIterator.next();

        // Step 2: Group records by channel for each EPC
        Map<Double, List<InterpolationRssiRecord>> channelMap1 = new HashMap<>();
        Map<Double, List<InterpolationRssiRecord>> channelMap2 = new HashMap<>();

        for (Map<String, Object> record : tagRecordsSubset) {
            try {
                String epc = (String) record.get("epc");
                if (epc.equals(epc1) || epc.equals(epc2)) {
                    long timestamp = Long.parseLong((String) record.get("timestamp"));
                    double rssi = (Double) record.get("rssi"); // Extract RSSI instead of phase
                    double channel = (Double) record.get("channel");
                    InterpolationRssiRecord ir = new InterpolationRssiRecord(epc, timestamp, rssi, channel);

                    if (epc.equals(epc1)) {
                        channelMap1.computeIfAbsent(channel, k -> new ArrayList<>()).add(ir);
                    } else {
                        channelMap2.computeIfAbsent(channel, k -> new ArrayList<>()).add(ir);
                    }
                }
            } catch (Exception e) {
                System.err.println("Skipping record in window due to parsing error: " + e.getMessage());
            }
        }

        List<Double> allDifferences = new ArrayList<>();

        // Step 3: Iterate over common channels and perform interpolation for each
        for (Double channel : channelMap1.keySet()) {
            if (channelMap2.containsKey(channel)) {
                List<InterpolationRssiRecord> records1 = channelMap1.get(channel);
                List<InterpolationRssiRecord> records2 = channelMap2.get(channel);

                // Need at least 2 points per tag on this specific channel to interpolate
                if (records1.size() < 2 || records2.size() < 2) {
                    continue; 
                }

                // Sort by timestamp
                records1.sort(Comparator.comparingLong(InterpolationRssiRecord::timestamp));
                records2.sort(Comparator.comparingLong(InterpolationRssiRecord::timestamp));

                // Note: No unwrapping needed for RSSI
                List<InterpolationRssiRecord> recordsA = records1; // Reference tag
                List<InterpolationRssiRecord> recordsB = records2; // Tag to interpolate

                List<Double> differencesOnThisChannel = new ArrayList<>();
                int searchIndexForB = 0;

                for (InterpolationRssiRecord recordA : recordsA) {
                    long timestampA = recordA.timestamp();

                    while (searchIndexForB < recordsB.size() && recordsB.get(searchIndexForB).timestamp() < timestampA) {
                        searchIndexForB++;
                    }

                    if (searchIndexForB == 0 || searchIndexForB >= recordsB.size()) continue;

                    InterpolationRssiRecord beforeB = recordsB.get(searchIndexForB - 1);
                    InterpolationRssiRecord afterB = recordsB.get(searchIndexForB);

                    long t_before = beforeB.timestamp();
                    double r_before = beforeB.rssi();
                    long t_after = afterB.timestamp();
                    double r_after = afterB.rssi();

                    if (t_after == t_before) continue;

                    // Linear interpolation of RSSI values
                    double interpolatedRssiB = r_before + (r_after - r_before) * ((double)(timestampA - t_before) / (double)(t_after - t_before));
                    double difference = recordA.rssi() - interpolatedRssiB;
                    differencesOnThisChannel.add(difference);
                }
                
                allDifferences.addAll(differencesOnThisChannel);
            }
        }

        // Step 4: Aggregate final result from all channel calculations
        if (allDifferences.isEmpty()) {
            return -1000.0;
        }

        double avgDifference = allDifferences.stream()
                .mapToDouble(d -> d)
                .average()
                .orElse(-1000.0);
        
        // Log to class-level list (assuming rssiDifferences list exists similar to phaseDifferences)
        this.rssiDifferences.add(avgDifference);

        return avgDifference;
    }

    public void logSequentialTagData(String fName) {
        try {
            // Get all tag records
            // System.out.println(this.getTagRecordsSize());
            List<Map<String, Object>> allTags = this.getAllTags();
            
            // Check if there's data to save
            if (allTags == null || allTags.isEmpty() || !config.getStoreData()) {
                if (!config.getStoreData()) {
                    System.out.println("Data storage is disabled in the configuration.");
                }
                else {
                    System.out.println("No tag data to save.");
                }
                return;
            }

            allTags = convertToRelativeTimestamps(allTags);
            
            // Create Gson instance with pretty printing
            Gson gson = new GsonBuilder()
                    .setPrettyPrinting()
                    .create();
            
            // Convert to JSON
            String json = gson.toJson(allTags);

            String timestamp = new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date());
            String filepath = config.getLocalParentPath(config.getRepoName()) + "/data/" + "json/" + "tags/";
            String filename = filepath + fName + "_" + timestamp + "_seq"  + ".json";

            System.out.println(filename);
            
            // Write to file
            try (FileWriter writer = new FileWriter(filename)) {
                writer.write(json);
                System.out.println("Tag data saved successfully to: " + filename);
                System.out.println("Total records saved: " + allTags.size());
            }
            catch (Exception e) {
                System.err.println("Could not save all tag data");
            }
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void saveAggregatedTagData(String fName) {
        try {
            // Get all tag records
            List<Map<String, Object>> allTags = this.getAllTags();
            
            // Check if there's data to save
            if (allTags == null || allTags.isEmpty() || !config.getStoreData()) {
                if (!config.getStoreData()) {
                    System.out.println("Data storage is disabled in the configuration.");
                }
                else {
                    System.out.println("No tag data to save.");
                }
                return;
            }

            allTags = convertToRelativeTimestamps(allTags);
            
            // Convert to grouped EPC format
            Map<String, Map<String, List<Object>>> groupedData = new HashMap<>();
            
            // Process each tag record
            for (Map<String, Object> tagRecord : allTags) {
                String epc = (String) tagRecord.get("epc");
                
                // Initialize EPC entry if it doesn't exist
                if (!groupedData.containsKey(epc)) {
                    Map<String, List<Object>> epcData = new HashMap<>();
                    epcData.put("timestamps", new ArrayList<>());
                    epcData.put("rssis", new ArrayList<>());
                    epcData.put("channels", new ArrayList<>());
                    epcData.put("phases", new ArrayList<>());
                    groupedData.put(epc, epcData);
                }
                
                // Get the EPC data and append values
                Map<String, List<Object>> epcData = groupedData.get(epc);
                epcData.get("timestamps").add(tagRecord.get("timestamp"));
                epcData.get("rssis").add(tagRecord.get("rssi"));
                epcData.get("channels").add(tagRecord.get("channel"));
                epcData.get("phases").add(tagRecord.get("phase"));
            }
            
            // Create Gson instance with pretty printing
            Gson gson = new GsonBuilder()
                    .setPrettyPrinting()
                    .create();
            
            // Convert to JSON
            String json = gson.toJson(groupedData);
            
            String timestamp = new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date());
            String filepath = config.getLocalParentPath(config.getRepoName()) + "/data/" + "json/" + "raw/";
            String filename = filepath + fName + "_" + timestamp + "_raw" + ".json";
            
            // Write to file
            try (FileWriter writer = new FileWriter(filename)) {
                writer.write(json);
                System.out.println("Aggregated tag data saved successfully to: " + filename);
                System.out.println("Total EPCs: " + groupedData.size());
                
                // Print summary of each EPC
                for (Map.Entry<String, Map<String, List<Object>>> entry : groupedData.entrySet()) {
                    String epc = entry.getKey();
                    int recordCount = entry.getValue().get("timestamps").size();
                    System.out.println("  EPC " + epc + ": " + recordCount + " records");
                }
            }
            catch (Exception e) {
                System.err.println("Could not save grouped tag data: " + e.getMessage());
            }
            
        } catch (Exception e) {
            System.err.println("Error processing tag data: " + e.getMessage());
            e.printStackTrace();
        }
    }

    public void savePhaseDifference(String fName) {
        try {
            if (this.phaseDifferences.size() > 0 && config.getStoreData()) {
                String timestamp = new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date());
                String filepath = config.getLocalParentPath(config.getRepoName()) + "/data/" + "/json/" + "phases/";
                String filename = filepath + fName + "_" + timestamp + "_phases" + ".json";

                // Create a JSON array from the phaseDifferences list
                JSONArray jsonArray = new JSONArray();
                jsonArray.addAll(this.phaseDifferences);
                
                // Write the JSON array to the file
                FileWriter file = new FileWriter(filename);
                file.write(jsonArray.toString());
                file.flush();
                file.close();
                System.out.println("Phase differences saved to " + filename);
            }
            else {
                if (!config.getStoreData()) {
                    System.out.println("Data storage is disabled in the configuration.");
                }
                else {
                    System.out.println("No tag data to save.");
                }
            }
        }
        catch (Exception e) {
            // Do nothing
            e.printStackTrace();
        }
    }

    // Get the last N tag records, or all records if fewer are available
    public List<Map<String, Object>> getLastNTags(int N) {
        List<Map<String, Object>> tagRecordsSubset;

        if (this.tagRecords.size() <= N) {
            tagRecordsSubset = new ArrayList<>(tagRecords);
        } else {
            tagRecordsSubset = this.tagRecords.subList(this.tagRecords.size() - N, this.tagRecords.size());
        }
        return tagRecordsSubset;
    }

    // Method to return the size of tagRecords
    public int getTagRecordsSize() {
        return this.tagRecords.size();
    }

    /**
     * Convert timestamps in tag records to relative milliseconds.
     * Finds the earliest timestamp across all records, subtracts it from all timestamps,
     * and converts from microseconds to milliseconds.
     * 
     * @param records List of tag records to convert
     * @return List of tag records with relative timestamps in milliseconds
     */
    private List<Map<String, Object>> convertToRelativeTimestamps(List<Map<String, Object>> records) {
        if (records.isEmpty()) {
            return records;
        }
        
        // Step 1: Find the earliest timestamp across all records
        long earliestTimestamp = Long.MAX_VALUE;
        for (Map<String, Object> record : records) {
            long timestamp = Long.parseLong((String) record.get("timestamp"));
            if (timestamp < earliestTimestamp) {
                earliestTimestamp = timestamp;
            }
        }
        
        // Step 2: Create new list with converted timestamps
        List<Map<String, Object>> convertedRecords = new ArrayList<>();
        for (Map<String, Object> record : records) {
            Map<String, Object> convertedRecord = new HashMap<>();
            
            // Copy all existing fields
            convertedRecord.put("epc", record.get("epc"));
            convertedRecord.put("phase", record.get("phase"));
            convertedRecord.put("rssi", record.get("rssi"));
            convertedRecord.put("channel", record.get("channel"));
            
            // Step 3: Convert timestamp to relative milliseconds
            long originalTimestamp = Long.parseLong((String) record.get("timestamp"));
            long relativeTimestampUs = originalTimestamp - earliestTimestamp;
            double relativeTimestampMs = relativeTimestampUs / 1000.0;
            
            // Store as double for precision
            convertedRecord.put("timestamp", relativeTimestampMs);
            
            convertedRecords.add(convertedRecord);
        }
        
        return convertedRecords;
    }
}
