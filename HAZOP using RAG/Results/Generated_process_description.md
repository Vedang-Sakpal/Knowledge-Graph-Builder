This analysis synthesizes information from the provided Cypher script (P&ID data) and the Markdown process description to detail the material flow, equipment functions, and control/energy aspects of the sour water stripper plant.

## 1. Main Material Streams

The sour water stripper plant efficiently processes a refinery sour water stream, progressively separating hydrocarbons, dissolved gases, and ultimately yielding treated water.

*   **Sour Water Feed from Refinery**:
    *   The raw **Sour water** (liquid, containing water, HC-OIL, hydrogen sulfide, and ammonia) enters the system from the **REFINERY Unit (101)**.
    *   It first flows via "SW from refinery pipe" into **Surge Drum-1 (56)**.
*   **Hydrocarbon (Slop Oil) Separation in Surge Drum**:
    *   In **Surge Drum-1**, density differences cause **HC-OIL** (slop oil) to separate and form a lighter layer on top.
    *   This slop oil is drawn off by the **Oil Recovery Pump (61)**, passes through **NRV-3 (72)**, and is sent via "Slop pipe 2" to **SLOP-OIL-CRUDE-TANK-WWT (105)** for recovery/disposal. This flow is controlled by `LLC` (Low Level Controller) acting on the `Oil Recovery Pump`, which indicates it's likely skimmed off when the oil layer reaches a certain thickness (or the water level drops to a low setpoint, indicating a significant oil layer above it that needs to be removed).
    *   A "vent pipe" also connects the Surge Drum-1 to **TO-FLARE-SYSTEM (103)** for pressure relief.
    *   A "drain pipe" with a **Drain Valve (82)** leads to **DRAIN-TO-SEWER (102)** for manual draining.
*   **Sour Water to Storage**:
    *   The heavier water phase from **Surge Drum-1** is pumped by the **SW Feed Pump (62)**, through **NRV-4 (73)** and **FCV-2 (77)** (controlled by `HLC` from Surge Drum), into the **SW Storage (57)** tank.
    *   In **SW Storage**, any residual **HC-OIL** can be further skimmed ("HC oil skim") and sent to **TO-SKIM-RECYCLE (106)**.
    *   A **PRV-1 (83)** protects the tank, venting to **TO-ATM (104)**.
*   **Preheating and Stripper Feed**:
    *   From **SW Storage**, the sour water is pumped by the **Stripper feed Pump (63)**, through **NRV-5 (74)**, **Flow sensor 1 (89)**, and **FCV-3 (78)**.
    *   It then enters the **Stripper OVHD Condenser (59)** as "SW feed pipe 3" where it is preheated by the hot overhead vapor from the stripper.
    *   The preheated sour water then enters the **Sour Water Stripper (58)** via "SW feed pipe 4".
*   **Steam Stripping**:
    *   **Steam** from **STEAM-IN (109)** is introduced into the **Sour Water Stripper (58)** through **FCV-5 (80)** (controlled by `FC-2`).
    *   Inside the stripper, the steam strips out dissolved **Hydrogen sulfide vapour** and **Ammonia vapour** from the sour water.
    *   A **PRV-2 (84)** on the stripper provides safety relief.
*   **Overhead Condensation and Separation**:
    *   The overhead vapor mixture from the **Sour Water Stripper (58)** ("SWS Overhead pipe"), consisting of steam, H₂S, and NH₃, flows to the **Stripper OVHD Condenser (59)**. Here, the steam and some H₂S/NH₃ condense (while preheating the incoming sour water).
    *   The condensed liquid and remaining non-condensable vapors (H₂S, NH₃) flow to the **SWS OVHD Accumulator (60)**.
    *   From the accumulator, the condensed liquid (primarily water) is pumped by the **Reflux Pump (64)**, through **NRV-6 (75)** and **FCV-4 (79)** (controlled by `LC-1`), and sent back to the **Sour Water Stripper (58)** as reflux ("Reflux pipe 4").
    *   The non-condensable **Hydrogen sulfide vapour** and **Ammonia vapour** exit the accumulator via "Acid gas pipe" to **ACID-GAS-TO-S-PLANT-EX (107)** for further treatment (e.g., Sulfur Recovery Unit).
