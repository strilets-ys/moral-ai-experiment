# Analysis Tables

This document contains all analysis tables from the LLM Persuasion in Moral Judgments study.

---

## Table 1: Sample Demographics (N = 24)

All participants were native English speakers.

| Characteristic | Value |
|----------------|-------|
| N | 24 |
| Age, M (SD) | 37.5 (13.1) |
| Age range | 20–79 |
| **Gender** | |
|   Female | 14 (58.3%) |
|   Male | 10 (41.7%) |
| **Education** | |
|   High school | 3 (12.5%) |
|   Some college | 5 (20.8%) |
|   Bachelor's degree | 10 (41.7%) |
|   Master's degree | 5 (20.8%) |
|   Doctorate | 1 (4.2%) |
| AI trust (S-TIAS), M (SD) | 5.14 (1.39) |
| **AI usage frequency** | |
|   Sometimes | 7 (29.2%) |
|   Often | 12 (50.0%) |
|   Very often | 5 (20.8%) |

---

## Table 2: Study Design and Procedure

| Characteristic | Value |
|----------------|-------|
| **Experimental condition** | |
|   Control (neutral) | 6 (25.0%) |
|   Persuade | 4 (16.7%) |
|   Persuade + Demographics | 6 (25.0%) |
|   Persuade + Demographics + Personality | 8 (33.3%) |
| **LLM provider** | |
|   Claude (Anthropic) | 11 (45.8%) |
|   Qwen (Alibaba) | 13 (54.2%) |
| **Procedure** | |
|   Dilemmas rated per participant | 8 |
|   Dilemmas discussed per participant | 4 |
|   Turns per conversation, M (SD) | 9.1 (2.4) |
|   Turn range | 3–19 |
|   Session duration in min, M (SD) | 45.3 (6.0) |

---

## Table 3: Design Balance - Condition × LLM Provider

| Condition | Claude | Qwen | Total |
|-----------|--------|------|-------|
| Control | 3 | 3 | 6 |
| Persuade | 1 | 3 | 4 |
| Persuade + Demo | 3 | 3 | 6 |
| Persuade + Info | 4 | 4 | 8 |
| *Total* | 11 | 13 | 24 |

*Note.* Assignment to condition and model was randomised per participant. Cell sizes are therefore unequal at N = 24; this imbalance is accounted for in the mixed-effects models.

---

## Table 4: Balance of Participant Traits Across Arms

| Trait | Control | Persuade | +Demo | +Info | Spread |
|-------|---------|----------|-------|-------|--------|
| Age | 47.5 | 34.5 | 37.0 | 31.8 | 1.20 |
| Extraversion | 2.8 | 2.6 | 3.2 | 4.3 | 1.06 |
| Agreeableness | 5.7 | 5.6 | 5.8 | 6.1 | 0.43 |
| Conscientiousness | 5.5 | 5.8 | 6.3 | 6.3 | 0.80 |
| Emotional stability | 4.5 | 4.6 | 5.0 | 4.9 | 0.35 |
| Openness | 4.4 | 5.5 | 6.1 | 5.9 | 1.12 |
| Female (%) | 50 | 75 | 33 | 75 | -- |

*Note.* Arm sizes are 6, 4, 6 and 8. Spread is the range of arm means divided by the pooled standard deviation; values above roughly 0.5 indicate chance imbalance large enough to be worth adjusting for on precision grounds.

---

## Table 5: Big Five Trait Scores (TIPI)

| Trait | M (SD) | Observed range |
|-------|--------|----------------|
| Extraversion | 3.38 (1.60) | 1.0–7.0 |
| Agreeableness | 5.83 (1.17) | 3.5–7.0 |
| Conscientiousness | 6.02 (1.04) | 4.0–7.0 |
| Emotional stability | 4.77 (1.44) | 2.0–7.0 |
| Openness | 5.50 (1.48) | 1.5–7.0 |

*Note.* Each trait is the mean of two items (one reverse-scored) rated on a 1–7 scale (Gosling et al., 2003). Higher values indicate a stronger expression of the trait.

---

## Table 6: Preregistered Hypothesis Tests (Continuous Outcome)

| Hypothesis | b | SE | 95% CI | p |
|------------|---|----|---------|----|
| H1: Persuasion prompt (vs. control) | 0.42 | 0.42 | [-0.41, 1.25] | .337 |
| H2: Personalised (vs. generic) | -0.20 | 0.51 | [-1.21, 0.80] | .695 |
| H3: +Personality (vs. demographics only) | -0.05 | 0.48 | [-0.99, 0.89] | .915 |
| H4: Baseline extremity (within)ᵃ | -0.06 | 0.26 | [-0.57, 0.45] | .813 |
| H5: Discussed (vs. undiscussed)ᵃ | 0.36 | 0.16 | [0.05, 0.67] | .024 |
| H6: Opposing (vs. reinforcing) | 1.23 | 0.33 | [0.58, 1.87] | <.001 |

