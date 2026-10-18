"""Review structural changes between NiFi versioned flow snapshots.

Property values are compared in memory but never included in a report.
"""

import argparse
import json
from pathlib import Path

# Names only: values never enter reports. These lists intentionally declare the scope.
PROCESSOR_BEHAVIOR_FIELDS = ("schedulingPeriod", "schedulingStrategy", "executionNode", "concurrentlySchedulableTaskCount", "runDurationMillis", "penaltyDuration", "yieldDuration", "scheduledState", "retryCount", "retriedRelationships", "backoffMechanism", "maxBackoffPeriod")
CONNECTION_BEHAVIOR_FIELDS = ("flowFileExpiration", "backPressureObjectThreshold", "backPressureDataSizeThreshold", "prioritizers", "loadBalanceStrategy", "partitioningAttribute", "loadBalanceCompression")
MISSING = object()



def collect(document):
    root = document.get("flowContents", document)
    if not isinstance(root, dict):
        raise ValueError("flowContents must be an object")
    processors = {}
    connections = set()

    def walk(group):
        for processor in group.get("processors", []):
            key = processor.get("identifier") or processor.get("id")
            if not key:
                raise ValueError("processor missing identifier")
            if key in processors:
                raise ValueError(f"duplicate processor identifier {key}")
            processors[key] = processor
        for connection in group.get("connections", []):
            source = connection.get("source", {})
            destination = connection.get("destination", {})
            source_id = source.get("id") or source.get("identifier") or connection.get("sourceId")
            destination_id = destination.get("id") or destination.get("identifier") or connection.get("destinationId")
            if not source_id or not destination_id:
                raise ValueError("connection missing source or destination")
            for relationship in connection.get("selectedRelationships", []) or []:
                connections.add((source_id, relationship, destination_id))
        for child in group.get("processGroups", []):
            walk(child)

    walk(root)
    return processors, connections


def behavior_changes(before, after):
    """Compare declared operational fields by stable component ID, without values."""
    def inventory(document):
        components = {}
        unchecked = 0
        if not isinstance(document, dict):
            raise ValueError("Snapshot invalide / Invalid snapshot / Snapshot no válido")
        root = document.get("flowContents", document)
        def walk(group):
            nonlocal unchecked
            if not isinstance(group, dict):
                raise ValueError("Groupe invalide / Invalid group / Grupo no válido")
            for kind, fields in (("processors", PROCESSOR_BEHAVIOR_FIELDS), ("connections", CONNECTION_BEHAVIOR_FIELDS)):
                items = group.get(kind, [])
                if not isinstance(items, list):
                    raise ValueError("Liste de composants invalide / Invalid component list / Lista de componentes no válida")
                for item in items:
                    if not isinstance(item, dict):
                        raise ValueError("Composant invalide / Invalid component / Componente no válido")
                    key = item.get("identifier") or item.get("id")
                    if not isinstance(key, str) or not key:
                        unchecked += 1
                        continue
                    identity = (kind, key)
                    if identity in components:
                        raise ValueError("Identifiant dupliqué / Duplicate identifier / Identificador duplicado")
                    components[identity] = (item, fields)
            children = group.get("processGroups", [])
            if not isinstance(children, list):
                raise ValueError("Liste de groupes invalide / Invalid group list / Lista de grupos no válida")
            for child in children:
                walk(child)
        walk(root)
        return components, unchecked
    old, old_unchecked = inventory(before)
    new, new_unchecked = inventory(after)
    changes = []
    for identity in sorted(old.keys() & new.keys()):
        previous, fields = old[identity]
        candidate = new[identity][0]
        for field in fields:
            if previous.get(field, MISSING) != candidate.get(field, MISSING):
                changes.append({"kind": identity[0], "component": identity[1], "field": field})
    added = [{"kind": k, "component": v} for k, v in sorted(new.keys() - old.keys())]
    removed = [{"kind": k, "component": v} for k, v in sorted(old.keys() - new.keys())]
    return {"behavior_changed": changes, "behavior_components_added": added, "behavior_components_removed": removed,
            "behavior_unchecked": [{"side": side, "count": count} for side, count in (("before", old_unchecked), ("after", new_unchecked)) if count]}


