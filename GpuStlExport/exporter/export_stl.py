import argparse
import os
import struct
import sys
import zipfile

import numpy as np

DEFAULT_INPUT_DIR = "in"
DEFAULT_OUTPUT_DIR = "out"
DEFAULT_SHAPE = None
DEFAULT_ROCM_PREFIX = "/opt/rocm"
DEFAULT_ROCM_PATH_FILE = ".rocm_path.local"
REEXEC_ENV = "FREECAD_STL_EXPORT_ROCM_REEXEC"
PRESETS = {
    "draft": {"samples": 96, "segments": 512},
    "standard": {"samples": 384, "segments": 4096},
    "fine": {"samples": 768, "segments": 8192},
}


def project_root():
    return os.path.dirname(os.path.abspath(__file__))


def project_venv_python():
    return os.path.join(project_root(), ".venv", "bin", "python")


def resolve_rocm_path():
    env_path = os.environ.get("ROCM_PATH")
    if env_path:
        return env_path

    env_path = os.environ.get("FREECAD_ROCM_PATH")
    if env_path:
        return env_path

    path_file = os.path.join(project_root(), DEFAULT_ROCM_PATH_FILE)
    if os.path.isfile(path_file):
        with open(path_file, "r", encoding="utf-8") as f:
            value = f.read().strip()
        if value:
            return value

    return DEFAULT_ROCM_PREFIX


def prepend_env_path(env, key, values):
    current = env.get(key, "")
    existing = [part for part in current.split(":") if part]
    merged = []
    for value in values:
        if value and value not in merged:
            merged.append(value)
    for value in existing:
        if value not in merged:
            merged.append(value)
    env[key] = ":".join(merged)


def maybe_reexec_into_project_venv():
    venv_python = project_venv_python()
    if os.environ.get(REEXEC_ENV) == "1":
        return
    if not os.path.exists(venv_python):
        return
    if os.path.abspath(sys.executable) == os.path.abspath(venv_python):
        return

    env = dict(os.environ)
    env[REEXEC_ENV] = "1"
    env["VIRTUAL_ENV"] = os.path.join(project_root(), ".venv")

    prepend_env_path(env, "PATH", [os.path.join(env["VIRTUAL_ENV"], "bin")])

    rocm = resolve_rocm_path()
    if os.path.isdir(rocm):
        env.setdefault("ROCM_PATH", rocm)
        env.setdefault("HIP_PATH", rocm)
        env.setdefault("HSA_PATH", rocm)
        env.setdefault("USE_ROCM_HIPBLASLT", "0")
        prepend_env_path(env, "PATH", [
            os.path.join(rocm, "bin"),
            os.path.join(rocm, "llvm", "bin"),
        ])
        prepend_env_path(env, "LD_LIBRARY_PATH", [
            os.path.join(rocm, "lib"),
            os.path.join(rocm, "lib64"),
            os.path.join(rocm, "lib", "llvm", "lib"),
            os.path.join(rocm, "lib", "host-math", "lib"),
            os.path.join(rocm, "lib", "rocm_sysdeps", "lib"),
            os.path.join(rocm, "llvm", "lib"),
        ])

        libomp = os.path.join(rocm, "lib", "llvm", "lib", "libomp.so")
        if os.path.exists(libomp):
            prepend_env_path(env, "LD_PRELOAD", [libomp])

        if "HIP_DEVICE_LIB_PATH" not in env:
            bitcode_paths = [
                os.path.join(rocm, "lib", "llvm", "amdgcn", "bitcode"),
                os.path.join(rocm, "amdgcn", "bitcode"),
            ]
            for path in bitcode_paths:
                if os.path.isdir(path):
                    env["HIP_DEVICE_LIB_PATH"] = path
                    break

    os.execvpe(venv_python, [venv_python, __file__, *sys.argv[1:]], env)


maybe_reexec_into_project_venv()

torch = None
TORCH_IMPORT_ERROR = None
TORCH_IMPORT_ATTEMPTED = False


def ensure_torch():
    global torch, TORCH_IMPORT_ERROR, TORCH_IMPORT_ATTEMPTED
    if TORCH_IMPORT_ATTEMPTED:
        return torch
    TORCH_IMPORT_ATTEMPTED = True
    try:
        import torch as torch_module
        torch = torch_module
        TORCH_IMPORT_ERROR = None
    except Exception:
        torch = None
        TORCH_IMPORT_ERROR = sys.exc_info()[1]
    return torch


