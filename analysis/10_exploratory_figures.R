# =============================================================================
# 10_exploratory_figures.R - Figures for Exploratory Analyses
# -----------------------------------------------------------------------------
# Produces publication-quality figures for the exploratory analysis section.
#
#   fig_11_provider_effect.pdf     Claude vs Qwen comparison
#   fig_12_engagement_turns.pdf    Chat turns vs movement
#   fig_13_effect_sizes.pdf        Effect sizes summary
#   fig_14_dilemma_types.pdf       Dilemma type comparison
#   fig_15_within_participant.pdf  Within-participant patterns
# =============================================================================

source("07_models.R")
source("00_theme.R")
suppressMessages(library(patchwork))

# Override save function to use standard PDF instead of cairo
save_thesis_fig <- function(filename, plot = last_plot(),
                            width = 6.5, height = 4.5) {
  filepath <- file.path("figures", "thesis", filename)
  ggsave(filepath, plot = plot, width = width, height = height,
         device = pdf)
  message(sprintf("Saved: %s", filepath))
}

pfmt <- function(p) ifelse(p < .001, "p < .001",
                           paste0("p = ", sub("^0", "", sprintf("%.3f", p))))

# =============================================================================
# Figure 11: Provider Effect (Claude vs Qwen)
# =============================================================================

provider_data <- mdc %>%
  mutate(
    provider = factor(ifelse(is_claude, "Claude", "Qwen"),
                      levels = c("Claude", "Qwen")),
    sign = factor(case_when(
      movement_toward_ai > 0 ~ "Moved toward AI",
      movement_toward_ai < 0 ~ "Backfired",
      TRUE ~ "No Change"
    ), levels = outcome_levels)
  )

# Stats
provider_stats <- provider_data %>%
  group_by(provider) %>%
  summarise(
    n = n(),
    m = mean(movement_toward_ai),
    sd = sd(movement_toward_ai),
    pos = mean(movement_toward_ai > 0) * 100,
    zero = mean(movement_toward_ai == 0) * 100,
    neg = mean(movement_toward_ai < 0) * 100,
    .groups = "drop"
  ) %>%
  mutate(lab = sprintf("n = %d,  M = %+.2f\n%.0f%% toward AI\n%.0f%% no change\n%.0f%% backfired",
                       n, m, pos, zero, neg))

provider_counts <- provider_data %>% count(provider, movement_toward_ai, sign)

# T-test for caption
claude_mv <- provider_data %>% filter(provider == "Claude") %>% pull(movement_toward_ai)
qwen_mv <- provider_data %>% filter(provider == "Qwen") %>% pull(movement_toward_ai)
t_prov <- t.test(claude_mv, qwen_mv)

# Cohen's d
pooled_sd <- sqrt(((length(claude_mv)-1)*sd(claude_mv)^2 +
                   (length(qwen_mv)-1)*sd(qwen_mv)^2) /
                  (length(claude_mv) + length(qwen_mv) - 2))
d_provider <- (mean(claude_mv) - mean(qwen_mv)) / pooled_sd

pal_provider <- c("Claude" = "#E67E22", "Qwen" = "#3498DB")

fig11 <- ggplot(provider_counts, aes(x = movement_toward_ai, y = n, fill = sign)) +
  geom_col(width = 0.78) +
  geom_vline(xintercept = 0, colour = "gray45", linewidth = 0.3) +
  geom_text(data = provider_counts %>% filter(n > 0), aes(label = n),
            vjust = -0.45, size = 2.5, colour = "gray30") +
  geom_point(data = provider_stats, aes(x = m, y = -1.8), inherit.aes = FALSE,
             shape = 18, size = 3, colour = tu_red) +
  geom_text(data = provider_stats, aes(x = 5.5, y = Inf, label = lab),
            inherit.aes = FALSE, hjust = 1, vjust = 1.1,
            size = 2.7, colour = "gray30", lineheight = 1.2) +
  scale_fill_manual(values = palette_outcomes, name = NULL,
                    breaks = rev(outcome_levels)) +
  scale_x_continuous(breaks = -5:5, limits = c(-5.6, 5.6)) +
  scale_y_continuous(expand = expansion(mult = c(0.10, 0.30))) +
  facet_wrap(~provider, ncol = 1) +
  labs(title = "Rating movement toward the AI, by LLM provider",
       subtitle = "Each bar counts conversations; the red diamond marks the group mean",
       caption = sprintf("Claude vs. Qwen: t = %.2f, %s, Cohen's d = %.2f",
                         t_prov$statistic, pfmt(t_prov$p.value), d_provider),
       x = "Movement toward the AI position (rating points)",
       y = "Conversations") +
  theme_thesis() +
  theme(panel.grid.major.x = element_blank())

