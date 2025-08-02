
## Process Overview

The facility is designed to compress natural gas for storage and then deliver it during peak demand periods. The plant has a design capacity to compress **19.88 MMSCFD** of gas into storage cylinders. The storage phase typically lasts for a maximum of **20 hours** daily, followed by a decanting (delivery) phase of **4 to 5 hours**.

---

## Key Process Units and Equipment

Here is a breakdown of the main equipment, along with their design and operating parameters.

### 1. Inlet Scrubber (V-100)

* **Purpose:** To remove hydrocarbon liquids from the incoming gas stream to prevent them from carrying over into the downstream CNG plant.
* **Operation:** Liquid level is controlled by a control valve (LV-0101) that operates in an on/off mode.
* **Design Parameters:**
    * **Overpressure Protection:** Equipped with two pressure safety valves (PSV-0101A/B) with a set pressure of **34 barg**.

### 2. Station Inlet Metering (M-100 A/B)

* **Purpose:** To measure the total incoming natural gas to the plant.
* **Design Parameters:**
    * **Configuration:** 2x100% custody orifice meters.
    * **Capacity:** Designed for a total gas inlet of **19.88 MMSCFD**.
    * **Special Consideration:** The orifice is designed for wet gas conditions due to high moisture content in the inlet gas.

### 3. Dryer Unit (D-100 A/B)

* **Purpose:** To remove water and H₂S from the feed gas.
* **Operation:** The unit consists of two parallel trains (D-100A/B), with one in drying mode while the other is in regeneration mode. The regeneration cycle, which includes heating, cooling, and standby, lasts for 4-8 hours.
* **Performance Specifications:**
    * Achieves a moisture dew point of **-40°C**.
    * Reduces H₂S content to a maximum of **3 ppm**.
* **Operating Parameters:**
    * **Inlet Pressure:** 20.6–25 barg.
* **Auxiliary Equipment:**
    * **Pre-filters (F-100):** Installed upstream to prevent liquid carryover to the molecular sieves.
    * **After-filters (F-110):** Installed downstream to prevent solid particles from entering the compressors.

### 4. CNG Compressors (K-101 to K-110)

* **Purpose:** To compress the dry gas to the required storage pressure.
* **Configuration:** Ten reciprocating compressor trains, with nine operating in parallel and one on standby. They are three-stage compressors with inter-stage air coolers.
* **Operating Parameters:**
    * **Suction Pressure:** 20.6–25 barg.
    * **Suction Temperature:** 26.7–51.7 °C.
    * **Discharge Pressure:** 250 barg.
    * **Discharge Temperature (Max):** 48°C.
    * **Individual Capacity:** 2.3 MMSCFD per compressor.

### 5. CNG Cooler (E-100)

* **Purpose:** To cool the compressed gas before it enters the storage cylinders, which optimizes storage capacity.
* **Operation:** During the storage period, the cooler reduces the gas temperature. During the decanting period, the cooler is bypassed.
* **Operating Parameters:**
    * **Gas Inlet Temperature:** 48°C.
    * **Gas Outlet Temperature:** 35°C.
    * **Cooling Water Inlet Temperature:** 30°C.
    * **Cooling Water Outlet Temperature:** 39°C.

### 6. CNG Storage Cylinders (V-200)

* **Purpose:** To store the high-pressure CNG.
* **Configuration:** The system consists of **95 compartments**, with each compartment containing **8 tube cylinders**. Each cylinder has a capacity of **2.38 m³**.
* **Safety:** Each cylinder is protected by a pressure relief device (PSV) that vents directly to the atmosphere.

### 7. CNG Heat Exchanger (E-200)

* **Purpose:** To reheat the CNG during the decanting phase after pressure is reduced, counteracting the Joule-Thompson cooling effect.
* **Operation:** This unit operates only during the decanting stage.
* **Operating Parameters:**
    * **Gas Inlet Temperature (Initial):** -38°C.
    * **Gas Outlet Temperature:** 30°C.
    * **Heating Media:** Hot water at **90°C**.
    * **Max Duty:** 4100 kW.

### 8. Pressure Reducing System (PV-0501 A/B)

* **Purpose:** To reduce the pressure of the CNG from the storage cylinders for delivery to the customer (PLN).
* **Configuration:** Two control valves (one operating, one standby) are used to control the outlet pressure.
* **Operating Parameters:**
    * **Outlet Pressure:** Maintained at **28 barg**.
    * **Outlet Temperature:** Maintained at **30°C**.

### 9. Station Outlet Metering (M-200 A/B)

* **Purpose:** To measure the natural gas being sent out from the plant during the decanting period.
* **Configuration:** 2x100% custody meters with a crossover.
* **Capacity:** Designed for a total gas outlet of **113 MMSCFD over 4 hours**.

### 10. Waste Heat Recovery Unit (WHRU) (E-300)

* **Purpose:** To utilize exhaust heat from the compressor gas engines to heat water, which is then used as the heating medium in the CNG Heat Exchanger (E-200).
* **Operation:** The WHRU heats water from a storage tank (T-200).
* **Operating Parameters:**
    * **Hot Water Temperature Increase:** From 63°C to **90°C**.
    * **Circulation Pump (P-500 A/B) Capacity (Storage Phase):** 45 m³/hr.
    * **Circulation Pump (P-300 A/B) Capacity (Decanting Phase):** 140 m³/hr.