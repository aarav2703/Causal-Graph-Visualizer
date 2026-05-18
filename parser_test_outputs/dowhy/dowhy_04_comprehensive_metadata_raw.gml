graph [
  directed 1
  node [ id "Treatment_Node" label "Treatment Node" role "treatment" ]
  node [ id "Outcome_Node" label "Outcome Node" role "outcome" ]
  node [ id "Confounder_Node" label "Confounder Node" role "common_cause" ]
  node [ id "Instrument_Node" label "Instrument Node" role "instrument" ]
  node [ id "Mediator_Node" label "Mediator Node" role "mediator" ]
  node [ id "Latent_Node" label "Latent Node" observed "no" latent 1 unobserved 1 ]

  edge [ source "Confounder_Node" target "Treatment_Node" weight 0.42 beta -0.37 confidence 0.91 label "confounder_to_treatment" ]
  edge [ source "Confounder_Node" target "Outcome_Node" weight 0.50 label "confounder_to_outcome" ]
  edge [ source "Treatment_Node" target "Mediator_Node" weight 0.63 beta 0.63 confidence 0.88 label "treatment_to_mediator" ]
  edge [ source "Mediator_Node" target "Outcome_Node" weight -0.22 beta -0.22 confidence 0.79 label "mediator_to_outcome" ]
  edge [ source "Instrument_Node" target "Treatment_Node" weight 0.71 label "instrument_to_treatment" ]
  edge [ source "Latent_Node" target "Treatment_Node" weight 0.30 label "latent_to_treatment" ]
  edge [ source "Latent_Node" target "Outcome_Node" weight 0.35 label "latent_to_outcome" ]
]
