// Create Equipment nodes with properties
CREATE (sg:Equipment {name: 'Surge Drum-1' , type: 'Separator'})
CREATE (sw:Equipment {name: 'SW Storage' , type: 'Storage Tank'})
CREATE (sws:Equipment {name: 'Sour Water Stripper'  ,type: 'Column'}) 
CREATE (stripper_cond:Equipment {name: 'Stripper OVHD Condenser' , type: 'Heat Exchanger'})
CREATE (sws_acc:Equipment {name: 'SWS OVHD Accumulator'  ,type: 'Reflux Drum/Separator'})
CREATE (oil_rec_pump:Equipment {name: 'Oil Recovery Pump' , type: 'Pump'})
CREATE (sw_feed_pump:Equipment {name: 'SW Feed Pump' , type: 'Pump'})
CREATE (stripper_feed_pump:Equipment {name: 'Stripper feed Pump' , type: 'Pump'})
CREATE (reflux_pump:Equipment {name: 'Reflux Pump' , type: 'Pump'})
CREATE (bottoms_pump:Equipment {name: 'Bottoms Pump'  ,type: 'Pump'})

// Create Chemical nodes with properties from the HAZOPExpert analysis

// 1. Sour Water
CREATE (ch1:Chemical {
  name: 'Sour water',
  type: 'Main input Feed',
  material_type: 'raw-material',
  physical_state: 'liquid',
  corrosive_nature: 'not-corrosive',
  flammable_nature: 'not-flammable',
  volatile_nature: 'non-volatile',
  toxic_nature: 'non-toxic',
  viscous_nature: 'non-viscous',
  source: 'Refinery'
})

// 2. HC-OIL
CREATE (ch2:Chemical {
  name: 'HC-OIL',
  type: 'Removed side stream',
  material_type: 'impurity',
  physical_state: 'liquid',
  corrosive_nature: 'not-corrosive',
  flammable_nature: 'flammable',
  volatile_nature: 'volatile',
  toxic_nature: 'non-toxic',
  viscous_nature: 'viscous',
  sink: 'SLOP-OIL-CRUDE-TANK-WWT',
  source: 'Refinery'
})

// 3. Hydrogen Sulfide Vapour
CREATE (ch3:Chemical {
  name: 'Hydrogen sulfide vapour',
  type: 'separated from sour water as a outlet',
  material_type: 'product-impurity',
  physical_state: 'vapour',
  corrosive_nature: 'corrosive',
  flammable_nature: 'flammable',
  volatile_nature: 'non-volatile',
  toxic_nature: 'toxic',
  viscous_nature: 'non-viscous',
  sink: 'ACID-GAS-TO-S-PLANT-EX',
  source: 'Refinery'
})

// 4. Ammonia Vapour
CREATE (ch4:Chemical {
  name: 'Ammonia vapour',
  type: 'separated from sour water as a outlet',
  material_type: 'product-impurity',
  physical_state: 'vapour',
  corrosive_nature: 'corrosive',
  flammable_nature: 'flammable',
  volatile_nature: 'non-volatile',
  toxic_nature: 'toxic',
  viscous_nature: 'non-viscous',
  sink: 'ACID-GAS-TO-S-PLANT-EX',
  source: 'Refinery'
})

// 5. Water (properties assumed based on general knowledge)
CREATE (ch5:Chemical {
  name: 'Water',
  type: 'Separated from sour water as a outlet',
  physical_state: 'liquid',
  corrosive_nature: 'not-corrosive',
  flammable_nature: 'not-flammable',
  volatile_nature: 'volatile',
  toxic_nature: 'non-toxic',
  viscous_nature: 'non-viscous',
  sink: 'WATER-TREATMENT',
  source: 'Refinery'
})

// 6. Steam (properties assumed based on general knowledge)
CREATE (ch6:Chemical {
  name: 'Steam',
  type: 'Used for stripping sour water',
  physical_state: 'vapour',
  corrosive_nature: 'not-corrosive',
  flammable_nature: 'not-flammable',
  volatile_nature: 'volatile',
  toxic_nature: 'non-toxic',
  viscous_nature: 'non-viscous',
  source: 'Steam-In'
})

