Here is the detailed analysis of the material and energy/control flow.

***

### Comprehensive Process Analysis: Sour Water Stripper Plant

This analysis integrates the specific equipment and control logic from the P&ID data with the operational context provided in the process description.

---

### 1. Main Material Streams

The plant processes four primary material streams: the main sour water feed, the recovered slop oil, the overhead acid gas, and the final treated water.

**a) Sour Water Feed Stream:**

1.  **Source:** Sour water originates from the `REFINERY Unit`.
2.  **Initial Separation:** It first enters the **Surge Drum-1** (`sg`), a three-phase separator. Here, due to density differences, free hydrocarbons (slop oil) separate and form a top layer.
3.  **Intermediate Storage:** The water phase is pumped by the **SW Feed Pump** through control valve `FCV-2` into the **SW Storage** tank. This tank provides buffer capacity and allows for any remaining trace hydrocarbons to be skimmed off (`TO-SKIM-RECYCLE`).
4.  **Preheating:** From storage, the **Stripper feed Pump** sends the sour water through the **Stripper OVHD Condenser**. This is a critical energy integration step: the cold incoming feed is preheated by the hot overhead vapors leaving the stripper column, improving thermal efficiency.
5.  **Stripper Entry:** The preheated sour water then enters the top section of the **Sour Water Stripper** (`sws`) to begin the stripping process.   

**b) Recovered Oil (Slop) Stream:**

1.  **Origin:** The separated hydrocarbon layer (HC-OIL) in **Surge Drum-1** is the source of this stream.
2.  **Removal:** The **Oil Recovery Pump** draws this slop oil from the top of the surge drum.
3.  **Destination:** The oil is pumped through a non-return valve (`NRV-3`) to its final sink: the `SLOP-OIL-CRUDE-TANK-WWT` for reprocessing or disposal.

**c) Overhead Acid Gas Stream:**

1.  **Origin:** Inside the **Sour Water Stripper**, steam strips volatile dissolved gases—primarily Hydrogen Sulfide (H₂S) and Ammonia (NH₃)—from the water. These gases, along with the stripping steam, exit from the top of the column.
2.  **Condensation:** The hot vapor mixture flows to the **Stripper OVHD Condenser**, where the steam and some water vapor are condensed back into a liquid by exchanging heat with the incoming cold sour water feed.
3.  **Separation:** The resulting two-phase mixture enters the **SWS OVHD Accumulator**. Here, the non-condensable acid gases (H₂S and NH₃) are separated from the condensed water (condensate).
4.  **Destination:** The acid gases exit the top of the accumulator and are sent to the `ACID-GAS-TO-S-PLANT-EX` (likely a Sulfur Recovery Unit) for further processing.

**d) Treated Water (Bottoms) Stream:**

1.  **Origin:** After the stripping process, the purified water collects at the bottom of the **Sour Water Stripper**.
2.  **Removal:** The **Bottoms Pump** draws the hot, treated water from the column sump.
3.  **Destination:** The water is pumped through non-return valve `NRV-7` and flow control valve `FCV-6` to the `WATER-TREATMENT` facility, its final sink.

---

### 2. Key Equipment and Purpose

| Equipment Name (from P&ID)       | Type                 | Purpose|
| -------------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Surge Drum-1**                 | Separator            | Acts as the initial feed receiver and performs the bulk separation of immiscible hydrocarbons (slop oil) from the sour water feed via gravity. It is equipped with level sensors to manage the oil/water interface and overall liquid level.                                   |
| **SW Storage**                   | Storage Tank         | Provides buffer capacity for the feed to the stripper, ensuring a stable flow. It also allows for secondary skimming of any residual hydrocarbons that may have carried over from the surge drum.                                                 |
| **Sour Water Stripper**          | Column               | The core of the process. It's a distillation column where direct steam injection provides the heat and stripping medium to remove dissolved H₂S and NH₃ from the sour water, purifying it.                                                      |
| **Stripper OVHD Condenser**      | Heat Exchanger       | Serves a dual purpose in an energy-efficient design: 1) It cools and partially condenses the overhead vapors from the stripper. 2) It simultaneously uses that heat to preheat the cold sour water feed before it enters the stripper, reducing the overall steam requirement. |
| **SWS OVHD Accumulator**         | Reflux Drum/Separator | Separates the condensed liquid (condensate) from the non-condensable acid gases after the overhead condenser. The liquid level is controlled to provide reflux back to the stripper, while the gases are sent downstream.                         |
| **Pumps** (5 total)                | Pump                 | Provide the motive force to transfer fluids between vessels and overcome system pressure drops. Each pump (Oil Recovery, SW Feed, Stripper Feed, Reflux, Bottoms) is dedicated to a specific liquid stream in the process.                     |