def find_default_fcstd(input_dir=DEFAULT_INPUT_DIR):
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    matches = sorted(
        os.path.join(input_dir, name)
        for name in os.listdir(input_dir)
        if name.lower().endswith(".fcstd")
    )

    if not matches:
        raise FileNotFoundError(f"No .FCStd file found in {input_dir}/")
    if len(matches) > 1:
        joined = "\n  ".join(matches)
        raise ValueError(f"Multiple .FCStd files found. Pick one explicitly:\n  {joined}")

    return matches[0]


def default_output_path(fcstd):
    stem = os.path.splitext(os.path.basename(fcstd))[0]
    return os.path.join(DEFAULT_OUTPUT_DIR, f"{stem}.stl")


def list_fcstd_shapes(fcstd_path):
    with zipfile.ZipFile(fcstd_path) as zf:
        return sorted(
            name[:-10]
            for name in zf.namelist()
            if name.endswith(".Shape.brp")
        )


def resolve_shape_name(fcstd_path, requested_shape):
    if requested_shape:
        return requested_shape
    shapes = list_fcstd_shapes(fcstd_path)
    if not shapes:
        raise ValueError(f"No .Shape.brp entries found in {fcstd_path}")
    if len(shapes) == 1:
        return shapes[0]
    joined = "\n  ".join(shapes)
    raise ValueError(
        "Multiple shapes found in FCStd. "
        "Please pass one explicitly via --shape NAME:\n  "
        f"{joined}"
    )


def read_shape_brep(fcstd_path, shape_name):
    member = f"{shape_name}.Shape.brp"
    with zipfile.ZipFile(fcstd_path) as zf:
        try:
            with zf.open(member) as f:
                return f.read().decode("utf-8")
        except KeyError as exc:
            shapes = sorted(
                name[:-10]
                for name in zf.namelist()
                if name.endswith(".Shape.brp")
            )
            joined = "\n  ".join(shapes)
            raise KeyError(f"Shape not found: {shape_name}\nAvailable shapes:\n  {joined}") from exc


def parse_curves(brep_text):
    lines = [line.strip() for line in brep_text.splitlines() if line.strip()]
    curves = []

    i = 0
    while i < len(lines):
        parts = lines[i].split()
        if len(parts) == 2 and parts[0] == "Curves":
            count = int(parts[1])
            i += 1
            for _ in range(count):
                parts = lines[i].split()
                curve_type = int(parts[0])

                if curve_type == 7:
                    degree = int(parts[3])
                    pole_count = int(parts[4])
                    knot_count = int(parts[5])
                    values = [float(x) for x in parts[6:]]

                    poles = []
                    weights = []
                    for j in range(pole_count):
                        x, y, z, w = values[j * 4:(j + 1) * 4]
                        poles.append((x, y, z))
                        weights.append(w)

                    knot_parts = lines[i + 1].split()
                    knots = []
                    for j in range(knot_count):
                        knot = float(knot_parts[j * 2])
                        multiplicity = int(knot_parts[j * 2 + 1])
                        knots.extend([knot] * multiplicity)

                    curves.append({
                        "degree": degree,
                        "poles": np.array(poles, dtype=float),
                        "weights": np.array(weights, dtype=float),
                        "knots": np.array(knots, dtype=float),
                    })
                    i += 2
                    continue

                i += 1

            return curves

        i += 1

    raise ValueError("No Curves section found in BREP.")


def basis_function(i, degree, knots, u):
    if degree == 0:
        if knots[i] <= u < knots[i + 1]:
            return 1.0
        if u == knots[-1] and knots[i] <= u <= knots[i + 1]:
            return 1.0
        return 0.0

    left = 0.0
    left_den = knots[i + degree] - knots[i]
    if left_den:
        left = (u - knots[i]) / left_den * basis_function(i, degree - 1, knots, u)

    right = 0.0
    right_den = knots[i + degree + 1] - knots[i + 1]
    if right_den:
        right = (
            (knots[i + degree + 1] - u)
            / right_den
            * basis_function(i + 1, degree - 1, knots, u)
        )

    return left + right


