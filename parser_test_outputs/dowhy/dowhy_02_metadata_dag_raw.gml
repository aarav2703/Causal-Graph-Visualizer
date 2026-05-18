graph [
  directed 1

  node [ id "Infant_Age" label "Infant Age" role "covariate" ]
  node [ id "Gestational_Age" label "Gestational Age" role "confounder" ]
  node [ id "Feeding_Difficulty" label "Feeding Difficulty" role "treatment" ]
  node [ id "Sleep_Duration" label "Sleep Duration" role "mediator" ]
  node [ id "Crying_Frequency" label "Crying Frequency" role "mediator" ]
  node [ id "Parent_Wellbeing" label "Parent Wellbeing" role "outcome" ]

  edge [ source "Infant_Age" target "Crying_Frequency" weight 0.20 label "age_to_crying" ]
  edge [ source "Gestational_Age" target "Feeding_Difficulty" weight -0.25 label "gestation_to_feeding" ]
  edge [ source "Gestational_Age" target "Sleep_Duration" weight 0.35 label "gestation_to_sleep" ]
  edge [ source "Feeding_Difficulty" target "Sleep_Duration" weight -0.60 label "feeding_to_sleep" ]
  edge [ source "Feeding_Difficulty" target "Crying_Frequency" weight 0.55 label "feeding_to_crying" ]
  edge [ source "Crying_Frequency" target "Parent_Wellbeing" weight -0.60 label "crying_to_parent" ]
]