*Note.* Linear mixed models with participant random intercepts. Outcome: movement toward the AI position (rating points). n = 96 conversations, 24 participants.
ᵃ Outcome is magnitude of rating change (n = 192 ratings).

---

## Table 7: Preregistered Hypothesis Tests (Binary Outcome)

| Hypothesis | OR | 95% CI | z | p |
|------------|-----|---------|---|---|
| H1: Persuasion prompt (vs. control) | 1.42 | [0.44, 4.54] | 0.59 | .554 |
| H2: Personalised (vs. generic) | 1.18 | [0.29, 4.75] | 0.23 | .820 |
| H3: +Personality (vs. demographics only) | 0.89 | [0.26, 3.10] | -0.18 | .861 |
| H4: Baseline extremity (within) | 0.40 | [0.16, 0.98] | -2.01 | .045 |
| H5: Discussed (vs. undiscussed)ᵃ | 1.18 | [0.61, 2.26] | 0.48 | .630 |
| H6: Opposing (vs. reinforcing) | 3.86 | [1.39, 10.68] | 2.60 | .009 |

*Note.* Generalised linear mixed models (logit link) with participant random intercepts. Outcome: moved toward AI position (yes/no). OR = odds ratio. n = 96 conversations, 24 participants.
ᵃ Outcome is whether rating changed (n = 192 ratings).

---

## Table 8: Full Model Coefficients (Continuous Outcomes)

|  | M1: Movement | M2: Movement | M3: \|Change\| |
|--|--------------|--------------|----------------|
| Intercept | -0.62* (0.30) | -0.63* (0.30) | 1.17*** (0.23) |
| **Condition (nested orthogonal contrasts)** | | | |
|   Any persuasion vs. control (H1) | 0.42 (0.42) | 0.42 (0.43) | -0.04 (0.32) |
|   Personalised vs. generic (H2) | -0.20 (0.51) | -0.16 (0.54) | 0.55 (0.38) |
|   + Personality vs. demographics (H3) | -0.05 (0.48) | -0.04 (0.49) | 0.26 (0.36) |
| Opposing AI (H6) | 1.23*** (0.33) | 1.24*** (0.34) | |
| Provider: Claude | 0.79* (0.37) | 0.83* (0.38) | |
| Discussed (H5) | | | 0.36* (0.16) |
| Extremity | | | -0.26** (0.08) |
| Extremity, within participant | | -0.06 (0.26) | |
| Extremity, between participants | | -0.27 (0.56) | |
|   Within × opposing (H4) | | 0.23 (0.37) | |
|   Between × opposing | | 0.02 (0.73) | |
| **Random effects and sample** | | | |
|   Participant variance | 0.134 | 0.141 | 0.306 |
|   Dilemma variance | -- | -- | 0.084 |
|   Residual variance | 2.605 | 2.701 | 1.181 |
|   Observations | 96 | 96 | 192 |
|   Participants | 24 | 24 | 24 |

*Note.* Cells are b (SE). M1 and M2 use the 96 conversations; M3 uses all 192 ratings. *p<.05; **p<.01; ***p<.001.

---

## Table 9: Full Model Coefficients (Binary Outcomes)

|  | M1b: Moved | M2b: Moved | M3b: Changed |
|--|------------|------------|--------------|
| Intercept | -2.15*** (0.55) | -2.55*** (0.59) | 0.90* (0.44) |
| **Condition (nested orthogonal contrasts)** | | | |
|   Any persuasion vs. control (H1) | 0.35 (0.59) | 0.38 (0.61) | -0.62 (0.47) |
|   Personalised vs. generic (H2) | 0.16 (0.71) | 0.53 (0.80) | 0.69 (0.58) |
|   + Personality vs. demographics (H3) | -0.11 (0.63) | -0.01 (0.66) | 0.15 (0.53) |
| Opposing AI (H6) | 1.35** (0.52) | 1.51** (0.57) | |
| Provider: Claude | 0.94 (0.51) | 1.30* (0.55) | |
| Discussed (H5) | | | 0.16 (0.33) |
| Extremity | | | -0.68*** (0.18) |
| Extremity, within participant | | -0.93* (0.46) | |
| Extremity, between participants | | -1.31 (0.99) | |
|   Within × opposing (H4) | | 1.11 (0.59) | |
|   Between × opposing | | -0.44 (1.20) | |
| **Random effects and sample** | | | |
|   Participant variance | 0.057 | 0.000 | 0.311 |
|   Dilemma variance | -- | -- | 0.416 |
|   Observations | 96 | 96 | 192 |
|   Participants | 24 | 24 | 24 |

