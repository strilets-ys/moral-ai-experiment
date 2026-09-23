# =============================================================================
# 07_models.R - Main hypothesis tests
# -----------------------------------------------------------------------------
# Control selection follows Cinelli, Forney & Pearl (2022),
# "A Crash Course in Good and Bad Controls".
#
#   All exposures (condition, provider, stance, discussed) are randomised or
#   blocked by design, so no covariate is *required* for identification
#   (H4 is the sole exception).  Every remaining candidate is a NEUTRAL control
#   -- included only if it is a cause of the outcome (variance reduction) and
#   excluded if it is a mediator, a collider, or a descendant of the outcome.
#
#   Included  : dilemma identity, AI stance, provider, baseline extremity
#   Excluded  : AI message content, participant message count, llm_framework
#               (collider), debrief_noticed_persuasion, debrief_stias_average
#               (both descendants of the outcome)
# =============================================================================

source("00_setup.R")
suppressMessages({
  library(lme4)
  library(lmerTest)
})

# -----------------------------------------------------------------------------
# Derived variables
# -----------------------------------------------------------------------------
# dilemma_type / dilemma_action are not stored as columns; they are encoded in
# the dilemma code.  Greene: G_{P|I}{A|O}_Name.  Koerner: K_{bg|bs}{A|O}_Name.

md <- data_long %>%
  mutate(
    movement_toward_ai = case_when(
      outcome == "Moved toward AI" ~ abs(rating_change),
      outcome == "Backfired"       ~ -abs(rating_change),
      TRUE                         ~ 0
    ),
    abs_change  = abs(rating_change),
    extremity   = abs(rating_pre - 4),
    is_opposing = stance_mode == "opposite",
    is_claude   = llm_provider == "anthropic",
    # Binary outcomes for GLMM
    moved_toward_ai = as.integer(outcome == "Moved toward AI"),
    any_change      = as.integer(rating_change != 0),

    dil_author     = ifelse(str_starts(dilemma, "G_"), "Greene", "Koerner"),
    dil_tag        = str_match(dilemma, "^[GK]_([A-Za-z]+)_")[, 2],
    dilemma_action = factor(ifelse(str_sub(dil_tag, -1) == "A", "Action", "Omission")),
    dilemma_type   = case_when(
      dil_author == "Greene" & str_sub(dil_tag, 1, 1) == "P" ~ "Personal",
      dil_author == "Greene" & str_sub(dil_tag, 1, 1) == "I" ~ "Impersonal",
      TRUE ~ str_sub(dil_tag, 1, 2)      # bg / bs for Koerner
    ),

    condition      = factor(condition,
                            levels = c("neutral", "persuade",
                                       "persuade_demo", "persuade_info")),
    participant_id = factor(participant_id),
    dilemma        = factor(dilemma)
  )

# Nested sequential contrasts: one model answers H1, H2 and H3 without
# discarding participants, and the three contrasts are mutually orthogonal.
contrasts(md$condition) <- cbind(
  C1_persuasion = c(-3/4,  1/4, 1/4, 1/4),   # H1  control vs any persuasion
  C2_personal   = c(   0, -2/3, 1/3, 1/3),   # H2  persuade vs personalised
  C3_info       = c(   0,    0, -1/2, 1/2)   # H3  + demo vs + demo & personality
)

# Chat subset, plus the within/between split of extremity used by H4.
# extremity_b is grand-mean centred so the stance main effect is the effect at
# average baseline extremity rather than at the impossible value extremity = 0.
mdc <- md %>%
  filter(had_chat) %>%
  group_by(participant_id) %>%
  mutate(extremity_b = mean(extremity),
         extremity_w = extremity - extremity_b) %>%
  ungroup() %>%
  mutate(extremity_b = extremity_b - mean(extremity_b))

message(sprintf("Model data: %d chat obs, %d participants, %d dilemmas",
                nrow(mdc), n_distinct(mdc$participant_id), n_distinct(mdc$dilemma)))

# -----------------------------------------------------------------------------
# M1: H1-H3 (condition), H6 (stance) and the provider contrast
# -----------------------------------------------------------------------------
# Crossed random intercepts absorb every dilemma-level feature -- wording,
# framework, personal/impersonal, action/omission -- without spending fixed
# degrees of freedom on 19 sparsely observed items.

