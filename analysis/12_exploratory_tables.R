# =============================================================================
# 12_exploratory_tables.R - Tables for Exploratory Analyses
# -----------------------------------------------------------------------------
# Produces LaTeX tables for the exploratory analysis section.
#
#   tables/tab_provider.tex        Provider effect (Claude vs Qwen)
#   tables/tab_engagement.tex      Engagement metrics (chat turns)
#   tables/tab_dilemma_types.tex   Dilemma type effects
#   tables/tab_effect_sizes.tex    Effect sizes summary
# =============================================================================

source("08_models.R")
suppressMessages(library(kableExtra))

stars <- function(p) ifelse(p < .001, "***", ifelse(p < .01, "**",
                     ifelse(p < .05, "*", "")))
pstr  <- function(p) ifelse(p < .001, "$<$.001", sub("^0", "", sprintf("%.3f", p)))

# =============================================================================
# Table: Provider Effect (Claude vs Qwen)
# =============================================================================

message("\n=== PROVIDER EFFECT ===")

# Prepare data
provider_data <- mdc %>%
  mutate(
    provider = factor(ifelse(is_claude, "Claude", "Qwen"), levels = c("Claude", "Qwen")),
    moved_binary = as.integer(outcome == "Moved toward AI")
  )

# Descriptive stats
provider_desc <- provider_data %>%
  group_by(provider) %>%
  summarise(
    n = n(),
    n_moved = sum(outcome == "Moved toward AI"),
    pct_moved = n_moved / n * 100,
    mean_movement = mean(movement_toward_ai),
    sd_movement = sd(movement_toward_ai),
    .groups = "drop"
  )
print(provider_desc)

# Statistical tests
claude_mv <- provider_data %>% filter(provider == "Claude") %>% pull(movement_toward_ai)
qwen_mv <- provider_data %>% filter(provider == "Qwen") %>% pull(movement_toward_ai)

# T-test (continuous)
t_res <- t.test(claude_mv, qwen_mv)

# Wilcoxon (non-parametric)
wilcox_res <- wilcox.test(claude_mv, qwen_mv, exact = FALSE)

# Proportion test (binary)
prop_res <- prop.test(
  c(sum(provider_data$provider == "Claude" & provider_data$outcome == "Moved toward AI"),
    sum(provider_data$provider == "Qwen" & provider_data$outcome == "Moved toward AI")),
  c(sum(provider_data$provider == "Claude"),
    sum(provider_data$provider == "Qwen"))
)

# Cohen's d
pooled_sd <- sqrt(((length(claude_mv)-1)*sd(claude_mv)^2 +
                   (length(qwen_mv)-1)*sd(qwen_mv)^2) /
                  (length(claude_mv) + length(qwen_mv) - 2))
cohens_d <- (mean(claude_mv) - mean(qwen_mv)) / pooled_sd

# LMM with provider as predictor (from primary models - extract coefficient)
# The is_claude coefficient from m1_adj gives us the provider effect
provider_coef <- summary(m1_adj)$coefficients["is_claudeTRUE", ]

# Build table
provider_tab <- data.frame(
  Analysis = c(
    "\\textbf{Descriptive statistics}",
    "\\hspace{1em}Claude: $n$, moved (\\%)",
    "\\hspace{1em}Qwen: $n$, moved (\\%)",
    "\\hspace{1em}Claude: $M$ (SD)",
    "\\hspace{1em}Qwen: $M$ (SD)",
    "\\textbf{Inferential tests}",
    "\\hspace{1em}Mixed model (LMM)",
    "\\hspace{1em}Independent $t$-test",
    "\\hspace{1em}Wilcoxon rank-sum",
    "\\hspace{1em}Proportion test ($\\chi^2$)",
    "\\textbf{Effect size}",
    "\\hspace{1em}Cohen's $d$"
  ),
  Statistic = c(
    "",
    sprintf("%d, %d (%.1f\\%%)", provider_desc$n[1], provider_desc$n_moved[1], provider_desc$pct_moved[1]),
    sprintf("%d, %d (%.1f\\%%)", provider_desc$n[2], provider_desc$n_moved[2], provider_desc$pct_moved[2]),
    sprintf("%.2f (%.2f)", provider_desc$mean_movement[1], provider_desc$sd_movement[1]),
    sprintf("%.2f (%.2f)", provider_desc$mean_movement[2], provider_desc$sd_movement[2]),
    "",
    sprintf("$b$ = %.2f, SE = %.2f, $t$ = %.2f", provider_coef[1], provider_coef[2], provider_coef[4]),
    sprintf("$t$(%.1f) = %.2f", t_res$parameter, t_res$statistic),
    sprintf("$W$ = %.0f", wilcox_res$statistic),
    sprintf("$\\chi^2$(1) = %.2f", prop_res$statistic),
    "",
    sprintf("%.2f", cohens_d)
  ),
  p = c(
    "", "", "", "", "",
    "",
    pstr(provider_coef[5]),
    pstr(t_res$p.value),
    pstr(wilcox_res$p.value),
    pstr(prop_res$p.value),
    "",
    ""
  ),
  stringsAsFactors = FALSE
)

