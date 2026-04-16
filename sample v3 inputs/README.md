These sample files all describe the same graph structure in different source formats:

- `Age -> Stress`
- `Exercise -> SleepQuality`
- `Stress -> SleepQuality`
- `SleepQuality -> HeartRisk`

They are intended as import fixtures for `Causal viewer_v3`.

Additional complex fixtures:

- `tetrad_complex_pag.txt`
- `causal_learn_complex_pag.txt`
- `dagitty_complex_pag.txt`
- `dowhy_complex_pag.json`

These four files normalize to the same mixed-edge graph with:

- directed edges
- undirected edges
- bidirected edges
- partially oriented edges with circle endpoints
- per-edge weights
- per-edge confidence values

That makes them better for showcasing:

- endpoint rendering
- target scope filtering
- edge thresholding
- edge labels for weight / beta values
- edge labels for confidence values
- right-click node and edge styling
- layout nudging on a denser graph

Legend files:

- `legend_simple.json`
- `legend_complex_pag.json`
- `legend_tetrad_complex_pag.json`

The Tetrad complex PAG file now has a dedicated legend keyed specifically to `tetrad_complex_pag.txt`.