m1_unadj <- lmer(movement_toward_ai ~ condition +
                   (1 | participant_id), data = mdc, REML = TRUE)

m1_adj   <- lmer(movement_toward_ai ~ condition + is_opposing + is_claude +
                   (1 | participant_id), data = mdc, REML = TRUE)

# Item variance check: with 19 dilemmas over 96 conversations the crossed
# dilemma intercept is estimated at exactly zero (singular).  It is therefore
# dropped from the conversation-level models and retained only in M3, which
# uses all 192 ratings.
m1_item  <- lmer(movement_toward_ai ~ condition + is_opposing + is_claude +
                   (1 | participant_id) + (1 | dilemma), data = mdc, REML = TRUE)

# -----------------------------------------------------------------------------
# M2: H4 (baseline extremity)
# -----------------------------------------------------------------------------
# Extremity is the one exposure that is NOT randomised, so it is the one place
# a genuine confounder adjustment is needed.  Splitting it into a within- and a
# between-participant component identifies the within effect free of every
# time-invariant participant confounder (age, gender, education, personality)
# without estimating those coefficients -- a stronger claim than adjusting for
# the handful of confounders that happen to be measured.
#
# The stance interaction is mandatory, not exploratory: on a 1-7 scale the room
# available to move toward the AI is 3 + extremity when it opposes and
# 3 - extremity when it reinforces, so extremity has mechanically opposite
# relations to the outcome in the two stance groups.

m2_unadj <- lmer(movement_toward_ai ~ extremity +
                   (1 | participant_id), data = mdc, REML = TRUE)

m2_adj   <- lmer(movement_toward_ai ~ is_opposing * extremity_w +
                   is_opposing * extremity_b + condition + is_claude +
                   (1 | participant_id), data = mdc, REML = TRUE)

# -----------------------------------------------------------------------------
# M3: H5 (discussed vs undiscussed)
# -----------------------------------------------------------------------------
# Uses all 192 ratings.  movement_toward_ai is undefined without an AI stance,
# so the outcome is the magnitude of change.  had_chat varies within
# participant, so the participant random intercept carries the contrast.

m3_unadj <- lmer(abs_change ~ had_chat + (1 | participant_id),
                 data = md, REML = TRUE)

m3_adj   <- lmer(abs_change ~ had_chat + condition + extremity +
                   (1 | participant_id) + (1 | dilemma),
                 data = md, REML = TRUE)

# -----------------------------------------------------------------------------
# Regression to the mean check
# -----------------------------------------------------------------------------
# If regression to the mean is present, extreme ratings should show LARGER
# changes toward the middle (positive extremity coefficient).
# H4 predicts the opposite: midpoint ratings show larger changes (negative).
#
# Test: compare extremity effect in undiscussed vs discussed dilemmas.
# - Undiscussed: pure regression to mean (no AI involvement)
# - Discussed: regression to mean + any AI effect
# - Interaction: does AI discussion change the extremity-change relationship?

# Undiscussed dilemmas only: extremity -> magnitude
md_undiscussed <- md %>% filter(!had_chat)
m_rtm_magnitude <- lmer(abs_change ~ extremity + (1 | participant_id),
                        data = md_undiscussed, REML = TRUE)

# Proper RTM test: did the rating get CLOSER to the midpoint?
# distance_pre = |rating_pre - 4|, distance_post = |rating_post - 4|
# moved_toward_mean = 1 if distance_post < distance_pre
md <- md %>%
  mutate(
    rating_pre_c = rating_pre - 4,
    distance_pre = abs(rating_pre - 4),
    distance_post = abs(rating_post - 4),
    moved_toward_mean = as.integer(distance_post < distance_pre),
    # How much closer to the mean (positive = moved toward, negative = moved away)
    rtm_amount = distance_pre - distance_post
  )
md_undiscussed <- md %>% filter(!had_chat)

# Binary: did they move toward the mean?
m_rtm_binary <- glmer(moved_toward_mean ~ 1 + (1 | participant_id),
                      data = md_undiscussed, family = binomial)