save_thesis_fig("fig_11_provider_effect.pdf", fig11, width = 6.5, height = 5.4)

# =============================================================================
# Figure 12: Engagement (Chat Turns) vs Movement
# =============================================================================

engagement_data <- mdc %>%
  mutate(
    sign = factor(case_when(
      movement_toward_ai > 0 ~ "Moved toward AI",
      movement_toward_ai < 0 ~ "Backfired",
      TRUE ~ "No Change"
    ), levels = outcome_levels)
  )

cor_res <- cor.test(engagement_data$chat_turns, engagement_data$movement_toward_ai)

fig12 <- ggplot(engagement_data, aes(x = chat_turns, y = movement_toward_ai)) +
  geom_hline(yintercept = 0, colour = "gray45", linewidth = 0.3) +
  geom_jitter(aes(colour = sign), width = 0.3, height = 0.15,
              size = 2.5, alpha = 0.7) +
  geom_smooth(method = "lm", se = TRUE, colour = "gray30",
              fill = "gray80", linewidth = 0.8, linetype = "dashed") +
  scale_colour_manual(values = palette_outcomes, name = "Outcome",
                      breaks = rev(outcome_levels)) +
  scale_x_continuous(breaks = seq(2, 20, 2)) +
  scale_y_continuous(breaks = seq(-6, 6, 2), limits = c(-6.2, 6.2)) +
  labs(title = "Conversation length does not predict persuasion",
       subtitle = sprintf("Pearson r = %.2f, %s", cor_res$estimate, pfmt(cor_res$p.value)),
       caption = "Points jittered slightly; dashed line is linear fit with 95% CI.",
       x = "Number of chat turns",
       y = "Movement toward the AI position") +
  theme_thesis()

save_thesis_fig("fig_12_engagement_turns.pdf", fig12, width = 6.5, height = 4.5)

# =============================================================================
# Figure 13: Effect Sizes Summary
# =============================================================================

# Calculate effect sizes
cohens_d_calc <- function(x, y) {
  nx <- length(x)
  ny <- length(y)
  pooled_sd <- sqrt(((nx - 1) * sd(x)^2 + (ny - 1) * sd(y)^2) / (nx + ny - 2))
  (mean(x) - mean(y)) / pooled_sd
}

# H6: Opposing vs Reinforcing
opposing_mv <- mdc %>% filter(is_opposing == TRUE) %>% pull(movement_toward_ai)
reinforcing_mv <- mdc %>% filter(is_opposing == FALSE) %>% pull(movement_toward_ai)
d_h6 <- cohens_d_calc(opposing_mv, reinforcing_mv)

# Provider
d_prov <- cohens_d_calc(claude_mv, qwen_mv)

# H5: Discussed vs Undiscussed
discussed_ch <- md %>% filter(had_chat == TRUE) %>% pull(abs_change)
undiscussed_ch <- md %>% filter(had_chat == FALSE) %>% pull(abs_change)
d_h5 <- cohens_d_calc(discussed_ch, undiscussed_ch)

