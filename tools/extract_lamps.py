import argparse
import os
import sys
import time
from typing import Dict, List, Optional, Sequence, TextIO, Tuple

from lamp_census import census_text, counted, grouped, map_line, route_totals, write_census
from lamp_formats import FormatError, model_file_name, parse_m2, parse_map_dbc, skin_path
from lamp_mpq import ArchiveChain, MpqError, VersionRead, read_archive_order
from lamp_rules import POINT_LIGHT, classify, emitting_point_lights, fire_emitter, fire_strength
from lamp_types import KIND_NAMES, ROUTE_NAMES, ArchiveSource, Lamp, M2Model, ModelLamp
from lamp_world import Census, evaluate_model, matching_skin, model_key, present_reads, skin_data, walk_map
from lamp_writer import prepare_lamps, write_lamp_data

PROGRAM = "extract_lamps.py"
MAP_DBC = "DBFilesClient\\Map.dbc"
OUT_FOLDER = "LuxVelum"
LAMP_DATA_NAME = "lampdata.bin"
CENSUS_NAME = "lamps-census.txt"
EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_USAGE = 2
INDENT = "  "
MAP_SEPARATOR = ","
MODEL_SEPARATOR = "\\"
LIGHT_TYPE_NAMES = {0: "directional", POINT_LIGHT: "point"}
FLAG_NAMES = ((0x1, "WMO doodad"), (0x2, "top of the box"), (0x4, "clamped into the box"), (0x8, "global WMO"),
              (0x10, "dead authored blocks"))


def say(out: TextIO, text: str) -> None:
    print(text, file=out, flush=True)


def map_ids(text: str) -> List[int]:
    try:
        ids = [int(part) for part in text.replace(" ", "").split(MAP_SEPARATOR) if part]
    except ValueError:
        raise argparse.ArgumentTypeError("%r is not a comma-separated list of map ids" % text) from None
    if not ids or any(map_id < 0 for map_id in ids):
        raise argparse.ArgumentTypeError("%r is not a comma-separated list of map ids" % text)
    return ids


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM, description="Finds the lamps of the client's maps in its MPQ archives and writes "
                                  "lampdata.bin, from which LuxVelum lets lamps without a light of their own glow "
                                  "in the fog.")
    parser.add_argument("--data", required=True, help="the client's Data folder")
    parser.add_argument("--out", help="lampdata.bin to write (default: LuxVelum\\lampdata.bin in the Data folder)")
    parser.add_argument("--census", help="census to write (default: lamps-census.txt next to --out)")
    parser.add_argument("--maps", type=map_ids, help="map ids to walk, such as 0,1,530,571 (default: every map)")
    parser.add_argument("--locale", help="locale folder in Data, such as enUS (default: found from its archives)")
    parser.add_argument("--archives", help="text file naming the archives to read, one path relative to the Data "
                                           "folder per line, lowest priority first (default: the client's order)")
    parser.add_argument("--model", nargs="+", metavar="PATH", help="describe these models in every archive that "
                                                                   "holds them, with their verdict, and stop")
    return parser


def usage_problem(args: argparse.Namespace) -> Optional[str]:
    if not os.path.isdir(args.data):
        return "--data %s is not a folder" % args.data
    if args.archives is None:
        return None
    try:
        read_archive_order(args.archives, args.data)
    except (MpqError, OSError, UnicodeDecodeError) as error:
        return "--archives: %s" % error
    return None


def kind_of_source(source: ArchiveSource) -> str:
    return "custom" if source.custom else "stock"


def report_chain(chain: ArchiveChain, out: TextIO) -> None:
    say(out, "archives in %s, locale %s, lowest priority first:" % (chain.data_dir, chain.locale or "none"))
    for source in chain.sources:
        say(out, "%s%-7s %s" % (INDENT, kind_of_source(source), source.name))
        for note in chain.malformed:
            if note.name == source.name:
                say(out, INDENT * 2 + note.text)
    if chain.ignored:
        say(out, "ignored: " + ", ".join(chain.ignored))
    for note in chain.unreadable:
        say(out, "unreadable, skipped: %s (%s)" % (note.name, note.text))


def vector(values: Sequence[float]) -> str:
    return "(%s)" % ", ".join("%.2f" % value for value in values)


def flag_names(flags: int) -> str:
    names = [name for bit, name in FLAG_NAMES if flags & bit]
    return ", ".join(names) if names else "none"