# Continuous: how much did they move toward/away from the mean?
m_rtm_amount <- lmer(rtm_amount ~ 1 + (1 | participant_id),
                     data = md_undiscussed, REML = TRUE)

# Does extremity predict moving toward mean?
m_rtm_by_extremity <- lmer(rtm_amount ~ extremity + (1 | participant_id),
                           data = md_undiscussed, REML = TRUE)

# Interaction: does RTM differ by discussion status?
m_rtm_interaction <- lmer(rtm_amount ~ extremity * had_chat + condition +
                            (1 | participant_id) + (1 | dilemma),
                          data = md, REML = TRUE)

# For discussed dilemmas: control for stance
# Opposing stance naturally pushes toward middle (confounded with RTM)
# Reinforcing stance pushes away from middle
md_discussed <- md %>% filter(had_chat)
m_rtm_stance <- lmer(rtm_amount ~ extremity * is_opposing +
                       (1 | participant_id),
                     data = md_discussed, REML = TRUE)

# -----------------------------------------------------------------------------
# H6 Robustness: exclude ceiling/floor cases
# -----------------------------------------------------------------------------
# Ceiling: can't move toward AI because already at the extreme AI argues for
# - If AI reinforces high rating (rating_pre > 4, !is_opposing) and rating = 7
# - If AI reinforces low rating (rating_pre < 4, !is_opposing) and rating = 1
#
# Determine AI's argued position based on stance and participant's rating
mdc <- mdc %>%
  mutate(
    ai_argues_high = case_when(
      rating_pre > 4 & !is_opposing ~ TRUE,   # reinforcing high
      rating_pre < 4 & is_opposing ~ TRUE,    # opposing low = argues high
      rating_pre > 4 & is_opposing ~ FALSE,   # opposing high = argues low
      rating_pre < 4 & !is_opposing ~ FALSE,  # reinforcing low
      rating_pre == 4 ~ NA                    # midpoint, ambiguous
    ),
    ceiling_case = (ai_argues_high == TRUE & rating_pre == 7) |
                   (ai_argues_high == FALSE & rating_pre == 1),
    ceiling_case = ifelse(is.na(ceiling_case), FALSE, ceiling_case)
  )

# Count ceiling cases
n_ceiling <- sum(mdc$ceiling_case, na.rm = TRUE)
message(sprintf("\nCeiling/floor cases: %d of %d (%.1f%%)",
                n_ceiling, nrow(mdc), 100 * n_ceiling / nrow(mdc)))

# H6 model excluding ceiling cases
mdc_no_ceiling <- mdc %>% filter(!ceiling_case)

m_h6_robust <- lmer(movement_toward_ai ~ condition + is_opposing + is_claude +
                      (1 | participant_id), data = mdc_no_ceiling, REML = TRUE)

m_h6_robust_binary <- glmer(moved_toward_ai ~ condition + is_opposing + is_claude +
                              (1 | participant_id), data = mdc_no_ceiling, family = binomial)

# -----------------------------------------------------------------------------
# GLMM: Binary outcomes (moved toward AI = 1, else = 0)
# -----------------------------------------------------------------------------
# These models complement the continuous DVs above with a binary framing:
# did the participant move toward the AI position at all?

# M1b: H1-H3 (condition), H6 (stance) - binary
m1b_unadj <- glmer(moved_toward_ai ~ condition +
                     (1 | participant_id), data = mdc, family = binomial)

m1b_adj   <- glmer(moved_toward_ai ~ condition + is_opposing + is_claude +
                     (1 | participant_id), data = mdc, family = binomial)

# M2b: H4 (baseline extremity) - binary
m2b_unadj <- glmer(moved_toward_ai ~ extremity +
                     (1 | participant_id), data = mdc, family = binomial)

m2b_adj   <- glmer(moved_toward_ai ~ is_opposing * extremity_w +
                     is_opposing * extremity_b + condition + is_claude +
                     (1 | participant_id), data = mdc, family = binomial)

# M3b: H5 (discussed vs undiscussed) - binary
# Uses any_change since moved_toward_ai is undefined for undiscussed dilemmas
m3b_unadj <- glmer(any_change ~ had_chat + (1 | participant_id),
                   data = md, family = binomial)

