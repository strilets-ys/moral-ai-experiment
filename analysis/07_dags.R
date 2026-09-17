# =============================================================================
# Causal DAG and covariate decisions for the confirmatory models (H1-H6)
#
# The key structural fact about this design is that demographics and personality
# are not only baseline covariates: they are INPUTS TO THE TREATMENT. The four
# arms are nested, each adding one component to the system prompt:
#
#   neutral       -> ethical framework only
#   persuade      -> + explicit persuasion goal
#   persuade_demo -> + participant age, gender, education
#   persuade_info -> + Big Five (TIPI) profile
#
# So Demographics and Personality have two distinct roles. They affect the
# outcome directly (some people are more persuadable), and in the personalised
# arms they also shape what the model actually says. That makes them moderators
# of the condition effect, not confounders of it.
# =============================================================================

setwd("/Users/wolfrieder/Desktop/analysis")
source("00_setup.R")
source("00_theme.R")
suppressMessages({
  library(dagitty); library(ggplot2); library(dplyr); library(kableExtra)
})

if (!dir.exists("figures/thesis")) dir.create("figures/thesis", recursive = TRUE)
if (!dir.exists("tables")) dir.create("tables")

# =============================================================================
# The design DAG
# =============================================================================

dag <- dagitty('dag {
  Demographics [pos="0.75,4.40"]
  Personality  [pos="0.75,3.20"]
  DilemmaFeat  [pos="0.75,1.00"]
  Condition    [pos="2.35,4.40"]
  Provider     [pos="2.35,3.20"]
  Stance       [pos="2.35,2.10"]
  RatingPre    [pos="2.35,1.00"]
  AIContent    [pos="3.95,3.20"]
  Framework    [pos="3.95,0.45"]
  Messages     [pos="5.55,4.30"]
  Discussed    [pos="5.55,2.90"]
  Noticed      [pos="5.55,1.10"]
  Movement     [pos="7.15,2.20"]
  Trust        [pos="7.15,0.45"]

  Condition    -> AIContent
  Demographics -> AIContent
  Personality  -> AIContent
  Stance       -> AIContent
  Provider     -> AIContent

  Demographics -> RatingPre
  Personality  -> RatingPre
  DilemmaFeat  -> RatingPre
  Demographics -> Movement
  Personality  -> Movement
  DilemmaFeat  -> Movement
  RatingPre    -> Movement
  RatingPre    -> Framework
  Stance       -> Framework

  AIContent    -> Messages
  AIContent    -> Movement
  AIContent    -> Noticed
  Demographics -> Messages
  Personality  -> Messages
  Messages     -> Movement
  Discussed    -> Movement
  Movement     -> Noticed
  Movement     -> Trust
  Demographics -> Trust
  Personality  -> Trust
}')

node_role <- c(
  Condition = "assigned", Provider = "assigned",
  Stance = "assigned", Discussed = "assigned",
  Demographics = "input", Personality = "input",
  DilemmaFeat = "baseline", RatingPre = "baseline",
  AIContent = "mediator", Framework = "derived",
  Messages = "post", Noticed = "post", Trust = "post",
  Movement = "outcome"
)

node_label <- c(
  Demographics = "Demographics\n(age, gender,\neducation)",
  Personality  = "Personality\n(TIPI)",
  DilemmaFeat  = "Dilemma\nfeatures",
  RatingPre    = "Baseline\nrating",
  Condition    = "Condition",
  Provider     = "Language\nmodel",
  Stance       = "AI stance\n(is_opposing)",
  Discussed    = "Dilemma\ndiscussed",
  AIContent    = "What the AI\nactually said",
  Framework    = "AI\nframework",
  Messages     = "Participant\nmessages",
  Movement     = "Movement\ntoward AI",
  Noticed      = "Noticed\npersuasion",
  Trust        = "Trust in AI\n(S-TIAS)"
)

# edges that are only active in the personalised arms
tailoring_edges <- list(c("Demographics", "AIContent"), c("Personality", "AIContent"))

# =============================================================================
# Adjustment sets
# =============================================================================

hyps <- list(
  list(id="H1", exp="Condition",    d="Persuasion vs. control"),
  list(id="H2", exp="Condition",    d="+Demographics vs. persuade"),
  list(id="H3", exp="Condition",    d="+Personality vs. +demographics"),
  list(id="H4", exp="RatingPre",    d="Initial opinion extremity"),
  list(id="H5", exp="Discussed",    d="Discussed vs. undiscussed"),
  list(id="H6", exp="Stance",       d="Opposing vs. reinforcing")
)