// Create Valve nodes with properties
CREATE (nrv3: Valve {name: 'NRV-3'  ,type: 'Non-Return Valve'})
CREATE (nrv4: Valve {name: 'NRV-4'  ,type: 'Non-Return Valve'})
CREATE (nrv5: Valve {name: 'NRV-5'  ,type: 'Non-Return Valve'}) 
CREATE (nrv6: Valve {name: 'NRV-6'  ,type: 'Non-Return Valve'}) 
CREATE (nrv7: Valve {name: 'NRV-7'  ,type: 'Non-Return Valve'}) 
CREATE (fcv2: Valve {name: 'FCV-2'  ,type: 'Flow Control Valve'}) 
CREATE (fcv3: Valve {name: 'FCV-3'  ,type: 'Flow Control Valve'}) 
CREATE (fcv4: Valve {name: 'FCV-4'  ,type: 'Flow Control Valve'}) 
CREATE (fcv5: Valve {name: 'FCV-5'  ,type: 'Flow Control Valve'}) 
CREATE (fcv6: Valve {name: 'FCV-6'  ,type: 'Flow Control Valve'}) 
CREATE (dv: Valve {name: 'Drain Valve'  ,type: 'Manual drain Valve for Surge Drum-1'}) 
CREATE (prv1: Valve {name: 'PRV-1'  ,type: 'Pressure Relief Valve on Sour water storage tank'}) 
CREATE (prv2: Valve {name: 'PRV-2'  ,type: 'Pressure Relief Valve on Sour water stripper'})

// Create Sensor nodes with properties
CREATE (l1:Sensor {name: 'Level sensor 1'  ,type: 'Low Level Sensor on Surge Drum-1'}) 
CREATE (l2:Sensor {name: 'Level sensor 2'  ,type: 'High Level Sensor on Surge Drum-1'}) 
CREATE (l3:Sensor {name: 'Level sensor 3'  ,type: 'Level Sensor on SWS OVHD Accumulator'}) 
CREATE (l4:Sensor {name: 'Level sensor 4'  ,type: 'Level Sensor on Sour Water Stripper'}) 
CREATE (f1:Sensor {name: 'Flow sensor 1'  ,type: 'Flow Sensor on Sour Water Feed'}) 
CREATE (t1:Sensor {name: 'Temperature sensor 1'  ,type: 'Temperature Sensor on sour water Feed to Stripper OVHD Condenser'}) 
CREATE (t2:Sensor {name: 'Temperature sensor 2'  ,type: 'Temperature Sensor on Overhead stream to Stripper OVHD Condenser'}) 
CREATE (p_oil_rec_pump:Sensor {name: 'Pressure sensor'  ,type: 'Pump pressure Sensor on oil recovery pump'}) 
CREATE (p_sw_feed_pump:Sensor {name: 'Pressure sensor'  ,type: 'Pump pressure Sensor on SW Feed Pump'}) 
CREATE (p_stripper_feed_pump:Sensor {name: 'Pressure sensor'  ,type: 'Pump pressure Sensor on Stripper feed Pump'}) 
CREATE (p_reflux_pump:Sensor {name: 'Pressure sensor'  ,type: 'Pump pressure Sensor on Reflux Pump'}) 
CREATE (p_bottoms_pump:Sensor {name: 'Pressure sensor'  ,type: 'Pump pressure Sensor on Bottoms Pump'})

// Create Controller nodes with properties
CREATE (llc:Controller {name: 'LLC'  ,type: 'Low Level Controller on Surge Drum-1'}) 
CREATE (hlc:Controller {name: 'HLC'  ,type: 'High Level Controller on Surge Drum-1'}) 
CREATE (fc2:Controller {name: 'FC-2'  ,type: 'Flow Controller for steam pipe'}) 
CREATE (fc1:Controller {name: 'FC-1'  ,type: 'Flow Controller for SW feed pipe'}) 
CREATE (lc1:Controller {name: 'LC-1'  ,type: 'Level Controller for SWS OVHD Accumulator'}) 
CREATE (lc2:Controller {name: 'LC-2'  ,type: 'Level Controller for Sour Water Stripper'})

