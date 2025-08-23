// To clear the database for a fresh start, you can run this line first:
// MATCH (n) DETACH DELETE n;

// =================================================================
// 1. CREATE NODES (Equipment, Instruments, Controllers, Boundaries)
//    - Based only on what is explicitly labeled in the P&ID.
// =================================================================

// -------- Equipment Nodes --------
CREATE (sg:Equipment {name: 'Surge Drum-1', type: 'Vessel'}),
       (sw:Equipment {name: 'SW Storage', type: 'Storage Tank'}),
       (sws:Equipment {name: 'Sour Water Stripper', type: 'Column'}),
       (stripper_cond:Equipment {name: 'Stripper OVHD Condenser', type: 'Heat Exchanger'}),
       (sws_acc:Equipment {name: 'SWS OVHD Accumulator', type: 'Vessel'}),
       (oil_rec_pump:Equipment {name: 'Oil Recovery Pump', type: 'Pump'}),
       (sw_feed_pump:Equipment {name: 'SW Feed Pump', type: 'Pump'}),
       (stripper_feed_pump:Equipment {name: 'Stripper feed Pump', type: 'Pump'}),
       (reflux_pump:Equipment {name: 'Reflux Pump', type: 'Pump'}),
       (bottoms_pump:Equipment {name: 'Bottoms Pump', type: 'Pump'});

// -------- Instrument Nodes (Valves) --------
CREATE (nrv3: Valve {name: 'NRV-3', type: 'Non-Return Valve'}),
       (nrv4: Valve {name: 'NRV-4', type: 'Non-Return Valve'}),
       (nrv5: Valve {name: 'NRV-5', type: 'Non-Return Valve'}),
       (nrv6: Valve {name: 'NRV-6', type: 'Non-Return Valve'}),
       (nrv7: Valve {name: 'NRV-7', type: 'Non-Return Valve'}),
       (fcv2: Valve {name: 'FCV-2', type: 'Flow Control Valve'}),
       (fcv3: Valve {name: 'FCV-3', type: 'Flow Control Valve'}),
       (fcv4: Valve {name: 'FCV-4', type: 'Flow Control Valve'}),
       (fcv5: Valve {name: 'FCV-5', type: 'Flow Control Valve'}),
       (fcv6: Valve {name: 'FCV-6', type: 'Flow Control Valve'}),
       (dv: Valve {name: 'Drain Valve', type: 'Manual drain Valve for Surge Drum-1'}),
       (prv1: Valve {name: 'PRV-1', type: 'Pressure Relief Valve on Sour water storage tank'}),
       (prv2: Valve {name: 'PRV-2', type: 'Pressure Relief Valve on Sour water stripper'});

CREATE (l1:Sensor {name: 'Level sensor 1', type: 'Low Level Sensor on Surge Drum-1'}),
       (l2:Sensor {name: 'Level sensor 2', type: 'High Level Sensor on Surge Drum-1'}),
       (l3:Sensor {name: 'Level sensor 3', type: 'Level Sensor on SWS OVHD Accumulator'}),
       (l4:Sensor {name: 'Level sensor 4', type: 'Level Sensor on Sour Water Stripper'}),
       (f1:Sensor {name: 'Flow sensor 1', type: 'Flow Sensor on Sour Water Feed'}),
       (p_oil_rec_pump:Sensor {name: 'Pressure sensor', type: 'Pump pressure Sensor on oil recovery pump'}),
       (p_sw_feed_pump:Sensor {name: 'Pressure sensor', type: 'Pump pressure Sensor on SW Feed Pump'}),
       (p_stripper_feed_pump:Sensor {name: 'Pressure sensor', type: 'Pump pressure Sensor on Stripper feed Pump'}),
       (p_reflux_pump:Sensor {name: 'Pressure sensor', type: 'Pump pressure Sensor on Reflux Pump'}),
       (p_bottoms_pump:Sensor {name: 'Pressure sensor', type: 'Pump pressure Sensor on Bottoms Pump'});