def light_lines(model: M2Model) -> List[str]:
    emitting = emitting_point_lights(model)
    lines = ["lights: %d" % len(model.lights)]
    for index, light in enumerate(model.lights):
        lines.append("%slight %d: %s, bone %d, at %s, colour %s x %.2f, attenuation %.2f to %.2f, %s, %s" % (
            INDENT, index, LIGHT_TYPE_NAMES.get(light.light_type, "type %d" % light.light_type), light.bone,
            vector(light.position), vector(light.diffuse_color), light.diffuse_intensity, light.attenuation_start,
            light.attenuation_end, "visible" if light.visible else "hidden",
            "emits" if light in emitting else "dark"))
    return lines


def emitter_lines(model: M2Model) -> List[str]:
    lines = ["emitters: %d" % len(model.emitters)]
    for index, emitter in enumerate(model.emitters):
        flame = "flame of strength %.2f" % fire_strength(emitter) if fire_emitter(emitter) else "no flame"
        lines.append("%semitter %d: texture %s, blend %d, peak rate %.2f, peak size %.2f, at %s, %s" % (
            INDENT, index, emitter.texture or "(replaceable)", emitter.blend, emitter.emission_rate,
            max([0.0] + list(emitter.sizes)), vector(emitter.position), flame))
    return lines


def batch_lines(model: M2Model) -> List[str]:
    lines = ["batches: %d" % len(model.batches)]
    for index, batch in enumerate(model.batches):
        lines.append("%sbatch %d: %s, blend %d, texture %s, centre %s, %s" % (
            INDENT, index, "unlit" if batch.unlit else "lit", batch.blend, batch.texture or "(replaceable)",
            vector(batch.center), counted(batch.index_count, "index", "indices")))
    return lines


def model_lines(model: M2Model) -> List[str]:
    lines = ["M2 version %d, box %s to %s, %s" % (model.version, vector(model.bounds_min), vector(model.bounds_max),
                                                  counted(len(model.textures), "texture"))]
    lines.extend(light_lines(model) + emitter_lines(model) + batch_lines(model))
    notes = getattr(model, "notes", [])
    if notes:
        lines.append("notes: " + "; ".join(notes))
    return lines


def model_lamp_line(index: int, lamp: ModelLamp) -> str:
    return "%slamp %d: %s %s at %s, colour %s x %.2f, reach %.1f yd, flags %s" % (
        INDENT * 2, index, ROUTE_NAMES.get(lamp.route, str(lamp.route)), KIND_NAMES.get(lamp.kind, str(lamp.kind)),
        vector(lamp.position), vector(lamp.color), lamp.intensity, lamp.reach, flag_names(lamp.flags))


def version_text(read: VersionRead) -> str:
    return "unreadable" if read.error is not None else counted(len(read.data), "byte")


def version_body(path: str, read: VersionRead, skin: Optional[bytes]) -> List[str]:
    if read.error is not None:
        return ["unreadable: %s" % read.error]
    try:
        return model_lines(parse_m2(path, read.data, skin))
    except FormatError as error:
        return ["parse error: %s" % error]


def version_lines(chain: ArchiveChain, path: str) -> List[str]:
    reads = present_reads(chain, path)
    skins = skin_data(present_reads(chain, skin_path(path)))
    if not reads:
        return [INDENT + "in no archive: missing file"]
    lines = []
    for index, read in enumerate(reads):
        lines.append("%sversion %d of %d: %s (%s), %s" % (INDENT, index + 1, len(reads), read.source.name,
                                                          kind_of_source(read.source), version_text(read)))
        skin = matching_skin(read.source, skins, index == 0)
        lines.extend(INDENT * 2 + line for line in version_body(path, read, skin))
    return lines


def verdict_lines(chain: ArchiveChain, path: str) -> List[str]:
    verdict, _ = evaluate_model(chain, model_key(path), classify)
    route = "none" if verdict.route is None else ROUTE_NAMES.get(verdict.route, str(verdict.route))
    lines = [INDENT + "verdict: %s, %s" % (route, counted(len(verdict.lamps), "lamp"))]
    lines.extend(model_lamp_line(index, lamp) for index, lamp in enumerate(verdict.lamps))
    if verdict.notes:
        lines.append(INDENT + "notes: " + "; ".join(verdict.notes))
    return lines


def describe_model(chain: ArchiveChain, path: str, out: TextIO) -> None:
    say(out, path)
    try:
        lines = version_lines(chain, path) + verdict_lines(chain, path)
    except MpqError as error:
        lines = [INDENT + "unreadable: %s" % error]
    for line in lines:
        say(out, line)


def model_path(text: str) -> str:
    return model_file_name(text.replace("/", MODEL_SEPARATOR))