message("\n============ MINIMAL SUFFICIENT ADJUSTMENT SETS ============\n")
for (h in hyps) {
  d <- dag; exposures(d) <- h$exp; outcomes(d) <- "Movement"
  s <- adjustmentSets(d, type = "minimal")
  txt <- if (length(s) == 0) "none available" else
         if (length(s[[1]]) == 0) "{ } empty set sufficient" else
         paste(sapply(s, function(z) paste0("{", paste(z, collapse=", "), "}")), collapse=" or ")
  message(sprintf("%-3s %-32s exp=%-13s -> %s", h$id, h$d, h$exp, txt))
}

message("\n============ NEVER ADJUST (descendants of exposure) ============\n")
for (h in hyps) {
  dn <- setdiff(descendants(dag, h$exp), c(h$exp, "Movement"))
  message(sprintf("%-3s %-13s %s", h$id, h$exp, paste(dn, collapse=", ")))
}

message("\n============ COLLIDER CHECKS ============\n")
d6 <- dag; exposures(d6) <- "Stance"; outcomes(d6) <- "Movement"
p0 <- paths(d6); p1 <- paths(d6, Z = "Framework")
message(sprintf("H6 open paths, Framework NOT conditioned: %d", sum(p0$open)))
message(sprintf("H6 open paths, Framework conditioned:     %d  <- collider bias", sum(p1$open)))
dc <- dag; exposures(dc) <- "Condition"; outcomes(dc) <- "Movement"
q0 <- paths(dc); q1 <- paths(dc, Z = "AIContent")
message(sprintf("H1-H3 open paths, AIContent NOT conditioned: %d", sum(q0$open)))
message(sprintf("H1-H3 open paths, AIContent conditioned:     %d  <- blocks the mechanism",
                sum(q1$open)))

# =============================================================================
# Figure
# =============================================================================

co <- coordinates(dag)
nodes <- data.frame(name = names(co$x), x = as.numeric(co$x), y = as.numeric(co$y),
                    stringsAsFactors = FALSE) %>%
  mutate(role = node_role[name], label = node_label[name],
         role = factor(role, levels = c("assigned","input","baseline",
                                        "mediator","derived","post","outcome")))

rx <- 0.66; ry <- 0.36
edges <- edges(dag) %>%
  dplyr::select(from = v, to = w) %>%
  mutate(from = as.character(from), to = as.character(to),
         tailoring = paste(from, to) %in% sapply(tailoring_edges, paste, collapse=" ")) %>%
  left_join(nodes[c("name","x","y")], by = c("from"="name")) %>% rename(x0=x, y0=y) %>%
  left_join(nodes[c("name","x","y")], by = c("to"="name"))   %>% rename(x1=x, y1=y) %>%
  mutate(dx = x1-x0, dy = y1-y0, len = sqrt(dx^2+dy^2), ux = dx/len, uy = dy/len,
         sc = 1/sqrt((ux/rx)^2 + (uy/ry)^2),
         xs = x0+ux*sc, ys = y0+uy*sc, xe = x1-ux*sc, ye = y1-uy*sc)

role_fill <- c(assigned = tu_red, input = col_sienna, baseline = col_sage,
               mediator = col_goldenrod, derived = col_taupe,
               post = "grey93", outcome = "grey25")
role_text <- c(assigned = "white", input = "white", baseline = "white",
               mediator = "white", derived = "grey15",
               post = "grey35", outcome = "white")

p_dag <- ggplot() +
  geom_segment(data = filter(edges, !tailoring),
               aes(x=xs, y=ys, xend=xe, yend=ye),
               arrow = arrow(length = unit(0.10,"cm"), type="closed"),
               colour = "grey62", linewidth = 0.26) +
  geom_segment(data = filter(edges, tailoring),
               aes(x=xs, y=ys, xend=xe, yend=ye),
               arrow = arrow(length = unit(0.13,"cm"), type="closed"),
               colour = col_sienna, linewidth = 0.62, linetype = "22") +
  geom_tile(data = nodes, aes(x=x, y=y, fill=role),
            width = 2*rx, height = 2*ry, colour = NA) +
  geom_text(data = nodes, aes(x=x, y=y, label=label, colour=role),
            size = 2.15, lineheight = 0.9, fontface = "bold") +
  scale_fill_manual(values = role_fill, name = NULL,
    labels = c(assigned="Assigned by design", input="Trait: also a treatment input",
               baseline="Measured pre-exposure", mediator="Treatment mechanism",
               derived="Derived (collider)", post="Post-exposure", outcome="Outcome")) +
  scale_colour_manual(values = role_text, guide = "none") +
  guides(fill = guide_legend(nrow = 2)) +
  coord_cartesian(xlim = c(0.02, 7.9), ylim = c(0.02, 4.95), expand = FALSE) +
  labs(x = NULL, y = NULL,
    title = "Causal structure of the experimental design",
    subtitle = paste0(
      "Dashed orange arrows are the personalisation manipulation: in Persuade+Demo the model receives the\n",
      "participant's demographics, and in Persuade+Demo+Info their TIPI profile as well. Those traits are\n",
      "therefore moderators of the condition effect, not confounders of it. Grey nodes follow AI exposure\n",
      "and are never valid controls.")) +
  theme_void(base_size = 10) +
  theme(
    plot.title = element_text(face="bold", size=rel(1.15), hjust=0, margin=margin(b=4)),
    plot.subtitle = element_text(colour="gray40", size=rel(0.76), hjust=0,
                                 lineheight=1.18, margin=margin(b=10)),
    legend.position = "bottom", legend.key.size = unit(0.34,"cm"),
    legend.text = element_text(size=6.8), legend.margin = margin(t=2),
    plot.margin = margin(10,10,6,10)
  )

