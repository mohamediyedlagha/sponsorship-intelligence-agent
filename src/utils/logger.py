from rich.console import Console
from rich.panel import Panel
from rich.text import Text


console = Console()


def print_header(
    message: str,
) -> None:
    """
    Display a major section header.
    """

    console.print()

    console.print(
        Panel.fit(
            Text(
                message,
                justify="center",
            ),
            border_style="bold",
        )
    )


def print_company_header(
    company: str,
) -> None:
    """
    Display the company currently being monitored.
    """

    console.print()

    console.rule(
        f"[bold]{company}[/bold]"
    )


def print_info(
    message: str,
) -> None:
    """
    Display informational output.
    """

    console.print(
        f"[cyan]INFO[/cyan] "
        f"{message}"
    )


def print_success(
    message: str,
) -> None:
    """
    Display successful operation output.
    """

    console.print(
        f"[green]✓[/green] "
        f"{message}"
    )


def print_warning(
    message: str,
) -> None:
    """
    Display warning output.
    """

    console.print(
        f"[yellow]![/yellow] "
        f"{message}"
    )


def print_error(
    message: str,
) -> None:
    """
    Display error output.
    """

    console.print(
        f"[red]ERROR[/red] "
        f"{message}"
    )