#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "template"


class BuildError(RuntimeError):
    pass


def project_path(name, require_main=True):
    if not name or Path(name).name != name or name in {".", ".."}:
        raise BuildError("Имя проекта должно быть именем одной папки без путей.")
    project = (ROOT / name).resolve()
    if project.parent != ROOT:
        raise BuildError("Проект должен находиться непосредственно внутри FolioXLTX.")
    if require_main and not (project / "main.tex").is_file():
        raise BuildError(f"Не найден файл проекта: {project / 'main.tex'}")
    return project


def require_program(name):
    program = shutil.which(name)
    if not program:
        raise BuildError(f"Не найдена программа `{name}`. Установите её и повторите команду.")
    return program


def require_tex_package(name):
    kpsewhich = shutil.which("kpsewhich")
    if kpsewhich and subprocess.run(
        [kpsewhich, name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode:
        raise BuildError(f"Не найден TeX-пакет `{name}`. Установите его и повторите команду.")


def run(command, cwd):
    print(f"+ {shlex.join(str(part) for part in command)}", flush=True)
    result = subprocess.run([str(part) for part in command], cwd=cwd)
    if result.returncode:
        raise BuildError(f"Команда завершилась с кодом {result.returncode}.")


def new_project(name):
    destination = project_path(name, require_main=False)
    if destination.exists():
        raise BuildError(f"Проект уже существует: {destination}")
    shutil.copytree(TEMPLATE, destination, ignore=shutil.ignore_patterns("build"))
    print(f"Создан проект: {destination}")
    print(f"Следующий шаг: python3 {Path(__file__).resolve()} all {shlex.quote(name)}")


def build_pdf(name):
    project = project_path(name)
    xelatex = require_program("xelatex")
    biber = require_program("biber")
    require_tex_package("biblatex.sty")
    require_tex_package("gost-authoryear.bbx")
    build = project / "build"
    build.mkdir(exist_ok=True)
    latex_command = [
        xelatex,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-output-directory=build",
        "main.tex",
    ]
    run(latex_command, project)
    run([biber, "build/main"], project)
    run(latex_command, project)
    run(latex_command, project)
    output = build / "main.pdf"
    if not output.is_file():
        raise BuildError(f"PDF не создан: {output}")
    print(f"PDF: {output}")


def build_docx(name):
    project = project_path(name)
    pandoc = require_program("pandoc")
    build = project / "build"
    build.mkdir(exist_ok=True)
    output = build / "main.docx"
    resource_path = os.pathsep.join([".", "content"])
    run(
        [
            pandoc,
            "main.tex",
            "--standalone",
            "--from=latex",
            f"--resource-path={resource_path}",
            "--citeproc",
            "--bibliography=../bibliography.bib",
            "--csl=../styles/gost-r-7-0-5-2008.csl",
            "--lua-filter=../scripts/draft.lua",
            "--reference-doc=../styles/reference.docx",
            "--metadata=lang:ru-RU",
            f"--output={output}",
        ],
        project,
    )
    if not output.is_file():
        raise BuildError(f"DOCX не создан: {output}")
    print(f"DOCX: {output}")


def clean_project(name):
    project = project_path(name)
    build = project / "build"
    if build.is_symlink() or (build.exists() and not build.is_dir()):
        raise BuildError(f"Отказываюсь удалять необычный каталог сборки: {build}")
    if build.is_dir():
        shutil.rmtree(build)
        print(f"Удалён каталог: {build}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Создание проектов FolioXLTX и сборка PDF/DOCX.",
        epilog=(
            "Примеры:\n"
            "  python3 scripts/build.py new my-book\n"
            "  python3 scripts/build.py all my-book\n"
            "  python3 scripts/build.py docx template\n"
            "  python3 scripts/build.py clean my-book"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in {
        "new": "создать проект из template",
        "pdf": "собрать PDF через XeLaTeX и Biber",
        "docx": "экспортировать DOCX через Pandoc",
        "all": "собрать PDF и DOCX",
        "clean": "удалить каталог build проекта",
    }.items():
        subparser = subparsers.add_parser(command, help=help_text)
        subparser.add_argument("project", help="имя папки проекта внутри FolioXLTX")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        if args.command == "new":
            new_project(args.project)
        elif args.command == "pdf":
            build_pdf(args.project)
        elif args.command == "docx":
            build_docx(args.project)
        elif args.command == "all":
            build_pdf(args.project)
            build_docx(args.project)
        elif args.command == "clean":
            clean_project(args.project)
    except (BuildError, OSError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
