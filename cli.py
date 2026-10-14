"""AutoClean CLI — clean a dataset automatically using rule-based detection + LLM decisions."""
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from autoclean.pipeline import run_and_save

app = typer.Typer(add_completion=False, help="AutoClean: LLM-driven automated data cleaning.")
console = Console()


@app.command()
def clean(
    input_file: str = typer.Argument(..., help="Path to input CSV/XLSX/JSON file"),
    output_file: str = typer.Option(None, "--output", "-o", help="Path for cleaned output file"),
    report_file: str = typer.Option(None, "--report", "-r", help="Path for the markdown report"),
):
    """Clean INPUT_FILE and write the cleaned data + a report."""
    in_path = Path(input_file)
    output_file = output_file or str(in_path.with_name(f"{in_path.stem}_cleaned{in_path.suffix}"))
    report_file = report_file or str(in_path.with_name(f"{in_path.stem}_report.md"))

    console.print(f"[bold cyan]AutoClean[/bold cyan] — processing [bold]{input_file}[/bold]...")

    try:
        result = run_and_save(input_file, output_file, report_file)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    if result.llm_error:
        console.print(f"[yellow]LLM warning:[/yellow] {result.llm_error}")

    applied = [e for e in result.execution_log if e["status"] == "applied"]
    table = Table(title="Actions Applied")
    table.add_column("Column")
    table.add_column("Action")
    table.add_column("Reason")
    for e in applied:
        table.add_row(e["column"], e["action"], e["reason"])

    if applied:
        console.print(table)
    else:
        console.print("[yellow]No cleaning actions were applied.[/yellow]")

    console.print(f"\n[green]Rows:[/green] {len(result.original_df)} -> {len(result.cleaned_df)}")
    console.print(f"[green]Cleaned file:[/green] {output_file}")
    console.print(f"[green]Report:[/green] {report_file}")

    if result.rejected_actions:
        console.print(
            f"[yellow]{len(result.rejected_actions)} proposed action(s) were rejected by the validator "
            f"— see report for details.[/yellow]"
        )


if __name__ == "__main__":
    app()
