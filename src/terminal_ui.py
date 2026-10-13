"""SecureVault Cloud terminal UI for the Plan-2 local CLI."""
from __future__ import annotations

import io
import math
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from configuration import ConfigurationCancelled, collect_s3_configuration
from infrastructure_viewer import GENERATED_DIR, PROJECT_ROOT, inspect_configuration
from prerequisites import check_prerequisites
from security_auditor import audit_terraform
from configuration_registry import record_configuration, record_audit, get_configuration_record
from terraform_generator import generate_terraform
from terraform_manager import check_terraform_configuration, initialize_terraform, validate_terraform

console = Console()
ORANGE = "#651827"  # Primary wine-red branding
WHITE = "#F2E8EA"
MUTED = "#B5A0A6"
DIM = "#716067"
GREEN = ORANGE  # Same primary wine red for branded success panels
ACCENT = ORANGE
AMBER = "#C9A15B"
RED = "#C94B5B"
TERRAFORM_DIR = PROJECT_ROOT / "terraform"

MENU_ITEMS = [
    ("1", "Check prerequisites", "Verify local tools and versions"),
    ("2", "New S3 configuration", "Generate and validate a secure bucket"),
    ("3", "Validate Terraform", "Check the existing project configuration"),
    ("4", "Configuration inventory", "Review local generated configurations"),
    ("5", "Security Audit", "Audit a generated configuration locally"),
    ("6", "Destroy infrastructure", "Unavailable in this build"),
    ("Q", "Quit SecureVault", "Exit the application"),
]


# ----------------------------------------------------------------------------
# Environment
# ----------------------------------------------------------------------------
def get_version(command: str) -> tuple[str, bool]:
    """Read a tool version. Called once at startup, not on every keypress."""
    executable = shutil.which(command)
    if not executable:
        return "Not installed", False
    try:
        result = subprocess.run(
            [executable, "--version"], capture_output=True, text=True,
            timeout=10, check=False,
        )
        if result.returncode:
            return "Unavailable", False
        lines = (result.stdout or result.stderr).strip().splitlines()
        return (lines[0].strip(), True) if lines else ("Available", True)
    except (OSError, subprocess.TimeoutExpired):
        return "Unavailable", False


def get_environment() -> list[tuple[str, str, str, str]]:
    """Cache environment checks so keyboard navigation stays responsive."""
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    tf_version, tf_ok = get_version("terraform")
    aws_version, aws_ok = get_version("aws")
    return [
        ("Python", py_version, "READY" if py_ok else "CHECK VERSION", WHITE if py_ok else AMBER),
        ("Terraform", tf_version, "READY" if tf_ok else "NOT FOUND", WHITE if tf_ok else AMBER),
        ("AWS CLI", aws_version, "AVAILABLE" if aws_ok else "NOT FOUND", WHITE if aws_ok else DIM),
    ]


# Do the relatively slow version checks only once, not on each redraw.
ENVIRONMENT = get_environment()


