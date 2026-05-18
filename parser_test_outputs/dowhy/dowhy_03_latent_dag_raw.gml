graph [
  directed 1

  node [ id "U_Stress" label "Unobserved Stress" unobserved 1 latent 1 ]
  node [ id "Feeding_Difficulty" label "Feeding Difficulty" role "treatment" ]
  node [ id "Sleep_Duration" label "Sleep Duration" role "mediator" ]
  node [ id "Crying_Frequency" label "Crying Frequency" role "mediator" ]
  node [ id "Parent_Wellbeing" label "Parent Wellbeing" role "outcome" ]
  node [ id "Soothing_Response" label "Soothing Response" role "covariate" ]

  edge [ source "U_Stress" target "Feeding_Difficulty" label "latent_to_feeding" ]
  edge [ source "U_Stress" target "Parent_Wellbeing" label "latent_to_parent" ]
  edge [ source "Feeding_Difficulty" target "Sleep_Duration" weight -0.60 ]
  edge [ source "Sleep_Duration" target "Crying_Frequency" weight -0.35 ]
  edge [ source "Crying_Frequency" target "Parent_Wellbeing" weight -0.60 ]
  edge [ source "Soothing_Response" target "Parent_Wellbeing" weight 0.25 ]
]