effect_data <- tibble(
  comparison = c("H6: Opposing vs.\nReinforcing AI",
                 "Provider:\nClaude vs. Qwen",
                 "H5: Discussed vs.\nUndiscussed"),
  d = c(d_h6, d_prov, d_h5),
  significant = c(TRUE, TRUE, TRUE)
) %>%
  mutate(
    comparison = factor(comparison, levels = rev(comparison)),
    interpretation = case_when(
      abs(d) < 0.2 ~ "negligible",
      abs(d) < 0.5 ~ "small",
      abs(d) < 0.8 ~ "medium",
      TRUE ~ "large"
    ),
    label = sprintf("d = %.2f (%s)", d, interpretation)
  )

fig13 <- ggplot(effect_data, aes(x = d, y = comparison)) +
  geom_vline(xintercept = 0, colour = "gray45", linewidth = 0.4) +
  geom_vline(xintercept = c(0.2, 0.5, 0.8), colour = "gray80",
             linewidth = 0.3, linetype = "dashed") +
  geom_segment(aes(x = 0, xend = d, yend = comparison, colour = d > 0),
               linewidth = 1.5, show.legend = FALSE) +
  geom_point(aes(colour = d > 0), size = 4, show.legend = FALSE) +
  geom_text(aes(label = label), hjust = ifelse(effect_data$d > 0, -0.1, 1.1),
            size = 3.2, colour = "gray20") +
  scale_colour_manual(values = c("FALSE" = col_control, "TRUE" = tu_red)) +
  scale_x_continuous(limits = c(-0.3, 1.1), breaks = seq(0, 1, 0.2)) +
  annotate("text", x = 0.2, y = 0.5, label = "small", size = 2.5,
           colour = "gray50", vjust = -0.5) +
  annotate("text", x = 0.5, y = 0.5, label = "medium", size = 2.5,
           colour = "gray50", vjust = -0.5) +
  annotate("text", x = 0.8, y = 0.5, label = "large", size = 2.5,
           colour = "gray50", vjust = -0.5) +
  labs(title = "Effect sizes for key comparisons",
       subtitle = "Cohen's d with conventional thresholds (0.2 = small, 0.5 = medium, 0.8 = large)",
       caption = "All effects are in the hypothesized direction (positive = first group higher).",
       x = "Cohen's d", y = NULL) +
  theme_thesis() +
  theme(panel.grid.major.y = element_blank())

save_thesis_fig("fig_13_effect_sizes.pdf", fig13, width = 6.5, height = 3.5)

# =============================================================================
# Figure 14: Dilemma Type Comparison
# =============================================================================

dilemma_type_data <- mdc %>%
  mutate(
    category = case_when(
      grepl("^G_P", dilemma) ~ "Personal",
      grepl("^G_I", dilemma) ~ "Impersonal",
      grepl("^K_", dilemma) ~ "Koerner"
    ),
    category = factor(category, levels = c("Personal", "Impersonal", "Koerner")),
    sign = factor(case_when(
      movement_toward_ai > 0 ~ "Moved toward AI",
      movement_toward_ai < 0 ~ "Backfired",
      TRUE ~ "No Change"
    ), levels = outcome_levels)
  ) %>%
  filter(!is.na(category))

dilemma_stats <- dilemma_type_data %>%
  group_by(category) %>%
  summarise(
    n = n(),
    m = mean(movement_toward_ai),
    se = sd(movement_toward_ai) / sqrt(n),
    .groups = "drop"
  )

dilemma_outcomes <- dilemma_type_data %>%
  count(category, sign) %>%
  group_by(category) %>%
  mutate(pct = n / sum(n) * 100) %>%
  ungroup()

# Kruskal-Wallis test
kw_res <- kruskal.test(movement_toward_ai ~ category, data = dilemma_type_data)

pal_dilemma <- c("Personal" = tu_red, "Impersonal" = col_sage, "Koerner" = "#3498DB")

# Panel A: Outcome distribution
pA_dil <- ggplot(dilemma_outcomes, aes(x = category, y = pct, fill = sign)) +
  geom_col(width = 0.65) +
  geom_text(aes(label = ifelse(pct >= 5, sprintf("%.0f%%", pct), "")),
            position = position_stack(vjust = 0.5),
            size = 2.8, colour = "white") +
  scale_fill_manual(values = palette_outcomes, name = NULL,
                    breaks = rev(outcome_levels)) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.05))) +
  labs(title = "Outcome distribution by dilemma type",
       x = NULL, y = "Percentage") +
  theme_thesis() +
  theme(legend.position = "bottom")