*Note.* Cells are b (SE) on the log-odds scale. *p<.05; **p<.01; ***p<.001.

---

## Table 10: Direction of Opinion Change

| Direction | n | % | p |
|-----------|---|---|---|
| Toward AI position | 28 | 63.6% | .048 |
| Away from AI position | 16 | 36.4% | |

*Note.* One-tailed binomial test against 50% null hypothesis (N = 44 participants who changed their rating).

---

## Table 11: Provider × Framework Effects

| Effect | b | SE | 95% CI | p |
|--------|---|----|---------|----|
| Provider (Claude) | 0.25 | 0.47 | [-0.67, 1.17] | .602 |
| Framework (Utilitarian) | -0.19 | 0.46 | [-1.09, 0.71] | .679 |
| Provider × Framework | 1.31 | 0.68 | [-0.02, 2.64] | .057 |

*Note.* Linear mixed model with participant random intercepts, controlling for AI stance. Reference categories: Qwen and deontological.

---

## Table 12: Exploratory Analyses

| Effect | b | SE | 95% CI | p |
|--------|---|----|---------|----|
| **Model A: Provider** | | | | |
|   Provider (Claude) | 0.79 | 0.37 | [0.07, 1.52] | .045 |
| **Model B: Provider × Framework** | | | | |
|   Provider (Claude) | 0.25 | 0.47 | [-0.67, 1.17] | .602 |
|   Framework (Utilitarian) | -0.19 | 0.46 | [-1.09, 0.71] | .679 |
|   Provider × Framework | 1.31 | 0.68 | [-0.02, 2.64] | .057 |
| **Model C: Engagement** | | | | |
|   Chat turns | 0.04 | 0.08 | [-0.11, 0.19] | .570 |
| **Model D: Dilemma characteristics** | | | | |
|   Dilemma source (Koerner) | 0.12 | 0.33 | [-0.53, 0.77] | .723 |
|   Contact level (Personal)ᵃ | -0.12 | 0.41 | [-0.92, 0.68] | .778 |
|   Harm type (Action) | 0.35 | 0.33 | [-0.30, 1.00] | .300 |

*Note.* Separate linear mixed models with participant random intercepts, controlling for AI stance and condition.
ᵃ Greene dilemmas only (n = 48).

---

## Table 13: Regression to the Mean Analysis

| Model | b | SE | 95% CI | t | p |
|-------|---|----|---------|----|---|
| **Undiscussed dilemmas only (n = 96)** | | | | | |
|   Extremity → \|change\| | -0.24 | 0.09 | [-0.41, -0.07] | -2.82 | .006 |
|   Extremity → RTM amount | 0.42 | 0.09 | [0.24, 0.59] | 4.67 | <.001 |
| **Discussed vs. undiscussed (all 192 ratings)** | | | | | |
|   Extremity (main effect) | 0.46 | 0.09 | [0.29, 0.63] | 5.29 | <.001 |
|   Discussed | -0.33 | 0.24 | [-0.80, 0.14] | -1.39 | .167 |
|   Extremity × discussed | 0.06 | 0.12 | [-0.17, 0.29] | 0.52 | .606 |
| **Discussed dilemmas only: controlling for stance (n = 96)** | | | | | |
|   Extremity | 0.48 | 0.12 | [0.24, 0.72] | 3.96 | <.001 |
|   Opposing stance | -0.01 | 0.35 | [-0.69, 0.67] | -0.04 | .970 |
|   Extremity × opposing | 0.07 | 0.17 | [-0.26, 0.40] | 0.43 | .670 |

*Note.* RTM amount = distance from midpoint before − distance after; positive values indicate movement toward the mean.

---

## Table 14: H6 Robustness Check (Excluding Ceiling Cases)

| Model | n | b | SE | OR | p |
|-------|---|---|----|----|---|
| **Continuous outcome (movement toward AI)** | | | | | |
|   Full sample (LMM) | 96 | 1.23 | 0.33 | -- | <.001 |
|   Excluding ceiling cases (LMM) | 79 | 1.35 | 0.40 | -- | .001 |
| **Binary outcome (moved toward AI: yes/no)** | | | | | |
|   Full sample (GLMM) | 96 | 1.35 | 0.52 | 3.86 | .009 |
|   Excluding ceiling cases (GLMM) | 79 | 0.76 | 0.53 | 2.14 | .154 |

