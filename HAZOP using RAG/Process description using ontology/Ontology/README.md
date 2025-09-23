# Process Engineering Ontologies

This folder contains the knowledge bases for the P&ID description generation project. These ontologies are formal, machine-readable models that define the concepts, properties, and relationships relevant to specific types of chemical engineering equipment.

An **ontology** acts like a detailed encyclopedia for our software. Instead of just knowing that a "reactor" is connected to a "valve," the ontology allows the program to understand that a `Reactor` has an `Inlet`, and a `Control_Valve` is a type of `Instrument` that can be part of a `Control_loop` to regulate a `Parameter` like `Flow`.

---

## 📄 File Descriptions

### 1. `Reactor Ontology.rdf`

This ontology models the domain of chemical reactors. It provides a structured vocabulary for describing a reactor's components, functions, and operational parameters.

#### Key Concepts (Classes)

The ontology defines a hierarchy of concepts, including:
* **Reactor Types**: Classifies reactors by their mode of operation, such as `Batch`, `Continuous`, and `Semi-batch`. It further specifies continuous types like `CSTR` (Continuous Stirred-Tank Reactor) and `PFR` (Plug Flow Reactor).
* **Internal Components**: Describes the physical parts inside a reactor vessel, such as an `Agitator` for mixing, `Internal_Baffles` to improve mixing efficiency, and a `Catalyst_bed` for facilitating reactions.
* **Auxiliary & Safety Systems**: Defines supporting systems like `Thermal_Jacket` for temperature control and crucial `Safety_system` components like `Alarms`, `ESD_valve` (Emergency Shutdown Valve), and `Pressure_relief` systems (e.g., `Rupture_disc`).
* **Process Connections**: Models the interfaces of the reactor, such as `Inlet` for reactants and `Outlet` for products.
* **Parameters**: Represents the measurable variables that define the reactor's state, including `Temperature`, `Pressure`, `Concentration`, and `Reaction_rate`.
* **Instrumentation**: Includes concepts for `Measuring_Instruments/Sensor` and automated `Control_loop` systems.

#### Key Relationships (Object Properties)

The ontology defines how these concepts relate to each other:
* `has_inlet` / `has_outlet`: A `Reactor` is connected to an `Inlet` and an `Outlet`.
* `has_internal_components`: A `Reactor` contains parts like an `Agitator`.
* `Controls`: A `Control_loop` manipulates a `Control_Valve` to manage a `Parameter`.
* `measures`: A `Measuring_Instruments/Sensor` is used to measure a `Parameter`.

---

### 2. `Storage Tank Ontology.rdf`

This ontology provides a formal representation of knowledge specific to storage tanks in process plants.

#### Key Concepts (Classes)

The ontology classifies tanks and their associated systems:
* **Tank Types**: Differentiates between `Atmospheric_Tank` and `Pressurized_Tank`. Atmospheric tanks are further specified by their roof type, such as `Fixed_roof` and `Floating_roof`.
* **Internal Components**: Defines components inside the tank, including `Agitator` for mixing, `Internal_Heating_Coil` for temperature control, and `Vortex_Breaker` to prevent vapor entrainment during drainage.
* **Auxiliary Systems**: Models essential support systems like a `Jacket` for external heating/cooling, a `Blanket_Gas_System` for inerting the vapor space, and `Drain_Points` for removing contaminants.
* **Safety Systems**: Includes critical safety features like `Pressure_Relief` devices (`Relief_Valve`, `Rupture_Disc`), `Bund_Wall` for secondary containment, `Fire_Protection` systems, and `ESD_Valves` for emergency isolation.
* **Instrumentation & Parameters**: Defines `Measuring_Instruments/Sensors` for monitoring `Parameter`s like `Level`, `Pressure`, and `Temperature`. It also models `Control_Loop`s that maintain these parameters at a desired `Setpoint`.

#### Key Relationships (Object & Data Properties)

The ontology connects these concepts and links them to data:
* `has_Inlet` / `has_Outlet`: A `Storage_tank` has connections for inflows and outflows.
* `Connected_to`: A `Storage_tank` is connected to other `Equipments`.
* `Supplied_to`: `Utilities` are supplied to systems like a `Jacket` or `Blanket_Gas_System`.
* `has_Volume` / `has_Design_Pressure`: These **Data Properties** link a `Storage_tank` to specific numerical values (e.g., a float value representing its volume).