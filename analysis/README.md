# LLM Persuasion in Moral Judgments: Analysis Repository

This repository contains the analysis code and data for a study examining whether large language models (LLMs) can influence human moral judgments through conversational persuasion.

## Project Structure

```
analysis/
├── data/
│   ├── data_long_renamed.csv      # Long format (one row per dilemma)
│   └── dilemma_metadata.json      # Dilemma characteristics
│
├── figures/
│   ├── thesis/                    # Final PDF figures for thesis
│   └── system_prompts_example.pdf
│
├── tables/
│   └── tables.md                  # All analysis tables in markdown format
│
├── 00_setup.R                     # Data loading and preprocessing
├── 00_theme.R                     # ggplot2 theme for figures
├── 08_models.R                    # Main statistical models
├── 09_results_figures.R           # Generate results figures
├── 10_results_tables.R            # Generate results tables
├── 11_exploratory_figures.R       # Exploratory figures
├── 12_exploratory_tables.R        # Exploratory tables
├── run_thesis_figures.R           # Run all figure generation
├── run_thesis_tables.R            # Run all table generation
│
├── 01_descriptive.ipynb           # Descriptive statistics (Jupyter)
├── 02_outcomes.ipynb              # Outcome analysis (Jupyter)
├── 02b_secondary_analysis.ipynb   # Secondary analysis (Jupyter)
├── 05_mixed_effects.ipynb         # Mixed effects models (Jupyter)
│
├── codebook.md                    # Variable documentation
└── analysis.Rproj                 # RStudio project file
```

## Reproducing the Analysis

### Requirements

**R packages:**
```r
install.packages(c(
  "tidyverse",
  "jsonlite",
  "lme4",
  "lmerTest",
  "broom",
  "kableExtra",
  "dagitty"
))
```

**Python packages (for Jupyter notebooks):**
```
pandas
numpy
matplotlib
seaborn
statsmodels
```

### Running the Analysis

1. Open `analysis.Rproj` in RStudio
2. Run `00_setup.R` to load and preprocess data
3. Run `08_models.R` to fit statistical models
4. Run `run_thesis_figures.R` to generate all figures
5. Run `run_thesis_tables.R` to generate all tables

## Key Findings

- Participants moved toward the AI's position significantly more often than away (63.6% vs 36.4%, p = .048)
- Movement was stronger when the AI opposed participants' initial judgments (41.7%) compared to reinforcing them (16.7%)
- Claude showed stronger persuasive effects than Qwen, particularly when arguing for utilitarian positions

## Tables

All analysis tables are available in `tables/tables.md`, including:

| Table | Description |
|-------|-------------|
| 1–5 | Sample demographics, study design, balance checks, TIPI scores |
| 6–7 | Preregistered hypothesis tests (continuous and binary outcomes) |
| 8–9 | Full model coefficients |
| 10 | Direction of opinion change |
| 11–12 | Provider × Framework effects, exploratory analyses |
| 13–14 | Regression to mean analysis, H6 robustness checks |
| 15–17 | Self-reports, reasons for change, persuasion tactics |

## Data

The data files contain anonymized participant responses. See `codebook.md` for detailed variable descriptions.

## License

This analysis code is provided for academic purposes as part of a thesis project.
