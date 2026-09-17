# =============================================================================
# 00_theme.R - Unified Theme & Palette for Thesis Figures
# =============================================================================
# Source this file after 00_setup.R:
#   source("00_theme.R")
# =============================================================================

library(ggplot2)

# -----------------------------------------------------------------------------
# Color Palette: TU Berlin Red + Muted Earth Tones
# -----------------------------------------------------------------------------

tu_red        <- "#C50E1F"   # TU Berlin brand red — primary accent
tu_red_light  <- "#E8939A"   # Light red — CI bands, muted accent

col_control   <- "#8C8C8C"   # Neutral grey — control / baseline / non-significant
col_sage      <- "#5B7B5D"   # Sage green — positive outcomes (moved toward AI)
col_taupe     <- "#B0A89A"   # Warm taupe — no change
col_sienna    <- "#D4764E"   # Burnt sienna — Persuade+Demo condition
col_goldenrod <- "#8B6B3D"   # Dark goldenrod — Persuade+Info condition

# --- Named palette vectors for scale_fill_manual / scale_color_manual ---

palette_outcomes <- c(
  "Moved toward AI" = col_sage,
  "No Change"       = col_taupe,
  "Backfired"       = tu_red
)

palette_conditions <- c(
  "Control"         = col_control,
  "Persuade"        = tu_red,
  "Persuade + Demo" = col_sienna,
  "Persuade + Info" = col_goldenrod
)

palette_stance <- c(
  "Opposing"    = tu_red,
  "Reinforcing" = col_sage
)

palette_significance <- c(
  "TRUE"  = tu_red,
  "FALSE" = col_control
)

# -----------------------------------------------------------------------------
# Label Mappings: raw variable name -> clean display label
# -----------------------------------------------------------------------------

condition_labels <- c(
  "neutral"       = "Control",
  "persuade"      = "Persuade",
  "persuade_demo" = "Persuade + Demo",
  "persuade_info" = "Persuade + Info"
)

education_labels <- c(
  "high_school"  = "High School",
  "some_college" = "Some College",
  "associate"    = "Associate",
  "bachelor"     = "Bachelor's",
  "master"       = "Master's",
  "doctorate"    = "Doctorate"
)

gender_labels <- c(
  "female"            = "Female",
  "male"              = "Male",
  "non_binary"        = "Non-Binary",
  "prefer_not_to_say" = "Prefer Not to Say",
  "other"             = "Other"
)

stance_labels <- c(
  "opposite" = "Opposing",
  "same"     = "Reinforcing"
)

ai_usage_labels <- c(
  "never"      = "Never",
  "rarely"     = "Rarely",
  "sometimes"  = "Sometimes",
  "often"      = "Often",
  "very_often" = "Very Often"
)

outcome_levels <- c("Backfired", "No Change", "Moved toward AI")

# Condition ordering (for factor levels)
condition_order <- c("Control", "Persuade", "Persuade + Demo", "Persuade + Info")

# -----------------------------------------------------------------------------
# theme_thesis(): Unified ggplot2 Theme
# -----------------------------------------------------------------------------

theme_thesis <- function(base_size = 11, base_family = "") {
  theme_minimal(base_size = base_size, base_family = base_family) %+replace%
    theme(
      # Text hierarchy
      # Align title, subtitle and caption to the plot edge rather than the
      # panel edge, so they do not indent by the width of the y-axis labels.
      plot.title.position   = "plot",
      plot.caption.position = "plot",

      plot.title       = element_text(size = rel(1.15), face = "bold",
                                      hjust = 0, margin = margin(b = 8)),
      plot.subtitle    = element_text(size = rel(0.9), color = "gray40",
                                      hjust = 0, margin = margin(b = 10)),
      plot.caption     = element_text(size = rel(0.75), color = "gray50",
                                      hjust = 1, margin = margin(t = 8)),

      # Axes
      # NOTE: %+replace% swaps the whole element, so theme_minimal's
      # axis.title.y angle is discarded here and must be restored explicitly.
      # Without angle = 90 the y-axis title renders horizontally and eats a
      # large slice of the plot width.
      axis.title       = element_text(size = rel(0.95), color = "gray20"),
      axis.title.x     = element_text(margin = margin(t = 8)),
      axis.title.y     = element_text(angle = 90, margin = margin(r = 8)),
      axis.text        = element_text(size = rel(0.85), color = "gray30"),

      # Grid
      panel.grid.major = element_line(color = "gray92", linewidth = 0.3),
      panel.grid.minor = element_blank(),

      # Legend
      legend.position  = "bottom",
      legend.title     = element_text(size = rel(0.85), face = "bold"),
      legend.text      = element_text(size = rel(0.8)),
      legend.key.size  = unit(0.4, "cm"),
      legend.margin    = margin(t = 4),

      # Strip (facets)
      strip.text       = element_text(size = rel(0.9), face = "bold",
                                      margin = margin(b = 4, t = 4)),
      strip.background = element_rect(fill = "gray96", color = NA),

      # Plot margins
      plot.margin      = margin(t = 12, r = 12, b = 8, l = 8)
    )
}

# -----------------------------------------------------------------------------
# save_thesis_fig(): Standardized PDF Output
# -----------------------------------------------------------------------------

save_thesis_fig <- function(filename, plot = last_plot(),
                            width = 6.5, height = 4.5) {
  filepath <- file.path("figures", "thesis", filename)
  ggsave(filepath, plot = plot, width = width, height = height,
         device = cairo_pdf)
  message(sprintf("Saved: %s", filepath))
}

message("Theme loaded: TU Berlin palette, theme_thesis(), save_thesis_fig()")