*   **Treated Water Effluent**:
    *   The stripped water (now largely free of H₂S, NH₃, and HC-OIL) collects at the bottom of the **Sour Water Stripper (58)**.
    *   This treated water is pumped by the **Bottoms Pump (65)**, through **NRV-7 (76)** and **FCV-6 (81)** (controlled by `LC-2`), and finally sent via "Water pipe 4" to **WATER-TREATMENT (108)** for further processing or safe disposal.

## 2. Key Equipment and Purpose

| Equipment Name                 | Type                  | Purpose                                                                                                                                                                                                                                                                                                         |
| :----------------------------- | :-------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Surge Drum-1 (56)**          | Separator             | Primary separation of the incoming sour water feed. Its main function is to allow **HC-OIL** (slop oil) to separate from the water phase by gravity, with the oil skimming off the top and water drawn from the bottom. It also acts as a buffer tank for feed flow.                                         |
| **SW Storage (57)**            | Storage Tank          | Provides a buffer volume for the sour water before it enters the stripper. It also facilitates further gravity separation and skimming of any residual **HC-OIL** carried over from the surge drum, ensuring a cleaner feed to the stripper.                                                               |
| **Sour Water Stripper (58)**   | Column                | The core separation unit. Steam is introduced to strip out volatile dissolved gases, specifically **Hydrogen sulfide vapour** and **Ammonia vapour**, from the sour water, purifying the water phase.                                                                                                |
| **Stripper OVHD Condenser (59)** | Heat Exchanger        | Condenses the hot overhead vapor from the stripper (steam, H₂S, NH₃). Crucially, this condensation simultaneously serves to preheat the incoming sour water feed to the stripper, optimizing energy efficiency in a common integrated heat recovery design.                                          |
| **SWS OVHD Accumulator (60)**  | Reflux Drum/Separator | Receives the partially condensed stream from the condenser. It separates the condensed liquid (mostly water) from the remaining non-condensable **Hydrogen sulfide vapour** and **Ammonia vapour**. The condensed liquid can then be refluxed, and acid gases routed for further treatment. |
| **Oil Recovery Pump (61)**     | Pump                  | Transfers the separated **HC-OIL** (slop oil) from Surge Drum-1 to external oil recovery/disposal systems.                                                                                                                                                                                               |
| **SW Feed Pump (62)**          | Pump                  | Moves the sour water from Surge Drum-1 to the SW Storage tank.                                                                                                                                                                                                                                          |
| **Stripper feed Pump (63)**    | Pump                  | Supplies sour water from the SW Storage tank to the stripper system, through the preheater.                                                                                                                                                                                                             |
| **Reflux Pump (64)**           | Pump                  | Pumps the condensed liquid from the SWS OVHD Accumulator back to the Sour Water Stripper as reflux, which helps improve separation efficiency in the column.                                                                                                                                         |
| **Bottoms Pump (65)**          | Pump                  | Discharges the treated, stripped water from the bottom of the Sour Water Stripper to the downstream water treatment facility.                                                                                                                                                                          |
| **Valves (NRV-3 to NRV-7)**    | Non-Return Valves     | Prevent backflow in pump discharge lines, ensuring unidirectional flow.                                                                                                                                                                                                                               |
| **Valves (FCV-2 to FCV-6)**    | Flow Control Valves   | Act as final control elements in various flow control loops to regulate process streams (e.g., sour water feed, steam, reflux, treated water outflow).                                                                                                                                               |
| **Valves (PRV-1, PRV-2)**      | Pressure Relief Valves| Safety devices designed to open and relieve excess pressure in the SW Storage tank and Sour Water Stripper, respectively, protecting equipment from overpressure.                                                                                                                                   |
| **Drain Valve (82)**           | Manual Drain Valve    | Allows for manual draining of Surge Drum-1, typically for maintenance or cleaning.                                                                                                                                                                                                                      |