# Panel B: Mean movement
pB_dil <- ggplot(dilemma_stats, aes(x = category, y = m, fill = category)) +
  geom_hline(yintercept = 0, colour = "gray45", linewidth = 0.3) +
  geom_col(width = 0.55, alpha = 0.85) +
  geom_errorbar(aes(ymin = m - se, ymax = m + se), width = 0.15, linewidth = 0.5) +
  geom_text(aes(label = sprintf("%.2f\n(n=%d)", m, n)),
            vjust = ifelse(dilemma_stats$m >= 0, -0.8, 1.5),
            size = 2.8, colour = "gray20") +
  scale_fill_manual(values = pal_dilemma, guide = "none") +
  scale_y_continuous(limits = c(-1, 1.5), breaks = seq(-1, 1.5, 0.5)) +
  labs(title = "Mean movement toward AI",
       subtitle = sprintf("Kruskal-Wallis: H = %.2f, %s", kw_res$statistic, pfmt(kw_res$p.value)),
       x = NULL, y = "Mean movement") +
  theme_thesis()

fig14 <- (pA_dil | pB_dil) +
  plot_annotation(
    title = "Persuasion outcomes by dilemma type",
    subtitle = "Personal (high contact), Impersonal (low contact), and Koerner (everyday) dilemmas",
    theme = theme_thesis()
  )

save_thesis_fig("fig_14_dilemma_types.pdf", fig14, width = 7.5, height = 4.5)

# =============================================================================
# Figure 15: Within-Participant Outcome Patterns
# =============================================================================

participant_patterns <- mdc %>%
  group_by(participant_id) %>%
  summarise(
    n_dilemmas = n(),
    n_toward_ai = sum(movement_toward_ai > 0),
    n_backfired = sum(movement_toward_ai < 0),
    n_no_change = sum(movement_toward_ai == 0),
    .groups = "drop"
  ) %>%
  mutate(
    pattern = case_when(
      n_toward_ai > 0 & n_backfired > 0 ~ "Mixed",
      n_toward_ai > 0 & n_backfired == 0 ~ "Only toward AI",
      n_toward_ai == 0 & n_backfired > 0 ~ "Only backfired",
      TRUE ~ "No change"
    ),
    pattern = factor(pattern, levels = c("Only toward AI", "Mixed",
                                          "Only backfired", "No change"))
  )

pattern_summary <- participant_patterns %>%
  count(pattern) %>%
  mutate(pct = n / sum(n) * 100)

pal_pattern <- c(
  "Only toward AI" = col_sage,
  "Mixed" = "#E67E22",
  "Only backfired" = tu_red,
  "No change" = col_control
)

fig15 <- ggplot(pattern_summary, aes(x = pattern, y = n, fill = pattern)) +
  geom_col(width = 0.6, alpha = 0.85) +
  geom_text(aes(label = sprintf("%d\n(%.0f%%)", n, pct)),
            vjust = -0.3, size = 3.5, colour = "gray20") +
  scale_fill_manual(values = pal_pattern, guide = "none") +
  scale_y_continuous(expand = expansion(mult = c(0, 0.25))) +
  labs(title = "Within-participant outcome patterns",
       subtitle = "Do participants consistently move toward or against the AI, or show mixed responses?",
       caption = sprintf("Based on %d participants, each with %d discussed dilemmas.",
                         nrow(participant_patterns),
                         median(participant_patterns$n_dilemmas)),
       x = NULL, y = "Number of participants") +
  theme_thesis() +
  theme(panel.grid.major.x = element_blank())

save_thesis_fig("fig_15_within_participant.pdf", fig15, width = 6.5, height = 4.0)

message("\nExploratory analysis figures written to figures/thesis/")