// Create Boundary nodes with properties
CREATE (src1:Boundary {name: 'REFINERY Unit'  ,type: 'Source'}) 
CREATE (s1:Boundary {name: 'DRAIN-TO-SEWER'  ,type: 'Sink'}) 
CREATE (s2:Boundary {name: 'TO-FLARE-SYSTEM'  ,type: 'Sink'}) 
CREATE (s3:Boundary {name: 'TO-ATM'  ,type: 'Sink'}) 
CREATE (s4:Boundary {name: 'SLOP-OIL-CRUDE-TANK-WWT'  ,type: 'Sink'}) 
CREATE (s5:Boundary {name: 'TO-SKIM-RECYCLE'  ,type: 'Sink'}) 
CREATE (s6:Boundary {name: 'ACID-GAS-TO-S-PLANT-EX'  ,type: 'Sink'}) 
CREATE (s7:Boundary {name: 'WATER-TREATMENT'  ,type: 'Sink'}) 
CREATE (src2:Boundary {name: 'STEAM-IN'  ,type: 'Source'})

// Create Flow relationships
CREATE (src1)-[: FLOWS_TO {name : "SW from refinery pipe"}]->(sg) 
CREATE (sg)-[: FLOWS_TO {name : "SW out pipe"}]->(sw_feed_pump) 
CREATE (sg)-[: FLOWS_TO {name : "vent pipe"}]->(s2) 
CREATE (sg)-[:FLOWS_TO {name: "Slop out pipe"}]->(oil_rec_pump) 
CREATE (sg)-[: FLOWS_TO {name: "drain pipe"}]->(dv) 
CREATE (dv)-[:FLOWS_TO {name: "drain to sewer"}]->(s1) 

CREATE (oil_rec_pump)-[: FLOWS_TO {name : "Slop pipe 1 "}]->(nrv3) 
CREATE (nrv3)-[: FLOWS_TO {name : 'Slop pipe 2 '}]->(s4) 

CREATE (sw_feed_pump)-[: FLOWS_TO {name : "SW feed pipe-1"}]->(nrv4) 
CREATE (nrv4)-[: FLOWS_TO {name : "SW feed pipe-2"}]->(fcv2) 
CREATE (fcv2)-[: FLOWS_TO {name : "Sw to storage pipe"}]->(sw) 
CREATE (sw)-[: FLOWS_TO {name : "vent pipe 2"}]->(prv1) 
CREATE (prv1)-[: FLOWS_TO {name : "vent to atm"}]->(s3) 
CREATE (sw)-[:FLOWS_TO {name : "HC oil skim "}]->(s5) 
CREATE (sw)-[:FLOWS_TO {name : "SW from storage pipe"}]->(stripper_feed_pump) 
CREATE (stripper_feed_pump)-[: FLOWS_TO {name : "SW feed pipe 1 "}]->(nrv5) 
CREATE (nrv5)-[: FLOWS_TO {name : "SW feed pipe 2 "}]->(f1) 
CREATE (f1)-[: FLOWS_TO {name : "SW feed pipe 2 "}]->(fcv3) 
CREATE (fcv3)-[: FLOWS_TO {name : "SW feed pipe 3 "}]->(stripper_cond) 
CREATE (stripper_cond)-[: FLOWS_TO {name : "SW feed pipe 4 "}]->(sws) 
CREATE (sws)-[: FLOWS_TO {name : " SWS Overhead pipe "}]->(stripper_cond) 
CREATE (stripper_cond)-[: FLOWS_TO {name : "Overhead Accumulator feed pipe "}]->(sws_acc) 
CREATE (sws_acc)-[: FLOWS_TO {name : "Acid gas pipe"}]->(s6) 
CREATE (sws_acc)-[: FLOWS_TO {name : "Reflux pipe 1"}]->(reflux_pump) 
CREATE (reflux_pump)-[: FLOWS_TO {name : "Reflux pipe 2"}]->(nrv6) 
CREATE (nrv6)-[: FLOWS_TO {name : "Reflux pipe 3"}]->(fcv4) 
CREATE (fcv4)-[: FLOWS_TO {name : "Reflux pipe 4"}]->(sws) 
CREATE (sws)-[: FLOWS_TO {name : "Water pipe 1 "}]->(bottoms_pump) 
CREATE (bottoms_pump)-[: FLOWS_TO {name : "Water pipe 2 "}]->(nrv7) 
CREATE (nrv7)-[: FLOWS_TO {name : "Water pipe 3 "}]->(fcv6) 
CREATE (fcv6)-[: FLOWS_TO {name : "Water pipe 4 "}]->(s7) 
CREATE (src2)-[: FLOWS_TO {name : "Steam pipe 1"}]->(fcv5) 
CREATE (fcv5)-[: FLOWS_TO {name : "Steam pipe 2"}]->(sws) 
CREATE (sws)-[: FLOWS_TO {name : "Pressure relief pipe"}]->(prv2)