---

### 3. Detail the Control and Energy Flows

The process is managed by several key control loops. The primary energy input is low-pressure steam injected into the stripper.

**Energy Flow:**

*   **Steam Injection:** Steam is the primary energy source, injected directly into the base of the **Sour Water Stripper** (`sws`). Its flow is regulated by control valve `FCV-5`. The latent heat of the steam provides the energy required to heat the water and volatilize the dissolved acid gases.   

**Control Flows (Loops):**

*   **Surge Drum Level Control:**
    *   **Low-Level (Oil Interface):** A low-level sensor (`l1`) detects the oil-water interface. The **Low Level Controller (`LLC`)** starts/stops the **Oil Recovery Pump** to skim the oil layer and maintain the interface at the desired point.
    *   **High-Level (Water):** A high-level sensor (`l2`) prevents the drum from overflowing. The **High Level Controller (`HLC`)** manipulates control valve **`FCV-2`** on the outlet water line to increase flow to the SW Storage tank if the level gets too high.

*   **Stripper Feed and Steam Ratio Control (Cascade Loop):**
    *   This is a sophisticated control scheme to maintain stripping efficiency.
    *   **Primary Loop:** The flow of sour water feed to the stripper is measured by flow sensor **`f1`**. The **Flow Controller (`FC-1`)** adjusts control valve **`FCV-3`** to maintain the desired feed rate.
    *   **Cascade/Ratio Loop:** The output from `FC-1` (representing the actual sour water flow) is sent as a setpoint to the steam **Flow Controller (`FC-2`)**. `FC-2` then adjusts the steam control valve **`FCV-5`** to maintain a constant, pre-defined ratio of steam to sour water, ensuring optimal and efficient stripping regardless of feed rate changes.

*   **Stripper Bottoms Level Control:**
    *   A level sensor (`l4`) in the sump of the **Sour Water Stripper** measures the amount of treated water.
    *   The **Level Controller (`LC-2`)** modulates the **`FCV-6`** valve on the outlet of the **Bottoms Pump** to maintain a stable liquid level at the base of the column, preventing it from running dry or flooding.

*   **Overhead Accumulator Level Control (Reflux Control):**
    *   A level sensor (`l3`) in the **SWS OVHD Accumulator** measures the amount of condensed water.
    *   The **Level Controller (`LC-1`)** controls the reflux flow back to the stripper by adjusting control valve **`FCV-4`** on the **Reflux Pump** discharge. This ensures a liquid seal in the accumulator and controls the amount of cooled liquid returned to the top of the column to enhance separation.

---

### 4. Summarize Inputs and Outputs

**Process Inputs:**

*   **Sour Water:** (From `REFINERY Unit`) The main feed stream, containing water, dissolved H₂S and NH₃, and free hydrocarbons.
*   **Steam:** (From `STEAM-IN`) The energy and stripping medium used in the Sour Water Stripper column.

**Process Outputs (Products & Waste):**

*   **Acid Gas (H₂S & NH₃):** (To `ACID-GAS-TO-S-PLANT-EX`) The primary gaseous product, containing concentrated hydrogen sulfide and ammonia, sent for further processing (e.g., conversion to sulfur).
*   **Treated Water:** (To `WATER-TREATMENT`) The main liquid product, stripped of most of its contaminants and ready for reuse or final treatment.   
*   **Slop Oil (HC-OIL):** (To `SLOP-OIL-CRUDE-TANK-WWT`) Recovered hydrocarbons skimmed from the feed, sent to be reprocessed with crude oil or treated in the wastewater plant.
*   **Minor Streams:**
    *   **Skimmed Hydrocarbons:** (To `TO-SKIM-RECYCLE`) Small amounts of oil skimmed from the storage tank.
    *   **Vented Gases:** (To `TO-FLARE-SYSTEM` / `TO-ATM`) Vapors from surge drum and pressure relief from tanks are safely disposed of.
    *   **Drainage:** (To `DRAIN-TO-SEWER`) Liquid drainage from equipment during maintenance.
========================================================================