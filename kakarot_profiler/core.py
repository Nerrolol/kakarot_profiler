import json
import csv
from collections import defaultdict

def load_trace(trace_file):
    """
    Lit le fichier CSV et retourne un dictionnaire {pc: steps}.
    """
    pc_counts = defaultdict(int)
    with open(trace_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                pc = int(row['pc'])
                pc_counts[pc] += 1
            except (KeyError, ValueError):
                continue
    return dict(pc_counts)

def load_references(program_file):
    """
    Extrait du JSON (hors "debug_info") les références : pour chaque référence,
    retourne un dictionnaire {pc: {source, offset, value}}
    """
    with open(program_file, 'r') as f:
        data = json.load(f)
    
    refs = {}
    for key, value in data.items():
        if key == "debug_info":
            continue
        if isinstance(value, dict) and "references" in value:
            for ref in value["references"]:
                pc = ref.get("pc")
                if pc is not None:
                    offset = ref.get("ap_tracking_data", {}).get("offset", 0)
                    refs[int(pc)] = {
                        "source": key,
                        "offset": offset,
                        "value": ref.get("value")
                    }
    return refs

def load_debug_info_section(program_file):
    """
    Extrait la section "debug_info" du JSON pour récupérer les instruction_locations
    et l'offset via "flow_tracking_data"
    """
    with open(program_file, 'r') as f:
        data = json.load(f)
    
    debug_info = data.get("debug_info", {})
    instruction_locations = debug_info.get("instruction_locations", {})
    mapped = {}
    for k, v in instruction_locations.items():
        offset = v.get("flow_tracking_data", {}).get("ap_tracking", {}).get("offset", 0)
        mapped[int(k)] = {
            "source_file": v.get("inst", {}).get("input_file", {}).get("filename"),
            "start_line": v.get("inst", {}).get("start_line"),
            "offset": offset
        }
    return mapped

def combine_debug_mapping(program_file):
    """
    Combine les mappings issus de références et de "debug_info" en privilégiant "debug_info"
    """
    refs = load_references(program_file)
    debug_section = load_debug_info_section(program_file)
    
    combined = {}
    for pc, info in debug_section.items():
        combined[pc] = info
    for pc, info in refs.items():
        if pc not in combined:
            combined[pc] = info
    return combined

def infer_missing_debug_mapping(pc_counts, debug_mapping, window=5):
    """
    Il existe des PC sans debug info associée. Pour chaque PC absent du mapping cherche un voisin dans ±window et attribue son mapping
    """
    new_mapping = debug_mapping.copy()
    sorted_pcs = sorted(pc_counts.keys())
    for pc in sorted_pcs:
        if pc not in new_mapping:
            candidates = [p for p in sorted_pcs if abs(p - pc) <= window and p in new_mapping]
            if candidates:
                nearest = min(candidates, key=lambda x: abs(x - pc))
                new_mapping[pc] = new_mapping[nearest]
            else:
                new_mapping[pc] = {"source": "Unknown", "offset": None}
    return new_mapping

def combine_profile_with_debug(pc_counts, debug_mapping):
    """
    Associe à chaque PC de la trace son nombre de steps et le mapping debug
    """
    profile = []
    for pc, count in pc_counts.items():
        debug_info = debug_mapping.get(pc, None)
        profile.append({
            "pc": pc,
            "steps": count,
            "debug": debug_info
        })
    return sorted(profile, key=lambda x: x["pc"])

def group_by_function_with_metrics(profile):
    """
    Regroupe les PC par fonction et calcule les métriques :
      - total_steps, inner_steps, nested_steps et call_count.
    """
    metrics = {}
    for item in profile:
        debug = item["debug"]
        if debug is None or debug.get("source") == "Unknown":
            func = "Unknown"
        else:
            if "source_file" in debug:
                func = f"{debug.get('source_file')}:{debug.get('start_line')}"
            elif "source" in debug:
                func = debug.get("source")
            else:
                func = "Unknown"
        if func not in metrics:
            metrics[func] = {"total_steps": 0, "inner_steps": 0, "nested_steps": 0, "call_count": 0}
        metrics[func]["total_steps"] += item["steps"]
        metrics[func]["call_count"] += 1
        if debug is not None and debug.get("offset", 0) == 0:
            metrics[func]["inner_steps"] += item["steps"]
        else:
            metrics[func]["nested_steps"] += item["steps"]
    return metrics

def calc_final_profiling(trace_file, program_file):
    """
    Ordonne l'ensemble du pipeline pour produire le profil final :
    retourne (grouped_metrics, percent_with_debug)
    """
    pc_counts = load_trace(trace_file)
    base_mapping = combine_debug_mapping(program_file)
    extended_mapping = infer_missing_debug_mapping(pc_counts, base_mapping, window=5)
    profile = combine_profile_with_debug(pc_counts, extended_mapping)
    grouped_metrics = group_by_function_with_metrics(profile)
    
    total_unique_pc = len(pc_counts)
    count_with_debug = sum(1 for pc in pc_counts if extended_mapping.get(pc, {}).get("source") != "Unknown")
    percent_with_debug = (count_with_debug / total_unique_pc * 100) if total_unique_pc > 0 else 0
    
    return grouped_metrics, percent_with_debug
