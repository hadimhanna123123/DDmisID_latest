# DDmisID Developer Guide

<div align="center">
<img src="assets/DDmisID_logo.png" alt="DDmisID Logo" width="40%">
</div>

## Table of Contents

1. [Introduction](#introduction)
2. [Use Case and Methodology](#use-case-and-methodology)
3. [Codebase Structure](#codebase-structure)
4. [Installation and Setup](#installation-and-setup)
5. [Configuration](#configuration)
6. [Workflow Orchestration](#workflow-orchestration)
7. [Key Components](#key-components)
   - [Configuration System](#configuration-system)
   - [PID Efficiency Extraction](#pid-efficiency-extraction)
   - [Data Discretization](#data-discretization)
   - [Template Building](#template-building)
   - [Binned Maximum Likelihood Fits](#binned-maximum-likelihood-fits)
   - [Weight Assignment](#weight-assignment)
8. [Design Patterns](#design-patterns)
9. [Testing](#testing)
10. [Contributing](#contributing)

## Introduction

DDmisID (DataDrivenMisID) is a Python library for data-driven particle misidentification modeling in high-energy physics experiments, particularly designed for LHCb analyses. The package derives single-track misidentification templates and event yields from control regions in experimental data, using particle identification (PID) efficiency maps.

DDmisID builds on top of the [PIDCalib2](https://pypi.org/project/pidcalib2/) framework and extends it with a comprehensive workflow for extracting misidentification probabilities, accounting for cross-contamination between particle species.

## Use Case and Methodology

### Problem Statement

In particle physics experiments, particles can sometimes be misidentified. For example, a kaon might be incorrectly identified as a muon. This misidentification contributes to background signals that need to be accurately modeled in data analyses.

### Methodology

DDmisID implements a data-driven approach to model misidentification through several key steps:

#### 1. Control and Target Samples Definition

The procedure starts by defining two critical sample regions:

- **Control region**: Particles failing specific muon identification criteria (e.g., `DLLmu<-3.0 & IsMuon==0.0`). This is a hadron-enriched sample containing mostly non-muon particles.
- **Target region**: Particles passing different muon identification criteria (e.g., `DLLmu>-2.0 & DLLmu<0.0 & IsMuon==0.0`). This represents potential misidentified particles.

#### 2. Reconstruction Partitioning

Within the control sample, high-purity partitions are created to isolate different particle species:

- **Kaon-like**: `DLLK>0.0 & (DLLK-DLLp)>0.0 & (DLLK-DLLe)>0.0`
- **Pion-like**: `DLLK<0.0 & DLLp<0.0 & DLLe<0.0`
- **Proton-like**: `DLLp>0.0 & (DLLp-DLLK)>0.0 & (DLLp-DLLe)>0.0`
- **Electron-like**: `DLLe>0.0 & (DLLe-DLLK)>0.0 & (DLLe-DLLp)>0.0`
- **Ghost-like**: Particles evading all the above categories

These partitions are not perfectly pure due to imperfect PID performance, necessitating the unfolding procedure.

#### 3. PID Efficiency Determination

For each particle species, several efficiencies are measured using calibration samples:

- **Control region efficiency**: $\varepsilon_{\mathrm{PID}}(i \to !\mu)$ - probability for species $i$ to satisfy the control region criteria
- **Target region efficiency**: $\varepsilon_{\mathrm{PID}}(i \to \mu)$ - probability for species $i$ to satisfy the target region criteria
- **Partition efficiencies**: $\varepsilon(i \to j)$ - probability for species $i$ to be reconstructed in partition $j$

These efficiencies are measured separately in bins of particle kinematics (momentum, pseudorapidity) and event properties (track multiplicity) to account for their variations.

#### 4. Unfolding True Species Abundances

The observed counts in different partitions ($N_j^{\mathrm{obs}}$) reflect a mixture of the true species abundances ($N_i$) due to cross-contamination:

$N_j^{\mathrm{obs}} = \sum_i N_i \cdot \varepsilon(i\to j)$

The true abundances are extracted by performing binned maximum-likelihood fits to the observed partition counts in each kinematic and occupancy bin. The fit procedure:

1. Creates templates for each species based on their partition efficiencies
2. Performs a simultaneous fit across all partitions
3. Extracts the parameter $N_i$ for each species, which represents their true abundance

This unfolding accounts for the fact that a kaon, for example, might occasionally be classified in the pion-like partition, and corrects for this contamination.

#### 5. Misidentification Weight Calculation

Finally, the misidentification weight is calculated for each event in the control sample:

$w_{\mathrm{misID}} = \sum_{i\in\{p,K,\pi,e,g\}} \frac{N_i}{N_{\mathrm{ref}}} \frac{1}{\varepsilon_{\mathrm{PID}}{(i \to !\mu)}}\varepsilon_{\mathrm{PID}}(i\to \mu)$

Where:
- $w_{\mathrm{misID}}$ is the misidentification weight
- $N_i$ is the true abundance of each species determined from unfolding
- $N_{\mathrm{ref}}$ is the total number of particles in the reference control sample
- $\varepsilon_{\mathrm{PID}}(i \to !\mu)$ is the efficiency of the control region criteria for species $i$
- $\varepsilon_{\mathrm{PID}}(i \to \mu)$ is the efficiency of the target region criteria for species $i$

This weight has a clear physical interpretation:

1. $\frac{N_i}{N_{\mathrm{ref}}}$ represents the fraction of species $i$ in the control sample
2. $\frac{1}{\varepsilon_{\mathrm{PID}}{(i \to !\mu)}}$ corrects for the efficiency of selecting the control sample
3. $\varepsilon_{\mathrm{PID}}(i\to \mu)$ gives the probability for species $i$ to be misidentified as a muon

#### 6. Kinematic and Occupancy Binning

All the above steps are performed separately in bins of particle kinematics and detector occupancy:

- **Momentum bins**: Typically 10-100 GeV/c, divided into several bins
- **Pseudorapidity bins**: Covering the detector acceptance range
- **Track multiplicity bins**: Capturing different detector occupancy scenarios

This binning is essential because PID performance varies significantly with these parameters. The final misidentification weights are assigned to each event based on its specific kinematic and occupancy bin.

## Codebase Structure

The codebase is organized as follows:

```
└── reallyblaised-ddmisid/
    ├── README.md                # Project overview
    ├── LICENSE                  # MIT License
    ├── setup.py                 # Package installation configuration
    ├── assets/                  # Images and other static assets
    ├── config/                  # Configuration files
    │   ├── calib_tuning.py      # Calibration sample specifications
    │   └── main.yml             # Main configuration file
    ├── ddmisid/                 # Main package directory
    │   ├── __init__.py          # Package initialization
    │   ├── auth.py              # Authentication utilities
    │   ├── cli.py               # Command-line interface
    │   ├── engine.py            # Configuration engine
    │   ├── pydantic_config_model.py # Config validation
    │   ├── data_transforms/     # Data transformation utilities
    │   │   ├── __init__.py 
    │   │   └── discretiser.py   # Data discretization
    │   ├── pid/                 # PID efficiency extraction
    │   │   ├── __init__.py
    │   │   ├── base_job_generator.py     # Abstract job generator
    │   │   ├── base_species_strategy.py  # Species strategy base
    │   │   ├── factory.py                # Factory for job generation
    │   │   ├── job_generator.py          # Job generators
    │   │   └── species_strategy.py       # Species-specific strategies
    │   ├── snakemake/           # Snakemake workflow scripts
    │   │   ├── assign_w_misid.py         # Weight assignment
    │   │   ├── collect_yields.py         # Yield collection
    │   │   ├── fit_reco.py               # Reco fitting
    │   │   └── ghost_pid_effs.py         # Ghost PID efficiencies
    │   └── utils/               # Utility functions
    │       ├── __init__.py
    │       ├── binning.py       # Binning utilities
    │       ├── histogram.py     # Histogram processing
    │       ├── io.py            # I/O utilities
    │       └── plot.py          # Plotting utilities
    ├── tests/                   # Unit tests
    │   ├── test_binning_generator.py
    │   ├── test_calib_tuning.py
    │   └── test_efficiency_histogram_processing.py
    └── workflow/                # Snakemake workflow
        └── Snakefile            # Main workflow definition
```

## Installation and Setup

### Prerequisites

- Python 3.8+
- [PIDCalib2](https://pypi.org/project/pidcalib2/)
- LHCb software environment (for PIDCalib2)

### Installation Steps

1. Clone the repository:
   ```bash
   git clone git@github.com:reallyblaised/DDmisID.git
   cd DDmisID
   ```

2. Install dependencies and package:

   For regular use:
   ```bash
   pip install -r requirements.txt
   ```

   For development (recommended until further notice):
   ```bash
   pip install -e .
   ```

## Configuration

**The primary task for users is to correctly configure the YAML file, after which the entire DDmisID workflow executes automatically.** This configuration-driven approach means you only need to modify `config/main.yml` to adapt the analysis to your specific needs.

DDmisID uses a YAML-based configuration system with validation through Pydantic. The main configuration file is located at `config/main.yml`. This file serves as the single point of control for the entire workflow.

### Key Configuration Elements

Below is a detailed explanation of the critical configuration sections:

1. **User identification** for CERN authentication:
   ```yaml
   user_id: "bldelane"  # CERN user ID for kinit @CERN.CH
   ```
   This is required to access EOS and other LHCb resources.

2. **Test run settings**:
   ```yaml
   max_calib_files: 25  # Number of calibration files to process (-1 for all)
   verbose: True        # Enable detailed output
   ```
   Useful for testing the workflow before running on full datasets.

3. **PIDCalib2 configuration**:
   ```yaml
   pid:
     # Binning for sWeight fits
     sweight_binning:
       "Brunel_P": [10_000, 12_500, 15_000, 17_500, 20_000, 25_000, 50_000, 100_000]
       "Brunel_ETA": [1.5, 2.5, 5.5]  
       "nTracks_Brunel": [0, 250, 1000]
     
     # More granular binning for PID efficiency extrapolation
     pid_extrap_binning:
       "Brunel_P": [10_000, 12_500, 15_000, 17_500, 20_000, 22_500, 25_000, 50_000, 100_000]
       "Brunel_ETA": [1.5, 2.5, 3.5, 5.5]  
       "nTracks_Brunel": [0, 250, 1000] 
     
     # Species to include in misID modeling
     species: 
       kaon: "K"          # Maps to PIDCalib2 "K" alias
       pion: "Pi"         # Maps to PIDCalib2 "Pi" alias
       proton: "P"        # Maps to PIDCalib2 "P" alias
       electron: "e_B_Jpsi" # Maps to PIDCalib2 "e_B_Jpsi" alias
     
     # Data-taking period configuration
     year: "2018"        # Year of data taking
     magpol: "up"        # Magnet polarity (follow pidcalib2 syntax)
     
     # PID selection criteria
     control: "ProbNNghost<0.1 & DLLmu<-3.0 & IsMuon==0.0 & probe_hasMuon==1.0 & InMuonAcc==1.0"
     target: "ProbNNghost<0.1 & DLLmu>-2.0 & DLLmu<0.0 & IsMuon==0.0 & probe_hasMuon==1.0 & InMuonAcc==1.0"
     
     # Common selection between control and target regions
     common_selection: "probe_Brunel_NShared==0 & Brunel_P>10000 & Brunel_P<100000 & Brunel_PT>1500"
     
     # Definitions of reconstruction partitions
     reco_partitions:
       kaon_like: "DLLK>0.0 & (DLLK-DLLp)>0.0 & (DLLK-DLLe)>0.0"
       pion_like: "DLLK<0.0 & DLLp<0.0 & DLLe<0.0"
       proton_like: "DLLp>0.0 & (DLLp-DLLK)>0.0 & (DLLp-DLLe)>0.0"
       electron_like: "DLLe>0.0 & (DLLe-DLLK)>0.0 & (DLLe-DLLp)>0.0"
   ```

4. **Data file paths and selection criteria**:
   ```yaml
   data: 
     # File location settings
     input_path: "/afs/cern.ch/user/h/hmhanna/private/DDmisID/DDmisID/Data/inputData/Bc2D0MuNuX.root"
     data_key: "B2DMuNuX_D02KPi_FakeMuonTuple"
     data_tree: "DecayTree"
     output_path: "/afs/cern.ch/user/h/hmhanna/private/DDmisID/DDmisID/Data/outputData/fakemuon_2018_MU.root"
     
     # Variable name mapping in your input data
     data_prefixes: 
       P: "Mu_plus"      # Variables follow Mu_plus_P naming convention
       ETA: "Mu_plus_LK" # Variables follow Mu_plus_LK_ETA naming convention
       nTracks: ""       # Variable is just "nTracks"
     
     # Data selection criteria for each partition
     data_reco_partitions: 
       kaon: "(Mu_plus_InMuonAcc==1.0) & (Mu_plus_NShared==0) & ... & (Mu_plus_PIDK>0.0) & ..."
       pion: "(Mu_plus_InMuonAcc==1.0) & (Mu_plus_NShared==0) & ... & (Mu_plus_PIDK<0.0) & ..."
       # Additional partitions...
   ```

### Configuration Validation

DDmisID validates your configuration through Pydantic models to ensure all required parameters are properly specified before running any workflow steps. This catches configuration errors early and provides clear error messages.

When you run `ddmisid-engine build`, the system:
1. Parses the YAML file
2. Validates all settings against the Pydantic models
3. Stores a validated JSON version for use by the workflow

### Configuration Best Practices

1. **Start with a template**: Use the provided `config/main.yml` as a starting point
2. **Validate binning**: Ensure your kinematic bins match your analysis requirements
3. **Check PID cuts**: Verify the PID selection criteria are appropriate for your analysis
4. **Test incrementally**: Start with `max_calib_files` set to a small number for testing
5. **Validate branch names**: Ensure that your data branch naming conventions match the configuration

### Step-by-Step Configuration Guide

1. **Copy the template configuration**:
   ```bash
   cp config/main.yml config/my_analysis.yml
   ```

2. **Edit your configuration file**:
   ```bash
   nano config/my_analysis.yml
   ```

3. **Build and validate your configuration**:
   ```bash
   ddmisid-engine build --config-path config/my_analysis.yml
   ```

4. **Run the workflow using your configuration**:
   ```bash
   ddmisid-engine run -- --cores 4
   ```

All other steps in the workflow automatically use your configuration without requiring additional input.

## Workflow Orchestration

DDmisID uses [Snakemake](https://snakemake.readthedocs.io/) to orchestrate its workflow. **Once the configuration file is set up correctly, the entire analysis runs automatically** through the Snakemake pipeline.

### Snakemake Fundamentals

For developers unfamiliar with Snakemake, here are the key concepts:

1. **Rules**: Basic building blocks that define how to create output files from input files
2. **Wildcards**: Variables in filenames that allow for pattern matching
3. **DAG**: Snakemake builds a directed acyclic graph of jobs and executes them in the correct order
4. **Checkpoints**: Special rules that can determine the structure of the DAG at runtime

### DDmisID Workflow Overview

The DDmisID workflow, defined in `workflow/Snakefile`, consists of several key stages:

1. **PID Efficiency Map Generation**: Generate efficiency maps using PIDCalib2
2. **Data Discretization**: Partition control data into species-specific bins
3. **Template Creation**: Build templates for binned maximum likelihood fits
4. **Binned ML Fits**: Extract true abundances of each species
5. **Weight Assignment**: Compute misidentification weights

### DDmisID Workflow Flowchart

Below is a flowchart of the main Snakemake rules in the DDmisID workflow:

```
                                    +---------------+
                                    |      all      |
                                    +-------+-------+
                                            |
                                            v
                                    +---------------+
                                    |  ddmisid.done |
                                    +-------+-------+
                                            |
                              +-------------+-------------+
                              |                           |
                              v                           v
                  +-----------------------+   +------------------------+
                  | extract_misid_weights |   | relative_abundances    |
                  +-----------+-----------+   +------------+-----------+
                              |                            |
                              v                            v
                 +-------------------------+   +------------------------+
                 | Build relative abundance|<--+      bml_fit           |
                 | lookup table            |   +------------+-----------+
                 +-------------------------+                |
                              ^                            |
                              |                            v
                  +-----------+-----------+   +------------------------+
                  |    collect_discretizer|   |    make_templates      |
                  +-----------+-----------+   +------------+-----------+
                              |                            |
                              v                            v
                  +-----------+-----------+   +------------------------+
                  |   discretize_data     |   |   process_pid_effs     |
                  +-----------+-----------+   +------------+-----------+
                                               |                       |
                                               v                       v
                                    +------------------------+         |
                                    |    extract_pid_effs    |         |
                                    +------------+-----------+         |
                                               |                       |
                                               v                       |
                                    +------------------------+         |
                                    | generate_pid_efficiency|<--------+
                                    | _scripts               |
                                    +------------------------+
```

This flowchart shows how the rules are connected and the dependencies between them. The workflow starts at the bottom with PID efficiency script generation and works its way up to the final misidentification weight extraction.

### Example Workflow Snippet

```python
rule extract_pid_effs:
    """
    Run the pideffx jobs as spawned in the previous step. Tally the resulting efficiency histograms.
    """
    input:
        bash_file = "scratch/bin/{year}/{magpol}/{dllmu_bin}/{species}/{eff_dirs}/run.sh",
    output:
        pidcalib_hists = "scratch/bin/{year}/{magpol}/{dllmu_bin}/{species}/{eff_dirs}/perf.pkl",
    log: 
        "logs/workflow/{year}/{magpol}/{dllmu_bin}/{species}/{eff_dirs}/pideffx.log"
    run:
        shell("bash {input.bash_file} &> {log}")
```

This rule executes PID efficiency extraction bash scripts and logs their output.

### Running the Workflow

To execute the DDmisID workflow:

1. Build the engine (validates configuration):
   ```bash
   ddmisid-engine build
   ```

2. Run the Snakemake pipeline:
   ```bash
   ddmisid-engine run -- --cores 4
   ```

Additional Snakemake options can be passed after the `--` separator.

### Common Snakemake Options

- `--cores N`: Specify the number of cores to use (use `--cores all` for all available cores)
- `--dryrun`: Show what would be done without executing anything
- `--reason`: Show the reason for each executed rule
- `--until RULE`: Execute the workflow until the specified rule
- `--dag | dot -Tpdf > dag.pdf`: Generate a PDF visualization of the workflow DAG

### Monitoring the Workflow

1. **Check log files**: Each rule generates log files in the `logs/` directory
2. **Review output files**: Intermediate outputs are stored in the `scratch/` directory
3. **Visual progress**: Use `--dag` to see the workflow structure and track progress
4. **Notifications**: Configure Snakemake to send email notifications on completion

### Handling Errors

If an error occurs during the workflow:

1. Check the log file for the failed rule
2. Fix the issue (often related to data paths or PID selection criteria)
3. Re-run the workflow - Snakemake will resume from the failed rule

### Workflow Outputs

The main output of the workflow is a ROOT file with misidentification weights assigned to each event in the input data. This file will be created at the path specified in `data.output_path` in your configuration.

## Key Components

### Configuration System

The configuration system uses Pydantic for validation and type checking. A simplified view of the config model:

```python
class PIDConfig(BaseModel):
    """PIDCalib2 configuration model."""
    sweight_binning: Dict[str, List[float]]
    pid_extrap_binning: Dict[str, List[float]]
    species: Dict[str, str]
    year: str
    magpol: str
    control: str
    target: str
    common_selection: Optional[str]
    reco_partitions: Dict[str, str]
    ghost_config: Optional[Dict[str, str]]

class DataConfig(BaseModel):
    """Data configuration for DDmisID."""
    input_path: str
    data_key: Optional[str]
    data_tree: str
    data_prefixes: Dict[str, str]
    data_reco_partitions: Dict[str, str]
    output_path: str

class DDmisIDConfig(BaseModel):
    """Main configuration model for DDmisID."""
    user_id: str
    max_calib_files: int
    verbose: bool
    pid: PIDConfig
    data: DataConfig
```

The engine module loads, validates, and provides access to this configuration:

```python
def _load_config(config_path: str):
    """Load and validate the configuration file."""
    global config

    # read in the YAML config file and validate
    config_data = read_config(config_path)
    config = DDmisIDConfig(**config_data)

    # Persist the validated config
    with config_path_json.open("w") as f:
        f.write(json.dumps(config.dict(), indent=4))
```

### PID Efficiency Extraction

DDmisID extracts PID efficiencies using design patterns like Strategy and Factory:

```python
class PIDEffXJobFactory:
    """Factory interface for PIDCalib2 job generation."""
    
    def generate_jobs(self, output_dir: str, region_ids: list = ["control", "target"], verbose: bool = False) -> None:
        """Factory interface to spawn all the requisite PIDCalib2 jobs."""
        for species_id, species_alias in self.species.items():
            logger.info(f"Generating PIDCalib2 jobs for species: {species_id}")

            # Fetch the appropriate strategy and job generators for each species
            strategy, control_target_job_generator, reco_partition_job_generator = self._get_strategy_and_generator(species_id) 
            
            # First, control and target pid-efficiency-extra jobs
            control_target_job_generator(config, strategy).generate_jobs(
                year=self.year,
                magpol=self.magpol,
                region_id=region_ids,
                output_dir=output_dir,
            )
            
            # Second, reco partition pid-efficiency-extra jobs
            reco_partition_job_generator(config, strategy).generate_jobs(
                year=self.year,
                magpol=self.magpol,
                output_dir=output_dir,
            )
```

### Data Discretization

The Discretiser class partitions data into bins of kinematics and occupancy:

```python
class Discretiser:
    """Base class for discretizing data into user-specified binnings."""

    def __init__(self, binning, reco_cuts, data, reco_label="reco"):
        self._binning = binning
        self._reco_cuts = reco_cuts
        self._data = data
        self.reco_label = reco_label
        self._hist = self.discretize()
        
    def discretize(self):
        """Fill the histogram with the data, in bins of occupancy, kinematics and reco-category"""
        self.assign_reco_id()
        hist = self.book_histogram()

        # book binning keys + reco axis
        binning_keys = list(self.binning.keys())
        reco_binning = [self.data[key] for key in binning_keys]
        reco_binning.append(self.data["reco"])

        # book empty histogram with n_{pidcalib axes} + reco axis
        hist.fill(*reco_binning)

        return hist
```

### Template Building

Templates for binned ML fits are created based on reco partitions:

```python
class TemplateFactory:
    """Factory for creating BinnedTemplate objects."""
    
    def register_species(self, species: str):
        """Register species-specific template maker."""
        self._species = species
        
    def fetch_template_maker(self, species: str, path_prefix: str, reco_partitions: Dict[str, str]):
        """Fetch the appropriate template maker for the given species."""
        return BinnedTemplate(species, path_prefix, reco_partitions)
```

### Binned Maximum Likelihood Fits

Binned ML fits extract true abundances of each species using pyhf and cabinetry:

```python
def build_channel_spec(obs, proton_template=None, pion_template=None, kaon_template=None, 
                      muon_template=None, electron_template=None, ghost_template=None):
    """Build the schema for the channel"""

    observations = list(load_hist(obs)[SPECIES].view())
    schema = {
        "channels": [
            {
                "name": "Control-channel data",
                "samples": build_sample_spec(
                    proton_template=proton_template,
                    pion_template=pion_template,
                    kaon_template=kaon_template,
                    electron_template=electron_template,
                    muon_template=muon_template,
                ),
            }
        ],
        "observations":[
            {"name": "Control-channel data", "data": observations} 
        ],
        "measurements": [
            {
                "name": "True !mu abundance extraction",
                "config": {
                    "poi": 'pion_yield', 
                    "parameters": [
                        # bounds on floating normalisations
                        {"name": "proton_yield", "bounds": [[0.0, np.sum(observations)]], "inits": [np.sum(observations)/10.0]},
                        {"name": "kaon_yield", "bounds": [[0.0, np.sum(observations)]], "inits": [np.sum(observations)/10.0]},
                        # Additional parameters...
                    ]
                }
            }
        ],
        "version": "1.0.0"
    }

    # build and validate according to pyhf specification
    ws = pyhf.workspace.Workspace(schema, validate=True)
    return ws
```

### Weight Assignment

The final step assigns misidentification weights based on the methodology equation:

```python
def compute_misid_weight(p_val, eta_val, ntracks_val, pid_effs, relative_yields_hist, species):
    """Element-wise weight assignment, accounting for different binning"""
    misid_w = ufloat(0.0, 0.0)

    for spc in species:
        # relative abundance
        sweight_prefactor = relative_yields_hist[
            bh.loc(p_val), bh.loc(eta_val), bh.loc(ntracks_val), f"{spc}_yield"
        ]
        sw_spc = ufloat(sweight_prefactor.value, sweight_prefactor.variance**0.5)

        # control-channel efficiency
        ctrl_pideff = pid_effs[f"{spc}_to_antimu"][
            bh.loc(p_val), bh.loc(eta_val), bh.loc(ntracks_val)
        ]
        ctrl_pideff_v = ufloat(ctrl_pideff.value, ctrl_pideff.variance**0.5)

        # signal-channel efficiency
        sig_pideff = pid_effs[f"{spc}_to_mu"][
            bh.loc(p_val), bh.loc(eta_val), bh.loc(ntracks_val)
        ]
        sig_pideff_v = ufloat(sig_pideff.value, sig_pideff.variance**0.5)

        # linear combination
        try:
            misid_w += sw_spc * (1.0 / ctrl_pideff_v) * sig_pideff_v
        except ZeroDivisionError:
            logger.warning(f"Division by zero encountered. ctrl_pideff_v: {ctrl_pideff_v}. Skipping.")

    return misid_w.n
```

## Design Patterns

DDmisID makes extensive use of design patterns to ensure maintainable, extensible code:

1. **Factory Pattern**: Used for creating PID efficiency jobs and templates
2. **Strategy Pattern**: Encapsulates species-specific behaviors
3. **Template Method Pattern**: Defines the skeleton of algorithms with specific steps implemented by subclasses
4. **Mixin Pattern**: Provides reusable functionality across different classes

Example of Strategy pattern implementation:

```python
class BaseSpeciesStrategy(ABC):
    """Abstract base class for species strategies."""

    @abstractmethod
    def get_species_name(self) -> str:
        """Return the internal species identifier within DDmisID."""
        pass

    @abstractmethod
    def get_species_alias(self) -> str:
        """Fetch the PIDCalib2-compliant alias for each species."""
        pass

class ParticleStrategy(BaseSpeciesStrategy, SpeciesValidatorMixin):
    """Strategy for particle species that rely on PIDCalib2 to extract PID efficiencies."""

    def __init__(self, species, config=config):
        self._species = species
        self._species_alias_map = config.pid.species
        self.validate_species()

    def get_species_name(self) -> str:
        return self.species

    def get_species_alias(self) -> str:
        return self.species_alias_map[self.species]
```

## Testing

The package includes various unit tests to ensure functionality:

1. **Binning Generator Tests**: Ensure correct binning structure for PIDCalib2
2. **Calibration Tuning Tests**: Validate calibration sample handling
3. **Efficiency Histogram Processing Tests**: Check correct handling of edge cases

Run tests with:

```bash
pytest
```

## Practical Workflow Examples

This section provides concrete examples of common tasks to help you get started quickly.

### Example 1: Running a Test Configuration

To test the workflow on a smaller dataset:

```yaml
# In config/main.yml
max_calib_files: 10  # Limit calibration samples
verbose: True        # Enable detailed logging
```

```bash
# Build and run with 2 cores
ddmisid-engine build
ddmisid-engine run -- --cores 2
```

### Example 2: Debugging a Failed Job

If a job fails:

```bash
# Find the error
cat logs/workflow/2018/up/control/pion/pion_to_control_like/pideffx.log

# Fix the issue (e.g., fixing paths or configuration)
nano config/main.yml

# Rebuild and rerun
ddmisid-engine build
ddmisid-engine run -- --cores 4
```

### Example 3: Changing Binning Scheme

To modify the binning for different analysis needs:

```yaml
# In config/main.yml
pid:
  sweight_binning:
    "Brunel_P": [5_000, 10_000, 20_000, 50_000, 100_000]  # Coarser binning
    "Brunel_ETA": [1.5, 3.0, 5.5]                         # Coarser binning
    "nTracks_Brunel": [0, 500, 1000]                      # Coarser binning
```

### Example 4: Analyzing Output Weights

After the workflow completes:

```python
# Example script to analyze weights
import uproot
import matplotlib.pyplot as plt
import numpy as np

# Open output file
f = uproot.open("path/to/output.root:B2DMuNuX_D02KPi_FakeMuonTuple/DecayTree")

# Extract misID weights
misid_w = f["misid_w"].array()

# Plot weight distribution
plt.figure(figsize=(10, 6))
plt.hist(misid_w, bins=50, range=(0, 0.01))
plt.xlabel('misID Weight')
plt.ylabel('Events')
plt.title('Distribution of Misidentification Weights')
plt.savefig('misid_weights.png')
```

## Troubleshooting Guide

### Common Issues and Solutions

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| `FileNotFoundError` | Missing input data file | Verify `data.input_path` exists and is accessible |
| `ValidationError` | Invalid configuration | Check error message for specific field and fix in YAML |
| PIDCalib2 job failure | Incorrect PID criteria | Verify PID selection criteria is valid for your dataset |
| Low statistics warning | Too few events in bins | Adjust binning to be coarser or use a larger dataset |
| Permission denied | Kerberos ticket expired | Re-authenticate with `kinit username@CERN.CH` |
| Missing dependency | Package not installed | Install missing package with `pip install package-name` |

### Interpreting Logs

Log files are stored in the `logs/` directory with a hierarchical structure that matches the workflow:

```
logs/
├── engine/
│   └── ddmisid_log_*.log       # Engine logs
└── workflow/
    ├── pideffx_script_generation.log  # PID efficiency script generation logs
    ├── data_discretizer.log           # Data discretization logs
    └── {year}/{magpol}/{rule}/...     # Rule-specific logs
```

When troubleshooting:
1. Start with the highest-level log file
2. Follow error messages to more specific log files
3. Look for specific error messages or warnings

## Glossary of Terms

| Term | Definition |
|------|------------|
| PID | Particle Identification |
| DLL | Delta Log-Likelihood (e.g., DLLK is log-likelihood difference between kaon and pion hypotheses) |
| Control region | Hadron-enriched sample failing muon identification criteria |
| Target region | Sample of particles passing specific muon identification criteria |
| Reco partition | High-purity subset of control region targeting specific particle species |
| PIDCalib2 | LHCb software package for measuring PID efficiencies from calibration samples |
| Ghost | Reconstructed track not corresponding to a real particle |
| Unfolding | Statistical procedure to extract true distributions from observed ones with detector effects |
| Misidentification weight | Event weight representing probability of misidentification |
| Binned ML fit | Binned Maximum Likelihood fit used to extract species yields |

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## Quick Reference

### Key Commands

```bash
# Authentication
kinit username@CERN.CH

# Build configuration
ddmisid-engine build [--config-path=path/to/config.yml]

# Run workflow
ddmisid-engine run -- [snakemake options]

# Common Snakemake options
--cores N      # Number of cores to use
--dryrun       # Show what will be done
--reason       # Show why each rule is executed
--until RULE   # Run until specified rule
```

### Important File Locations

- **Configuration**: `config/main.yml`
- **Validated config**: `.schema/validated_config.json`
- **Log files**: `logs/`
- **Intermediate outputs**: `scratch/`
- **Final output**: Path specified in `data.output_path`

---

This guide provides an overview of the DDmisID package for new developers. For specific implementation details, refer to the source code and comments within each module. With this document, you should have everything needed to understand, configure, and run the DDmisID workflow without additional assistance.