// -------- Controller Nodes --------
CREATE (llc:Controller {name: 'LLC', type: 'Low Level Controller on Surge Drum-1'}),
       (hlc:Controller {name: 'HLC', type: 'High Level Controller on Surge Drum-1'}),
       (fc2:Controller {name: 'FC-2', type: 'Flow Controller for steam pipe'}),
       (fc1:Controller {name: 'FC-1', type: 'Flow Controller for SW feed pipe'}),
       (lc1:Controller {name: 'LC-1', type: 'Level Controller for SWS OVHD Accumulator'}),
       (lc2:Controller {name: 'LC-2', type: 'Level Controller for Sour Water Stripper'});

// -------- Boundary Nodes (Inputs/Outputs) --------
CREATE (src1:Boundary {name: 'REFINERY Unit', type: 'Source'}),
       (s1:Boundary {name: 'DRAIN-TO-SEWER', type: 'Sink'}),
       (s2:Boundary {name: 'TO-FLARE-SYSTEM', type: 'Sink'}),
       (s3:Boundary {name: 'TO-ATM', type: 'Sink'}),
       (s4:Boundary {name: 'SLOP-OIL-CRUDE-TANK-WWT', type: 'Sink'}),
       (s5:Boundary {name: 'TO-SKIM-RECYCLE', type: 'Sink'}),
       (s6:Boundary {name: 'ACID-GAS-TO-S-PLANT-EX', type: 'Sink'}),
       (s7:Boundary {name: 'WATER-TREATMENT', type: 'Sink'}),
       (src2:Boundary {name: 'STEAM-IN', type: 'Source'});

// =================================================================
// 2. CREATE RELATIONSHIPS (Process Flow & Control Loops)
// =================================================================
// Create all FLOWS_TO relationships
CREATE (src1)-[: FLOWS_TO {name : "SW from refinery pipe"}]->(sg),
       (sg)-[: FLOWS_TO {name : "SW out pipe"}]->(sw_feed_pump),
       (sg)-[: FLOWS_TO {name : "vent pipe"}]->(s2),
       (sg)-[:FLOWS_TO {name: "Slop out pipe"}]->(oil_rec_pump),
       (sg)-[: FLOWS_TO {name: "drain pipe"}]->(dv),
       (dv)-[:FLOWS_TO {name: "drain to sewer"}]->(s1),

       (oil_rec_pump)-[: FLOWS_TO {name : "Slop pipe 1 "}]->(nrv3),
       (nrv3)-[: FLOWS_TO {name : 'Slop pipe 2 '}]->(s4),

       (sw_feed_pump)-[: FLOWS_TO {name : "SW feed pipe-1"}]->(nrv4),
       (nrv4)-[: FLOWS_TO {name : "SW feed pipe-2"}]->(fcv2),
       (fcv2)-[: FLOWS_TO {name : "Sw to storage pipe"}]->(sw),
       (sw)-[: FLOWS_TO {name : "vent pipe 2"}]->(prv1),
       (prv1)-[: FLOWS_TO {name : "vent to atm"}]->(s3),
       (sw)-[:FLOWS_TO {name : "HC oil skim "}]->(s5),
       (sw)-[:FLOWS_TO {name : "SW from storage pipe"}]->(stripper_feed_pump),
       (stripper_feed_pump)-[: FLOWS_TO {name : "SW feed pipe 1 "}]->(nrv5),
       (nrv5)-[: FLOWS_TO {name : "SW feed pipe 2 "}]->(f1),
       (f1)-[: FLOWS_TO {name : "SW feed pipe 2 "}]->(fcv3),
       (fcv3)-[: FLOWS_TO {name : "SW feed pipe 3 "}]->(stripper_cond),
       (stripper_cond)-[: FLOWS_TO {name : "SW feed pipe 4 "}]->(sws),
       (sws)-[: FLOWS_TO {name : " SWS Overhead pipe "}]->(stripper_cond),
       (stripper_cond)-[: FLOWS_TO {name : "Overhead Accumulator feed pipe "}]->(sws_acc),
       (sws_acc)-[: FLOWS_TO {name : "Acid gas pipe"}]->(s6),
       (sws_acc)-[: FLOWS_TO {name : "Reflux pipe 1"}]->(reflux_pump),
       (reflux_pump)-[: FLOWS_TO {name : "Reflux pipe 2"}]->(nrv6),
       (nrv6)-[: FLOWS_TO {name : "Reflux pipe 3"}]->(fcv4),
       (fcv4)-[: FLOWS_TO {name : "Reflux pipe 4"}]->(sws),
       (sws)-[: FLOWS_TO {name : "Water pipe 1 "}]->(bottoms_pump),
       (bottoms_pump)-[: FLOWS_TO {name : "Water pipe 2 "}]->(nrv7),
       (nrv7)-[: FLOWS_TO {name : "Water pipe 3 "}]->(fcv6),
       (fcv6)-[: FLOWS_TO {name : "Water pipe 4 "}]->(s7),
       (src2)-[: FLOWS_TO {name : "Steam pipe 1"}]->(fcv5),
       (fcv5)-[: FLOWS_TO {name : "Steam pipe 2"}]->(sws),
       (sws)-[: FLOWS_TO {name : "Pressure relief pipe"}]->(prv2);

