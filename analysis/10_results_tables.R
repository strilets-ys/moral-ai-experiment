# =============================================================================
# 10_results_tables.R - Results-chapter tables (LaTeX / booktabs)
# -----------------------------------------------------------------------------
# Reads the DAG-specified models from 08_models.R, so the tables, the forest
# plot (09_results_figures.R) and the notebook cannot drift apart.
#
#   tables/tab_hypotheses.tex  one row per hypothesis  (companion to Figure 7)
#   tables/tab_models.tex      full coefficients for the three primary models
# =============================================================================

source("08_models.R")
suppressMessages(library(kableExtra))

stars <- function(p) ifelse(p < .001, "***", ifelse(p < .01, "**",
                     ifelse(p < .05, "*", "")))
pstr  <- function(p) ifelse(p < .001, "$<$.001", sub("^0", "", sprintf("%.3f", p)))

# =============================================================================
# Table 1: hypothesis-level summary
# =============================================================================

grab <- function(m, term, label) {
  co <- summary(m)$coefficients
  data.frame(Hypothesis = label,
             b = co[term, 1], se = co[term, 2],
             df = co[term, 3], t = co[term, 4], p = co[term, 5],
             stringsAsFactors = FALSE)
}

hyp <- rbind(
  grab(m1_adj, "conditionC1_persuasion",      "H1\\quad Persuasion prompt vs.\\ control"),
  grab(m1_adj, "conditionC2_personal",        "H2\\quad Personalised vs.\\ generic persuasion"),
  grab(m1_adj, "conditionC3_info",            "H3\\quad Demographics + personality vs.\\ demographics only"),
  grab(m2_adj, "extremity_w",                 "H4\\quad Baseline extremity (within)"),
  grab(m3_adj, "had_chatTRUE",                "H5\\quad Discussed vs.\\ undiscussed\\textsuperscript{a}"),
  grab(m1_adj, "is_opposingTRUE",             "H6\\quad Opposing vs.\\ reinforcing")
)

hyp_tab <- data.frame(
  Hypothesis = hyp$Hypothesis,
  b   = sprintf("%.2f", hyp$b),
  SE  = sprintf("%.2f", hyp$se),
  CI  = sprintf("[%.2f, %.2f]", hyp$b - 1.96 * hyp$se, hyp$b + 1.96 * hyp$se),
  t   = sprintf("%.2f", hyp$t),
  p   = pstr(hyp$p),
  stringsAsFactors = FALSE
)

