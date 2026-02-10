package gui;

import com.google.gson.JsonObject;

public class DataCollection {
    private static final double DEFAULT_TIME_TO_COLLECT = 30.0;
    private TagData tagData;
    private AntennaReader antennaReader;
    private Configs config;

    public DataCollection(TagData tagData, AntennaReader antennaReader) {
        this.tagData = tagData;
        this.antennaReader = antennaReader;
        this.config = Configs.getCfgInstance();
    }
    
    public static void main(String[] args) {
        TagData tagData = new TagData();
        AntennaReader antennaReader = new AntennaReader(tagData);
        Configs config = Configs.getCfgInstance();
        
        // Parse filename and time
        String fname;
        double collectionTimeInSeconds;
        String dataTimeString;

        config.setStoreData(true);
        
        try {
            if (args.length < 1) {
                System.out.println("Usage: java DataCollection <time> <filename>");
                System.out.println("Time format: 10s, 5m, 2h, 1d, or just 30 (defaults to seconds)");
            }
            
            try {
                fname = args[1];
            }
            catch (Exception e) {
                fname = config.getSensorDef();
            }
            
            try {
                String collectionTimeStr = args[0];
                dataTimeString = collectionTimeStr;
                
                if (collectionTimeStr.contains("s")) {
                    collectionTimeStr = collectionTimeStr.replace("s", "");
                    collectionTimeInSeconds = Double.parseDouble(collectionTimeStr);
                } else if (collectionTimeStr.contains("m")) {
                    collectionTimeStr = collectionTimeStr.replace("m", "");
                    collectionTimeInSeconds = Double.parseDouble(collectionTimeStr) * 60;
                } else if (collectionTimeStr.contains("h")) {
                    collectionTimeStr = collectionTimeStr.replace("h", "");
                    collectionTimeInSeconds = Double.parseDouble(collectionTimeStr) * 60 * 60;
                } else if (collectionTimeStr.contains("d")) {
                    collectionTimeStr = collectionTimeStr.replace("d", "");
                    collectionTimeInSeconds = Double.parseDouble(collectionTimeStr) * 60 * 60 * 24;
                } else {
                    collectionTimeInSeconds = Double.parseDouble(collectionTimeStr);
                    dataTimeString = collectionTimeStr + "s";
                }
            } catch (Exception e) {
                collectionTimeInSeconds = DEFAULT_TIME_TO_COLLECT;
                dataTimeString = String.valueOf((int)DEFAULT_TIME_TO_COLLECT) + "s";
            }
            
            // Build final filename
            fname = fname + "_" + dataTimeString;
            System.out.println("Experiment: " + fname);
            
        } catch (Exception e) {
            System.err.println("Error parsing arguments: " + e.getMessage());
            return;
        }
        
        DataCollection dataCollection = null;
        Thread readerThread = null;
        Thread processingThread = null;
        
        try {
            readerThread = new Thread(antennaReader::startReading);
            readerThread.start();
            
            dataCollection = new DataCollection(tagData, antennaReader);
            
            final double finalCollectionTime = collectionTimeInSeconds;
            
            processingThread = new Thread(() -> {
                long startTime = System.currentTimeMillis();
                long endTime = startTime + (long)(finalCollectionTime * 1000);
                
                System.out.println("Starting data collection for " + finalCollectionTime + " seconds...");
                
                while (System.currentTimeMillis() < endTime) {
                    // tagData.calculateAvgPhaseDifference();
                    tagData.calculateInterpolatedAvgPhaseDifference();
                    try {
                        Thread.sleep(10);
                    } catch (InterruptedException e) {
                        System.out.println("Processing interrupted");
                        break;
                    }
                }
                
                System.out.println("Data collection completed.");
            });
            
            processingThread.start();
            processingThread.join();
            
        } catch (Exception e) {
            System.err.println("Error during data collection: " + e.getMessage());
            e.printStackTrace();
        } finally {
            if (antennaReader != null) {
                antennaReader.stopReader();
            }
            
            if (tagData != null) {
                tagData.logSequentialTagData(fname);
                tagData.saveAggregatedTagData(fname);
                tagData.savePhaseDifference(fname);
            }
            
            System.out.println("Cleaning up...");
            if (processingThread != null && processingThread.isAlive()) {
                processingThread.interrupt();
            }

            System.out.println("Application finished.");
        }
        System.exit(0);
    }
}
