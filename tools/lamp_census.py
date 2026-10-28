import os
from typing import Dict, Iterable, List, Optional, Sequence

from lamp_mpq import ArchiveNote
from lamp_rules import is_lamp_like
from lamp_types import ROUTE_NAMES, ArchiveSource
from lamp_world import Census, MapCensus, ModelCensus

ROUTE_ORDER = sorted(ROUTE_NAMES)
INDENT = "  "
NONE = "none"
STOCK = "stock"
CUSTOM = "custom"
UNREADABLE = "unreadable"
TITLE = "LuxVelum lamp census"


def grouped(number: int) -> str:
    return "{:,}".format(number).replace(",", " ")


def counted(number: int, singular: str, plural: Optional[str] = None) -> str:
    return "%s %s" % (grouped(number), singular if number == 1 else plural or singular + "s")


def route_totals(routes: Dict[int, int]) -> str:
    return ", ".join("%s %s" % (ROUTE_NAMES[route], grouped(routes.get(route, 0))) for route in ROUTE_ORDER)


def map_line(record: MapCensus) -> str:
    return "map %d %s: %s, %s, %s (%s)" % (record.map_id, record.directory, counted(record.tiles, "tile"),
                                           counted(record.placements, "placement"), counted(record.lamps, "lamp"),
                                           route_totals(record.routes))


def file_counts(counts: Dict[str, int]) -> str:
    return ", ".join("%s %s" % (kind, grouped(number)) for kind, number in sorted(counts.items()))


def map_details(record: MapCensus) -> str:
    details = [counted(record.wmo_placements, "WMO placement")]
    if record.missing:
        details.append("missing: " + file_counts(record.missing))
    if record.errors:
        details.append("unreadable: " + file_counts(record.errors))
    return "; ".join(details)


def kind_of_source(source: ArchiveSource) -> str:
    return CUSTOM if source.custom else STOCK


def source_lines(source: ArchiveSource, malformed: Sequence[ArchiveNote]) -> List[str]:
    lines = ["%s%-7s %s, %s" % (INDENT, kind_of_source(source), source.name, counted(source.size, "byte"))]
    lines.extend(INDENT * 2 + note.text for note in malformed if note.name == source.name)
    return lines


def unreadable_line(note: ArchiveNote) -> str:
    return "%s%s, %s: %s" % (INDENT, note.name, counted(note.size, "byte"), note.text)


def archive_lines(sources: Sequence[ArchiveSource], ignored: Sequence[str], unreadable: Sequence[ArchiveNote] = (),
                  malformed: Sequence[ArchiveNote] = ()) -> List[str]:
    lines = ["archives, lowest priority first:"]
    for source in sources:
        lines.extend(source_lines(source, malformed))
    if not sources:
        lines.append(INDENT + NONE)
    lines.append("ignored archives:")
    lines.extend(INDENT + name for name in ignored)
    if not ignored:
        lines.append(INDENT + NONE)
    lines.append("unreadable archives, skipped:")
    lines.extend(unreadable_line(note) for note in unreadable)
    if not unreadable:
        lines.append(INDENT + NONE)
    return lines


def total_routes(records: Iterable[MapCensus]) -> Dict[int, int]:
    totals: Dict[int, int] = {}
    for record in records:
        for route, number in record.routes.items():
            totals[route] = totals.get(route, 0) + number
    return totals


def map_lines(census: Census) -> List[str]:
    lines = ["lamps per map:"]
    records = [census.maps[map_id] for map_id in sorted(census.maps)]
    for record in records:
        lines.append(INDENT + map_line(record))
        lines.append(INDENT * 2 + map_details(record))
    if not records:
        lines.append(INDENT + NONE)
    routes = total_routes(records)
    lines.append("all maps: %s (%s)" % (counted(sum(routes.values()), "lamp"), route_totals(routes)))
    return lines


def notable(model: ModelCensus) -> bool:
    return model.lamp_like or model.light_blocks or is_lamp_like(model.path)


def notable_models(census: Census) -> List[ModelCensus]:
    models = [model for model in census.models.values() if notable(model)]
    return sorted(models, key=lambda model: (-model.total_placements, model.path))


def version_text(name: str, lights: Optional[int], custom: Dict[str, bool]) -> str:
    kind = (CUSTOM if custom[name] else STOCK) if name in custom else "?"
    return "%s (%s): %s" % (name, kind, UNREADABLE if lights is None else counted(lights, "light"))


def placement_text(model: ModelCensus) -> str:
    per_map = ", ".join("map %d: %s" % (map_id, grouped(model.placements[map_id]))
                        for map_id in sorted(model.placements))
    return grouped(model.total_placements) + (" (%s)" % per_map if per_map else "")


def model_lines(model: ModelCensus, custom: Dict[str, bool]) -> List[str]:
    versions = "; ".join(version_text(name, lights, custom)
                         for name, lights in zip(model.archives, model.version_lights))
    route = NONE if model.route is None else ROUTE_NAMES.get(model.route, str(model.route))
    lines = [INDENT + model.path,
             INDENT * 2 + "placements: " + placement_text(model),
             INDENT * 2 + "versions: " + (versions or NONE),
             INDENT * 2 + "lights: top %d, stock %d" % (model.top_lights, model.stock_lights),
             INDENT * 2 + "route: " + route]
    if model.notes:
        lines.append(INDENT * 2 + "notes: " + "; ".join(model.notes))
    return lines


def models_section(census: Census, sources: Sequence[ArchiveSource]) -> List[str]:
    custom = {source.name: source.custom for source in sources}
    models = notable_models(census)
    lines = ["models that look like lamps or carry light blocks, most placed first: %d" % len(models)]
    for model in models:
        lines.extend(model_lines(model, custom))
    return lines


def output_lines(out_path: Optional[str], written: int, clamped: int, dropped: int) -> List[str]:
    if out_path is None:
        return []
    return ["written to %s: %s; %s brought into range, %s dropped as unstorable"
            % (out_path, counted(written, "lamp"), grouped(clamped), grouped(dropped))]


def census_text(chain, census: Census, out_path: Optional[str] = None, written: int = 0, clamped: int = 0,
                dropped: int = 0) -> str:
    sources = list(chain.sources)
    lines = [TITLE, "", "data folder: %s" % os.path.abspath(chain.data_dir), "locale: %s" % (chain.locale or NONE)]
    lines.extend(archive_lines(sources, list(chain.ignored), list(chain.unreadable), list(chain.malformed)))
    lines.append("")
    lines.extend(map_lines(census))
    lines.extend(output_lines(out_path, written, clamped, dropped))
    lines.append("")
    lines.extend(models_section(census, sources))
    return "\n".join(lines) + "\n"


def write_census(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