save_thesis_fig("fig_dag_design.pdf", p_dag, width = 6.5, height = 5.4)

# =============================================================================
# Covariate balance across arms
# =============================================================================

dd <- data %>% mutate(cond = factor(recode(condition, !!!condition_labels),
                                    levels = condition_order))
num_vars <- c(demographics_age = "Age",
              tipi_extraversion = "Extraversion",
              tipi_agreeableness = "Agreeableness",
              tipi_conscientiousness = "Conscientiousness",
              tipi_emotional_stability = "Emotional stability",
              tipi_openness = "Openness")

bal <- lapply(names(num_vars), function(v) {
  st <- dd %>% group_by(cond) %>% summarise(m = mean(.data[[v]]), .groups="drop")
  data.frame(Variable = num_vars[[v]],
             Control = sprintf("%.1f", st$m[1]), Persuade = sprintf("%.1f", st$m[2]),
             Demo = sprintf("%.1f", st$m[3]), Info = sprintf("%.1f", st$m[4]),
             Spread = sprintf("%.2f", diff(range(st$m)) / sd(dd[[v]])),
             stringsAsFactors = FALSE)
}) %>% bind_rows()

gtab <- table(dd$cond, dd$demographics_gender)
bal <- rbind(bal, data.frame(
  Variable = "Female (\\%)",
  Control  = sprintf("%.0f", 100*gtab[1,"female"]/sum(gtab[1,])),
  Persuade = sprintf("%.0f", 100*gtab[2,"female"]/sum(gtab[2,])),
  Demo     = sprintf("%.0f", 100*gtab[3,"female"]/sum(gtab[3,])),
  Info     = sprintf("%.0f", 100*gtab[4,"female"]/sum(gtab[4,])),
  Spread   = "--", stringsAsFactors = FALSE))

bal_latex <- bal %>%
  kbl(format="latex", booktabs=TRUE, escape=FALSE, align=c("l","c","c","c","c","c"),
      col.names = c("", "Control", "Persuade", "+Demo", "+Info", "Spread"),
      caption = "Balance of participant traits across the four experimental arms.",
      label = "balance") %>%
  kable_styling(latex_options="hold_position", font_size=9, full_width=FALSE) %>%
  add_header_above(c(" "=1, "Arm mean"=4, " "=1)) %>%
  footnote(general = paste(
      "Arm sizes are 6, 4, 6 and 8. Spread is the range of arm means divided by",
      "the pooled standard deviation; values above roughly 0.5 indicate chance",
      "imbalance large enough to be worth adjusting for on precision grounds,",
      "even though randomisation makes adjustment unnecessary for identification."),
    general_title="Note.", footnote_as_chunk=FALSE, threeparttable=TRUE, escape=FALSE)

writeLines(bal_latex, "tables/tab_balance.tex")

# =============================================================================
# Recommended specifications
# =============================================================================

spec <- data.frame(
  H = c("H1","H2","H3","H4","H5","H6"),
  Contrast = c("Persuasive arms vs.\\ control",
               "Persuade+Demo vs.\\ Persuade",
               "+Info vs.\\ Persuade+Demo",
               "Baseline extremity $|R_0-4|$",
               "Discussed vs.\\ undiscussed",
               "Opposing vs.\\ reinforcing"),
  Level = c("Between","Between","Between","Within","Within","Within"),
  Req = c("--","--","--","Demographics, personality, dilemma features","--","--"),
  Rec = c("Age","Age","Age","--","Dilemma features","Baseline rating, dilemma features"),
  stringsAsFactors = FALSE)