def describe_models(chain: ArchiveChain, paths: Sequence[str], out: TextIO) -> int:
    for path in paths:
        describe_model(chain, model_path(path), out)
    return EXIT_OK


def read_maps(chain: ArchiveChain, out: TextIO) -> Optional[List[Tuple[int, str]]]:
    try:
        data = chain.read(MAP_DBC)
        if data is None:
            say(out, "no %s in any archive" % MAP_DBC)
            return None
        return parse_map_dbc(data)
    except (MpqError, FormatError) as error:
        say(out, "%s is unreadable: %s" % (MAP_DBC, error))
        return None


def selected_maps(maps: Sequence[Tuple[int, str]], wanted: Optional[Sequence[int]],
                  out: TextIO) -> List[Tuple[int, str]]:
    if wanted is None:
        return list(maps)
    known = dict(maps)
    for map_id in wanted:
        if map_id not in known:
            say(out, "map %d is not in %s and is skipped" % (map_id, MAP_DBC))
    return [(map_id, known[map_id]) for map_id in dict.fromkeys(wanted) if map_id in known]


def default_out(data_dir: str) -> str:
    return os.path.join(data_dir, OUT_FOLDER, LAMP_DATA_NAME)


def census_path(out_path: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(out_path)), CENSUS_NAME)


def walk_maps(chain: ArchiveChain, maps: Sequence[Tuple[int, str]], census: Census, out: TextIO) -> List[Lamp]:
    model_cache: Dict = {}
    wmo_cache: Dict = {}
    lamps: List[Lamp] = []
    for map_id, directory in maps:
        started = time.perf_counter()
        lamps.extend(walk_map(chain, map_id, directory, model_cache, census, wmo_cache=wmo_cache))
        say(out, "%s; %.1f s" % (map_line(census.map(map_id, directory)), time.perf_counter() - started))
    return lamps


def written_routes(lamps: Sequence[Lamp]) -> Dict[int, int]:
    routes: Dict[int, int] = {}
    for lamp in lamps:
        routes[lamp.route] = routes.get(lamp.route, 0) + 1
    return routes


def extract(chain: ArchiveChain, args: argparse.Namespace, out: TextIO) -> int:
    started = time.perf_counter()
    maps = read_maps(chain, out)
    if maps is None:
        return EXIT_NOT_FOUND
    census = Census()
    prepared = prepare_lamps(walk_maps(chain, selected_maps(maps, args.maps, out), census, out))
    out_path = os.path.abspath(args.out or default_out(args.data))
    census_file = args.census or census_path(out_path)
    try:
        write_lamp_data(out_path, prepared.lamps, chain.sources)
        write_census(census_file, census_text(chain, census, out_path, len(prepared.lamps), prepared.clamped,
                                              prepared.dropped))
    except OSError as error:
        say(out, "cannot write the results: %s" % error)
        return EXIT_NOT_FOUND
    lamp_maps = len({lamp.map_id for lamp in prepared.lamps})
    say(out, "wrote %s on %s to %s (%s); %s brought into range, %s dropped" % (
        counted(len(prepared.lamps), "lamp"), counted(lamp_maps, "map"), out_path,
        route_totals(written_routes(prepared.lamps)), grouped(prepared.clamped), grouped(prepared.dropped)))
    say(out, "census of %s in %s" % (counted(len(census.models), "model"), census_file))
    say(out, "done in %.1f s" % (time.perf_counter() - started))
    return EXIT_OK


def run(args: argparse.Namespace, out: TextIO) -> int:
    try:
        chain = ArchiveChain(args.data, locale=args.locale, order_file=args.archives)
    except (MpqError, OSError) as error:
        say(out, "cannot open the archives: %s" % error)
        return EXIT_NOT_FOUND
    with chain:
        report_chain(chain, out)
        if not chain.sources:
            say(out, ("no MPQ archive in %s could be opened" if chain.unreadable else "no MPQ archive found in %s")
                % args.data)
            return EXIT_NOT_FOUND
        if args.model:
            return describe_models(chain, args.model, out)
        return extract(chain, args, out)


def main(argv: Optional[Sequence[str]] = None, out: Optional[TextIO] = None) -> int:
    parser = argument_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:
        return stop.code if isinstance(stop.code, int) else EXIT_USAGE
    problem = usage_problem(args)
    if problem is not None:
        parser.print_usage(sys.stderr)
        print("%s: error: %s" % (PROGRAM, problem), file=sys.stderr)
        return EXIT_USAGE
    return run(args, out or sys.stdout)


def replace_unprintable(stream: TextIO) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(errors="replace")


if __name__ == "__main__":
    replace_unprintable(sys.stdout)
    sys.exit(main())
