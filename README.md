# ZenseTag
* Contains the source code for ZenseTag, an independent platform for real-time batteryless, wireless sensing
* Work can be referred to at: [ZenseTag](https://dl.acm.org/doi/10.1145/3666025.3699342)

## How to Compile and Run the Java Programs
**Ensure Java dependencies are available**
**Make sure that the current working directory is the repo parent and the right branch is selected** 
   ```bash
   zensetag (dev) > pwd
   \home\Project\zensetag
   ```
   ```
   zensetag (dev) > java --version
   java 22.0.2 2024-07-16
   Java(TM) SE Runtime Environment (build 22.0.2+9-70)
   Java HotSpot(TM) 64-Bit Server VM (build 22.0.2+9-70, mixed mode, sharing)
   ```
* For Data Logging:

  **Windows**
  ```
  javac -cp "./lib/fastdtw.jar;./lib/octane.jar;./lib/jfreechart.jar;./lib/flatlaf.jar;./lib/websocket.jar;./lib/sl4j.jar" src/gui/*.java
  java -cp "./lib/fastdtw.jar;./lib/octane.jar;./lib/jfreechart.jar;./lib/flatlaf.jar;./lib/websocket.jar;./lib/sl4j.jar;src" gui.DataCollection
  ```
  **Linux**
  ```
  javac -cp "./lib/fastdtw.jar:./lib/octane.jar:./lib/jfreechart.jar:./lib/flatlaf.jar:./lib/websocket.jar:./lib/sl4j.jar" src/gui/*.java
  java -cp "./lib/fastdtw.jar:./lib/octane.jar:./lib/jfreechart.jar:./lib/flatlaf.jar:./lib/websocket.jar:./lib/sl4j.jar:src" gui.DataCollection
  ```

* For GUI:

  **Windows**
   ```
   javac -cp "./lib/fastdtw.jar;./lib/octane.jar;./lib/jfreechart.jar;./lib/flatlaf.jar;./lib/websocket.jar;./lib/sl4j.jar" src/gui/*.java
   java -cp "./lib/fastdtw.jar;./lib/octane.jar;./lib/jfreechart.jar;./lib/flatlaf.jar;./lib/websocket.jar;./lib/sl4j.jar;src" gui.RealTimeGui
   ```
  **Linux**
   ```
   javac -cp "./lib/fastdtw.jar:./lib/octane.jar:./lib/jfreechart.jar:./lib/flatlaf.jar:./lib/websocket.jar:./lib/sl4j.jar" src/gui/*.java
   java -cp "./lib/fastdtw.jar:./lib/octane.jar:./lib/jfreechart.jar:./lib/flatlaf.jar:./lib/websocket.jar:./lib/sl4j.jar:src" gui.RealTimeGui
   ```
   
* For AR App:

  **Windows**
   ```
   javac -cp "./lib/fastdtw.jar;./lib/octane.jar;./lib/jfreechart.jar;./lib/flatlaf.jar;./lib/websocket.jar;./lib/sl4j.jar" src/gui/*.java
   java -cp "./lib/fastdtw.jar;./lib/octane.jar;./lib/jfreechart.jar;./lib/flatlaf.jar;./lib/websocket.jar;./lib/sl4j.jar;src" gui.DataStreamer
   ```
  **Linux**
   ```
   javac -cp "./lib/fastdtw.jar:./lib/octane.jar:./lib/jfreechart.jar:./lib/flatlaf.jar:./lib/websocket.jar:./lib/sl4j.jar" src/gui/*.java
   java -cp "./lib/fastdtw.jar:./lib/octane.jar:./lib/jfreechart.jar:./lib/flatlaf.jar:./lib/websocket.jar:./lib/sl4j.jar:src" gui.DataStreamer
   ```



## **Data Collection**

  This module collects sequential RFID tag data independently of the GUI, computes rolling phase-difference statistics during capture, and writes three JSON artifacts per run (sequential reads, EPC-grouped raw data, and phase-difference series).

  ### What it does
  - Spawns a **reader thread** (`antennaReader.startReading`) to stream tag reads.
  - Spawns a **processing thread** that calls `tagData.calculateAvgPhaseDifference()` every ~10 ms for the requested duration.
  - Converts collected timestamps to **relative ms (t=0 at experiment start)** before saving.
  - Writes out:
    - **Sequential reads**: `..._seq.json` (array of reads as seen by the reader)
    - **Aggregated raw**: `..._raw.json` (grouped by `epc`: timestamps, phases, rssi, channels)
    - **Phase differences**: `..._phases.json` (time-series list)

  ### Output locations & naming
  Base path (from config):  
  `config.getLocalParentPath(config.getRepoName())`

  Subfolders:
  - Sequential reads: `data/json/tags/`
  - Aggregated raw: `data/json/raw/`
  - Phase series: `data/json/phases/`

  File name format (per run): <fname><timeArg><YYYYMMDD_HHMMSS>_<suffix>.json
   where:
   - `<fname>` comes from CLI (or `config.getSensorDef()` if omitted)
   - `<timeArg>` is the duration string you pass (e.g., `10s`, `2m`)
   - `<suffix>` ∈ `{ seq | raw | phases }`

   **Examples**
   - `mob_c2a_10s_20250905_125331_seq.json`
   - `mob_c2a_10s_20250905_125331_raw.json`
   - `mob_c2a_10s_20250905_125331_phases.json`

   ### CLI usage
   Windows
    ```
    javac -cp "./lib/fastdtw.jar;./lib/octane.jar;./lib/jfreechart.jar;./lib/flatlaf.jar;./lib/websocket.jar;./lib/sl4j.jar" src/gui/*.java
    java -cp "./lib/fastdtw.jar;./lib/octane.jar;./lib/jfreechart.jar;./lib/flatlaf.jar;./lib/websocket.jar;./lib/sl4j.jar;src" gui.DataCollection
    ```
   Linux
    ```
    javac -cp "./lib/fastdtw.jar:./lib/octane.jar:./lib/jfreechart.jar:./lib/flatlaf.jar:./lib/websocket.jar:./lib/sl4j.jar" src/gui/*.java
    java -cp "./lib/fastdtw.jar:./lib/octane.jar:./lib/jfreechart.jar:./lib/flatlaf.jar:./lib/websocket.jar:./lib/sl4j.jar:src" gui.DataCollection
    ```

   - `<time>` supports:
   - Seconds: `10s` or `10`
   - Minutes: `5m`
   - Hours:   `2h`
   - Days:    `1d`
   - `<fname>`: experiment name prefix (e.g., `mob_c2a`, `paciforce`)

   **Examples**
   ```bash
   # Collect for 10 seconds, name prefix "mob_c2a"
   java -cp build/libs/app.jar gui.DataCollection 10s mob_c2a

   # Collect for 2 minutes, name prefix "paciforce"
   java -cp build/libs/app.jar gui.DataCollection 2m paciforce

   # Collect for 30 seconds (no 's' provided) and default fname from config
   java -cp build/libs/app.jar gui.DataCollection 30
   ```
   ### Data Collection Structure
   **Sequential Tag Data**
   ```
   [
      { "epc": "ADDA...", "rssi": -47.0, "phase": 193.0, "channel": 918.25, "timestamp": 0.0 },
      { "epc": "ADDA...", "rssi": -48.0, "phase": 175.8, "channel": 918.25, "timestamp": 98.0 }
   ]
   ```
   **Raw Data**
   ```
   {
      "ADDA...": {
         "timestamps": [0.0, 98.0, 391.0],
         "rssis": [-47.0, -48.0, -48.0],
         "channels": [918.25, 918.25, 918.25],
         "phases": [193.0, 175.8, 175.8]
      }
   }
   ```
# RFID Data Visualization and Analysis Module

This Python module provides functions to analyze and visualize sequential RFID tag data collected during experiments. It supports phase and RSSI comparisons, Dynamic Time Warping (DTW) alignment, moving-average analysis, and channel-wise breakdowns.  

The code is designed to work with data saved in JSON format (`*_raw.json`, `*_phases.json`, `*_seq.json`) generated by the data collection pipeline.

---

## Features

- **Phase cleaning and normalization**  
  Normalizes phase values into a consistent 0–180° range.

- **Dynamic Time Warping (DTW)**  
  Aligns tag phase sequences to account for differences in read rates.

- **Channel-wise analysis**  
  - Phase and RSSI breakdown for each frequency channel.  
  - Channel-wise DTW-based phase difference visualization.

- **Real-time phase difference simulation**  
  - Plots phase difference time-series at experiment rate.  
  - Supports flexible experiment durations.

- **Moving average analysis**  
  - Time-based sliding window for phase difference.  
  - Handles variable sampling rates between tags.  

- **Combined view**  
  - Overlaid plots of phases and RSSIs across tags.  
  - Basic statistics summary (duration, phase range, average RSSI).

---

## File Structure and Requirements

- Input data is expected under the `DATA/json/` directory:
  - `DATA/json/raw/` → aggregated EPC data (`*_raw.json`)
  - `DATA/json/phases/` → sequential phase differences (`*_phases.json`)
  - `DATA/json/tags/` → sequential reads (`*_seq.json`)

- Each JSON file corresponds to one experiment run:
  - `<experiment>_<duration>_<YYYYMMDD>_<HHMMSS>_raw.json`
  - `<experiment>_<duration>_<YYYYMMDD>_<HHMMSS>_phases.json`
  - `<experiment>_<duration>_<YYYYMMDD>_<HHMMSS>_seq.json`

- Dependencies:
  - `numpy`
  - `matplotlib`
  - `fastdtw`
  - `json`
  - Project-specific configs (`lib.params.DATA`, `SENSOR_CONFIGS`, `SENSOR_DEF`, `read_rate`)

---

## Usage

### Command-line Execution

```bash
python analyze.py <base_file_name> <start_index> <end_index>