*Note.* Ceiling cases are conversations where the participant could not move toward the AI because they were already at the extreme the AI argued for (17 cases, 17.7%).

---

## Table 15: Self-Reports and Actual Behavior

### Panel A: Self-reports by condition

| | Control (n=6) | Persuade (n=4) | +Demo (n=6) | +Info (n=8) | Overall (N=24) | p |
|-|---------------|----------------|-------------|-------------|----------------|---|
| Noticed persuasion | 83% | 50% | 67% | 100% | 79% | .135 |
| Self-reported change | 50% | 25% | 17% | 75% | 46% | .169 |

### Panel B: Self-reported vs. actual change

| Self-reported change | Moved toward AI: No | Moved toward AI: Yes |
|----------------------|---------------------|----------------------|
| No | 7 | 6 |
| Yes | 0 | 11 |

*Note.* Panel A: p-values from Fisher's exact tests. Panel B: Actual change defined as moving toward AI position on at least one dilemma.

---

## Table 16: Reasons for Judgment Change (n = 10)

| Category | n (%) | Representative quote |
|----------|-------|---------------------|
| New perspectives | 4 (40%) | "The discussions made me consider perspectives I had not thought of initially." (P45) |
| Deliberation process | 3 (30%) | "I changed my mind based on my back and forth with the AI about the different moral considerations." (P59) |
| Compelling arguments | 3 (30%) | "The AI made a good argument that if the nurse hit the switch, she would be directly involved in the death." (P60) |

*Note.* Descriptive categories from open-ended debrief responses. Categories were mutually exclusive.

---

## Table 17: Persuasion Tactics Identified by Participants (n = 19)

| Category | n (%) | Representative quote |
|----------|-------|---------------------|
| AI persistence | 7 (37%) | "It would not budge on its stance at all. Even if I brought up very good points, it just kept reinforcing the same thing." (P24) |
| Acknowledge & counter | 4 (21%) | "It kept saying that it understood my point of view, but disagreed with it and explained why." (P22) |
| Questioning tactics | 3 (16%) | "It would ask me a question to make me question my own point." (P54) |
| Emotional appeals | 3 (16%) | "It used emotional examples, such as discussing families or responsibilities." (P45) |
| Respectful persuasion | 2 (11%) | "It was done in a way which was considered and not pressurising." (P59) |

*Note.* Descriptive categories from open-ended debrief responses. Each response assigned to one primary category.

---

## Table 18: Classification of Candidate Controls

| Variable | Role in the DAG | Classification | Decision |
|----------|-----------------|----------------|----------|
| **Pre-exposure** | | | |
|   Dilemma features (type, action/omission) | Cause of Y only | Neutral, good for precision | Include |
|   Baseline rating R₀ | Cause of Y only | Neutral, good for precision | Include |
|   Age, gender, education | Cause of Y only | Neutral, good for precision | Include (H4: required) |
|   Personality (TIPI) | Cause of Y only | Neutral, good for precision | Include (H4: required) |
| **Post-exposure** | | | |
|   What the AI actually said | Mediator of X → Y | **Bad control** | Exclude |
|   Participant message count | Mediator of X → Y | **Bad control** | Exclude |
|   AI framework (is_utilitarian) | Collider on stance and R₀ | **Bad control** | Exclude |
|   Noticed persuasion | Descendant of Y | **Bad control** | Exclude |
|   Trust in AI (S-TIAS) | Descendant of Y | **Bad control** | Exclude |

*Note.* Following Cinelli, Forney and Pearl (2022). Bad controls are harmful: mediators remove part of the effect being estimated, and colliders and descendants of the outcome create spurious associations.

---

## Table 19: Covariate Decisions for Confirmatory Models

| Hypothesis | Contrast | Level | Required for identification | Recommended for precision |
|------------|----------|-------|----------------------------|---------------------------|
| H1 | Persuasive arms vs. control | Between | -- | Age |
| H2 | Persuade+Demo vs. Persuade | Between | -- | Age |
| H3 | +Info vs. Persuade+Demo | Between | -- | Age |
| H4 | Baseline extremity \|R₀-4\| | Within | Demographics, personality, dilemma features | -- |
| H5 | Discussed vs. undiscussed | Within | -- | Dilemma features |
| H6 | Opposing vs. reinforcing | Within | -- | Baseline rating, dilemma features |

*Note.* Condition, language model, stance and dilemma selection were assigned by the experimenter, so the empty set identifies their effects; H4 is the only observational contrast.