def sample_bspline(curve, count):
    degree = curve["degree"]
    poles = curve["poles"]
    weights = curve["weights"]
    knots = curve["knots"]

    u0 = knots[degree]
    u1 = knots[-degree - 1]
    samples = []

    for u in np.linspace(u0, u1, count):
        numerator = np.zeros(3)
        denominator = 0.0

        for i, (point, weight) in enumerate(zip(poles, weights)):
            b = basis_function(i, degree, knots, float(u))
            bw = b * weight
            numerator += bw * point
            denominator += bw

        samples.append(numerator / denominator)

    return [np.array([(abs(float(p[0])), float(p[1])) for p in samples], dtype=np.float32)]


def load_profile_loops(fcstd, shape, samples):
    brep_text = read_shape_brep(fcstd, shape)
    curves = parse_curves(brep_text)
    if not curves:
        raise ValueError(f"No B-spline profile curves found in shape: {shape}")
    return [loop for curve in curves for loop in sample_bspline(curve, samples)]


def remove_duplicate_closing_point(points, eps=1e-6):
    if len(points) >= 2 and np.linalg.norm(points[0] - points[-1]) < eps:
        return points[:-1]
    return points


def make_loop_triangles_numpy(points, segments, closed=True):
    points = remove_duplicate_closing_point(points).astype(np.float32, copy=False)
    if len(points) < 2:
        return None

    p0 = points if closed else points[:-1]
    p1 = np.roll(points, shift=-1, axis=0) if closed else points[1:]

    theta = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False, dtype=np.float32)
    c = np.cos(theta)
    s = np.sin(theta)

    def rotate(profile_points):
        r = profile_points[:, 0]
        z = profile_points[:, 1]
        x = r[:, None] * c[None, :]
        y = r[:, None] * s[None, :]
        zz = np.broadcast_to(z[:, None], x.shape)
        return np.stack((x, y, zz), axis=-1)

    v00 = rotate(p0)
    v10 = rotate(p1)
    v01 = np.roll(v00, shift=-1, axis=1)
    v11 = np.roll(v10, shift=-1, axis=1)

    tri_a = np.stack((v00, v10, v11), axis=2).reshape(-1, 3, 3)
    tri_b = np.stack((v00, v11, v01), axis=2).reshape(-1, 3, 3)
    return np.concatenate((tri_a, tri_b), axis=0)


def make_loop_triangles_torch(points, segments, device, closed=True):
    points = remove_duplicate_closing_point(points)
    if len(points) < 2:
        return None

    p = torch.tensor(points, dtype=torch.float32, device=device)
    p0 = p if closed else p[:-1]
    p1 = torch.roll(p, shifts=-1, dims=0) if closed else p[1:]

    theta = torch.linspace(
        0.0,
        2.0 * torch.pi,
        segments + 1,
        device=device,
        dtype=torch.float32,
    )[:-1]
    c = torch.cos(theta)
    s = torch.sin(theta)

    def rotate(profile_points):
        r = profile_points[:, 0]
        z = profile_points[:, 1]
        x = r[:, None] * c[None, :]
        y = r[:, None] * s[None, :]
        zz = z[:, None].expand_as(x)
        return torch.stack((x, y, zz), dim=-1)

    v00 = rotate(p0)
    v10 = rotate(p1)
    v01 = torch.roll(v00, shifts=-1, dims=1)
    v11 = torch.roll(v10, shifts=-1, dims=1)

    tri_a = torch.stack((v00, v10, v11), dim=2).reshape(-1, 3, 3)
    tri_b = torch.stack((v00, v11, v01), dim=2).reshape(-1, 3, 3)
    return torch.cat((tri_a, tri_b), dim=0)


def select_device(mode):
    if mode == "cpu":
        return None

    torch_module = ensure_torch()
    if torch_module is None:
        raise RuntimeError(
            "GPU mode needs the local .venv with PyTorch (CUDA or ROCm). "
            f"Torch import failed: {TORCH_IMPORT_ERROR!r}"
        )
    if not torch_module.cuda.is_available():
        raise RuntimeError("GPU mode requested, but PyTorch reports no GPU.")
    return torch_module.device("cuda")


