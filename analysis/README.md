# LLM Persuasion in Moral Judgments: Analysis Repository

This repository contains the analysis code and data for a study examining whether large language models (LLMs) can influence human moral judgments through conversational persuasion.

## Project Structure

```
analysis/
├── data/                          # Data files (anonymized)
│   ├── data_long_renamed.csv      # Long format (one row per dilemma)
│   └── dilemma_metadata.json      # Dilemma characteristics
│
├── figures/
│   ├── thesis/                    # Final PDF figures for thesis (17 files)
│   └── system_prompts_example.pdf
│
├── tables/                        # LaTeX tables for thesis (19 files)
│
├── 00_setup.R                     # Data loading and preprocessing
├── 00_theme.R                     # ggplot2 theme for figures
├── 07_dags.R                      # DAG analysis
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

### Main Text
| File | Description |
|------|-------------|
| `tab_hypotheses.tex` | H1-H6 continuous outcomes |
| `tab_hypotheses_binary.tex` | H1-H6 binary outcomes |
| `tab_exploratory_main.tex` | Provider × Framework interaction |
| `tab_self_reports.tex` | Self-reports and actual vs. reported change |
| `tab_reasons_change.tex` | Reasons for judgment change |
| `tab_direction_change.tex` | Direction of opinion change |

### Appendix
| File | Description |
|------|-------------|
| `tab_exploratory_appendix.tex` | All exploratory models |
| `tab_persuasion_tactics_appendix.tex` | Persuasion tactics |
| `tab_demographics.tex` | Sample demographics |
| `tab_models.tex` / `tab_models_binary.tex` | Full model output |
| `tab_rtm.tex` | Regression to mean analysis |
| `tab_h6_robust.tex` | H6 robustness checks |
| + others (balance, controls, DAG adjustments, etc.) |

## Data

The data files contain anonymized participant responses. See `codebook.md` for detailed variable descriptions.

## License

This analysis code is provided for academic purposes as part of a thesis project.