provider_latex <- provider_tab %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "r", "r"),
      col.names = c("", "Statistic", "$p$"),
      caption = "Provider effect: Claude vs.\\ Qwen.",
      label = "provider", row.names = FALSE, linesep = "") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  footnote(
    general = paste(
      "Movement toward AI is the signed change in rating toward the AI's argued position.",
      "The mixed model coefficient is from M1 (controlling for condition and stance).",
      "Claude showed significantly greater movement toward the AI position than Qwen,",
      "with a small-to-medium effect size."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(provider_latex, "tables/tab_provider.tex")
message("Saved: tables/tab_provider.tex")

# =============================================================================
# Table: Engagement Metrics (Chat Turns)
# =============================================================================

message("\n=== ENGAGEMENT METRICS ===")

# Correlation
cor_pearson <- cor.test(mdc$chat_turns, mdc$movement_toward_ai)
cor_spearman <- cor.test(mdc$chat_turns, mdc$movement_toward_ai, method = "spearman")

# Compare by outcome
moved_turns <- mdc %>% filter(outcome == "Moved toward AI") %>% pull(chat_turns)
not_moved_turns <- mdc %>% filter(outcome != "Moved toward AI") %>% pull(chat_turns)
t_turns <- t.test(moved_turns, not_moved_turns)

# LMM with chat_turns as predictor
m_engagement <- lmer(movement_toward_ai ~ chat_turns + condition + is_opposing + is_claude +
                       (1 | participant_id), data = mdc, REML = TRUE)
engage_coef <- summary(m_engagement)$coefficients["chat_turns", ]

# Descriptive by outcome
turns_desc <- mdc %>%
  mutate(outcome_simple = ifelse(outcome == "Moved toward AI", "Moved toward AI", "Did not move")) %>%
  group_by(outcome_simple) %>%
  summarise(
    n = n(),
    mean_turns = mean(chat_turns),
    sd_turns = sd(chat_turns),
    .groups = "drop"
  )

engagement_tab <- data.frame(
  Analysis = c(
    "\\textbf{Descriptive statistics}",
    "\\hspace{1em}Overall: $M$ (SD), range",
    "\\hspace{1em}Moved toward AI: $M$ (SD)",
    "\\hspace{1em}Did not move: $M$ (SD)",
    "\\textbf{Correlation with movement}",
    "\\hspace{1em}Pearson $r$",
    "\\hspace{1em}Spearman $\\rho$",
    "\\textbf{Group comparison}",
    "\\hspace{1em}Independent $t$-test",
    "\\textbf{Mixed model}",
    "\\hspace{1em}Chat turns $\\rightarrow$ movement"
  ),
  Statistic = c(
    "",
    sprintf("%.1f (%.1f), %d--%d", mean(mdc$chat_turns), sd(mdc$chat_turns),
            min(mdc$chat_turns), max(mdc$chat_turns)),
    sprintf("%.1f (%.1f)", turns_desc$mean_turns[turns_desc$outcome_simple == "Moved toward AI"],
            turns_desc$sd_turns[turns_desc$outcome_simple == "Moved toward AI"]),
    sprintf("%.1f (%.1f)", turns_desc$mean_turns[turns_desc$outcome_simple == "Did not move"],
            turns_desc$sd_turns[turns_desc$outcome_simple == "Did not move"]),
    "",
    sprintf("$r$ = %.2f", cor_pearson$estimate),
    sprintf("$\\rho$ = %.2f", cor_spearman$estimate),
    "",
    sprintf("$t$(%.1f) = %.2f", t_turns$parameter, t_turns$statistic),
    "",
    sprintf("$b$ = %.3f, SE = %.3f", engage_coef[1], engage_coef[2])
  ),
  p = c(
    "", "", "", "",
    "",
    pstr(cor_pearson$p.value),
    pstr(cor_spearman$p.value),
    "",
    pstr(t_turns$p.value),
    "",
    pstr(engage_coef[5])
  ),
  stringsAsFactors = FALSE
)

engagement_latex <- engagement_tab %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "r", "r"),
      col.names = c("", "Statistic", "$p$"),
      caption = "Engagement metrics: conversation length and persuasion.",
      label = "engagement", row.names = FALSE, linesep = "") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  footnote(
    general = paste(
      "Chat turns is the number of message exchanges in each conversation.",
      "Movement toward AI is the signed rating change toward the AI position.",
      "Conversation length was not associated with persuasion outcomes."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(engagement_latex, "tables/tab_engagement.tex")
message("Saved: tables/tab_engagement.tex")

# =============================================================================
# Table: Dilemma Type Effects
# =============================================================================

message("\n=== DILEMMA TYPE EFFECTS ===")

# Add dilemma type
dilemma_data <- mdc %>%
  mutate(
    dilemma_category = case_when(
      grepl("^G_P", dilemma) ~ "Personal",
      grepl("^G_I", dilemma) ~ "Impersonal",
      grepl("^K_", dilemma) ~ "Koerner"
    ),
    dilemma_category = factor(dilemma_category, levels = c("Personal", "Impersonal", "Koerner")),
    action_omission = case_when(
      grepl("A_", dilemma) ~ "Action",
      grepl("O_", dilemma) ~ "Omission"
    ),
    action_omission = factor(action_omission, levels = c("Action", "Omission"))
  )

# Descriptive by category
cat_desc <- dilemma_data %>%
  filter(!is.na(dilemma_category)) %>%
  group_by(dilemma_category) %>%
  summarise(
    n = n(),
    n_moved = sum(outcome == "Moved toward AI"),
    pct_moved = n_moved / n * 100,
    mean_movement = mean(movement_toward_ai),
    sd_movement = sd(movement_toward_ai),
    .groups = "drop"
  )

# Kruskal-Wallis for category
kw_cat <- kruskal.test(movement_toward_ai ~ dilemma_category,
                        data = dilemma_data %>% filter(!is.na(dilemma_category)))

# Action vs Omission
ao_data <- dilemma_data %>% filter(!is.na(action_omission))
ao_desc <- ao_data %>%
  group_by(action_omission) %>%
  summarise(
    n = n(),
    mean_movement = mean(movement_toward_ai),
    sd_movement = sd(movement_toward_ai),
    .groups = "drop"
  )

action_mv <- ao_data %>% filter(action_omission == "Action") %>% pull(movement_toward_ai)
omission_mv <- ao_data %>% filter(action_omission == "Omission") %>% pull(movement_toward_ai)
wilcox_ao <- wilcox.test(action_mv, omission_mv, exact = FALSE)

dilemma_tab <- data.frame(
  Analysis = c(
    "\\textbf{By dilemma category}",
    "\\hspace{1em}Personal: $n$, $M$ (SD)",
    "\\hspace{1em}Impersonal: $n$, $M$ (SD)",
    "\\hspace{1em}Koerner: $n$, $M$ (SD)",
    "\\hspace{1em}Kruskal-Wallis $H$",
    "\\textbf{Action vs.\\ omission}",
    "\\hspace{1em}Action: $n$, $M$ (SD)",
    "\\hspace{1em}Omission: $n$, $M$ (SD)",
    "\\hspace{1em}Wilcoxon $W$"
  ),
  Statistic = c(
    "",
    sprintf("%d, %.2f (%.2f)", cat_desc$n[1], cat_desc$mean_movement[1], cat_desc$sd_movement[1]),
    sprintf("%d, %.2f (%.2f)", cat_desc$n[2], cat_desc$mean_movement[2], cat_desc$sd_movement[2]),
    sprintf("%d, %.2f (%.2f)", cat_desc$n[3], cat_desc$mean_movement[3], cat_desc$sd_movement[3]),
    sprintf("$H$(2) = %.2f", kw_cat$statistic),
    "",
    sprintf("%d, %.2f (%.2f)", ao_desc$n[1], ao_desc$mean_movement[1], ao_desc$sd_movement[1]),
    sprintf("%d, %.2f (%.2f)", ao_desc$n[2], ao_desc$mean_movement[2], ao_desc$sd_movement[2]),
    sprintf("$W$ = %.0f", wilcox_ao$statistic)
  ),
  p = c(
    "", "", "", "",
    pstr(kw_cat$p.value),
    "", "", "",
    pstr(wilcox_ao$p.value)
  ),
  stringsAsFactors = FALSE
)

dilemma_latex <- dilemma_tab %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "r", "r"),
      col.names = c("", "Statistic", "$p$"),
      caption = "Dilemma type effects on persuasion.",
      label = "dilemma_types", row.names = FALSE, linesep = "") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  footnote(
    general = paste(
      "Personal = Greene high-contact dilemmas; Impersonal = Greene low-contact dilemmas;",
      "Koerner = everyday moral dilemmas.",
      "Action dilemmas involve actively causing harm; omission dilemmas involve failing to prevent harm.",
      "No significant differences were found across dilemma types."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(dilemma_latex, "tables/tab_dilemma_types.tex")
message("Saved: tables/tab_dilemma_types.tex")

# =============================================================================
# Table: Effect Sizes Summary
# =============================================================================

message("\n=== EFFECT SIZES ===")

# Helper function
cohens_d_calc <- function(x, y) {
  nx <- length(x)
  ny <- length(y)
  pooled_sd <- sqrt(((nx - 1) * sd(x)^2 + (ny - 1) * sd(y)^2) / (nx + ny - 2))
  (mean(x) - mean(y)) / pooled_sd
}

interpret_d <- function(d) {
  abs_d <- abs(d)
  if (abs_d < 0.2) return("negligible")
  if (abs_d < 0.5) return("small")
  if (abs_d < 0.8) return("medium")
  return("large")
}

# Calculate all effect sizes
# H6: Opposing vs Reinforcing
opposing_mv <- mdc %>% filter(is_opposing == TRUE) %>% pull(movement_toward_ai)
reinforcing_mv <- mdc %>% filter(is_opposing == FALSE) %>% pull(movement_toward_ai)
d_h6 <- cohens_d_calc(opposing_mv, reinforcing_mv)

# Provider
d_provider <- cohens_d_calc(claude_mv, qwen_mv)

# H5: Discussed vs Undiscussed
discussed_ch <- md %>% filter(had_chat == TRUE) %>% pull(abs_change)
undiscussed_ch <- md %>% filter(had_chat == FALSE) %>% pull(abs_change)
d_h5 <- cohens_d_calc(discussed_ch, undiscussed_ch)

# Dilemma types
personal_mv <- dilemma_data %>% filter(dilemma_category == "Personal") %>% pull(movement_toward_ai)
impersonal_mv <- dilemma_data %>% filter(dilemma_category == "Impersonal") %>% pull(movement_toward_ai)
koerner_mv <- dilemma_data %>% filter(dilemma_category == "Koerner") %>% pull(movement_toward_ai)
d_pers_impers <- cohens_d_calc(personal_mv, impersonal_mv)
d_action_omission <- cohens_d_calc(action_mv, omission_mv)

effect_tab <- data.frame(
  Comparison = c(
    "H6: Opposing vs.\\ reinforcing AI",
    "H5: Discussed vs.\\ undiscussed",
    "Provider: Claude vs.\\ Qwen",
    "Personal vs.\\ impersonal dilemmas",
    "Action vs.\\ omission dilemmas"
  ),
  Group1_M = c(
    sprintf("%.2f", mean(opposing_mv)),
    sprintf("%.2f", mean(discussed_ch)),
    sprintf("%.2f", mean(claude_mv)),
    sprintf("%.2f", mean(personal_mv)),
    sprintf("%.2f", mean(action_mv))
  ),
  Group1_SD = c(
    sprintf("%.2f", sd(opposing_mv)),
    sprintf("%.2f", sd(discussed_ch)),
    sprintf("%.2f", sd(claude_mv)),
    sprintf("%.2f", sd(personal_mv)),
    sprintf("%.2f", sd(action_mv))
  ),
  Group2_M = c(
    sprintf("%.2f", mean(reinforcing_mv)),
    sprintf("%.2f", mean(undiscussed_ch)),
    sprintf("%.2f", mean(qwen_mv)),
    sprintf("%.2f", mean(impersonal_mv)),
    sprintf("%.2f", mean(omission_mv))
  ),
  Group2_SD = c(
    sprintf("%.2f", sd(reinforcing_mv)),
    sprintf("%.2f", sd(undiscussed_ch)),
    sprintf("%.2f", sd(qwen_mv)),
    sprintf("%.2f", sd(impersonal_mv)),
    sprintf("%.2f", sd(omission_mv))
  ),
  d = c(
    sprintf("%.2f", d_h6),
    sprintf("%.2f", d_h5),
    sprintf("%.2f", d_provider),
    sprintf("%.2f", d_pers_impers),
    sprintf("%.2f", d_action_omission)
  ),
  Interpretation = c(
    interpret_d(d_h6),
    interpret_d(d_h5),
    interpret_d(d_provider),
    interpret_d(d_pers_impers),
    interpret_d(d_action_omission)
  ),
  stringsAsFactors = FALSE
)

effect_latex <- effect_tab %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "r", "r", "r", "r", "r", "l"),
      col.names = c("Comparison", "$M_1$", "$SD_1$", "$M_2$", "$SD_2$", "$d$", "Size"),
      caption = "Effect sizes (Cohen's $d$) for key comparisons.",
      label = "effect_sizes", row.names = FALSE, linesep = "") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  footnote(
    general = paste(
      "Cohen's $d$ computed using pooled standard deviation.",
      "Conventional thresholds: $|d| < 0.2$ = negligible, $0.2$--$0.5$ = small,",
      "$0.5$--$0.8$ = medium, $> 0.8$ = large.",
      "Group 1 is the first-named group in each comparison."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(effect_latex, "tables/tab_effect_sizes.tex")
message("Saved: tables/tab_effect_sizes.tex")

# =============================================================================
# Table: Feedback/Debrief Analysis
# =============================================================================

message("\n=== FEEDBACK ANALYSIS ===")

# Create clean condition labels (matching run_thesis_figures.R)
condition_labels <- c(
  "neutral" = "Control",
  "persuade" = "Persuade",
  "persuade_demo" = "Persuade + Demo",
  "persuade_info" = "Persuade + Info"
)
condition_order <- c("Control", "Persuade", "Persuade + Demo", "Persuade + Info")

data <- data %>%
  mutate(
    condition_clean = recode(condition, !!!condition_labels),
    condition_clean = factor(condition_clean, levels = condition_order)
  )

# Debrief data by condition
debrief_data <- data %>%
  group_by(condition_clean) %>%
  summarise(
    n = n(),
    noticed_n = sum(debrief_noticed_persuasion == TRUE, na.rm = TRUE),
    noticed_pct = noticed_n / n * 100,
    changed_n = sum(debrief_changed_mind == TRUE, na.rm = TRUE),
    changed_pct = changed_n / n * 100,
    .groups = "drop"
  )

# Overall stats
overall_noticed <- sum(data$debrief_noticed_persuasion == TRUE, na.rm = TRUE)
overall_noticed_pct <- overall_noticed / nrow(data) * 100
overall_changed <- sum(data$debrief_changed_mind == TRUE, na.rm = TRUE)
overall_changed_pct <- overall_changed / nrow(data) * 100

# Fisher's exact test for noticed persuasion by condition
noticed_matrix <- matrix(
  c(debrief_data$noticed_n, debrief_data$n - debrief_data$noticed_n),
  nrow = 2, byrow = TRUE
)
fisher_noticed <- fisher.test(noticed_matrix)

# Fisher's exact test for self-reported change by condition
changed_matrix <- matrix(
  c(debrief_data$changed_n, debrief_data$n - debrief_data$changed_n),
  nrow = 2, byrow = TRUE
)
fisher_changed <- fisher.test(changed_matrix)

# Relationship between self-reported and actual behavioral change
# Compute at participant level - convert IDs to character for matching
participant_outcomes <- aggregate(
  cbind(any_moved = outcome == "Moved toward AI", movement = movement_toward_ai) ~ participant_id,
  data = mdc,
  FUN = function(x) if(is.logical(x)) any(x) else mean(x)
)
participant_outcomes$participant_id <- as.character(participant_outcomes$participant_id)

# Create lookup for debrief data
debrief_lookup <- data.frame(
  participant_id = as.character(data$participant_id),
  noticed = data$debrief_noticed_persuasion,
  changed = data$debrief_changed_mind
)

# Merge participant outcomes with debrief data
participant_level <- merge(participant_outcomes, debrief_lookup, by = "participant_id")

# McNemar/agreement between self-reported and actual change
agreement_tab <- table(
  "Self-reported" = participant_level$changed,
  "Actual behavioral" = participant_level$any_moved > 0
)

# Proportion agreeing
agree_n <- sum(diag(agreement_tab))
agree_pct <- agree_n / sum(agreement_tab) * 100

# Correlation between noticed persuasion and movement (at observation level)
# Create lookup and merge with mdc
mdc_df <- as.data.frame(mdc)
mdc_df$participant_id_char <- as.character(mdc_df$participant_id)
mdc_with_debrief <- merge(mdc_df, debrief_lookup,
                          by.x = "participant_id_char", by.y = "participant_id",
                          all.x = TRUE)

cor_noticed_move <- cor.test(
  as.numeric(mdc_with_debrief$noticed),
  mdc_with_debrief$movement_toward_ai
)

cor_selfreport_move <- cor.test(
  as.numeric(mdc_with_debrief$changed),
  mdc_with_debrief$movement_toward_ai
)

# Build table
feedback_tab <- data.frame(
  Analysis = c(
    "\\textbf{Noticed persuasion by condition}",
    "\\hspace{1em}Control",
    "\\hspace{1em}Persuade",
    "\\hspace{1em}Persuade + Demo",
    "\\hspace{1em}Persuade + Info",
    "\\hspace{1em}Overall",
    "\\hspace{1em}Fisher's exact test",
    "\\textbf{Self-reported mind change}",
    "\\hspace{1em}Control",
    "\\hspace{1em}Persuade",
    "\\hspace{1em}Persuade + Demo",
    "\\hspace{1em}Persuade + Info",
    "\\hspace{1em}Overall",
    "\\hspace{1em}Fisher's exact test",
    "\\textbf{Self-report vs.\\ behavioral change}",
    "\\hspace{1em}Agreement rate",
    "\\hspace{1em}$r$ (self-report, movement)",
    "\\hspace{1em}$r$ (noticed, movement)"
  ),
  Statistic = c(
    "",
    sprintf("%d/%d (%.0f\\%%)", debrief_data$noticed_n[1], debrief_data$n[1], debrief_data$noticed_pct[1]),
    sprintf("%d/%d (%.0f\\%%)", debrief_data$noticed_n[2], debrief_data$n[2], debrief_data$noticed_pct[2]),
    sprintf("%d/%d (%.0f\\%%)", debrief_data$noticed_n[3], debrief_data$n[3], debrief_data$noticed_pct[3]),
    sprintf("%d/%d (%.0f\\%%)", debrief_data$noticed_n[4], debrief_data$n[4], debrief_data$noticed_pct[4]),
    sprintf("%d/%d (%.0f\\%%)", overall_noticed, nrow(data), overall_noticed_pct),
    "",
    "",
    sprintf("%d/%d (%.0f\\%%)", debrief_data$changed_n[1], debrief_data$n[1], debrief_data$changed_pct[1]),
    sprintf("%d/%d (%.0f\\%%)", debrief_data$changed_n[2], debrief_data$n[2], debrief_data$changed_pct[2]),
    sprintf("%d/%d (%.0f\\%%)", debrief_data$changed_n[3], debrief_data$n[3], debrief_data$changed_pct[3]),
    sprintf("%d/%d (%.0f\\%%)", debrief_data$changed_n[4], debrief_data$n[4], debrief_data$changed_pct[4]),
    sprintf("%d/%d (%.0f\\%%)", overall_changed, nrow(data), overall_changed_pct),
    "",
    "",
    sprintf("%.0f\\%% (%d/%d)", agree_pct, agree_n, sum(agreement_tab)),
    sprintf("$r$ = %.2f", cor_selfreport_move$estimate),
    sprintf("$r$ = %.2f", cor_noticed_move$estimate)
  ),
  p = c(
    "", "", "", "", "", "",
    pstr(fisher_noticed$p.value),
    "", "", "", "", "", "",
    pstr(fisher_changed$p.value),
    "", "",
    pstr(cor_selfreport_move$p.value),
    pstr(cor_noticed_move$p.value)
  ),
  stringsAsFactors = FALSE
)

feedback_latex <- feedback_tab %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "r", "r"),
      col.names = c("", "Statistic", "$p$"),
      caption = "Participant feedback: persuasion awareness and self-reported change.",
      label = "feedback", row.names = FALSE, linesep = "") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  footnote(
    general = paste(
      "Noticed persuasion = participant reported awareness of AI's persuasive intent.",
      "Self-reported change = participant believed they changed their mind.",
      "Agreement rate shows concordance between self-reported and actual behavioral change.",
      "Correlations computed at the rating level (n = 96 chat interactions)."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(feedback_latex, "tables/tab_feedback.tex")
message("Saved: tables/tab_feedback.tex")

message("\nExploratory analysis tables written to tables/")
