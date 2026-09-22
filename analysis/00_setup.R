# =============================================================================
# 00_setup.R - Common Setup for All Analysis Notebooks
# =============================================================================
# Source this file at the top of each notebook:
#   source("00_setup.R")
# =============================================================================

# -----------------------------------------------------------------------------
# Libraries
# -----------------------------------------------------------------------------

library(tidyverse)
library(jsonlite)
library(broom)

# Ensure dplyr functions take precedence
select <- dplyr::select
filter <- dplyr::filter

# -----------------------------------------------------------------------------
# Option 1: Load Pre-processed Data (Recommended - faster)
# -----------------------------------------------------------------------------
# Use this if you have data_renamed.csv and data_long_renamed.csv

USE_PREPROCESSED <- TRUE  # Set to FALSE to use original processing

if (USE_PREPROCESSED && file.exists("data/data_long_renamed.csv")) {

  message("Loading pre-processed data...")

  # Load dilemma-level data (already reshaped)
  data_long <- read_csv("data/data_long_renamed.csv", show_col_types = FALSE)

  # Create participant-level summary from long format
  data <- data_long %>%
    group_by(participant_id, condition, llm_provider, demographics_age,
             demographics_gender, demographics_education,
             debrief_stias_average, debrief_noticed_persuasion, debrief_changed_mind) %>%
    summarise(.groups = "drop")

  # Create chat analysis subset
  data_chat_analysis <- data_long %>%
    filter(had_chat == TRUE)

  message(sprintf("Loaded: %d participants, %d observations, %d chat observations",
                  nrow(data), nrow(data_long), nrow(data_chat_analysis)))

} else {

# -----------------------------------------------------------------------------
# Option 2: Original Data Processing (from raw export)
# -----------------------------------------------------------------------------

  message("Processing raw data...")

  # Load raw data
  data_raw <- read_csv("data/experiment_export_20260627_155037.csv", show_col_types = FALSE)

  # Filter to complete participants who didn't withdraw
  data <- data_raw %>%
    filter(status == "complete", withdrawn == FALSE | is.na(withdrawn))

  message(sprintf("Total rows: %d", nrow(data_raw)))
  message(sprintf("After filtering (complete, not withdrawn): %d", nrow(data)))

  # Get dilemma names from column names
  dilemma_cols <- names(data)[grepl("^rating_pre_", names(data))]
  dilemmas <- str_replace(dilemma_cols, "^rating_pre_", "")

  # Reshape to long format
  data_long <- data %>%
    dplyr::select(
      participant_id, condition, llm_provider,
      demographics_age, demographics_gender, demographics_education,
      debrief_stias_average, debrief_noticed_persuasion, debrief_changed_mind,
      starts_with("rating_pre_"), starts_with("rating_post_"),
      starts_with("chat_turn_count_"), starts_with("system_prompt_")
    ) %>%
    pivot_longer(
      cols = starts_with("rating_pre_"),
      names_to = "dilemma",
      names_prefix = "rating_pre_",
      values_to = "rating_pre"
    ) %>%
    left_join(
      data %>%
        dplyr::select(participant_id, starts_with("rating_post_")) %>%
        pivot_longer(
          cols = starts_with("rating_post_"),
          names_to = "dilemma",
          names_prefix = "rating_post_",
          values_to = "rating_post"
        ),
      by = c("participant_id", "dilemma")
    ) %>%
    left_join(
      data %>%
        dplyr::select(participant_id, starts_with("chat_turn_count_")) %>%
        pivot_longer(
          cols = starts_with("chat_turn_count_"),
          names_to = "dilemma",
          names_prefix = "chat_turn_count_",
          values_to = "chat_turns"
        ),
      by = c("participant_id", "dilemma")
    ) %>%
    dplyr::select(-starts_with("rating_post_"), -starts_with("chat_turn_count_"), -starts_with("system_prompt_")) %>%
    mutate(
      rating_change = rating_post - rating_pre,
      had_chat = !is.na(chat_turns) & chat_turns > 0
    ) %>%
    filter(!is.na(rating_pre) & !is.na(rating_post))

  # Load dilemma metadata
  json_data <- fromJSON("data/dilemma_metadata.json", simplifyVector = FALSE)
  dilemma_metadata <- map_dfr(names(json_data$dilemmas), function(code) {
    d <- json_data$dilemmas[[code]]
    tibble(
      dilemma = code,
      low_rating_framework = d$low_rating_framework
    )
  })

  # Parse system prompts for stance info
  stance_data <- data %>%
    dplyr::select(participant_id, system_prompts_json) %>%
    filter(!is.na(system_prompts_json) & system_prompts_json != "") %>%
    rowwise() %>%
    mutate(prompts = list(fromJSON(system_prompts_json))) %>%
    unnest(prompts) %>%
    dplyr::select(participant_id, dilemma_code, stance_mode, llm_framework)

  # Join stance and metadata
  data_long <- data_long %>%
    left_join(stance_data, by = c("participant_id", "dilemma" = "dilemma_code")) %>%
    left_join(dilemma_metadata, by = "dilemma")

  # Define outcomes
  data_long <- data_long %>%
    mutate(
      ai_argues_for = case_when(
        is.na(llm_framework) | is.na(low_rating_framework) ~ NA_character_,
        llm_framework == low_rating_framework ~ "low",
        llm_framework != low_rating_framework ~ "high"
      ),
      moved_toward_ai = case_when(
        is.na(ai_argues_for) ~ NA,
        rating_change == 0 ~ NA,
        ai_argues_for == "low" & rating_change < 0 ~ TRUE,
        ai_argues_for == "high" & rating_change > 0 ~ TRUE,
        TRUE ~ FALSE
      ),
      outcome = case_when(
        is.na(stance_mode) ~ NA_character_,
        rating_change == 0 ~ "No Change",
        moved_toward_ai == TRUE ~ "Moved toward AI",
        moved_toward_ai == FALSE ~ "Backfired",
        TRUE ~ NA_character_
      ),
      stance_label = case_when(
        stance_mode == "opposite" ~ "Opposing",
        stance_mode == "same" ~ "Reinforcing",
        TRUE ~ NA_character_
      )
    )

  # Create chat analysis subset
  data_chat_analysis <- data_long %>%
    filter(!is.na(stance_mode)) %>%
    mutate(changed = rating_change != 0)

  message(sprintf("Observations: %d (participants × dilemmas)", nrow(data_long)))
  message(sprintf("Observations with stance info: %d", sum(!is.na(data_long$stance_mode))))
}

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

message("\n=== Data Loaded ===")
message(sprintf("Participants: %d", nrow(data)))
message(sprintf("Total observations (data_long): %d", nrow(data_long)))
message(sprintf("Chat observations (data_chat_analysis): %d", nrow(data_chat_analysis)))