// Create all control loops
CREATE (l1)-[: CONNECTED_TO {name : "Electrical connection"}]->(sg),
       (l1)-[: SEND_SIGNAL_TO {name : "Level Signal"}]->(llc),
       (llc)-[: CONTROLS {name : "Sends control signals to OIL recovery pump to control flow"}]->(oil_rec_pump),
       (l2)-[: CONNECTED_TO {name : "Electrical connection"}]->(sg),
       (l2)-[: SEND_SIGNAL_TO {name : "Level Signal"}]->(hlc),
       (hlc)-[: CONTROLS {name : "Sends control signals to Control Valve fcv2"}]->(fcv2),
       (f1)-[: SEND_SIGNAL_TO {name : "Flow Signal"}]->(fc1),
       (fc1)-[: CONTROLS {name : "Sends control signals to Control Valve fcv3"}]->(fcv3),
       (fc1)-[: SEND_SIGNAL_TO {name : "Flow Signal to Flow controller 2 for steam pipeline"}]->(fc2),
       (fc2)-[: CONTROLS {name : "Sends control signals to Control Valve fcv5"}]->(fcv5),
       (l3)-[: CONNECTED_TO {name : "Electrical connection"}]->(sws_acc),
       (l3)-[: SEND_SIGNAL_TO {name : "Level Signal"}]->(lc1),
       (lc1)-[: CONTROLS {name : "Sends control signals to Control Valve fcv4"}]->(fcv4),
       (l4)-[: CONNECTED_TO {name : "Electrical connection"}]->(sws),
       (l4)-[: SEND_SIGNAL_TO {name : "Level Signal"}]->(lc2),
       (lc2)-[: CONTROLS {name : "Sends control signals to Control Valve fcv6"}]->(fcv6),
       (p_oil_rec_pump)-[: CONNECTED_TO {name : "Electrical connection for pressure indicator"}]->(oil_rec_pump),
       (p_sw_feed_pump)-[: CONNECTED_TO {name : "Electrical connection for pressure indicator"}]->(sw_feed_pump),
       (p_stripper_feed_pump)-[: CONNECTED_TO {name : "Electrical connection for pressure indicator"}]->(stripper_feed_pump),
       (p_reflux_pump)-[: CONNECTED_TO {name : "Electrical connection for pressure indicator"}]->(reflux_pump),
       (p_bottoms_pump)-[: CONNECTED_TO {name : "Electrical connection for pressure indicator"}]->(bottoms_pump);
