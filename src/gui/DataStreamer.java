package gui;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.util.concurrent.CopyOnWriteArraySet;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

import org.java_websocket.server.WebSocketServer;
import org.java_websocket.WebSocket;
import org.java_websocket.handshake.ClientHandshake;

import com.google.gson.JsonObject;


public class DataStreamer extends WebSocketServer {
    private Configs config;
    private TagData tagData;

    private static final int PORT = 8080; // Port for the WebSocket
    private static final CopyOnWriteArraySet<WebSocket> clients = new CopyOnWriteArraySet<>();

    public DataStreamer(TagData tagData) {
        super(new InetSocketAddress(PORT));
        this.tagData = tagData;
        this.config = Configs.getCfgInstance();
    }

    @Override
    public void onStart() {
        System.out.println("WebSocket server started on port: " + PORT);
    }

    @Override
    public void onOpen(WebSocket conn, ClientHandshake handshake) {
        clients.add(conn);
        System.out.println("New connection: " + conn.getRemoteSocketAddress());
        
        // Create a JSON object to send sensor names
        JsonObject sensorNames = new JsonObject();
        sensorNames.addProperty("sensorNames", config.getAllSensorNames().toString());
        conn.send(sensorNames.toString());
    }

    @Override
    public void onClose(WebSocket conn, int code, String reason, boolean remote) {
        clients.remove(conn);
        System.out.println("Connection closed: " + conn.getRemoteSocketAddress());
    }

    @Override
    public void onMessage(WebSocket conn, String message) {
        System.out.println("Received message: " + message);

        // if (message.toLowerCase().equals(config.getSensorDef())) {
        //     // Pass
        //     config.setAutoSelect(false);
        //     System.out.println("Sensor set to: " + config.getSensorDef());
        // }
        if (message.toLowerCase().equals("auto")) {
            config.setAutoSelect(true);
            System.out.println("Sensor set to auto");
        }
        else {
            config.setAutoSelect(false);
            config.setSensorDef(message);
            System.out.println("Sensor set to: " + config.getSensorDef());
        }

    }

    @Override
    public void onError(WebSocket conn, Exception ex) {
        ex.printStackTrace();
    }

    public void broadcastData(String data) {
        for (WebSocket client : clients) {
            client.send(data);
        }
    }

    public static void main(String[] args) throws IOException {
        TagData tagData = new TagData();
        Configs config = Configs.getCfgInstance();
        AntennaReader antennaReader = new AntennaReader(tagData);
        new Thread(antennaReader::startReading).start();

        DataStreamer server = new DataStreamer(tagData);
        server.start();

        new Thread(() -> {
            try {
                while (true) {
                    long currentTimeMillis = System.currentTimeMillis();
                    SimpleDateFormat sdf = new SimpleDateFormat("HH:mm:ss yy/MM/dd");
                    String formattedDate = sdf.format(new Date(currentTimeMillis));

                    // System.out.println("Sensor: " + config.getSensorDef());
                    // System.out.println("AutoSet: " + config.getAutoSelect());

                    double avgPhaseDiff = tagData.calculateAvgPhaseDifference();
                    // double avgPhaseDiff = Math.random() * 100; // Simulated value for testing
                    JsonObject data = new JsonObject();
                    System.out.println("phase: " + avgPhaseDiff + "°");
                    if (avgPhaseDiff <= 0) {
                        data.addProperty("avgPhaseDiff", String.format("Error"));
                    }
                    else {
                        if ("soil".equals(config.getSensorDef())) {
                            Integer sat = 15;
                            Integer dry = 70;
                            if (avgPhaseDiff < sat) {
                                data.addProperty("avgPhaseDiff", String.format("100") + "%");
                            }
                            else if (avgPhaseDiff < dry) {
                                data.addProperty("avgPhaseDiff", String.format("%.0f", 100 - ((100.0 / (dry - sat)) * (avgPhaseDiff - sat))) + "%");
                            }
                            else {
                                data.addProperty("avgPhaseDiff", String.format("0") + "%");
                            }
                        }
                        else if ("force".equals(config.getSensorDef())) {
                            Integer min = 30;
                            Integer max = 5;
                            if (avgPhaseDiff > min) {
                                data.addProperty("avgPhaseDiff", String.format("0") + "%");
                            }
                            else if (avgPhaseDiff > max) {
                                data.addProperty("avgPhaseDiff", String.format("%.0f", 100 - ((100 / (min - max)) * (avgPhaseDiff - max))) + "%");
                            }
                            else {
                                data.addProperty("avgPhaseDiff", String.format("100" ) + "%");
                            }
                        }
                        else if ("forcesticker".equals(config.getSensorDef())) {
                            Integer min = 40;
                            Integer max = 10;
                            if (avgPhaseDiff > min) {
                                data.addProperty("avgPhaseDiff", String.format("Off"));
                            }
                            else if (avgPhaseDiff < max) {
                                data.addProperty("avgPhaseDiff", String.format("On"));
                            }
                        }
                        else if ("photo".equals(config.getSensorDef())) {
                            Integer min = 25;
                            Integer max = 35;
                            if (avgPhaseDiff < min) {
                                data.addProperty("avgPhaseDiff", String.format("0") + "%");
                            }
                            else if (avgPhaseDiff < max) {
                                data.addProperty("avgPhaseDiff", String.format("%.0f", 100 - ((100 / (max - min)) * (avgPhaseDiff - min))) + "%");
                            }
                            else {
                                data.addProperty("avgPhaseDiff", String.format("100" ) + "%");
                            }
                        }
                        else {
                            data.addProperty("avgPhaseDiff", String.format("%.0f", avgPhaseDiff) + "°");
                        }
                    }

                        
                    
                    // Create a JSON object to send structured data
                    data.addProperty("timestamp", formattedDate);
                    data.addProperty("sensor", config.getSensorDef());
                    
                    if (avgPhaseDiff > 0) {
                        server.broadcastData(data.toString());
                    }
                    Thread.sleep(1000); // Send data every second
                }
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }).start();
    }

}