m3b_adj   <- glmer(any_change ~ had_chat + condition + extremity +
                     (1 | participant_id) + (1 | dilemma),
                   data = md, family = binomial)

# -----------------------------------------------------------------------------
# Report
# -----------------------------------------------------------------------------
show_model <- function(m, label) {
  cat("\n=====", label, "=====\n")
  if (isSingular(m, tol = 1e-4)) cat("  [singular fit]\n")
  print(round(summary(m)$coefficients, 3))
  vc <- as.data.frame(VarCorr(m))
  cat("  variance: ",
      paste(sprintf("%s=%.3f", vc$grp, vc$vcov), collapse = "  "), "\n")
}

message("\n============ LINEAR MIXED MODELS (continuous DV) ============")
show_model(m1_unadj, "M1 unadjusted  (H1-H3)")
show_model(m1_adj,   "M1 adjusted    (H1-H3, H6)")
cat("\n  item-variance check, (1|dilemma) added: ",
    sprintf("%.4f", as.data.frame(VarCorr(m1_item))$vcov[
      as.data.frame(VarCorr(m1_item))$grp == "dilemma"]), "\n")
show_model(m2_unadj, "M2 unadjusted  (H4)")
show_model(m2_adj,   "M2 adjusted    (H4)")
show_model(m3_unadj, "M3 unadjusted  (H5)")
show_model(m3_adj,   "M3 adjusted    (H5)")

message("\n============ REGRESSION TO THE MEAN CHECK ============")
show_model(m_rtm_magnitude, "Extremity -> |change| (undiscussed only)")
message("\n--- Proper RTM: did rating get closer to midpoint? ---")
show_model(m_rtm_binary, "Binary: P(moved toward mean) - undiscussed")
show_model(m_rtm_amount, "Continuous: distance_pre - distance_post (undiscussed)")
show_model(m_rtm_by_extremity, "Does extremity predict RTM amount? (undiscussed)")
show_model(m_rtm_interaction, "RTM interaction: extremity x had_chat")
show_model(m_rtm_stance, "Discussed only: RTM by stance (extremity x is_opposing)")

message("\n============ H6 ROBUSTNESS: EXCLUDING CEILING CASES ============")
show_model(m_h6_robust, "H6 robust (LMM, no ceiling)")
show_model(m_h6_robust_binary, "H6 robust (GLMM, no ceiling)")

message("\n============ GENERALIZED LINEAR MIXED MODELS (binary DV) ============")
show_model(m1b_unadj, "M1b unadjusted (H1-H3, binary)")
show_model(m1b_adj,   "M1b adjusted   (H1-H3, H6, binary)")
show_model(m2b_unadj, "M2b unadjusted (H4, binary)")
show_model(m2b_adj,   "M2b adjusted   (H4, binary)")
show_model(m3b_unadj, "M3b unadjusted (H5, binary)")
show_model(m3b_adj,   "M3b adjusted   (H5, binary)")

models <- list(
  # LMM (continuous)
  m1_unadj = m1_unadj, m1_adj = m1_adj, m1_item = m1_item,
  m2_unadj = m2_unadj, m2_adj = m2_adj,
  m3_unadj = m3_unadj, m3_adj = m3_adj,
  # Regression to the mean
  m_rtm_magnitude = m_rtm_magnitude,
  m_rtm_binary = m_rtm_binary, m_rtm_amount = m_rtm_amount,
  m_rtm_by_extremity = m_rtm_by_extremity, m_rtm_interaction = m_rtm_interaction,
  m_rtm_stance = m_rtm_stance,
  # H6 robustness
  m_h6_robust = m_h6_robust, m_h6_robust_binary = m_h6_robust_binary,
  # GLMM (binary)
  m1b_unadj = m1b_unadj, m1b_adj = m1b_adj,
  m2b_unadj = m2b_unadj, m2b_adj = m2b_adj,
  m3b_unadj = m3b_unadj, m3b_adj = m3b_adj
)
saveRDS(models, "models.rds")
message("\nSaved: models.rds")