## 3. Detail the Control and Energy Flows

The plant employs several control loops to maintain stable operation, product quality, and safety. Energy is primarily supplied by steam and recovered internally.

### Energy Flows:

*   **Main Energy Input**: **Steam** from **STEAM-IN (109)** is introduced directly into the **Sour Water Stripper (58)** via "Steam pipe 2" to provide the heat and stripping vapor required to remove H₂S and NH₃.
*   **Internal Energy Recovery**: The hot overhead vapor from the **Sour Water Stripper (58)** is directed to the **Stripper OVHD Condenser (59)**. Here, its sensible and latent heat is used to **preheat** the incoming cold sour water feed, significantly reducing the overall energy demand of the process. This is a crucial energy efficiency measure.
*   **Pump Work**: Electrical energy is consumed by all pumps (Oil Recovery, SW Feed, Stripper feed, Reflux, Bottoms) to move fluids against pressure gradients.
*   **Heat Loss**: Heat is inevitably lost to the surroundings from equipment surfaces and piping.

### Control Flows (Control Loops):

The control system primarily focuses on level control in tanks and columns, and flow control for feed and stripping medium.

1.  **Surge Drum-1 Low Level Control (Slop Oil Removal)**:
    *   **Sensor**: **Level sensor 1 (85)** (Low Level Sensor on Surge Drum-1).
    *   **Controller**: **LLC (95)** (Low Level Controller on Surge Drum-1).
    *   **Final Control Element**: **Oil Recovery Pump (61)**.
    *   **Function**: This loop controls the removal of **HC-OIL** (slop oil) from the surge drum. When the liquid level in the drum drops to a low setpoint (indicating a significant layer of oil has accumulated and the water level is low), the LLC likely activates or deactivates the pump to control the rate of oil withdrawal, aiming to maintain the interface or remove the oil layer.

2.  **Surge Drum-1 High Level Control (Sour Water Outflow)**:
    *   **Sensor**: **Level sensor 2 (86)** (High Level Sensor on Surge Drum-1).
    *   **Controller**: **HLC (96)** (High Level Controller on Surge Drum-1).
    *   **Final Control Element**: **FCV-2 (77)** (Flow Control Valve on "Sw to storage pipe" to SW Storage).
    *   **Function**: Manages the flow of sour water out of the surge drum to the SW Storage tank. If the level in Surge Drum-1 rises too high, the HLC opens FCV-2 more to increase outflow, preventing overflow.

3.  **Sour Water Stripper Feed Flow Control**:
    *   **Sensor**: **Flow sensor 1 (89)** (Flow Sensor on Sour Water Feed).
    *   **Controller**: **FC-1 (98)** (Flow Controller for SW feed pipe).
    *   **Final Control Element**: **FCV-3 (78)** (Flow Control Valve on "SW feed pipe 3" to Stripper OVHD Condenser).
    *   **Function**: Maintains a steady flow rate of preheated sour water into the Sour Water Stripper, which is crucial for stable column operation and consistent stripping.

4.  **Steam Flow Control (Ratio/Feed-forward)**:
    *   **Sensor**: Implied measurement from **FC-1 (98)** (Sour Water Feed Flow Controller).
    *   **Controller**: **FC-2 (97)** (Flow Controller for steam pipe). `FC-1` (SW feed flow) sends a signal to `FC-2`.
    *   **Final Control Element**: **FCV-5 (80)** (Flow Control Valve on "Steam pipe 1" to Sour Water Stripper).
    *   **Function**: This appears to be a feed-forward or ratio control scheme. The flow rate of incoming sour water (measured by `Flow sensor 1` and controlled by `FC-1`) dictates the setpoint for the steam flow controller (`FC-2`). This ensures the correct steam-to-feed ratio is maintained, optimizing stripping efficiency while preventing excessive steam consumption.

