
// Processing Ref 1 - Quantity/step/No B is added—step omitted
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Quantity/step"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "No B is added—step omitted", ref: "1"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Operator error, e.g., shift handover. MV307 closed after maintenance"})
MATCH (dev:Deviation {name: "No B is added—step omitted", ref: "1"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Spoilt batch"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Detected at sampling and can easily be corrected"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (s:Safeguard {description: "Batch sheet requires analysis to be signed off by supervisor"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Start-up check to confirm that MV307 is open", assigned: "TB", ref: "1"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 2 - Quantity/Excess of B is added
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Quantity"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Excess of B is added", ref: "2"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "F2 not fully emptied from last batch"})
MATCH (dev:Deviation {name: "Excess of B is added", ref: "2"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Excess of B in product; batch will be out of specification"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Detected at sampling but a special procedure will then be required"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Operating procedure to include a check on vessel F2 before B is measured out", assigned: "TB", ref: "2"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 3 - Quantity/Too little of B is added
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Quantity"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Too little of B is added", ref: "3"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Blockage in line or at OP1"})
MATCH (dev:Deviation {name: "Too little of B is added", ref: "3"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Batch out of specification and process delay"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Detected at sampling"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Check procedure for clearing line and OP1 when transfer line holds component B", assigned: "FL", ref: "3"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 4 - Quantity/Too much of A is present
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Quantity"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Too much of A is present", ref: "4"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Error at earlier stage resulting in small excess (double charging covered in HAZOP of addition step)"})
MATCH (dev:Deviation {name: "Too much of A is present", ref: "4"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Batch out of specification and process delay"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Detected at sampling"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Check that procedure will be written to cover this case and include in training program", assigned: "JH", ref: "4"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 5 - Quantity/Too little A is present
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Quantity"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Too little A is present", ref: "5"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Error at earlier stage resulting in small deficiency"})
MATCH (dev:Deviation {name: "Too little A is present", ref: "5"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Batch out of specification and process delay. Not easily corrected"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Detected at sampling"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Evaluate likelihood of this deviation and, if necessary, draw up procedure", assigned: "MS", ref: "5"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 6 - Flow (rate)/Too fast
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Flow (rate)"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Too fast", ref: "6"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Corrosion/erosion of OP1"})
MATCH (dev:Deviation {name: "Too fast", ref: "6"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Reaction rate and heat release increased. May eventually exceed vessel cooling capacity leading to over-temperature"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Independent alarms TICA 32/33 located in a manned control room"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Check that OP1 material is compatible with component B", assigned: "BT", ref: "6"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 7 - Flow (rate)/Too fast
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Flow (rate)"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Too fast", ref: "7"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Wrong OP fitted at OP1 after maintenance"})
MATCH (dev:Deviation {name: "Too fast", ref: "7"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Could quickly exceed the vessel cooling capacity, causing a reaction runaway and demand on BD2"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "TICA32/33 located in a manned control and BD2 relieving to dump tank"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (s:Safeguard {description: "Good control of maintenance"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "7.1 Specify OP1 size in operating procedure and ensure problem is covered in operator training", assigned: "TB", ref: "7"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 8 - Flow (rate)/Too fast
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Flow (rate)"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Too fast", ref: "8"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "MV306 is open and so orifice plate OP1 is bypassed"})
MATCH (dev:Deviation {name: "Too fast", ref: "8"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Will very quickly exceed the vessel cooling capacity and lead to a reaction runaway and demand on BD2"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "TICA32/33 to manned control room and BD2 relief to dump tank"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (s:Safeguard {description: "BD2 is sized for addition at maximum possible flow rate in a 25 mm line"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "8.1 MV306 to be locked closed as it is not used in this process", assigned: "FL", ref: "8"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 9 - Flow (rate)/Too slow
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Flow (rate)"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Too slow", ref: "9"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Partial blockage in line or at orifice plate OP1"})
MATCH (dev:Deviation {name: "Too slow", ref: "9"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Batch time extended"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Operator will note problem when seeking to move to next stage"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Covered by actions 3.1 and 3.2", assigned: "FL", ref: "9"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 10 - Flow/Elsewhere
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Flow"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Elsewhere", ref: "10"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Crack or leak at BD2 (action 8.2 only detects full burst)"})
MATCH (dev:Deviation {name: "Elsewhere", ref: "10"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Loss of contaminated nitrogen to dump tank and eventually to atmosphere"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "None"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Put BD2 on a regular checking schedule", assigned: "FL", ref: "10"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 11 - Temperature/High
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Temperature"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "High", ref: "11"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Control problem or faulty temperature signal (reads low)"})
MATCH (dev:Deviation {name: "High", ref: "11"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Overheating will occur, with contributions from the heating system. Most serious condition would be common effect since both temperature probes are in the same pocket in F2"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "None unless the fault also leads to a low temperature alarm when operator intervention could be expected"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Check whether it is possible to physically separate the two temperature probes (control and protection) to reduce common cause effects", assigned: "FL", ref: "11"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 12 - Temperature/High
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Temperature"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "High", ref: "12"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Loss of cooling water (a low probability event)"})
MATCH (dev:Deviation {name: "High", ref: "12"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Overheating. Runaway if cooling water is not restored or the addition halted"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "TICA32/33 are located in the manned control room and BD2 relieves to dump tank"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Covered by action 7.3", assigned: "AW", ref: "12"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 13 - Temperature/High
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Temperature"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "High", ref: "13"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Jacket not switched from steam to cooling water after earlier step"})
MATCH (dev:Deviation {name: "High", ref: "13"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Overheating with possible reaction runaway"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "TICA32/33 to manned control room and BD2 relieves to dump tank"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Control program to include checks that valve CV301 on the steam line is closed", assigned: "AW", ref: "13"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 14 - Temperature/Low
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Temperature"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Low", ref: "14"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Control problem or faulty temperature signal (reads high)"})
MATCH (dev:Deviation {name: "Low", ref: "14"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Poor quality batch. Extreme outcome is cessation of reaction and accumulation of unreacted B"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "TAL from TICA 32"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "14.1 Take TAL from both the control and the protection temperature sensors", assigned: "AW", ref: "14"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 15 - Pressure/High/low
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Pressure"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "High/low", ref: "15"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "No causes identified in addition to the runaway situations discussed above"})
MATCH (dev:Deviation {name: "High/low", ref: "15"})
MERGE (dev)-[:HAS_CAUSE]->(c);


// Processing Ref 16 - Reaction rate/High/low
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Reaction rate"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "High/low", ref: "16"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "No additional causes found"})
MATCH (dev:Deviation {name: "High/low", ref: "16"})
MERGE (dev)-[:HAS_CAUSE]->(c);


// Processing Ref 17 - Mix/No mixing
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Mix"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "No mixing", ref: "17"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Mechanical coupling fails or agitator blade becomes detached"})
MATCH (dev:Deviation {name: "No mixing", ref: "17"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Risk of accumulation of unmixed B leading to uncontrolled reaction"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Possibly detected by low motor current alarm"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Add a rotation sensor to the shaft of the stirrer; interlock to reactant feed valve AV203", assigned: "AW", ref: "17"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 18 - Mix/No mixing
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Mix"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "No mixing", ref: "18"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Motor failure"})
MATCH (dev:Deviation {name: "No mixing", ref: "18"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Risk of accumulation of unmixed B leading to uncontrolled reaction"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Alarm on motor current (low)"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "18.1 Existing safeguard adequate provided action 17.1 is implemented", assigned: "AW", ref: "18"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 19 - Mix/Less mixing
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Mix"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Less mixing", ref: "19"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Viscous mixture formed"})
MATCH (dev:Deviation {name: "Less mixing", ref: "19"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Stirring becomes inefficient and unmixed B may accumulate"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "May be alarmed by sensor added in action 17"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (s:Safeguard {description: "1"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Check viscosity under extreme conditions to decide if action is needed. If so, include an alarm on high motor current", assigned: "BT", ref: "19"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 20 - Mix/Reverse
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Mix"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Reverse", ref: "20"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Incorrect connection after maintenance"})
MATCH (dev:Deviation {name: "Reverse", ref: "20"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Stirring becomes inefficient and unmixed B may accumulate"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "None"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Include a check on stirrer operation in the commissioning trials and in the maintenance procedures", assigned: "TB", ref: "20"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 21 - Composition/Part of
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Composition"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Part of", ref: "21"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Wrong ratio of reactants covered under high/low quantity"})
MATCH (dev:Deviation {name: "Part of", ref: "21"})
MERGE (dev)-[:HAS_CAUSE]->(c);


// Processing Ref 22 - Composition/As well as
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Composition"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "As well as", ref: "22"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Wrong drum used when charging component B"})
MATCH (dev:Deviation {name: "As well as", ref: "22"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Unpredictable but minimum will be a spoilt batch"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Covered in HAZOP of the charging step"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Review actions from earlier HAZOP and ensure that the purchasing department specifies a distinct drum color", assigned: "MS", ref: "22"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 23 - Control/None
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Control"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "None", ref: "23"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Complete loss of control computer"})
MATCH (dev:Deviation {name: "None", ref: "23"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "System moves to fail safe condition"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Design assumes a period of operation of the computer on its UPS"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (s:Safeguard {description: "Ultimate protection is provided by BD2"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Check that fail safe settings include isolation of feed of B, continued stirring and full cooling to vessel jacket", assigned: "AW", ref: "23"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 24 - Control/Part of
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Control"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Part of", ref: "24"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Selective failure. Most serious: loss of temperature sensors/control"})
MATCH (dev:Deviation {name: "Part of", ref: "24"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Possible undetected overheating"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Ultimate protection is provided by BD2"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Check that the temperature sensors connect to different input boards", assigned: "AW", ref: "24"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 25 - Operator action/Sooner
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Operator action"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Sooner", ref: "25"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Step started early"})
MATCH (dev:Deviation {name: "Sooner", ref: "25"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Starting temperature is low. Reactant may accumulate and then cause runaway reaction once mixing starts"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Ultimate protection is provided by BD2"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Specify the lowest safe starting temperature", assigned: "BT", ref: "25"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 26 - Operator action/Part of
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Operator action"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Part of", ref: "26"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Workout period is shortened if the addition is slow (for any reason)"})
MATCH (dev:Deviation {name: "Part of", ref: "26"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Uncertain—basis for inclusion of the workout period is not clear"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (a:Action {description: "Carry out further laboratory work to determine the importance of the workout and to define the minimum allowable time", assigned: "BT", ref: "26"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 27 - Services/Loss of instrument air
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Services"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Loss of instrument air", ref: "27"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MERGE (con:Consequence {description: "All valves move to assigned failure positions"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (a:Action {description: "Review the failure modes of all valves to ensure specification is correct", assigned: "JH", ref: "27"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 28 - Services/Power loss
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Services"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Power loss", ref: "28"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Unpredicted failure, cut cable, and so on"})
MATCH (dev:Deviation {name: "Power loss", ref: "28"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Stirrer stops. Computer moves plant to a safe hold position"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Computer has its own UPS"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Include this condition in the check under 27.1", assigned: "AW", ref: "28"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 29 - Maintenance/Work on AV203
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Maintenance"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Work on AV203", ref: "29"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Valve problem on AV203 during the transfer"})
MATCH (dev:Deviation {name: "Work on AV203", ref: "29"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "AV203 cannot be isolated from F2 for safe maintenance"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "None"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Put additional manual valves in the F2/F3 line", assigned: "FL", ref: "29"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 30 - Vessel entry (F3)/Other activity
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Vessel entry (F3)"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Other activity", ref: "30"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Inspection or other requirement for entry to vessel"})
MATCH (dev:Deviation {name: "Other activity", ref: "30"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Risk to operator from inert atmosphere, especially nitrogen"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Spades installed on all lines"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Review the isolation of F3, including possible insertion of flexible section into the nitrogen line so it can be disconnected and blanked off. Need to cover F2 as well since it has its own nitrogen supply and is linked to F3", assigned: "MS", ref: "30"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 31 - Drainage/Leak of B
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Drainage"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Leak of B", ref: "31"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Leaking flange on transfer line from F2 to F3"})
MATCH (dev:Deviation {name: "Leak of B", ref: "31"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Some loss of component B into process area"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "All spillages in this area run to a common sump"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Check the materials in use on adjacent units for potential incompatibility", assigned: "FL", ref: "31"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 32 - pH/High/low
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "pH"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "High/low", ref: "32"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Imbalance in quantities of A or caustic added previously"})
MATCH (dev:Deviation {name: "High/low", ref: "32"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Batch quality affected unless initial pH is range 10—11.5"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "None"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Operating procedure to include a check on pH before this step is initiated", assigned: "TB", ref: "32"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 33 - Trip action/Out of range condition
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Trip action"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Out of range condition", ref: "33"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Any"})
MATCH (dev:Deviation {name: "Out of range condition", ref: "33"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Control system moves the plant to a predetermined state based on the trip signals"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (a:Action {description: "Prepare matrix to show which valves act in each trip scenario. Review the matrix at next HAZOP meeting", assigned: "JH", ref: "33"});
MERGE (dev)-[:HAS_ACTION]->(a);


// Processing Ref 34 - Operator PPE/Exposure
MERGE (p:Process {name: "Chemical Batch Process"});
MERGE (param:Parameter {name: "Operator PPE"});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {name: "Exposure", ref: "34"}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
MATCH (c:Cause {description: "Leakage or spillage"})
MATCH (dev:Deviation {name: "Exposure", ref: "34"})
MERGE (dev)-[:HAS_CAUSE]->(c);
MERGE (con:Consequence {description: "Contamination"});
MERGE (dev)-[:LEADS_TO]->(con);
MERGE (s:Safeguard {description: "Standard procedures"});
MERGE (dev)-[:HAS_SAFEGUARD]->(s);
MERGE (a:Action {description: "Confirm that procedures exist for all materials handled in the process", assigned: "TB", ref: "34"});
MERGE (dev)-[:HAS_ACTION]->(a);