hyp_latex <- hyp_tab %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "r", "r", "c", "r", "r"),
      col.names = c("Hypothesis", "$b$", "SE", "95\\% CI", "$t$", "$p$"),
      caption = "Preregistered hypothesis tests from the mixed models.",
      label = "hypotheses", row.names = FALSE, linesep = "") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  footnote(
    general = paste(
      "Linear mixed models with a random intercept for participant;",
      "confidence intervals are Wald intervals and $p$-values use",
      "Satterthwaite degrees of freedom (lmerTest).",
      "The outcome is movement toward the AI position, in rating-scale points,",
      "on 96 conversations from 24 participants.",
      "H4 tests a within-participant association, as baseline extremity",
      "was measured rather than assigned."
    ),
    alphabet = c(
      paste("Outcome is the magnitude of rating change across all 192 ratings,",
            "since movement toward the AI is undefined for dilemmas that were",
            "never discussed.")
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(hyp_latex, "tables/tab_hypotheses.tex")
message("Saved: tables/tab_hypotheses.tex")

# =============================================================================
# Table 2: full coefficients for the three primary models
# =============================================================================

term_order <- c(
  "(Intercept)"                 = "Intercept",
  "conditionC1_persuasion"      = "\\quad Any persuasion vs.\\ control (H1)",
  "conditionC2_personal"        = "\\quad Personalised vs.\\ generic (H2)",
  "conditionC3_info"            = "\\quad + Personality vs.\\ demographics (H3)",
  "is_opposingTRUE"             = "Opposing AI (H6)",
  "is_claudeTRUE"               = "Provider: Claude",
  "had_chatTRUE"                = "Discussed (H5)",
  "extremity"                   = "Extremity",
  "extremity_w"                 = "Extremity, within participant",
  "extremity_b"                 = "Extremity, between participants",
  "is_opposingTRUE:extremity_w" = "\\quad Within $\\times$ opposing (H4)",
  "is_opposingTRUE:extremity_b" = "\\quad Between $\\times$ opposing"
)

cell <- function(m, term) {
  co <- summary(m)$coefficients
  if (!term %in% rownames(co)) return("")
  sprintf("%.2f%s (%.2f)", co[term, 1], stars(co[term, 5]), co[term, 2])
}

vc_of <- function(m, grp) {
  vc <- as.data.frame(VarCorr(m))
  v <- vc$vcov[vc$grp == grp]
  if (length(v) == 0) return("--")
  sprintf("%.3f", v)
}

mods <- list(m1_adj, m2_adj, m3_adj)

coef_block <- data.frame(
  Term = unname(term_order),
  M1 = vapply(names(term_order), function(t) cell(mods[[1]], t), ""),
  M2 = vapply(names(term_order), function(t) cell(mods[[2]], t), ""),
  M3 = vapply(names(term_order), function(t) cell(mods[[3]], t), ""),
  stringsAsFactors = FALSE
)

stat_block <- data.frame(
  Term = c("Participant variance", "Dilemma variance", "Residual variance",
           "Observations", "Participants"),
  M1 = c(vc_of(mods[[1]], "participant_id"), vc_of(mods[[1]], "dilemma"),
         vc_of(mods[[1]], "Residual"), "96", "24"),
  M2 = c(vc_of(mods[[2]], "participant_id"), vc_of(mods[[2]], "dilemma"),
         vc_of(mods[[2]], "Residual"), "96", "24"),
  M3 = c(vc_of(mods[[3]], "participant_id"), vc_of(mods[[3]], "dilemma"),
         vc_of(mods[[3]], "Residual"), "192", "24"),
  stringsAsFactors = FALSE
)

mod_tab <- rbind(coef_block, stat_block)
n_coef  <- nrow(coef_block)

mod_latex <- mod_tab %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "c", "c", "c"),
      col.names = c("", "M1: Movement", "M2: Movement", "M3: $|$Change$|$"),
      caption = "Mixed-model coefficients for the three primary models.",
      label = "models", row.names = FALSE, linesep = "") %>%
  kable_styling(latex_options = "hold_position", font_size = 9,
                full_width = FALSE) %>%
  add_header_above(c(" " = 1, "H1--H3, H6" = 1, "H4" = 1, "H5" = 1)) %>%
  pack_rows("Condition (nested orthogonal contrasts)", 2, 4) %>%
  pack_rows("Random effects and sample", n_coef + 1, nrow(mod_tab)) %>%
  row_spec(n_coef, extra_latex_after = "\\midrule") %>%
  footnote(
    general = paste(
      "Cells are $b$ (SE). M1 and M2 use the 96 conversations;",
      "M3 uses all 192 ratings, so movement toward the AI is replaced by the",
      "magnitude of rating change.",
      "Condition is coded with three nested orthogonal contrasts, so H1--H3 are",
      "answered from one model without discarding participants.",
      "The crossed dilemma intercept is estimable only in M3: over 96",
      "conversations its variance is exactly zero (singular), so it is dropped",
      "from M1 and M2 and reported here as a dash.",
      "Covariates were selected from the design DAG following Cinelli, Forney",
      "and Pearl (2022); because every exposure is randomised or blocked,",
      "they reduce residual variance rather than remove confounding.",
      "$^{*}p<.05$; $^{**}p<.01$; $^{***}p<.001$."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(mod_latex, "tables/tab_models.tex")
message("Saved: tables/tab_models.tex")

# =============================================================================
# Table 3: GLMM hypothesis-level summary (binary outcomes)
# =============================================================================

grab_glmm <- function(m, term, label) {
  co <- summary(m)$coefficients
  data.frame(Hypothesis = label,
             b = co[term, 1], se = co[term, 2],
             z = co[term, 3], p = co[term, 4],
             stringsAsFactors = FALSE)
}

hyp_glmm <- rbind(
  grab_glmm(m1b_adj, "conditionC1_persuasion",      "H1\\quad Persuasion prompt vs.\\ control"),
  grab_glmm(m1b_adj, "conditionC2_personal",        "H2\\quad Personalised vs.\\ generic persuasion"),
  grab_glmm(m1b_adj, "conditionC3_info",            "H3\\quad Demographics + personality vs.\\ demographics only"),
  grab_glmm(m2b_adj, "extremity_w",                 "H4\\quad Baseline extremity (within)"),
  grab_glmm(m3b_adj, "had_chatTRUE",                "H5\\quad Discussed vs.\\ undiscussed\\textsuperscript{a}"),
  grab_glmm(m1b_adj, "is_opposingTRUE",             "H6\\quad Opposing vs.\\ reinforcing")
)

hyp_glmm_tab <- data.frame(
  Hypothesis = hyp_glmm$Hypothesis,
  b   = sprintf("%.2f", hyp_glmm$b),
  SE  = sprintf("%.2f", hyp_glmm$se),
  OR  = sprintf("%.2f", exp(hyp_glmm$b)),
  CI  = sprintf("[%.2f, %.2f]", exp(hyp_glmm$b - 1.96 * hyp_glmm$se),
                                exp(hyp_glmm$b + 1.96 * hyp_glmm$se)),
  z   = sprintf("%.2f", hyp_glmm$z),
  p   = pstr(hyp_glmm$p),
  stringsAsFactors = FALSE
)

hyp_glmm_latex <- hyp_glmm_tab %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "r", "r", "r", "c", "r", "r"),
      col.names = c("Hypothesis", "$b$", "SE", "OR", "95\\% CI (OR)", "$z$", "$p$"),
      caption = "Preregistered hypothesis tests from the mixed models (binary outcomes).",
      label = "hypotheses_binary", row.names = FALSE, linesep = "") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  footnote(
    general = paste(
      "Generalised linear mixed models (logit link) with a random intercept for",
      "participant. The outcome is whether the participant moved toward the AI",
      "position (1) or not (0). OR = odds ratio; confidence intervals are Wald",
      "intervals on the odds-ratio scale.",
      "H4 tests a within-participant association."
    ),
    alphabet = c(
      paste("Outcome is whether the rating changed at all (1) or not (0) across",
            "all 192 ratings, since movement toward the AI is undefined for",
            "dilemmas that were never discussed.")
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(hyp_glmm_latex, "tables/tab_hypotheses_binary.tex")
message("Saved: tables/tab_hypotheses_binary.tex")

# =============================================================================
# Table 4: full GLMM coefficients for the three primary models
# =============================================================================

cell_glmm <- function(m, term) {
  co <- summary(m)$coefficients
  if (!term %in% rownames(co)) return("")
  sprintf("%.2f%s (%.2f)", co[term, 1], stars(co[term, 4]), co[term, 2])
}

mods_glmm <- list(m1b_adj, m2b_adj, m3b_adj)

coef_block_glmm <- data.frame(
  Term = unname(term_order),
  M1b = vapply(names(term_order), function(t) cell_glmm(mods_glmm[[1]], t), ""),
  M2b = vapply(names(term_order), function(t) cell_glmm(mods_glmm[[2]], t), ""),
  M3b = vapply(names(term_order), function(t) cell_glmm(mods_glmm[[3]], t), ""),
  stringsAsFactors = FALSE
)

stat_block_glmm <- data.frame(
  Term = c("Participant variance", "Dilemma variance",
           "Observations", "Participants"),
  M1b = c(vc_of(mods_glmm[[1]], "participant_id"), vc_of(mods_glmm[[1]], "dilemma"),
          "96", "24"),
  M2b = c(vc_of(mods_glmm[[2]], "participant_id"), vc_of(mods_glmm[[2]], "dilemma"),
          "96", "24"),
  M3b = c(vc_of(mods_glmm[[3]], "participant_id"), vc_of(mods_glmm[[3]], "dilemma"),
          "192", "24"),
  stringsAsFactors = FALSE
)

mod_glmm_tab <- rbind(coef_block_glmm, stat_block_glmm)
n_coef_glmm  <- nrow(coef_block_glmm)

mod_glmm_latex <- mod_glmm_tab %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "c", "c", "c"),
      col.names = c("", "M1b: Moved", "M2b: Moved", "M3b: Changed"),
      caption = "GLMM coefficients for the three primary models (binary outcomes).",
      label = "models_binary", row.names = FALSE, linesep = "") %>%
  kable_styling(latex_options = "hold_position", font_size = 9,
                full_width = FALSE) %>%
  add_header_above(c(" " = 1, "H1--H3, H6" = 1, "H4" = 1, "H5" = 1)) %>%
  pack_rows("Condition (nested orthogonal contrasts)", 2, 4) %>%
  pack_rows("Random effects and sample", n_coef_glmm + 1, nrow(mod_glmm_tab)) %>%
  row_spec(n_coef_glmm, extra_latex_after = "\\midrule") %>%
  footnote(
    general = paste(
      "Cells are $b$ (SE) on the log-odds scale. M1b and M2b use the 96",
      "conversations with outcome = moved toward AI (1) vs.\\ not (0);",
      "M3b uses all 192 ratings with outcome = any change (1) vs.\\ no change (0).",
      "Condition is coded with three nested orthogonal contrasts.",
      "M2b shows a singular fit (participant variance = 0).",
      "Covariates were selected from the design DAG following Cinelli, Forney",
      "and Pearl (2022).",
      "$^{*}p<.05$; $^{**}p<.01$; $^{***}p<.001$."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(mod_glmm_latex, "tables/tab_models_binary.tex")
message("Saved: tables/tab_models_binary.tex")

# =============================================================================
# Table 5: Regression to the mean check
# =============================================================================

rtm_rows <- rbind(
  grab(m_rtm_magnitude, "extremity", "Extremity $\\rightarrow$ $|$change$|$"),
  grab(m_rtm_by_extremity, "extremity", "Extremity $\\rightarrow$ RTM amount"),
  grab(m_rtm_interaction, "extremity", "Extremity (main effect)"),
  grab(m_rtm_interaction, "had_chatTRUE", "Discussed"),
  grab(m_rtm_interaction, "extremity:had_chatTRUE", "Extremity $\\times$ discussed"),
  grab(m_rtm_stance, "extremity", "Extremity"),
  grab(m_rtm_stance, "is_opposingTRUE", "Opposing stance"),
  grab(m_rtm_stance, "extremity:is_opposingTRUE", "Extremity $\\times$ opposing")
)

rtm_tab <- data.frame(
  Term = rtm_rows$Hypothesis,
  b   = sprintf("%.2f", rtm_rows$b),
  SE  = sprintf("%.2f", rtm_rows$se),
  CI  = sprintf("[%.2f, %.2f]", rtm_rows$b - 1.96 * rtm_rows$se,
                                 rtm_rows$b + 1.96 * rtm_rows$se),
  t   = sprintf("%.2f", rtm_rows$t),
  p   = pstr(rtm_rows$p),
  stringsAsFactors = FALSE
)

rtm_latex <- rtm_tab %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "r", "r", "c", "r", "r"),
      col.names = c("", "$b$", "SE", "95\\% CI", "$t$", "$p$"),
      caption = "Regression to the mean analysis.",
      label = "rtm", row.names = FALSE, linesep = "") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  pack_rows("Undiscussed dilemmas only (n = 96)", 1, 2) %>%
  pack_rows("Discussed vs. undiscussed (all 192 ratings)", 3, 5) %>%
  pack_rows("Discussed dilemmas only: controlling for stance (n = 96)", 6, 8) %>%
  footnote(
    general = paste(
      "RTM amount $=$ distance from midpoint before $-$ distance after;",
      "positive values indicate movement toward the mean.",
      "Extreme ratings change less in magnitude but move toward the mean when they change.",
      "RTM is similar in discussed and undiscussed dilemmas (non-significant interaction).",
      "Critically, opposing stance does not produce additional RTM beyond what extremity",
      "predicts, ruling out stance assignment as a confound."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(rtm_latex, "tables/tab_rtm.tex")
message("Saved: tables/tab_rtm.tex")

# =============================================================================
# Table: H6 robustness check (excluding ceiling cases)
# =============================================================================

# Count ceiling cases
n_ceiling <- sum(mdc$ceiling_case, na.rm = TRUE)
n_total <- nrow(mdc)

# Original H6 estimates
h6_orig_lmm <- grab(m1_adj, "is_opposingTRUE", "Full sample (LMM)")
h6_orig_glmm <- grab_glmm(m1b_adj, "is_opposingTRUE", "Full sample (GLMM)")

# Robust H6 estimates
h6_rob_lmm <- grab(m_h6_robust, "is_opposingTRUE", "Excluding ceiling (LMM)")
h6_rob_glmm <- grab_glmm(m_h6_robust_binary, "is_opposingTRUE", "Excluding ceiling (GLMM)")

h6_robust_tab <- data.frame(
  Model = c("Full sample (LMM)", "Excluding ceiling cases (LMM)",
            "Full sample (GLMM)", "Excluding ceiling cases (GLMM)"),
  n = c(n_total, n_total - n_ceiling, n_total, n_total - n_ceiling),
  b = c(sprintf("%.2f", h6_orig_lmm$b), sprintf("%.2f", h6_rob_lmm$b),
        sprintf("%.2f", h6_orig_glmm$b), sprintf("%.2f", h6_rob_glmm$b)),
  SE = c(sprintf("%.2f", h6_orig_lmm$se), sprintf("%.2f", h6_rob_lmm$se),
         sprintf("%.2f", h6_orig_glmm$se), sprintf("%.2f", h6_rob_glmm$se)),
  OR = c("--", "--",
         sprintf("%.2f", exp(h6_orig_glmm$b)), sprintf("%.2f", exp(h6_rob_glmm$b))),
  p = c(pstr(h6_orig_lmm$p), pstr(h6_rob_lmm$p),
        pstr(h6_orig_glmm$p), pstr(h6_rob_glmm$p)),
  stringsAsFactors = FALSE
)

h6_robust_latex <- h6_robust_tab %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "c", "r", "r", "r", "r"),
      col.names = c("Model", "$n$", "$b$", "SE", "OR", "$p$"),
      caption = sprintf("H6 robustness check: excluding ceiling cases (%d cases, %.1f\\%%).",
                        n_ceiling, 100 * n_ceiling / n_total),
      label = "h6_robust", row.names = FALSE, linesep = "") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  pack_rows("Continuous outcome (movement toward AI)", 1, 2) %>%
  pack_rows("Binary outcome (moved toward AI: yes/no)", 3, 4) %>%
  footnote(
    general = paste(
      "Ceiling cases are conversations where the participant could not move",
      "toward the AI because they were already at the extreme the AI argued for",
      "(e.g., rating = 7 when AI argued for high ratings).",
      "The H6 effect (opposing vs.\\\\ reinforcing) remains significant in the",
      "continuous model but becomes non-significant in the binary model,",
      "suggesting some of the binary effect was driven by ceiling constraints."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(h6_robust_latex, "tables/tab_h6_robust.tex")
message("Saved: tables/tab_h6_robust.tex")