// Create Connection relationships
CREATE (t1)-[: CONNECTED_TO {name : "Electrical connection"}]->(stripper_cond)
CREATE (t2)-[: CONNECTED_TO {name : "Electrical connection"}]->(stripper_cond)
CREATE (l1)-[: CONNECTED_TO {name : "Electrical connection"}]->(sg) 
CREATE (l1)-[: SEND_SIGNAL_TO {name : "Level Signal"}]->(llc) 
CREATE (llc)-[: CONTROLS {name : "Sends control signals to OIL recovery pump to control flow"}]->(oil_rec_pump) 
CREATE (l2)-[: CONNECTED_TO {name : "Electrical connection"}]->(sg) 
CREATE (l2)-[: SEND_SIGNAL_TO {name : "Level Signal"}]->(hlc) 
CREATE (hlc)-[: CONTROLS {name : "Sends control signals to Control Valve fcv2"}]->(fcv2) 
CREATE (f1)-[: SEND_SIGNAL_TO {name : "Flow Signal"}]->(fc1) 
CREATE (fc1)-[: CONTROLS {name : "Sends control signals to Control Valve fcv3"}]->(fcv3) 
CREATE (fc1)-[: SEND_SIGNAL_TO {name : "Flow Signal to Flow controller 2 for steam pipeline"}]->(fc2) 
CREATE (fc2)-[: CONTROLS {name : "Sends control signals to Control Valve fcv5"}]->(fcv5) 
CREATE (l3)-[: CONNECTED_TO {name : "Electrical connection"}]->(sws_acc) 
CREATE (l3)-[: SEND_SIGNAL_TO {name : "Level Signal"}]->(lc1) 
CREATE (lc1)-[: CONTROLS {name : "Sends control signals to Control Valve fcv4"}]->(fcv4) 
CREATE (l4)-[: CONNECTED_TO {name : "Electrical connection"}]->(sws) 
CREATE (l4)-[: SEND_SIGNAL_TO {name : "Level Signal"}]->(lc2) 
CREATE (lc2)-[: CONTROLS {name : "Sends control signals to Control Valve fcv6"}]->(fcv6) 
CREATE (p_oil_rec_pump)-[: CONNECTED_TO {name : "Electrical connection for pressure indicator"}]->(oil_rec_pump) 
CREATE (p_sw_feed_pump)-[: CONNECTED_TO {name : "Electrical connection for pressure indicator"}]->(sw_feed_pump) 
CREATE (p_stripper_feed_pump)-[: CONNECTED_TO {name : "Electrical connection for pressure indicator"}]->(stripper_feed_pump) 
CREATE (p_reflux_pump)-[: CONNECTED_TO {name : "Electrical connection for pressure indicator"}]->(reflux_pump) 
CREATE (p_bottoms_pump)-[: CONNECTED_TO {name : "Electrical connection for pressure indicator"}]->(bottoms_pump)

// Create Chemical relationships
CREATE (ch1)-[: Inlet {name: 'Feed Inlet for Sour Water'}]->(src1)
CREATE (ch2)<-[: Outlet {name: 'HC-OIL Outlet'}]-(s4)
CREATE (ch2)<-[: Outlet {name: 'HC-OIL Outlet'}]-(s5)
CREATE (ch3)<-[: Outlet {name: 'H2S vapour Outlet'}]-(s6)
CREATE (ch4)<-[: Outlet {name: 'Ammonia vapour Outlet'}]-(s6)

CREATE (ch5)<-[: Outlet {name: 'Water Outlet'}]-(s7)
CREATE (ch6)-[:Inlet {name: 'Steam Inlet'}]->(src2)