def build_triangles(loops, segments, mode, closed):
    device = select_device(mode)
    print("mode:", mode)
    print("device:", device if device is not None else "numpy-cpu")

    all_triangles = []
    for loop_id, points in enumerate(loops):
        if device is None:
            tris = make_loop_triangles_numpy(points, segments, closed=closed)
        else:
            tris = make_loop_triangles_torch(points, segments, device=device, closed=closed)

        if tris is None:
            continue

        all_triangles.append(tris)
        print(f"loop {loop_id}: {len(points)} profile points -> {tris.shape[0]} triangles")

    if not all_triangles:
        raise RuntimeError("No triangles generated.")

    if device is None:
        return np.concatenate(all_triangles, axis=0)
    return torch.cat(all_triangles, dim=0)


def write_binary_stl(path, triangles):
    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    if isinstance(triangles, np.ndarray):
        v1 = triangles[:, 1] - triangles[:, 0]
        v2 = triangles[:, 2] - triangles[:, 0]
        normals = np.cross(v1, v2, axis=1)
        lengths = np.linalg.norm(normals, axis=1)
        mask = lengths > 1e-12
        tri_cpu = triangles[mask].astype("<f4", copy=False)
        normal_cpu = (normals[mask] / lengths[mask, None]).astype("<f4", copy=False)
    else:
        v1 = triangles[:, 1] - triangles[:, 0]
        v2 = triangles[:, 2] - triangles[:, 0]
        normals = torch.cross(v1, v2, dim=1)
        lengths = torch.linalg.norm(normals, dim=1)
        mask = lengths > 1e-12
        tri_cpu = triangles[mask].detach().cpu().numpy().astype("<f4", copy=False)
        normal_cpu = (
            normals[mask] / lengths[mask, None]
        ).detach().cpu().numpy().astype("<f4", copy=False)

    count = tri_cpu.shape[0]
    dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attr", "<u2"),
    ])

    data = np.zeros(count, dtype=dtype)
    data["normal"] = normal_cpu
    data["vertices"] = tri_cpu

    with open(path, "wb") as f:
        header = b"FreeCAD revolved STL"
        f.write(header.ljust(80, b" "))
        f.write(struct.pack("<I", count))
        data.tofile(f)

    return count


def main():
    parser = argparse.ArgumentParser(
        description="Export one FreeCAD profile from in/ to one STL in out/.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("fcstd", nargs="?", help="Default: the only .FCStd file in in/")
    parser.add_argument("--output", help="Output STL. Default: out/<input-name>.stl")
    parser.add_argument(
        "--shape",
        default=DEFAULT_SHAPE,
        help="Shape member inside the FCStd archive (auto if exactly one shape exists)",
    )
    parser.add_argument("--preset", choices=PRESETS, default="fine")
    parser.add_argument("--samples", type=int, help="Override preset profile samples")
    parser.add_argument("--segments", type=int, help="Override preset rotational segments")
    parser.add_argument("--cpu", action="store_true", help="Use CPU instead of the default GPU mode")
    parser.add_argument("--flip", action="store_true", help="Reverse triangle orientation")
    parser.add_argument("--open-profile", action="store_true", help="Do not close profile loops")
    args = parser.parse_args()

    fcstd = args.fcstd or find_default_fcstd()
    output = args.output or default_output_path(fcstd)
    preset = PRESETS[args.preset]
    samples = args.samples or preset["samples"]
    segments = args.segments or preset["segments"]
    mode = "cpu" if args.cpu else "gpu"

    print(f"input:   {fcstd}")
    print(f"output:  {output}")
    print(f"preset:  {args.preset} ({samples} samples, {segments} segments)")

    shape = resolve_shape_name(fcstd, args.shape)
    print(f"shape:   {shape}")

    loops = load_profile_loops(fcstd, shape, samples)
    print(f"profile points: {sum(len(loop) for loop in loops)}")

    triangles = build_triangles(
        loops=loops,
        segments=segments,
        mode=mode,
        closed=not args.open_profile,
    )

    if args.flip:
        triangles = triangles[:, [0, 2, 1], :]

    count = write_binary_stl(output, triangles)
    print(f"written: {output}")
    print(f"triangles: {count}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
