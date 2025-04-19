#!/usr/bin/env python3
"""
Open Codex CLI - Main Entry Point
A lightweight coding agent that runs in your terminal.
"""

import os
import sys
from typing import Optional, List
import asyncio
from pathlib import Path
import click
from rich.console import Console
from dotenv import load_dotenv
from ..core.config import load_config
from ..core.executor import CommandExecutor, ExecutionContext
from .interactive import process_prompt, interactive_mode

console = Console()

# Load environment variables early
load_dotenv()

@click.command()
@click.argument('prompt', required=False)
@click.option('-m', '--model', 
              help='Ollama model to use (default: qwen2.5-coder)',
              default=None)
@click.option('--base-url',
              help='Ollama API base URL (default: http://localhost:11434/api)',
              default=None)
@click.option('-i', '--image', multiple=True,
              help='Path(s) to image files to include as input',
              type=click.Path(exists=True))
@click.option('-d', '--doc',
              help='Path to project documentation file',
              type=click.Path(exists=True))
@click.option('--cwd',
              help='Working directory for commands',
              default=None)
@click.option('--debug', is_flag=True,
              help='Enable debug mode')
@click.option('-q', '--quiet', is_flag=True,
              help='Non-interactive mode that only prints the assistant\'s final output')
@click.option('-c', '--config', 'show_config', is_flag=True,
              help='Open the instructions file in your editor')
@click.option('-a', '--approval-mode',
              type=click.Choice(['suggest', 'auto-edit', 'full-auto'], case_sensitive=False),
              help='Override the approval policy')
@click.option('--auto-edit', is_flag=True,
              help='Automatically approve file edits; still prompt for commands')
@click.option('--full-auto', is_flag=True,
              help='Automatically approve edits and commands when executed in the sandbox')
@click.option('--no-project-doc', is_flag=True,
              help='Do not automatically include the repository\'s \'codex.md\'')
@click.option('--project-doc',
              help='Include an additional markdown file as context',
              type=click.Path(exists=True))
@click.option('--full-stdout', is_flag=True,
              help='Do not truncate stdout/stderr from command outputs')
def cli(prompt: Optional[str], model: Optional[str], base_url: Optional[str],
        image: List[str], doc: Optional[str], cwd: Optional[str], debug: bool,
        quiet: bool, show_config: bool, approval_mode: Optional[str],
        auto_edit: bool, full_auto: bool, no_project_doc: bool,
        project_doc: Optional[str], full_stdout: bool) -> None:
    """
    Open Codex CLI - A lightweight coding agent that runs in your terminal.
    
    If PROMPT is provided, executes that prompt immediately. Otherwise, starts an interactive session.
    """
    try:
        # Load configuration
        config = load_config(
            provider='ollama',  # Always use Ollama
            model=model,
            base_url=base_url,
            disable_project_doc=no_project_doc,
            project_doc_path=project_doc or doc  # Support both --doc and --project-doc
        )
        
        if show_config:
            click.echo("Opening configuration file...")
            editor = os.environ.get('EDITOR', 'vi')
            click.edit(filename=config.instructions_path, editor=editor)
            return
            
        # Setup execution context
        context = ExecutionContext(
            cwd=str(Path(cwd).resolve()) if cwd else str(Path().resolve()),

            env={
                **os.environ,
                'DEBUG': '1' if debug else '0',
                'FULL_STDOUT': '1' if full_stdout else '0'
            },
            writable_paths=[str(Path().resolve())]
        )
        
        # Create executor
        executor = CommandExecutor(
            model=config.model or 'qwen2.5-coder',
            base_url=config.base_url,
            context=context
        )
        
        if quiet:
            # Process single prompt and exit
            if not prompt:
                console.print("[red]Error: Prompt is required in quiet mode[/red]")
                sys.exit(1)
            asyncio.run(_process_prompt(executor, prompt))
        else:
            # Interactive mode
            if prompt:
                # Process initial prompt
                asyncio.run(process_prompt(executor, prompt))
            asyncio.run(interactive_mode(executor))

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        if os.environ.get('DEBUG') == '1':
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    cli()
