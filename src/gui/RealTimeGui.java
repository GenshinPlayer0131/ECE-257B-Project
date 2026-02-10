package gui;

import java.awt.*;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;
import java.util.Timer;
import java.util.TimerTask;
import javax.swing.*;

import com.formdev.flatlaf.FlatDarkLaf;
import org.jfree.chart.ChartFactory;
import org.jfree.chart.ChartPanel;
import org.jfree.chart.JFreeChart;
import org.jfree.chart.plot.XYPlot;
import org.jfree.chart.renderer.xy.XYLineAndShapeRenderer;
import org.jfree.data.xy.XYSeries;
import org.jfree.data.xy.XYSeriesCollection;

public class RealTimeGui extends JFrame {

    private TagData tagData;
    private Configs config;
    private AntennaReader antennaReader;

    private XYSeries series;
    private JFreeChart chart;
    private Timer timer;
    private int visualXLength = 200;
    private int xData = 0;
    private int yRange = 120; 
    private JPanel buttonPanel;

    public RealTimeGui(TagData tagData, AntennaReader antennaReader) {
        this.config = Configs.getCfgInstance();
        this.tagData = tagData;
        this.antennaReader = antennaReader;

        this.series = new XYSeries("");

        XYSeriesCollection dataset = new XYSeriesCollection(series);
        this.chart = ChartFactory.createXYLineChart(
                "ZenseTag: Real-Time Sensing Platform", 
                "Time",                       
                "Sensory Change",      
                dataset
        );

        XYPlot plot = chart.getXYPlot();
        plot.getRangeAxis().setRange(0, yRange);
        
        plot.setBackgroundPaint(new Color(48, 48, 48));
        plot.setDomainGridlinePaint(new Color(128, 128, 128));
        plot.setRangeGridlinePaint(new Color(128, 128, 128));

        XYLineAndShapeRenderer renderer = new XYLineAndShapeRenderer();
        renderer.setSeriesPaint(0, Color.WHITE);
        // Remove the square shapes denoting the points
        renderer.setSeriesShapesVisible(0, false);
        // Set a thicker line
        float lineThickness = 5.0f;  // Adjust this value to change the line thickness
        renderer.setSeriesStroke(0, new BasicStroke(lineThickness));

        plot.setRenderer(renderer);

        setTitle("ZenseTag: Universal Multi-Modal Sensing Platform");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLayout(new BorderLayout());

        ChartPanel chartPanel = new ChartPanel(chart);
        chartPanel.setBackground(new Color(38, 50, 56));
        add(chartPanel, BorderLayout.CENTER);

        JLabel avgLabel = new JLabel("\u03C6: N/A");
        avgLabel.setForeground(new Color(176, 190, 197));
        avgLabel.setHorizontalAlignment(SwingConstants.CENTER);
        avgLabel.setFont(new Font("Segoe UI", Font.PLAIN, 16));
        add(avgLabel, BorderLayout.SOUTH);

        // Create and add the button panel
        createButtonPanel();
        add(buttonPanel, BorderLayout.NORTH);

        setSize(1366, 768);
        setVisible(true);

        // Add a WindowListener to save data when the GUI is closed
        addWindowListener(new WindowAdapter() {
            @Override
            public void windowClosing(WindowEvent e) {
                antennaReader.stopReader();
                stop();  // Stop the timer as well
                tagData.savePhaseDifference(config.getSensorDef());
                tagData.logSequentialTagData(config.getSensorDef());
                tagData.saveAggregatedTagData(config.getSensorDef());
                System.out.println("Resources released.");
                System.exit(0);
            }
        });

        this.timer = new Timer();
        timer.scheduleAtFixedRate(new TimerTask() {
            @Override
            public void run() {
                updatePlot(avgLabel);
            }
        }, 100, 20);
    }

    private void createButtonPanel() {
        buttonPanel = new JPanel();
        buttonPanel.setLayout(new FlowLayout());
        buttonPanel.setBackground(new Color(38, 50, 56));

        List<String> sensorNames = config.getAllSensorNames();
        for (String sensorName : sensorNames) {
            JButton button = new JButton(toTitleCase(sensorName));
            button.setForeground(Color.WHITE);
            button.setBackground(new Color(0, 150, 136));
            button.setFocusPainted(false);
            button.setBorderPainted(false);
            button.addActionListener(e -> switchSensor(sensorName));
            buttonPanel.add(button);
        }
    }

    private void switchSensor(String sensorName) {
        if ("auto".equalsIgnoreCase(sensorName)) {
            config.setAutoSelect(true);
            refreshXYPlot(true);
            return;
        }
        config.setAutoSelect(false);
        config.setSensorDef(sensorName);
        refreshXYPlot(true);
    }
    
    private void refreshXYPlot(Boolean reset) {
        this.yRange = (int) config.getSensorConfig(config.getSensorDef()).get("y_range");
        XYPlot plot = chart.getXYPlot();
        plot.getRangeAxis().setRange(-20, yRange);
        if (reset) {
            series.clear();
            xData = 0;
        }
    }
    
    private String toTitleCase(String input) {
        if (input == null || input.isEmpty()) {
            return input;
        }
        return input.substring(0, 1).toUpperCase() + input.substring(1).toLowerCase();
    }
    
    private void updatePlot(JLabel avgLabel) {
        // Calculate the average phase difference
        // double avgDiff = tagData.calculateAvgPhaseDifference();
        double avgDiff = tagData.calculateInterpolatedAvgPhaseDifference();
        
        // Calculate the average RSSI difference
        // double avgDiff = tagData.calculateInterpolatedAvgRssiDifference();

        if (avgDiff > -1000) {
            xData++;
            series.add(xData, avgDiff);
            if (series.getItemCount() > visualXLength) {
                series.remove(0);
            }
            avgLabel.setText(String.format("Sensor: " + toTitleCase(config.getSensorDef()) + " || \u03BC: %.2f", avgDiff));
        }
        try {
            refreshXYPlot(false);
        } 
        catch (Exception e) {}
    }

    public void stop() {
        if (timer != null) {
            timer.cancel();
        }
    }

    public static void main(String[] args) {
        FlatDarkLaf.setup();
        SwingUtilities.invokeLater(() -> {
            TagData tagData = new TagData();
            AntennaReader antennaReader = new AntennaReader(tagData);
            new Thread(antennaReader::startReading).start();
            try {
                Thread.sleep(2500);
                new RealTimeGui(tagData, antennaReader);
            } catch (Exception e) {
                // Do nothing
            }
        });
    }
}
