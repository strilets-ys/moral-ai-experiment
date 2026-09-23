# =============================================================================
# Thesis Descriptive Tables (LaTeX / booktabs)
#
# Generates the descriptive statistics tables for the thesis. Content is
# deliberately kept complementary to the Procedure and Recruitment sections,
# which already describe the study protocol, eligibility, and compensation
# in prose. Tables report what the prose does not: who the sample was, how
# they scored on the trait measures, how conditions were balanced, and what
# participants actually did (as opposed to what they were instructed to do).
# =============================================================================

source("00_setup.R")
source("00_theme.R")
library(kableExtra)

if (!dir.exists("tables")) dir.create("tables")

n_total <- nrow(data)

# n (pct) with a LaTeX-escaped percent sign
fmt_n_pct <- function(n, total) {
  n <- ifelse(is.na(n), 0L, as.integer(n))
  sprintf("%d (%.1f\\%%)", n, n / total * 100)
}
fmt_m_sd <- function(x, digits = 2) {
  sprintf(paste0("%.", digits, "f (%.", digits, "f)"),
          mean(x, na.rm = TRUE), sd(x, na.rm = TRUE))
}

count_of <- function(col, value) sum(data[[col]] == value, na.rm = TRUE)

# =============================================================================
# Table 1: Sample characteristics
# =============================================================================

age_m  <- mean(data$demographics_age, na.rm = TRUE)
age_sd <- sd(data$demographics_age, na.rm = TRUE)

demo_df <- data.frame(
  Characteristic = c(
    "Age, M (SD)",
    "Age range",
    "AI trust (S-TIAS), M (SD)",
    "Female", "Male",
    "High school", "Some college", "Bachelor's degree",
    "Master's degree", "Doctorate",
    "Sometimes", "Often", "Very often"
  ),
  Value = c(
    sprintf("%.1f (%.1f)", age_m, age_sd),
    sprintf("%d--%d", min(data$demographics_age, na.rm = TRUE),
            max(data$demographics_age, na.rm = TRUE)),
    fmt_m_sd(data$debrief_stias_average),
    fmt_n_pct(count_of("demographics_gender", "female"), n_total),
    fmt_n_pct(count_of("demographics_gender", "male"), n_total),
    fmt_n_pct(count_of("demographics_education", "high_school"), n_total),
    fmt_n_pct(count_of("demographics_education", "some_college"), n_total),
    fmt_n_pct(count_of("demographics_education", "bachelor"), n_total),
    fmt_n_pct(count_of("demographics_education", "master"), n_total),
    fmt_n_pct(count_of("demographics_education", "doctorate"), n_total),
    fmt_n_pct(count_of("debrief_ai_usage_frequency", "sometimes"), n_total),
    fmt_n_pct(count_of("debrief_ai_usage_frequency", "often"), n_total),
    fmt_n_pct(count_of("debrief_ai_usage_frequency", "very_often"), n_total)
  ),
  stringsAsFactors = FALSE
)