spec_latex <- spec %>%
  kbl(format="latex", booktabs=TRUE, escape=FALSE, align=c("l","l","c","l","l"),
      col.names = c("","Contrast","Level","Required for identification","Recommended for precision"),
      caption = "Covariate decisions for the confirmatory models, derived from the design DAG.",
      label = "dag_adjustment") %>%
  kable_styling(latex_options="hold_position", font_size=9, full_width=FALSE) %>%
  column_spec(2, width="4.3cm") %>%
  column_spec(4, width="3.3cm") %>% column_spec(5, width="3.0cm") %>%
  footnote(general = paste(
    "Condition, language model, stance and dilemma selection were assigned by the",
    "experimenter, so the empty set identifies their effects; H4 is the only",
    "observational contrast. Age is recommended for the between-participant",
    "contrasts because it is badly imbalanced across arms (Table~\\\\ref{tab:balance}).",
    "Within-participant exposures need no participant-level covariate at all: the",
    "participant random intercept absorbs that confounding entirely. Never adjust for",
    "the AI framework, what the AI said, participant message count, noticed",
    "persuasion, or S-TIAS trust."),
    general_title="Note.", footnote_as_chunk=FALSE, threeparttable=TRUE, escape=FALSE)

writeLines(spec_latex, "tables/tab_dag_adjustment.tex")

message("\nSaved: figures/thesis/fig_dag_design.pdf")
message("Saved: tables/tab_balance.tex")
message("Saved: tables/tab_dag_adjustment.tex")

# =============================================================================
# Good and bad controls, following Cinelli, Forney & Pearl (2022)
#
# The classification below is read off the DAG. The organising fact is that
# condition, language model, stance and dilemma selection have no parents:
# they were set by the experimenter. An exposure with no parents has no
# backdoor path, so NO variable is needed to remove confounding. Every
# covariate is therefore a "neutral control" in the paper's terms, and the
# only question left is whether it helps or hurts precision -- except for H4,
# where the exposure is observational and genuine confounders exist.
# =============================================================================

controls <- data.frame(
  Variable = c(
    "Dilemma features (type, action/omission)",
    "Baseline rating $R_0$",
    "Age, gender, education",
    "Personality (TIPI)",
    "What the AI actually said",
    "Participant message count",
    "AI framework (\\texttt{is\\_utilitarian})",
    "Noticed persuasion",
    "Trust in AI (S-TIAS)"),
  Structure = c(
    "Cause of $Y$ only",
    "Cause of $Y$ only",
    "Cause of $Y$ only",
    "Cause of $Y$ only",
    "Mediator of $X \\rightarrow Y$",
    "Mediator of $X \\rightarrow Y$",
    "Collider on stance and $R_0$",
    "Descendant of $Y$",
    "Descendant of $Y$"),
  Verdict = c(
    "Neutral, good for precision",
    "Neutral, good for precision",
    "Neutral, good for precision",
    "Neutral, good for precision",
    "\\textbf{Bad control}",
    "\\textbf{Bad control}",
    "\\textbf{Bad control}",
    "\\textbf{Bad control}",
    "\\textbf{Bad control}"),
  Use = c("Include", "Include", "Include (H4: required)", "Include (H4: required)",
          "Exclude", "Exclude", "Exclude", "Exclude", "Exclude"),
  stringsAsFactors = FALSE)

ctrl_latex <- controls %>%
  kbl(format="latex", booktabs=TRUE, escape=FALSE, align=c("l","l","l","l"),
      col.names = c("Variable", "Role in the DAG", "Classification", "Decision"),
      caption = "Classification of candidate controls following Cinelli, Forney and Pearl (2022).",
      label = "controls") %>%
  kable_styling(latex_options="hold_position", font_size=9, full_width=FALSE) %>%
  column_spec(1, width="4.0cm") %>% column_spec(2, width="3.4cm") %>%
  column_spec(3, width="3.2cm") %>%
  pack_rows("Pre-exposure", 1, 4) %>%
  pack_rows("Post-exposure", 5, 9) %>%
  footnote(general = paste(
    "For H1--H3, H5 and H6 the exposure was assigned by the experimenter and has",
    "no backdoor path, so no variable is required to remove confounding and every",
    "pre-exposure covariate is a neutral control included only to reduce residual",
    "variance. H4 is the exception: baseline extremity is observational, so the",
    "trait variables act as genuine confounders there and become good controls.",
    "Bad controls are harmful regardless of sample size: mediators remove part of",
    "the effect being estimated, and colliders and descendants of the outcome",
    "create associations that do not exist in the data-generating process."),
    general_title="Note.", footnote_as_chunk=FALSE, threeparttable=TRUE, escape=FALSE)

writeLines(ctrl_latex, "tables/tab_controls.tex")
message("Saved: tables/tab_controls.tex")