# ----------------------------------------------------------------------------
# Pixel logo
# ----------------------------------------------------------------------------
PIXEL_FONT = {
    "S": ["#####", "#....", "#####", "....#", "#####"],
    "E": ["#####", "#....", "###..", "#....", "#####"],
    "C": ["#####", "#....", "#....", "#....", "#####"],
    "U": ["#...#", "#...#", "#...#", "#...#", "#####"],
    "R": ["####.", "#...#", "####.", "#.#..", "#..##"],
    "V": ["#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "A": [".###.", "#...#", "#####", "#...#", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#####"],
    "T": ["#####", "..#..", "..#..", "..#..", "..#.."],
}


def pixel_word(word: str) -> Text:
    """Draw chunky wine-red pixel letters with a subdued lower-right shadow."""
    patterns = [PIXEL_FONT[ch] for ch in word]
    rows = 5
    gap = 1
    width = len(patterns) * 5 + (len(patterns) - 1) * gap
    pixels = [[False] * width for _ in range(rows)]

    offset = 0
    for glyph in patterns:
        for row_index, row in enumerate(glyph):
            for col_index, cell in enumerate(row):
                pixels[row_index][offset + col_index] = cell == "#"
        offset += 5 + gap

    char_width = width * 2 + 1
    char_height = rows + 1
    canvas = Text()
    for y in range(char_height):
        for x in range(char_width):
            is_solid = y < rows and (x // 2) < width and pixels[y][x // 2] and x < width * 2

            is_shadow = False
            if y > 0 and x > 0:
                source_y, source_x = y - 1, x - 1
                if source_y < rows:
                    source_col = source_x // 2
                    if source_col < width and pixels[source_y][source_col]:
                        is_shadow = True

            if is_solid:
                canvas.append("█", style=f"bold {ORANGE}")
            elif is_shadow:
                canvas.append("░", style="#2A0D14")
            else:
                canvas.append(" ")
        if y < char_height - 1:
            canvas.append("\n")
    return canvas


# ----------------------------------------------------------------------------
# Animation helpers
# ----------------------------------------------------------------------------
SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
BASE, LIGHT, TRAIL = (101, 24, 39), (242, 232, 234), (42, 13, 20)


def _lerp(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def _rgb(c):
    return f"rgb({c[0]},{c[1]},{c[2]})"


LOGO_LINES = pixel_word("SECUREVAULT").plain.split("\n")
LOGO_W = max(len(line) for line in LOGO_LINES)


def make_logo(phase: int = 0, reveal: int | None = None) -> Text:
    """Shimmer sweep across logo. `reveal` = left-to-right wipe column."""
    pos = phase % (LOGO_W + 40) - 10
    out = Text()
    for i, line in enumerate(LOGO_LINES):
        for x, ch in enumerate(line):
            if reveal is not None and x > reveal:
                out.append(" ")
            elif ch == "█":
                if reveal is not None and x >= reveal - 1:
                    color = LIGHT
                else:
                    color = _lerp(BASE, LIGHT, max(0.0, 1 - abs(x - pos) / 8))
                out.append("█", style=f"bold {_rgb(color)}")
            elif ch == "░":
                out.append("░", style="#2A0D14")
            else:
                out.append(" ")
        if i < len(LOGO_LINES) - 1:
            out.append("\n")
    return out


def _pulse_bar(tick: int, width: int = 36) -> Text:
    head = int((math.sin(tick * 0.12) + 1) / 2 * (width - 1))
    bar = Text()
    for i in range(width):
        k = max(0.0, 1 - abs(i - head) / 7)
        bar.append("━", style=_rgb(_lerp(TRAIL, LIGHT if i == head else BASE, k)))
    return bar


# ----------------------------------------------------------------------------
# Dashboard widgets
# ----------------------------------------------------------------------------
def make_branding(phase: int = 0, reveal: int | None = None):
    logo = make_logo(phase, reveal)
    if reveal is not None and reveal < LOGO_W:
        return Group(logo)
    subtitle = Text("C L O U D   S E C U R I T Y", style=f"bold {MUTED}")
    tagline = Text("Private by design. Secure by default.", style=WHITE)
    return Group(logo, Text(""), subtitle, tagline)


def make_environment():
    table = Table(box=None, show_header=True, show_edge=False, padding=(0, 1), expand=False)
    table.add_column("COMPONENT", style=MUTED, no_wrap=True)
    table.add_column("VERSION", style=WHITE, no_wrap=True)
    table.add_column("STATUS", no_wrap=True)
    for name, version, status, color in ENVIRONMENT:
        table.add_row(name, version, Text(status, style=color))
    return Panel(
        table, title=f"[bold {WHITE}]LOCAL ENVIRONMENT[/]", title_align="left",
        border_style=DIM, box=box.ROUNDED, padding=(0, 1), expand=False,
    )


def make_menu(selected: int):
    table = Table(box=None, show_header=False, show_edge=False, expand=False, padding=(0, 1), pad_edge=False)
    table.add_column("KEY", width=5, justify="center", no_wrap=True)
    table.add_column("OPERATION", width=29, no_wrap=True)
    table.add_column("DESCRIPTION", no_wrap=True)
    for index, (key, label, description) in enumerate(MENU_ITEMS):
        disabled = key == "6"
        if index == selected:
            key_text = Text(f" {key} ", style=f"bold #161616 on {ACCENT}")
            label_text = Text.assemble(("› ", f"bold {ACCENT}"), (label, f"bold {WHITE}"))
            detail_text = Text(description, style=ACCENT if not disabled else AMBER)
        else:
            key_text = Text(f" {key} ", style=DIM)
            label_text = Text(label, style=DIM if disabled else WHITE)
            detail_text = Text(description, style=DIM)
        table.add_row(key_text, label_text, detail_text)
    return Panel(
        table, title=f"[bold {WHITE}]OPERATIONS[/]", title_align="left",
        border_style=ACCENT, box=box.ROUNDED, padding=(1, 1), expand=False,
    )


def make_footer():
    footer = Table.grid(expand=True)
    footer.add_column(ratio=1)
    footer.add_column(justify="right")
    footer.add_row(
        Text("PLAN 2  ·  LOCAL CLI", style=DIM),
        Text("BUILD  /  VALIDATE  /  SECURE", style=f"bold {ACCENT}"),
    )
    return footer


def build_screen(selected: int, phase: int = 0, reveal: int | None = None):
    key_help = Text()
    key_help.append("↑ / ↓", style=f"bold {WHITE}")
    key_help.append(" navigate    ", style=MUTED)
    key_help.append("ENTER", style=f"bold {WHITE}")
    key_help.append(" select    ", style=MUTED)
    key_help.append("1–6", style=f"bold {WHITE}")
    key_help.append(" shortcut    ", style=MUTED)
    key_help.append("Q", style=f"bold {WHITE}")
    key_help.append(" quit", style=MUTED)

    return Group(
        Text(""),
        Panel(make_branding(phase, reveal), border_style=ACCENT, box=box.DOUBLE, padding=(1, 2), expand=False),
        Text(""),
        Text("COMMAND CENTER", style=f"bold {WHITE}"),
        Text("Local configuration and validation. No live AWS deployment is available.", style=MUTED),
        Text(""),
        make_environment(),
        Text(""),
        make_menu(selected),
        Text(""),
        Rule(style=DIM),
        make_footer(),
        Text(""),
        Align.center(key_help),
        Text(""),
    )


# ----------------------------------------------------------------------------
# Input
# ----------------------------------------------------------------------------
def read_choice(selected: int, on_idle=None) -> str:
    """Read a key. On Windows, `on_idle` runs repeatedly while waiting (animation)."""
    if os.name == "nt":
        import msvcrt
        while True:
            while on_idle and not msvcrt.kbhit():
                on_idle()
                time.sleep(0.05)
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                key = msvcrt.getwch()
                if key == "H":
                    return "UP"
                if key == "P":
                    return "DOWN"
                continue
            if key in ("\r", "\n"):
                return MENU_ITEMS[selected][0]
            if key.lower() == "q":
                return "Q"
            if key in ("1", "2", "3", "4", "5", "6"):
                return key
    choice = console.input("  › ").strip().upper()
    return choice if choice in ("Q", "1", "2", "3", "4", "5", "6", "UP", "DOWN") else ""


def pause():
    console.print()
    console.input(f"[{MUTED}]Press Enter to return to SecureVault...[/]")


# ----------------------------------------------------------------------------
# Operation output
# ----------------------------------------------------------------------------
def operation_header(title: str, number: str):
    console.print()
    title_text = Text.assemble((f"  {number}  ", f"bold black on {ACCENT}"), (f"  {title}  ", f"bold {WHITE}"))
    console.print(Rule(title_text, style=DIM))
    console.print()


def result_panel(title: str, message: str, tone: str = GREEN):
    console.print(Panel(message, title=f"[bold {tone}]{title}[/]", title_align="left", border_style=tone, box=box.ROUNDED, padding=(1, 2), expand=False))


def show_inventory():
    """Show generated local configurations and their latest recorded audit."""
    files = sorted(GENERATED_DIR.rglob("main.tf")) if GENERATED_DIR.is_dir() else []
    if not files:
        result_panel("NO CONFIGURATIONS", "No generated Terraform configurations were found.\nChoose ‘New S3 configuration’ to create one.", AMBER)
        return

    table = Table(
        title="LOCAL CONFIGURATION INVENTORY",
        title_style=f"bold {ACCENT}", box=box.ROUNDED,
        border_style="#2A0D14", header_style=f"bold {ACCENT}",
        show_lines=True, row_styles=["", "on #190D11"], padding=(0, 1),
    )
    table.add_column("No.", justify="right", style=ACCENT)
    table.add_column("BUCKET", style="#F2E8EA", no_wrap=True)
    table.add_column("ENCRYPTION", style=WHITE)
    table.add_column("VERSIONING", style="#C7B7BB")
    table.add_column("LATEST AUDIT", style=WHITE)
    table.add_column("LAST AUDITED", style=MUTED)

    usable = []
    for terraform_file in files:
        try:
            details = inspect_configuration(terraform_file)
            record = get_configuration_record(terraform_file)
            audit = record.get("latest_audit") if record else None
            audit_status = audit.get("overall_result", "Not audited") if audit else "Not audited"
            audited_at = audit.get("audited_at", "—") if audit else "—"
            if audited_at != "—":
                audited_at = audited_at.replace("T", " ").replace("+00:00", " UTC")[:19]
            usable.append((terraform_file, details, record))
            index = len(usable)
            tone = "green" if audit_status == "ALL AUDITED CHECKS PASSED" else ("red" if audit_status == "ACTION REQUIRED" else ("yellow" if audit_status not in {"Not audited", "—"} else MUTED))
            table.add_row(str(index), details["bucket_name"], details["encryption"], details["versioning"], Text(audit_status, style=tone), audited_at)
        except (OSError, UnicodeError, KeyError, ValueError) as error:
            table.add_row("—", "Unreadable", "—", "—", "Unavailable", str(error))

    console.print(table)
    console.print(Text("Local Terraform only • audit status is the latest saved local audit, not live AWS verification.", style=MUTED))
    if not usable:
        return

    console.print("\n[bold]Enter a number to view configuration details, or press Enter to return.[/bold]")
    choice = console.input("Configuration: ").strip()
    if not choice:
        return
    if not choice.isdigit() or not 1 <= int(choice) <= len(usable):
        result_panel("INVALID SELECTION", "Choose one of the listed configuration numbers.", AMBER)
        return

    terraform_file, details, record = usable[int(choice) - 1]
    audit = (record or {}).get("latest_audit") or {}
    audit_counts = audit.get("counts", {})
    generated_at = (record or {}).get("generated_at", "Unknown")
    console.print(Panel(
        f"[bold]Bucket:[/bold] {details['bucket_name']}\n"
        f"[bold]Encryption:[/bold] {details['encryption']}\n"
        f"[bold]Public access protections:[/bold] {details['public_access']}\n"
        f"[bold]Versioning:[/bold] {details['versioning']}\n"
        f"[bold]Generated:[/bold] {generated_at}\n"
        f"[bold]Terraform file:[/bold] {terraform_file}\n"
        f"[bold]Latest audit:[/bold] {audit.get('overall_result', 'Not audited')}\n"
        f"[bold]Audit counts:[/bold] PASS {audit_counts.get('PASS', 0)} • FAIL {audit_counts.get('FAIL', 0)} • WARN {audit_counts.get('WARN', 0)} • UNKNOWN {audit_counts.get('UNKNOWN', 0)}\n\n"
        "[dim]Configuration and audit history are stored locally. Live AWS deployment is not verified.[/dim]",
        title="CONFIGURATION DETAILS", border_style=ACCENT, box=box.ROUNDED,
    ))


def _capture_call(function, *args, **kwargs):
    """Capture backend text so successful commands don't flood the UI."""
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    result = None
    error = None
    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        try:
            result = function(*args, **kwargs)
        except Exception as exc:  # preserve backend diagnostics, then report cleanly
            error = exc
    output = "\n".join(
        part.strip() for part in (stdout_buffer.getvalue(), stderr_buffer.getvalue()) if part.strip()
    )
    return result, output, error


def _show_diagnostics(output: str, *, limit: int = 24):
    """Show bounded diagnostics only when they are useful or an operation fails."""
    if not output.strip():
        return
    lines = output.strip().splitlines()
    if len(lines) > limit:
        lines = lines[:limit] + [f"… {len(output.strip().splitlines()) - limit} additional lines omitted"]
    console.print(Panel(Text("\n".join(lines), style=MUTED), title="DIAGNOSTICS", title_align="left", border_style=DIM, box=box.ROUNDED, padding=(1, 1), expand=False))


def _run_with_progress(label: str, function, *args, **kwargs):
    """Run a blocking task with a braille spinner, pulse bar and elapsed timer."""
    started = time.monotonic()
    tick = 0
    # Real stdout: the worker's stdout capture must not touch Rich's renderer.
    out = getattr(sys, "__stdout__", None) or sys.stdout
    progress_console = Console(file=out, force_terminal=True)

    def stamp():
        s = int(time.monotonic() - started)
        return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"

    with Live(Text(""), console=progress_console, auto_refresh=False, transient=False,
              redirect_stdout=False, redirect_stderr=False) as live:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_capture_call, function, *args, **kwargs)
            while not future.done():
                head = Text()
                head.append(SPIN[tick % len(SPIN)] + "  ", style=f"bold {ACCENT}")
                head.append(label, style=f"bold {WHITE}")
                head.append(f"  ·  {stamp()}", style=f"bold {AMBER}")
                live.update(Group(head, _pulse_bar(tick)), refresh=True)
                tick += 1
                time.sleep(0.05)
            result = future.result()
            done = Text()
            done.append("✓  ", style=f"bold {GREEN}")
            done.append(f"{label} completed", style=f"bold {WHITE}")
            done.append(f"  ·  {stamp()}", style=f"bold {AMBER}")
            live.update(Group(done, Text("━" * 36, style=ACCENT)), refresh=True)
    return result


def _stage_screen(title: str, detail: str):
    """Brief branded stage card before a longer operation begins."""
    console.clear()
    console.print(Panel(
        Group(
            Text("SECUREVAULT  /  LOCAL WORKFLOW", style=f"bold {ACCENT}"),
            Text(""),
            Text(title, style=f"bold {WHITE}"),
            Text(detail, style=MUTED),
            Text(""),
            Text("This may take a little while on the first run.", style=DIM),
        ),
        title=f"[bold {WHITE}]WORKING[/]",
        title_align="left",
        border_style=ACCENT,
        box=box.DOUBLE,
        padding=(1, 2),
        expand=False,
    ))



def show_security_audit():
    """Select a generated Terraform configuration and audit it locally."""
    generated_dir = GENERATED_DIR
    if not generated_dir.is_dir():
        console.print(Panel(
            "No generated configurations directory was found.",
            title=f"[bold {ACCENT}]SECURITY AUDIT[/bold]", border_style=ACCENT,
        ))
        return

    configurations = sorted(generated_dir.rglob("main.tf"))
    if not configurations:
        console.print(Panel(
            "No generated Terraform configurations were found.\n\n"
            "Use option 2 to create a configuration first.",
            title=f"[bold {ACCENT}]SECURITY AUDIT[/bold]", border_style=ACCENT,
        ))
        return

    if len(configurations) > 1:
        selection_table = Table(title="Select a configuration to audit", box=box.ROUNDED, show_lines=True)
        selection_table.add_column("No.", style=f"bold {ACCENT}", justify="right")
        selection_table.add_column("Configuration", style="white")
        for index, config_path in enumerate(configurations, start=1):
            selection_table.add_row(str(index), str(config_path.relative_to(generated_dir)))
        console.print(selection_table)
        console.print("[dim]Enter Q to cancel the audit.[/dim]")
        while True:
            selection = console.input("[bold]Configuration number: [/bold]").strip()
            if selection.upper() == "Q":
                console.print("[dim]Security audit cancelled.[/dim]")
                return
            if selection.isdigit() and 1 <= int(selection) <= len(configurations):
                selected_file = configurations[int(selection) - 1]
                break
            console.print("[yellow]Invalid selection. Choose a listed number or Q.[/yellow]")
    else:
        selected_file = configurations[0]

    try:
        report = audit_terraform(selected_file)
    except (OSError, UnicodeError, ValueError) as exc:
        console.print(Panel(
            f"Could not audit the selected configuration:\n{exc}",
            title="[bold red]AUDIT ERROR[/bold red]", border_style="red",
        ))
        return

    findings = report.get("findings", [])
    console.print()
    console.print(Panel(
        f"[bold]File:[/bold] {selected_file}\n"
        f"[bold]Bucket:[/bold] {report.get('bucket_name') or 'Unknown'}\n"
        f"[bold]Deployment status:[/bold] {report.get('deployment_status', 'Not verified')}\n\n"
        "[dim]This report analyses local Terraform configuration. It does not verify live AWS resources.[/dim]",
        title="[bold]SECUREVAULT SECURITY AUDIT[/bold]", border_style=ORANGE,
    ))

    audit_table = Table(title="Security Findings", box=box.ROUNDED, show_lines=True)
    audit_table.add_column("Security Rule", style="white", min_width=20)
    audit_table.add_column("Status", min_width=10)
    audit_table.add_column("Severity", min_width=10)
    audit_table.add_column("Verdict", min_width=10)
    audit_table.add_column("Recommendation", style="white", min_width=30)

    verdict_styles = {"PASS": "bold green", "FAIL": "bold red", "WARN": "bold yellow", "UNKNOWN": "bold bright_black"}
    severity_styles = {"CRITICAL": "bold white on red", "HIGH": "bold red", "MEDIUM": "bold yellow", "LOW": "cyan", "INFO": "green"}
    counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "UNKNOWN": 0}
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}

    for finding in findings:
        rule = str(finding.get("rule", "Unknown rule"))
        status = str(finding.get("status", "UNKNOWN")).upper()
        severity = str(finding.get("severity", "UNKNOWN")).upper()
        verdict = str(finding.get("verdict", "UNKNOWN")).upper()
        recommendation = str(finding.get("recommendation", "Review this setting."))
        verdict_key = next((key for key in counts if verdict.startswith(key)), "UNKNOWN")
        counts[verdict_key] += 1
        severity_key = next((key for key in severity_counts if severity.startswith(key)), None)
        if severity_key:
            severity_counts[severity_key] += 1
        audit_table.add_row(
            Text(rule), Text(status),
            Text(severity, style=severity_styles.get(severity, "white")),
            Text(verdict, style=verdict_styles.get(verdict_key, "white")),
            Text(recommendation),
        )

    total = len(findings)
    if not findings:
        overall_label = "NO RESULTS — REVIEW REQUIRED"
        overall_style = "bold yellow"
        overall_detail = "No findings were returned. This is not evidence that the configuration is secure."
    elif counts["FAIL"] or severity_counts["CRITICAL"]:
        overall_label = "ACTION REQUIRED"
        overall_style = "bold red"
        overall_detail = "One or more checks failed. Review the failed findings and recommendations below."
    elif counts["UNKNOWN"]:
        overall_label = "INCONCLUSIVE — REVIEW REQUIRED"
        overall_style = "bold yellow"
        overall_detail = "At least one check could not be verified from the local Terraform configuration."
    elif counts["WARN"]:
        overall_label = "NEEDS ATTENTION"
        overall_style = "bold yellow"
        overall_detail = "No failed checks were reported, but one or more warnings need review."
    else:
        overall_label = "ALL AUDITED CHECKS PASSED"
        overall_style = "bold green"
        overall_detail = "Every check reported by this local audit passed; this does not verify live AWS resources."

    record_audit(selected_file, {
        "overall_result": overall_label,
        "counts": counts,
        "severity_counts": severity_counts,
        "finding_count": total,
        "deployment_status": report.get("deployment_status", "Not verified"),
    })

    # Keep the overall assessment and detailed findings; omit the KPI boxes.
    console.print(Panel(
        Group(
            Text(overall_label, style=overall_style, justify="center"),
            Text(overall_detail, style=MUTED, justify="center"),
            Text(f"{total} total finding(s)  •  {severity_counts['CRITICAL']} critical  •  {severity_counts['HIGH']} high", style=WHITE, justify="center"),
        ),
        title="OVERALL SECURITY ASSESSMENT", border_style="red" if counts["FAIL"] or severity_counts["CRITICAL"] else ("yellow" if counts["WARN"] or counts["UNKNOWN"] or not findings else ORANGE),
        box=box.DOUBLE, padding=(1, 2),
    ))

    if findings:
        console.print(audit_table)
    else:
        console.print(Panel(
            "The auditor returned no findings. Check that the selected Terraform files contain the expected resources.",
            title="NO FINDINGS", border_style="yellow",
        ))

    console.print(Panel(
        "Local Terraform configuration only • Live AWS resources and runtime permissions are not verified.",
        title="AUDIT SCOPE", border_style=DIM, box=box.ROUNDED,
    ))