def review(before, after):
    behavior = behavior_changes(before, after)
    old_processors, old_routes = collect(before)
    new_processors, new_routes = collect(after)
    report = {"processors_added": [], "processors_removed": [], "properties_changed": [], "routes_added": [], "routes_removed": [], "auto_terminated_added": [], "auto_terminated_removed": []}
    report["processors_added"] = sorted(set(new_processors) - set(old_processors))
    report["processors_removed"] = sorted(set(old_processors) - set(new_processors))
    for key in sorted(set(old_processors) & set(new_processors)):
        old = old_processors[key]
        new = new_processors[key]
        old_properties = old.get("properties") or {}
        new_properties = new.get("properties") or {}
        if not isinstance(old_properties, dict) or not isinstance(new_properties, dict):
            raise ValueError(f"processor {key}: properties must be an object")
        for name in sorted(old_properties.keys() | new_properties.keys()):
            if old_properties.get(name, MISSING) != new_properties.get(name, MISSING):
                report["properties_changed"].append({"processor": key, "property": name})
        old_terminated = set(old.get("autoTerminatedRelationships") or [])
        new_terminated = set(new.get("autoTerminatedRelationships") or [])
        report["auto_terminated_added"].extend({"processor": key, "relationship": name} for name in sorted(new_terminated - old_terminated))
        report["auto_terminated_removed"].extend({"processor": key, "relationship": name} for name in sorted(old_terminated - new_terminated))
    report["routes_added"] = [dict(zip(("source", "relationship", "destination"), route)) for route in sorted(new_routes - old_routes)]
    report["routes_removed"] = [dict(zip(("source", "relationship", "destination"), route)) for route in sorted(old_routes - new_routes)]
    report.update(behavior)
    return report


def check_contract(document, contract):
    """Check explicit route invariants against a candidate flow."""
    _, routes = collect(document)
    expected = contract.get("required_routes")
    if not isinstance(expected, list):
        raise ValueError("contract requires a required_routes array")
    missing = []
    for route in expected:
        if not isinstance(route, dict) or not all(isinstance(route.get(name), str) for name in ("source", "relationship", "destination")):
            raise ValueError("required_routes entries need source, relationship and destination strings")
        key = (route["source"], route["relationship"], route["destination"])
        if key not in routes:
            missing.append(route)
    return missing


def markdown(report, lang="en"):
    copy = {
        "fr": ("Revue du flow NiFi", "Changements structurels et champs de comportement déclarés ; aucune valeur affichée. Les composants sans identifiant restent non vérifiés.", "Aucun."),
        "en": ("NiFi flow review", "Structural changes and declared behavior fields; values are never shown. Components without identifiers remain unchecked.", "None."),
        "es": ("Revisión del flujo NiFi", "Cambios estructurales y campos de comportamiento declarados; nunca se muestran valores. Los componentes sin identificador quedan sin verificar.", "Ninguno."),
    }
    labels = {
        "fr": ("Champs de comportement modifiés", "Composants ajoutés", "Composants supprimés", "Couverture non vérifiée"),
        "en": ("Changed behavior fields", "Added components", "Removed components", "Unchecked coverage"),
        "es": ("Campos de comportamiento modificados", "Componentes añadidos", "Componentes eliminados", "Cobertura sin verificar"),
    }
    headings = dict(zip(("behavior_changed", "behavior_components_added", "behavior_components_removed", "behavior_unchecked"), labels[lang]))
    title, scope, empty = copy[lang]
    lines = ["# " + title, "", scope, ""]
    for key, entries in report.items():
        lines += [f"## {headings.get(key, key)} ({len(entries)})", ""]
        for entry in entries:
            if isinstance(entry, dict):
                label = ", ".join(f"{name}={value}" for name, value in entry.items())
            else:
                label = entry
            lines.append("- " + str(label).replace("\n", " ").replace("\r", " "))
        if not entries:
            lines.append(empty)
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Review two NiFi versioned flow JSON files")
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--lang", choices=("fr", "en", "es"), default="en", help="Langue / Language / Idioma")
    parser.add_argument("--fail-on-behavior-change", action="store_true", help="Refuser changements ou couverture incomplète / Reject changes or incomplete coverage / Rechazar cambios o cobertura incompleta")
    parser.add_argument("--fail-on-removed-route", action="store_true")
    parser.add_argument("--contract", help="JSON file with required_routes structural assertions")
    args = parser.parse_args(argv)
    try:
        before = json.loads(Path(args.before).read_text(encoding="utf-8"))
        after = json.loads(Path(args.after).read_text(encoding="utf-8"))
        report = review(before, after)
        if args.contract:
            contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
            report["required_routes_missing"] = check_contract(after, contract)
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.format == "json" else markdown(report, args.lang))
    return int((args.fail_on_removed_route and bool(report["routes_removed"])) or bool(report.get("required_routes_missing")) or (args.fail_on_behavior_change and any(report[key] for key in ("behavior_changed", "behavior_components_added", "behavior_components_removed", "behavior_unchecked"))))


if __name__ == "__main__":
    raise SystemExit(main())
