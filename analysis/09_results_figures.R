# =============================================================================
# 09_results_figures.R - Figures for the Results chapter
# -----------------------------------------------------------------------------
# Estimates come from the DAG-specified models in 08_models.R; nothing is
# re-fitted here, so the figures and the results tables cannot drift apart.
#
#   fig_07_forest_hypotheses.pdf   H1-H6 in one forest plot
#   fig_08_movement_by_stance.pdf  distribution of movement, by AI stance (H6)
#   fig_09_room_to_move.pdf        the bounded-scale ceiling (explains H4)
#   fig_10_discussed_paired.pdf    within-participant paired slopes (H5)
#
# Descriptive figures 01-06 are produced by run_thesis_figures.R.
# =============================================================================

source("08_models.R")
source("00_theme.R")
suppressMessages(library(patchwork))

pfmt <- function(p) ifelse(p < .001, "p < .001",
                           paste0("p = ", sub("^0", "", sprintf("%.3f", p))))

stance_lab <- c("TRUE"  = "AI opposes the participant",
                "FALSE" = "AI reinforces the participant")
pal_stance2 <- setNames(c(tu_red, col_sage), unname(stance_lab))

# =============================================================================
# Figure 7: Forest plot of all six hypotheses
# =============================================================================
# One plot replaces six per-hypothesis bar charts.  Four of the six estimates
# are null; a forest plot shows that as a fact about the intervals rather than
# as six separate anticlimaxes.

grab <- function(m, term, label) {
  co <- summary(m)$coefficients
  tibble(label = label, b = co[term, 1], se = co[term, 2], p = co[term, 5])
}

hyp_labels <- c(
  "H1  Persuasion prompt vs. control",
  "H2  Personalised vs. generic persuasion",
  "H3  Demographics + personality vs. demographics only",
  "H4  Baseline extremity (within)",
  "H5  Discussed vs. undiscussed †",
  "H6  Opposing vs. reinforcing"
)

forest <- bind_rows(
  grab(m1_adj, "conditionC1_persuasion",      hyp_labels[1]),
  grab(m1_adj, "conditionC2_personal",        hyp_labels[2]),
  grab(m1_adj, "conditionC3_info",            hyp_labels[3]),
  grab(m2_adj, "is_opposingTRUE:extremity_w", hyp_labels[4]),
  grab(m3_adj, "had_chatTRUE",                hyp_labels[5]),
  grab(m1_adj, "is_opposingTRUE",             hyp_labels[6])
) %>%
  mutate(
    lo    = b - 1.96 * se,
    hi    = b + 1.96 * se,
    sig   = factor(ifelse(p < .05, "p < .05", "n.s."),
                   levels = c("p < .05", "n.s.")),
    label = factor(label, levels = rev(hyp_labels)),
    est_lab = sprintf("%.2f [%.2f, %.2f]", b, lo, hi),
    p_lab   = pfmt(p)
  )

pal_sig <- c("p < .05" = tu_red, "n.s." = col_control)

# Simplified forest plot: just the visual, no numbers (those are in the table)
fig07 <- ggplot(forest, aes(x = b, y = label, colour = sig)) +
  geom_vline(xintercept = 0, linetype = "dashed",
             colour = "gray45", linewidth = 0.4) +
  geom_linerange(aes(xmin = lo, xmax = hi), linewidth = 0.8) +
  geom_point(size = 3) +
  scale_colour_manual(values = pal_sig, name = NULL) +
  scale_x_continuous(breaks = seq(-1, 2, 0.5)) +
  labs(title = "Preregistered hypothesis tests",
       subtitle = "Estimated effects with 95% confidence intervals",
       x = "Effect on movement toward the AI position (rating points)",
       y = NULL,
       caption = paste0("† H5 outcome is magnitude of rating change. ",
                        "See Table for full statistics.")) +
  theme_thesis() +
  theme(panel.grid.major.y = element_blank(),
        legend.position = "bottom")