# ----------------------------------------------------------------------------
# Operations
# ----------------------------------------------------------------------------
def run_operation(choice: str):
    labels = {
        "1": "Check prerequisites", "2": "New S3 configuration",
        "3": "Validate Terraform", "4": "Configuration inventory",
        "5": "Security Audit", "6": "Destroy infrastructure",
    }
    operation_header(labels[choice], choice)
    try:
        if choice == "1":
            _, output, error = _capture_call(check_prerequisites)
            if error:
                _show_diagnostics(output)
                result_panel("PREREQUISITE CHECK FAILED", f"{type(error).__name__}: {error}", RED)
            else:
                failed = any(token in output.lower() for token in ("[error]", "[failed]", "not installed", "need attention"))
                if failed:
                    _show_diagnostics(output)
                    result_panel("CHECK NEEDS ATTENTION", "One or more local prerequisites need attention. Review the details above.", AMBER)
                else:
                    result_panel("PREREQUISITES READY", "Python and Terraform checks completed.\nYour local environment is ready.", GREEN)

        elif choice == "2":
            try:
                configuration = collect_s3_configuration()
            except ConfigurationCancelled:
                result_panel("CANCELLED", "No configuration was generated. Returning to the dashboard.", AMBER)
                return
            if configuration is None:
                result_panel("CANCELLED", "No configuration was generated. Returning to the dashboard.", AMBER)
                return

            _stage_screen(
                "Generating local Terraform configuration",
                "Writing the reviewed settings to a local .tf file. No AWS resources will be created.",
            )
            generated_file, generation_output, generation_error = _run_with_progress(
                "Generating Terraform files", generate_terraform, configuration
            )
            if generation_error:
                _show_diagnostics(generation_output)
                result_panel("GENERATION FAILED", f"{type(generation_error).__name__}: {generation_error}", RED)
                return
            if not generated_file:
                _show_diagnostics(generation_output)
                result_panel("GENERATION NOT CONFIRMED", "No output file was returned. Review the details above.", AMBER)
                return

            record_configuration(Path(generated_file))
            target_dir = Path(generated_file).parent
            _stage_screen(
                "Preparing Terraform",
                "Terraform init may download the AWS provider the first time. Later runs are often faster because it is cached.",
            )
            initialized, init_output, init_error = _run_with_progress(
                "Initializing Terraform provider and modules", initialize_terraform, target_dir
            )
            if init_error:
                _show_diagnostics(init_output)
                result_panel("INITIALIZATION FAILED", f"{type(init_error).__name__}: {init_error}", RED)
                return
            if not initialized:
                _show_diagnostics(init_output)
                result_panel(
                    "INITIALIZATION NEEDS ATTENTION",
                    "Terraform could not finish initialization. Check the diagnostics above and retry when connectivity is available.",
                    AMBER,
                )
                return

            _stage_screen(
                "Validating Terraform configuration",
                "Checking syntax and configuration consistency only. This does not plan or deploy infrastructure.",
            )
            valid, validation_output, validation_error = _run_with_progress(
                "Validating generated configuration", validate_terraform, target_dir
            )
            if validation_error:
                _show_diagnostics(validation_output)
                result_panel("VALIDATION FAILED", f"{type(validation_error).__name__}: {validation_error}", RED)
            elif valid:
                result_panel(
                    "CONFIGURATION READY",
                    f"Terraform configuration generated and validated.\n\nFile: {generated_file}\n\nNo AWS resources have been created.",
                    GREEN,
                )
            else:
                _show_diagnostics(generation_output + "\n" + init_output + "\n" + validation_output)
                result_panel(
                    "VALIDATION FAILED",
                    "Review the Terraform diagnostics above.\nNo deployment was started by SecureVault.",
                    RED,
                )

        elif choice == "3":
            _stage_screen(
                "Checking the project's Terraform configuration",
                "Running Terraform initialization and validation only. No AWS resources will be created.",
            )
            valid, output, error = _run_with_progress(
                "Checking Terraform configuration", check_terraform_configuration, TERRAFORM_DIR
            )
            if error:
                _show_diagnostics(output)
                result_panel("VALIDATION FAILED", f"{type(error).__name__}: {error}", RED)
            elif valid:
                result_panel("VALIDATION PASSED", "The project's Terraform configuration passed validation.", GREEN)
            else:
                _show_diagnostics(output)
                result_panel("VALIDATION FAILED", "Review the Terraform diagnostics above.", RED)

        elif choice == "4":
            show_inventory()

        elif choice == "5":
            show_security_audit()

        elif choice == "6":
            result_panel("ACTION DISABLED", "Destruction is not implemented.\nNo destroy command was run and no resources were destroyed.", AMBER)
    except (ValueError, OSError, KeyError) as error:
        result_panel("OPERATION FAILED", f"{type(error).__name__}: {error}", RED)


