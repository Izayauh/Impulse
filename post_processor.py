import pathlib
import sys


def _bootstrap_src_path() -> None:
    root = pathlib.Path(__file__).resolve().parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> int:
    _bootstrap_src_path()
    from whisper_local.processing.post_processor import main as _main
    return _main()


if __name__ == "__main__":
    raise SystemExit(main())