5.  **SWS OVHD Accumulator Level Control (Reflux Flow)**:
    *   **Sensor**: **Level sensor 3 (87)** (Level Sensor on SWS OVHD Accumulator).
    *   **Controller**: **LC-1 (99)** (Level Controller for SWS OVHD Accumulator).
    *   **Final Control Element**: **FCV-4 (79)** (Flow Control Valve on "Reflux pipe 3" to Sour Water Stripper).
    *   **Function**: Controls the rate of reflux (condensed water) returned to the stripper to maintain a stable liquid level in the accumulator. If the level rises, LC-1 opens FCV-4 more to send more reflux back.

6.  **Sour Water Stripper Bottoms Level Control (Treated Water Outflow)**:
    *   **Sensor**: **Level sensor 4 (88)** (Level Sensor on Sour Water Stripper).
    *   **Controller**: **LC-2 (100)** (Level Controller for Sour Water Stripper).
    *   **Final Control Element**: **FCV-6 (81)** (Flow Control Valve on "Water pipe 3" from Bottoms Pump).
    *   **Function**: Controls the outflow rate of treated water from the stripper bottom to maintain a stable liquid level within the column. This prevents the reboiler (if present, though not explicitly mentioned as separate equipment) from running dry and ensures sufficient residence time for stripping.

### Pressure Monitoring:

*   **Pressure sensors (90-94)** are connected to all pumps (Oil Recovery, SW Feed, Stripper feed, Reflux, Bottoms Pumps). These provide essential operational data for monitoring pump performance, detecting blockages, or indicating pump failure. While not directly linked to a valve for control in the provided data, they would typically feed into a Distributed Control System (DCS) for alarming, interlocks (e.g., pump trip on low discharge pressure), and operator information.

### Safety Devices:

*   **PRV-1 (83)**: On SW Storage tank, vents to **TO-ATM (104)** to prevent overpressure.
*   **PRV-2 (84)**: On Sour Water Stripper, vents to flare **TO-FLARE-SYSTEM (103)** to prevent overpressure, handling potentially flammable acid gases.

## 4. Summarize Inputs and Outputs

### Main Chemical Inputs to the Process:

*   **Sour water**: The primary feed stream from the **REFINERY Unit (101)**. It is a liquid containing water, **HC-OIL**, **Hydrogen sulfide vapour**, and **Ammonia vapour**.
*   **Steam**: Provided from **STEAM-IN (109)**. This is the main utility input, serving as both a heat source and the stripping agent in the Sour Water Stripper.

### Final Products or Waste Streams Leaving the System:

*   **HC-OIL (Slop Oil)**: Separated from the sour water. It exits to:
    *   **SLOP-OIL-CRUDE-TANK-WWT (105)** from Surge Drum-1.
    *   **TO-SKIM-RECYCLE (106)** from SW Storage.
*   **Hydrogen sulfide vapour**: A hazardous and corrosive acid gas separated from the sour water. It exits the SWS OVHD Accumulator to **ACID-GAS-TO-S-PLANT-EX (107)**, typically for a sulfur recovery unit.
*   **Ammonia vapour**: A toxic and corrosive acid gas separated from the sour water. It exits the SWS OVHD Accumulator to **ACID-GAS-TO-S-PLANT-EX (107)**, typically alongside H₂S.
*   **Water (Treated)**: The stripped water, significantly cleaner, exits the Sour Water Stripper to **WATER-TREATMENT (108)** for further purification or disposal.
*   **Vent Streams (Safety/Relief)**:
    *   Vent from Surge Drum-1 to **TO-FLARE-SYSTEM (103)**.
    *   Vent from SW Storage (via PRV-1) to **TO-ATM (104)**.
    *   Vent from Sour Water Stripper (via PRV-2) to **TO-FLARE-SYSTEM (103)**.
*   **Drain Stream**: Manual drain from Surge Drum-1 via **Drain Valve (82)** to **DRAIN-TO-SEWER (102)**.