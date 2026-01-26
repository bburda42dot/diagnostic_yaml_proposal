"""Command-line interface for yaml-to-mdd converter."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from yaml_to_mdd import __version__
from yaml_to_mdd.models import (
    DiagnosticDescription,
    LoaderError,
    load_diagnostic_description,
    validate_diagnostic_description,
)

# Create Typer app
app = typer.Typer(
    name="yaml-to-mdd",
    help="Convert OpenSOVD CDA Diagnostic Description YAML to MDD binary format.",
    add_completion=True,
    no_args_is_help=True,
)

# Rich consoles for output
console = Console()
error_console = Console(stderr=True, style="bold red")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"yaml-to-mdd version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """Convert OpenSOVD CDA Diagnostic Description YAML/JSON to MDD format.

    This tool validates YAML diagnostic description files against the
    opensovd.cda.diagdesc/v1 schema and converts them to MDD binary format.
    """


@app.command()
def validate(
    input_file: Annotated[
        Path,
        typer.Argument(
            help="Input YAML/JSON file to validate.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Only output errors, no success messages.",
        ),
    ] = False,
    show_summary: Annotated[
        bool,
        typer.Option(
            "--summary",
            "-s",
            help="Show summary of document contents.",
        ),
    ] = False,
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format for validation results: text, table, tree.",
        ),
    ] = "text",
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Show verbose output including source context.",
        ),
    ] = False,
) -> None:
    """Validate a YAML/JSON diagnostic description file.

    Checks the file against the opensovd.cda.diagdesc/v1 schema and reports
    any validation errors found. Also runs semantic validation checks.

    Examples
    --------
        yaml-to-mdd validate diagnostic.yaml
        yaml-to-mdd validate diagnostic.yaml --summary
        yaml-to-mdd validate diagnostic.yaml --quiet
        yaml-to-mdd validate diagnostic.yaml --format table
        yaml-to-mdd validate diagnostic.yaml --format tree

    """
    from yaml_to_mdd.cli.error_formatter import ErrorFormatter, ErrorTable, ErrorTree
    from yaml_to_mdd.validation.validator import DiagnosticValidator

    # First validate schema
    errors = validate_diagnostic_description(input_file)

    if errors:
        error_console.print(f"\n[bold red]✗ Validation failed for {input_file.name}[/bold red]\n")

        # Create error table
        table = Table(title="Validation Errors", show_header=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Location", style="cyan")
        table.add_column("Error", style="red")

        for i, error in enumerate(errors, 1):
            # Split error into location and message if possible
            if ": " in error:
                loc, msg = error.split(": ", 1)
            else:
                loc, msg = "", error
            table.add_row(str(i), loc, msg)

        console.print(table)
        raise typer.Exit(code=1)

    # Schema valid - load document and run semantic validation
    try:
        doc = load_diagnostic_description(input_file)
    except LoaderError as e:
        error_console.print(f"\n[bold red]✗ Failed to load {input_file.name}[/bold red]")
        error_console.print(str(e))
        raise typer.Exit(code=1) from None

    # Run semantic validation
    validator = DiagnosticValidator()
    result = validator.validate(doc)

    # Format and display validation results
    if not result.is_valid or result.warnings:
        source_content = input_file.read_text() if verbose else None

        if output_format == "table":
            ErrorTable(error_console).print_result(result)
        elif output_format == "tree":
            ErrorTree(error_console).print_result(result)
        else:
            ErrorFormatter(error_console, show_context=verbose).format_validation_result(
                result, input_file, source_content
            )

        if not result.is_valid:
            raise typer.Exit(code=1)

    if not quiet:
        if result.is_valid and not result.warnings:
            console.print(f"\n[bold green]✓ {input_file.name} is valid[/bold green]\n")
        elif result.is_valid and result.warnings:
            console.print(
                f"\n[bold yellow]⚠ {input_file.name} is valid with warnings[/bold yellow]\n"
            )

        if show_summary:
            _print_summary(doc)


def _print_summary(doc: DiagnosticDescription) -> None:
    """Print a summary of the diagnostic description document."""
    table = Table(title="Document Summary", show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    # Meta info
    table.add_row("Author", doc.meta.author)
    table.add_row("Domain", doc.meta.domain)
    table.add_row("Revision", doc.meta.revision)
    description = doc.meta.description
    if len(description) > 60:
        description = description[:60] + "..."
    table.add_row("Description", description)

    # ECU info
    table.add_row("", "")  # Spacer
    table.add_row("ECU ID", doc.ecu.id)
    table.add_row("ECU Name", doc.ecu.name)

    # Counts
    table.add_row("", "")  # Spacer
    table.add_row("Sessions", str(len(doc.sessions)))

    if doc.dids:
        table.add_row("DIDs", str(len(doc.dids)))
    if doc.routines:
        table.add_row("Routines", str(len(doc.routines)))
    if doc.dtcs:
        table.add_row("DTCs", str(len(doc.dtcs)))
    if doc.types:
        table.add_row("Custom Types", str(len(doc.types)))

    console.print(table)


@app.command()
def convert(
    input_file: Annotated[
        Path,
        typer.Argument(
            help="Input YAML/JSON file to convert.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output MDD file path. Defaults to input filename with .mdd extension.",
            dir_okay=False,
            writable=True,
            resolve_path=True,
        ),
    ] = None,
    audience: Annotated[
        str | None,
        typer.Option(
            "--audience",
            "-a",
            help="Target audience (development, production, aftermarket, oem, or custom).",
        ),
    ] = None,
    compression: Annotated[
        str | None,
        typer.Option(
            "--compression",
            "-c",
            help="Compression algorithm (lzma, gzip, zstd, or 'none'). Defaults to lzma.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite output file if it exists.",
        ),
    ] = False,
    validate_only: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Validate without writing output file.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-V",
            help="Show detailed conversion progress.",
        ),
    ] = False,
) -> None:
    """Convert a YAML/JSON diagnostic description to MDD binary format.

    First validates the input file, then converts it to the MDD format
    used by the Classic Diagnostic Adapter.

    Examples
    --------
        yaml-to-mdd convert diagnostic.yaml
        yaml-to-mdd convert diagnostic.yaml -o custom.mdd
        yaml-to-mdd convert diagnostic.yaml --force
        yaml-to-mdd convert diagnostic.yaml --dry-run
        yaml-to-mdd convert diagnostic.yaml --compression gzip
        yaml-to-mdd convert diagnostic.yaml --audience aftermarket

    """
    from rich.progress import Progress, SpinnerColumn, TextColumn

    from yaml_to_mdd.converters import MDDWriter
    from yaml_to_mdd.filter.audience_filter import AudienceFilter
    from yaml_to_mdd.models.audience import StandardAudience
    from yaml_to_mdd.transform.transformer import YamlToIRTransformer

    # Determine output path
    if output is None:
        output = input_file.with_suffix(".mdd")

    # Check if output exists
    if output.exists() and not force and not validate_only:
        error_console.print(
            f"\n[bold red]✗ Output file already exists: {output}[/bold red]\n"
            "Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    # Validate compression option (None means use default lzma, "none" means no compression)
    valid_compressions = ("lzma", "gzip", "zstd", "none")
    if compression and compression not in valid_compressions:
        error_console.print(
            f"\n[bold red]✗ Invalid compression: {compression}[/bold red]\n"
            f"Supported: {', '.join(valid_compressions)}"
        )
        raise typer.Exit(code=1)

    # Convert "none" string to None for MDDWriter
    effective_compression = None if compression == "none" else compression

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=not verbose,
        ) as progress:
            # Step 1: Validate
            task = progress.add_task("Validating...", total=None)
            errors = validate_diagnostic_description(input_file)
            if errors:
                progress.stop()
                error_console.print("\n[bold red]✗ Validation failed[/bold red]\n")
                for error in errors[:10]:
                    error_console.print(f"  • {error}")
                if len(errors) > 10:
                    error_console.print(f"  ... and {len(errors) - 10} more errors")
                raise typer.Exit(code=1)
            progress.update(task, description="[green]✓ Validated[/green]")

            # Step 2: Load document
            task = progress.add_task("Loading document...", total=None)
            doc = load_diagnostic_description(input_file)
            progress.update(task, description="[green]✓ Loaded[/green]")

            if verbose:
                console.print(f"  [dim]Schema: {doc.schema_version}[/dim]")
                console.print(f"  [dim]ECU: {doc.ecu.id}[/dim]")

            # Step 2.5: Apply audience filter if specified
            if audience:
                task = progress.add_task("Filtering by audience...", total=None)
                # Try to parse as standard audience, otherwise use as custom
                try:
                    aud_value: StandardAudience | str = StandardAudience(audience)
                except ValueError:
                    aud_value = audience  # Custom audience string

                original_doc = doc
                filter_obj = AudienceFilter(aud_value)
                doc = filter_obj.filter(doc)
                progress.update(task, description="[green]✓ Filtered[/green]")

                if verbose:
                    summary = filter_obj.get_filter_summary(original_doc, doc)
                    console.print(f"  [dim]Audience: {audience}[/dim]")
                    console.print(f"  [dim]Removed: {summary['removed']}[/dim]")

            # Step 3: Transform to IR
            task = progress.add_task("Transforming to IR...", total=None)
            transformer = YamlToIRTransformer()
            ir_db = transformer.transform(doc)
            progress.update(task, description="[green]✓ Transformed[/green]")

            if verbose:
                console.print(f"  [dim]DOPs: {len(ir_db.dops)}[/dim]")
                console.print(f"  [dim]Services: {len(ir_db.services)}[/dim]")

            # Step 4: Write MDD
            if validate_only:
                task = progress.add_task("Serializing (dry run)...", total=None)
                if effective_compression is not None:
                    writer = MDDWriter(compression=effective_compression)
                else:
                    writer = MDDWriter()  # Use default compression (lzma)
                mdd_bytes = writer.write_bytes(ir_db)
                progress.update(task, description="[green]✓ Serialized[/green]")
                size = len(mdd_bytes)
                console.print(
                    f"\n[bold green]✓ Would write {size:,} bytes to {output}[/bold green]\n"
                )
            else:
                task = progress.add_task(f"Writing {output.name}...", total=None)
                if effective_compression is not None:
                    writer = MDDWriter(compression=effective_compression)
                else:
                    writer = MDDWriter()  # Use default compression (lzma)
                writer.write(ir_db, output)
                progress.update(task, description="[green]✓ Written[/green]")

                file_size = output.stat().st_size
                console.print(
                    f"\n[bold green]✓ Wrote {file_size:,} bytes to {output}[/bold green]\n"
                )

                if verbose:
                    _print_mdd_info(output)

    except (LoaderError, Exception) as e:
        error_console.print(f"\n[bold red]✗ Conversion failed: {e}[/bold red]\n")
        if verbose:
            import traceback

            error_console.print(traceback.format_exc())
        raise typer.Exit(code=1) from None


@app.command()
def info(
    input_file: Annotated[
        Path,
        typer.Argument(
            help="Input YAML, JSON, or MDD file to inspect.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
) -> None:
    """Display information about a diagnostic file.

    Supports YAML, JSON, and MDD (binary) file formats.

    Examples
    --------
        yaml-to-mdd info diagnostic.yaml
        yaml-to-mdd info diagnostic.mdd

    """
    suffix = input_file.suffix.lower()

    try:
        if suffix in (".yaml", ".yml", ".json"):
            doc = load_diagnostic_description(input_file)

            console.print(
                Panel.fit(
                    f"[bold]YAML Diagnostic Description[/bold]\n" f"File: {input_file}",
                    title="File Info",
                )
            )

            _print_summary(doc)

        elif suffix == ".mdd":
            _print_mdd_info(input_file)

        else:
            error_console.print(
                f"\n[bold red]✗ Unknown file type: {suffix}[/bold red]\n"
                "Supported: .yaml, .yml, .json, .mdd"
            )
            raise typer.Exit(code=1)

    except Exception as e:
        error_console.print(f"\n[bold red]✗ Failed to read file: {e}[/bold red]\n")
        raise typer.Exit(code=1) from None


def _print_mdd_info(path: Path) -> None:
    """Print MDD file information."""
    from yaml_to_mdd.converters.mdd_writer import FILE_MAGIC
    from yaml_to_mdd.proto_generated import MDDFile

    with open(path, "rb") as f:
        data = f.read()

    # Skip magic header if present
    magic_len = len(FILE_MAGIC)
    if data[:magic_len] == FILE_MAGIC:
        proto_data = data[magic_len:]
        has_magic = True
    else:
        proto_data = data
        has_magic = False

    mdd = MDDFile()
    mdd.ParseFromString(proto_data)

    magic_info = "[green]✓ Valid[/green]" if has_magic else "[yellow]⚠ Missing[/yellow]"
    console.print(
        Panel.fit(
            f"[bold]MDD Binary File[/bold]\n"
            f"File: {path}\n"
            f"Size: {len(data):,} bytes\n"
            f"Magic Header: {magic_info}",
            title="File Info",
        )
    )

    # Main info table
    table = Table(title="MDD Contents", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Format Version", mdd.version)
    table.add_row("ECU Name", mdd.ecu_name)
    table.add_row("Revision", mdd.revision)

    for key, value in mdd.metadata.items():
        table.add_row(f"Metadata: {key}", value)

    console.print(table)

    # Chunks table
    if mdd.chunks:
        chunk_type_names = {
            0: "DIAGNOSTIC_DESCRIPTION",
            1: "JAR_FILE",
            2: "JAR_FILE_PARTIAL",
            3: "EMBEDDED_FILE",
            4: "VENDOR_SPECIFIC",
        }

        chunks_table = Table(title="Chunks")
        chunks_table.add_column("#", style="dim")
        chunks_table.add_column("Type")
        chunks_table.add_column("Name")
        chunks_table.add_column("Size")
        chunks_table.add_column("Compression")

        for i, chunk in enumerate(mdd.chunks):
            type_name = chunk_type_names.get(chunk.type, f"UNKNOWN({chunk.type})")
            compression = chunk.compression_algorithm or "-"
            size = f"{len(chunk.data):,} bytes" if chunk.data else "-"

            chunks_table.add_row(
                str(i),
                type_name,
                chunk.name or "-",
                size,
                compression,
            )

        console.print(chunks_table)


if __name__ == "__main__":
    app()