save_thesis_fig("fig_07_forest_hypotheses.pdf", fig07, width = 6, height = 3.5)

# =============================================================================
# Figure 8: Distribution of movement by AI stance (H6)
# =============================================================================
# The DV is 54% exact zeros, so a mean with an error bar hides the shape of the
# data.  This shows the whole distribution and lets the stance asymmetry - the
# study's largest effect - be read directly off the counts.

mv <- mdc %>%
  mutate(stance = factor(stance_lab[as.character(is_opposing)],
                         levels = unname(stance_lab)),
         sign = factor(case_when(movement_toward_ai > 0 ~ "Moved toward AI",
                                 movement_toward_ai < 0 ~ "Backfired",
                                 TRUE                   ~ "No Change"),
                       levels = outcome_levels))

mv_counts <- mv %>% count(stance, movement_toward_ai, sign)

mv_notes <- mv %>%
  group_by(stance) %>%
  summarise(n = n(), m = mean(movement_toward_ai),
            pos = mean(movement_toward_ai > 0) * 100,
            zero = mean(movement_toward_ai == 0) * 100,
            neg = mean(movement_toward_ai < 0) * 100, .groups = "drop") %>%
  mutate(lab = sprintf("n = %d,  M = %+.2f\n%.0f%% toward AI\n%.0f%% no change\n%.0f%% backfired",
                       n, m, pos, zero, neg))

fig08 <- ggplot(mv_counts, aes(x = movement_toward_ai, y = n, fill = sign)) +
  geom_col(width = 0.78) +
  geom_vline(xintercept = 0, colour = "gray45", linewidth = 0.3) +
  geom_text(data = mv_counts %>% filter(n > 0), aes(label = n),
            vjust = -0.45, size = 2.5, colour = "gray30") +
  geom_point(data = mv_notes, aes(x = m, y = -2.2), inherit.aes = FALSE,
             shape = 18, size = 3, colour = tu_red) +
  geom_text(data = mv_notes, aes(x = 5.5, y = Inf, label = lab),
            inherit.aes = FALSE, hjust = 1, vjust = 1.1,
            size = 2.7, colour = "gray30", lineheight = 1.2) +
  scale_fill_manual(values = palette_outcomes, name = NULL,
                    breaks = rev(outcome_levels)) +
  scale_x_continuous(breaks = -5:5, limits = c(-5.6, 5.6)) +
  scale_y_continuous(expand = expansion(mult = c(0.10, 0.30))) +
  facet_wrap(~stance, ncol = 1) +
  labs(title = "Rating movement toward the AI, by AI stance",
       subtitle = "Each bar counts conversations; the red diamond marks the group mean",
       caption = paste0("Opposing vs. reinforcing: b = ",
                        sprintf("%.2f", forest$b[forest$label == hyp_labels[6]]),
                        ", ", pfmt(forest$p[forest$label == hyp_labels[6]]),
                        " (H6). Negative values are movement away from the AI."),
       x = "Movement toward the AI position (rating points)",
       y = "Conversations") +
  theme_thesis() +
  theme(panel.grid.major.x = element_blank())

save_thesis_fig("fig_08_movement_by_stance.pdf", fig08, width = 6.5, height = 5.4)

# =============================================================================
# Figure 9: The bounded-scale ceiling (why H4 is null)
# =============================================================================
# On a 1-7 scale the room available to move toward the AI is fixed by the
# participant's own baseline rating and the AI's stance:
#     room = 3 + extremity   when the AI opposes
#     room = 3 - extremity   when the AI reinforces
# So part of the headline "54% did not change" is arithmetic, not psychology,
# and a single pooled extremity slope averages two mechanically opposite
# relations toward zero.

rm_dat <- mv %>%
  mutate(room = ifelse(is_opposing, 3 + extremity, 3 - extremity))

stopifnot(all(rm_dat$movement_toward_ai <= rm_dat$room),
          all(rm_dat$movement_toward_ai >= -(6 - rm_dat$room)))