demo_latex <- demo_df %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      col.names = c("Characteristic", "Value"),
      caption = "Sample characteristics ($N = 24$).",
      label = "demographics") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  pack_rows("Gender", 4, 5) %>%
  pack_rows("Highest education", 6, 10) %>%
  pack_rows("Self-reported AI use", 11, 13) %>%
  footnote(
    general = paste(
      "AI trust was measured with the three-item Short Trust in Automation",
      "Scale (S-TIAS) on a 1--7 scale, administered at debriefing.",
      "No participant reported using AI ``never'' or ``rarely''."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(demo_latex, "tables/tab_demographics.tex")
message("Saved: tables/tab_demographics.tex")

# =============================================================================
# Table 2: TIPI personality traits
# =============================================================================

tipi_traits <- c(
  "Extraversion"        = "tipi_extraversion",
  "Agreeableness"       = "tipi_agreeableness",
  "Conscientiousness"   = "tipi_conscientiousness",
  "Emotional stability" = "tipi_emotional_stability",
  "Openness"            = "tipi_openness"
)

tipi_df <- data.frame(
  Trait = names(tipi_traits),
  MSD = vapply(tipi_traits, function(v) fmt_m_sd(data[[v]]), character(1)),
  Range = vapply(tipi_traits, function(v) {
    sprintf("%.1f--%.1f", min(data[[v]], na.rm = TRUE),
            max(data[[v]], na.rm = TRUE))
  }, character(1)),
  stringsAsFactors = FALSE, row.names = NULL
)

tipi_latex <- tipi_df %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE, align = c("l", "c", "c"),
      col.names = c("Trait", "M (SD)", "Observed range"),
      caption = "Big Five trait scores from the Ten-Item Personality Inventory ($N = 24$).",
      label = "tipi") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  footnote(
    general = paste(
      "Each trait is the mean of two items (one reverse-scored) rated on a",
      "1--7 scale (Gosling et al., 2003). Higher values indicate a stronger",
      "expression of the trait. In the \\\\emph{Persuade + Demographics +",
      "Personality} condition these scores were passed to the model as part",
      "of the participant profile."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(tipi_latex, "tables/tab_tipi.tex")
message("Saved: tables/tab_tipi.tex")

# =============================================================================
# Table 3: Condition x LLM provider allocation
# =============================================================================

balance <- data %>%
  mutate(
    Condition = factor(recode(condition, !!!condition_labels),
                       levels = condition_order),
    Provider = recode(llm_provider,
                      "anthropic" = "Claude", "qwen" = "Qwen")
  ) %>%
  count(Condition, Provider) %>%
  pivot_wider(names_from = Provider, values_from = n, values_fill = 0) %>%
  arrange(Condition) %>%
  mutate(Total = Claude + Qwen)

balance_df <- rbind(
  data.frame(Condition = as.character(balance$Condition),
             Claude = balance$Claude, Qwen = balance$Qwen,
             Total = balance$Total, stringsAsFactors = FALSE),
  data.frame(Condition = "\\textit{Total}",
             Claude = sum(balance$Claude), Qwen = sum(balance$Qwen),
             Total = sum(balance$Total), stringsAsFactors = FALSE)
)

balance_latex <- balance_df %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", "c", "c", "c"),
      col.names = c("Condition", "Claude", "Qwen", "Total"),
      caption = "Allocation of participants to experimental conditions and language models.",
      label = "design_balance") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  add_header_above(c(" " = 1, "Language model" = 2, " " = 1)) %>%
  row_spec(nrow(balance_df) - 1, hline_after = TRUE) %>%
  footnote(
    general = paste(
      "Assignment to condition and model was randomised per participant.",
      "Cell sizes are therefore unequal at $N = 24$; this imbalance is",
      "accounted for in the mixed-effects models."
    ),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(balance_latex, "tables/tab_design_balance.tex")
message("Saved: tables/tab_design_balance.tex")

# =============================================================================
# Table 4: Observed engagement by condition
#
# The Procedure section states what participants were *instructed* to do
# (>= 3 messages, prompted to proceed at 4.5 min or 6 messages, ~52 min
# estimated total). This table reports what they actually did.
#
# NOTE ON TURN COUNTING: the exported chat_turn_count_* columns (and hence
# data_long$chat_turns) count EVERY message in the conversation, the model's
# included. The model always opens with an argument and the exchange strictly
# alternates, so total turns = 2 * participant messages + 1. Because the
# instructions given to participants were phrased in participant messages,
# that is reported as the primary column here; turn counts are parsed from
# the raw transcripts rather than inferred from the identity above.
# =============================================================================

library(jsonlite)

msg_counts <- do.call(rbind, lapply(seq_len(nrow(data)), function(i) {
  tr <- fromJSON(data$chat_transcripts_json[i], simplifyVector = FALSE)
  do.call(rbind, lapply(tr, function(e) {
    senders <- vapply(e$turns, function(t) t$sender, character(1))
    data.frame(participant_id = data$participant_id[i],
               n_user  = sum(senders == "user"),
               n_total = length(senders),
               stringsAsFactors = FALSE)
  }))
}))

stopifnot(nrow(msg_counts) == 96)

msg_counts <- msg_counts %>%
  left_join(data %>% dplyr::select(participant_id, condition), by = "participant_id") %>%
  mutate(Condition = factor(recode(condition, !!!condition_labels),
                            levels = condition_order))

engagement <- msg_counts %>%
  group_by(Condition) %>%
  summarise(
    n_conv = n(),
    p_msg  = fmt_m_sd(n_user, 1),
    p_rng  = sprintf("%d--%d", min(n_user), max(n_user)),
    turns  = fmt_m_sd(n_total, 1),
    .groups = "drop"
  )

durations <- data %>%
  mutate(
    Condition = factor(recode(condition, !!!condition_labels),
                       levels = condition_order),
    dur = as.numeric(difftime(as.POSIXct(completed_at),
                              as.POSIXct(created_at), units = "mins"))
  ) %>%
  group_by(Condition) %>%
  summarise(n_part = n(), dur = fmt_m_sd(dur, 1), .groups = "drop")

eng_df <- engagement %>%
  left_join(durations, by = "Condition") %>%
  transmute(Condition = as.character(Condition),
            n_part, n_conv, p_msg, p_rng, turns, dur)

all_dur <- data %>%
  mutate(dur = as.numeric(difftime(as.POSIXct(completed_at),
                                   as.POSIXct(created_at), units = "mins")))

eng_df <- rbind(
  eng_df,
  data.frame(
    Condition = "\\textit{Overall}",
    n_part = nrow(data), n_conv = nrow(msg_counts),
    p_msg = fmt_m_sd(msg_counts$n_user, 1),
    p_rng = sprintf("%d--%d", min(msg_counts$n_user), max(msg_counts$n_user)),
    turns = fmt_m_sd(msg_counts$n_total, 1),
    dur = fmt_m_sd(all_dur$dur, 1),
    stringsAsFactors = FALSE
  )
)

pct_min <- 100 * mean(msg_counts$n_user >= 3)
pct_cap <- 100 * mean(msg_counts$n_user >= 6)

eng_latex <- eng_df %>%
  kbl(format = "latex", booktabs = TRUE, escape = FALSE,
      align = c("l", rep("c", 6)),
      col.names = c("Condition", "$n$", "Conversations",
                    "M (SD)", "Range", "M (SD)", "M (SD)"),
      caption = "Observed engagement with the discussion phase, by condition.",
      label = "engagement") %>%
  kable_styling(latex_options = "hold_position", font_size = 10,
                full_width = FALSE) %>%
  add_header_above(c(" " = 3, "Participant messages" = 2,
                     "Total turns" = 1, "Session (min)" = 1)) %>%
  row_spec(nrow(eng_df) - 1, hline_after = TRUE) %>%
  footnote(
    general = sprintf(paste(
      "Participant messages counts only messages written by the participant.",
      "Total turns additionally counts the model's replies: the model opened",
      "every conversation with an argument and the exchange then strictly",
      "alternated, so total turns $=2\\\\times$ participant messages $+\\\\,1$.",
      "Each participant discussed four dilemmas, giving 96 conversations.",
      "%.1f\\\\%% of conversations met the encouraged minimum of three participant",
      "messages, and %.1f\\\\%% reached the six-message point at which participants",
      "were prompted to move on. Session duration covers consent to debriefing",
      "and can be compared against the 52-minute estimate used to set compensation."
    ), pct_min, pct_cap),
    general_title = "Note.", footnote_as_chunk = FALSE,
    threeparttable = TRUE, escape = FALSE
  )

writeLines(eng_latex, "tables/tab_engagement.tex")
message("Saved: tables/tab_engagement.tex")

message("\nAll descriptive tables written to tables/")
