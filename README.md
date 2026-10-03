# NiFi Flow Review

Review two Apache NiFi versioned flow JSON exports before merging a pull request. The report lists processor additions and removals, changed property **names**, changed routes and automatic termination changes. Property **values are never printed**.

```sh
python3 flow_review.py examples/before.json examples/after.json
python3 flow_review.py examples/before.json examples/after.json --contract examples/route-contract.json
python3 -m unittest discover -s tests
```

The optional contract contains `required_routes`, each with `source`, `relationship` and `destination` IDs. Missing routes cause exit code 1. `--fail-on-removed-route` also makes removed routes fail. This checks the **structure** of a downloaded/versioned flow, including nested process groups; it does not execute processors, evaluate NiFi Expression Language, or prove runtime routing. See [NiFi versioned flows](https://nifi.apache.org/nifi-docs/user-guide.html) and [Stateless NiFi's flow snapshot format](https://github.com/apache/nifi/blob/main/nifi-stateless/nifi-stateless-assembly/README.md).

## Français

Comparez deux exports JSON d’un flow NiFi dans une PR. Le rapport montre les routes et processeurs modifiés ainsi que les noms des propriétés changées, sans afficher leurs valeurs. Un contrat JSON peut exiger certaines routes. Ce contrôle est structurel : il ne rejoue pas les FlowFiles.

## Español

Compare dos exportaciones JSON de un flujo NiFi en una PR. El informe muestra rutas y procesadores modificados y los nombres de las propiedades cambiadas, sin mostrar sus valores. Un contrato JSON puede exigir ciertas rutas. Esta comprobación es estructural: no reproduce los FlowFiles.

MIT licensed.