n_stuck   <- sum(rm_dat$room == 0)
pct_stuck <- n_stuck / nrow(rm_dat) * 100
# Zero rate inside vs outside the constrained cell.  Note that room = 0 bounds
# movement toward the AI only; these participants could still have moved AWAY,
# and one did, so the zeros are near-determined rather than forced.
pct_zero_stuck <- mean(rm_dat$movement_toward_ai[rm_dat$room == 0] == 0) * 100
pct_zero_free  <- mean(rm_dat$movement_toward_ai[rm_dat$room > 0] == 0) * 100

room_counts <- rm_dat %>% count(room, stance)

pA <- ggplot(room_counts, aes(x = room, y = n, fill = stance)) +
  geom_col(width = 0.78) +
  geom_text(data = room_counts %>% group_by(room) %>%
              summarise(n = sum(n), .groups = "drop"),
            aes(x = room, y = n, label = n), inherit.aes = FALSE,
            vjust = -0.45, size = 2.6, colour = "gray30") +
  annotate("segment", x = 0.42, xend = 0.06, y = 21.5, yend = 18,
           colour = tu_red, linewidth = 0.4,
           arrow = arrow(length = unit(0.10, "cm"), type = "closed")) +
  annotate("text", x = 0.52, y = 23.5, hjust = 0, vjust = 1,
           size = 2.75, colour = tu_red, lineheight = 1.2,
           label = sprintf("%d conversations (%.0f%%) had no room to move toward the AI:\n%.0f%% of them scored zero, against %.0f%% everywhere else",
                           n_stuck, pct_stuck, pct_zero_stuck, pct_zero_free)) +
  scale_fill_manual(values = pal_stance2, name = NULL) +
  scale_x_continuous(breaks = 0:6, limits = c(-0.6, 6.6)) +
  scale_y_continuous(expand = expansion(mult = c(0.05, 0.42))) +
  labs(title = "The rating scale bounds how far anyone can move",
       subtitle = "Fixed before the conversation by the baseline rating and the AI's stance",
       x = NULL, y = "Conversations") +
  theme_thesis() +
  theme(panel.grid.major.x = element_blank(),
        axis.text.x = element_blank())

band <- tibble(room = seq(0, 6, 0.02)) %>%
  mutate(hi = room, lo = -(6 - room))

pB <- ggplot(rm_dat, aes(x = room, y = movement_toward_ai)) +
  geom_ribbon(data = band, aes(x = room, ymin = lo, ymax = hi),
              inherit.aes = FALSE, fill = "gray93") +
  geom_line(data = band, aes(x = room, y = hi), inherit.aes = FALSE,
            colour = "gray55", linewidth = 0.35) +
  geom_line(data = band, aes(x = room, y = lo), inherit.aes = FALSE,
            colour = "gray55", linewidth = 0.35) +
  geom_hline(yintercept = 0, colour = "gray45", linewidth = 0.3) +
  geom_jitter(aes(colour = stance), width = 0.16, height = 0.16,
              size = 1.5, alpha = 0.75, show.legend = FALSE) +
  annotate("text", x = 6.4, y = 6.0, hjust = 1, size = 2.7, colour = "gray45",
           label = "ceiling") +
  annotate("text", x = 6.4, y = -6.0, hjust = 1, size = 2.7, colour = "gray45",
           label = "floor") +
  scale_colour_manual(values = pal_stance2, guide = "none") +
  scale_x_continuous(breaks = 0:6, limits = c(-0.6, 6.6)) +
  scale_y_continuous(breaks = seq(-6, 6, 2), limits = c(-6.4, 6.4)) +
  labs(x = "Room available to move toward the AI (rating points)",
       y = "Observed movement",
       caption = paste0("Grey band is the arithmetically feasible region; ",
                        "points are jittered.\n",
                        "Available room moves in opposite directions under the ",
                        "two stances, so H4 is specified\n",
                        "as an extremity × stance interaction rather than a ",
                        "single pooled slope.")) +
  theme_thesis() +
  theme(panel.grid.major.x = element_blank())