# ----------------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------------
def main():
    selected = 0
    phase = 0
    try:
        with Live(build_screen(selected, reveal=0), console=console, screen=True,
                  auto_refresh=False, redirect_stdout=False, redirect_stderr=False) as live:
            # Intro: logo wipes in left → right.
            for r in range(0, LOGO_W + 4, 4):
                live.update(build_screen(0, phase=r, reveal=r), refresh=True)
                time.sleep(0.015)

            def tick():
                nonlocal phase
                phase += 3
                live.update(build_screen(selected, phase), refresh=True)

            while True:
                live.update(build_screen(selected, phase), refresh=True)
                choice = read_choice(selected, tick)
                if choice == "UP":
                    selected = (selected - 1) % len(MENU_ITEMS)
                elif choice == "DOWN":
                    selected = (selected + 1) % len(MENU_ITEMS)
                elif choice == "Q":
                    break
                elif choice in ("1", "2", "3", "4", "5", "6"):
                    live.stop()
                    console.clear()
                    run_operation(choice)
                    pause()
                    console.clear()
                    live.start()
                else:
                    selected = (selected + 1) % len(MENU_ITEMS)
        console.print(Text("SecureVault closed.", style=f"bold {ACCENT}"))
    except KeyboardInterrupt:
        console.print(f"\n[{ACCENT}]SecureVault closed.[/]")


if __name__ == "__main__":
    main()