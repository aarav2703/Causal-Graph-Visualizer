graph [
  directed 1

  node [ id "Gestational_Age" label "Gestational_Age" ]
  node [ id "Feeding_Difficulty" label "Feeding_Difficulty" ]
  node [ id "Sleep_Duration" label "Sleep_Duration" ]
  node [ id "Crying_Frequency" label "Crying_Frequency" ]
  node [ id "Parent_Wellbeing" label "Parent_Wellbeing" ]

  edge [ source "Gestational_Age" target "Feeding_Difficulty" ]
  edge [ source "Gestational_Age" target "Sleep_Duration" ]
  edge [ source "Feeding_Difficulty" target "Sleep_Duration" ]
  edge [ source "Sleep_Duration" target "Crying_Frequency" ]
  edge [ source "Crying_Frequency" target "Parent_Wellbeing" ]
]