fig09 <- (pA / pB) + plot_layout(heights = c(1, 1.55), guides = "collect") &
  theme(legend.position = "bottom")

save_thesis_fig("fig_09_room_to_move.pdf", fig09, width = 6.5, height = 7.0)

# =============================================================================
# Figure 10: Discussed vs. undiscussed dilemmas, within participant (H5)
# =============================================================================
# had_chat varies within participant (each rated 8 dilemmas and discussed 4), so
# the contrast is carried entirely within participants.  Paired slopes show that
# directly, and show that the effect is not driven by a handful of outliers.

paired <- md %>%
  group_by(participant_id, had_chat) %>%
  summarise(m = mean(abs_change), .groups = "drop") %>%
  mutate(x = factor(ifelse(had_chat, "Discussed", "Undiscussed"),
                    levels = c("Undiscussed", "Discussed")))

dirs <- paired %>%
  dplyr::select(participant_id, had_chat, m) %>%
  tidyr::pivot_wider(names_from = had_chat, values_from = m,
                     names_prefix = "chat_") %>%
  mutate(direction = factor(case_when(chat_TRUE > chat_FALSE ~ "More change when discussed",
                                      chat_TRUE < chat_FALSE ~ "Less change when discussed",
                                      TRUE                   ~ "No difference"),
                            levels = c("More change when discussed",
                                       "Less change when discussed",
                                       "No difference")))

paired <- paired %>% left_join(dirs %>% dplyr::select(participant_id, direction),
                               by = "participant_id")

grp <- paired %>% group_by(x) %>%
  summarise(m = mean(m), .groups = "drop")

n_up   <- sum(dirs$direction == "More change when discussed")
n_down <- sum(dirs$direction == "Less change when discussed")
n_tie  <- sum(dirs$direction == "No difference")
y_top  <- max(paired$m) * 1.30

pal_dir <- c("More change when discussed" = tu_red,
             "Less change when discussed" = col_sage,
             "No difference"              = col_control)

fig10 <- ggplot(paired, aes(x = x, y = m)) +
  geom_line(aes(group = participant_id, colour = direction),
            linewidth = 0.5, alpha = 0.65) +
  geom_point(aes(colour = direction), size = 1.5, alpha = 0.8) +
  geom_line(data = grp, aes(group = 1), colour = "gray15", linewidth = 1.2) +
  geom_point(data = grp, size = 3.2, colour = "gray15") +
  geom_text(data = grp, aes(label = sprintf("M = %.2f", m)),
            hjust = c(1.25, -0.25), size = 3, colour = "gray15",
            fontface = "bold") +
  annotate("text", x = 0.5, y = y_top, hjust = 0, vjust = 1,
           size = 2.8, colour = "gray30", lineheight = 1.25,
           label = sprintf("%d of %d participants changed more on the\ndilemmas they discussed; %d changed less, %d tied",
                           n_up, nrow(dirs), n_down, n_tie)) +
  scale_colour_manual(values = pal_dir, name = NULL, drop = TRUE) +
  scale_x_discrete(expand = expansion(add = 0.55)) +
  scale_y_continuous(limits = c(0, y_top)) +
  labs(title = "Discussed dilemmas move more than undiscussed ones",
       subtitle = "One line per participant: mean absolute change over 4 discussed and 4 undiscussed dilemmas",
       caption = paste0("Mixed model on all 192 ratings: b = ",
                        sprintf("%.2f", forest$b[forest$label == hyp_labels[5]]),
                        ", ", pfmt(forest$p[forest$label == hyp_labels[5]]),
                        " (H5).\nThe contrast is within participant, so no ",
                        "between-participant confounder can bias it."),
       x = NULL, y = "Mean absolute rating change") +
  theme_thesis() +
  theme(panel.grid.major.x = element_blank())

save_thesis_fig("fig_10_discussed_paired.pdf", fig10, width = 6.5, height = 4.6)

message("\nResults figures written to figures/thesis/")
