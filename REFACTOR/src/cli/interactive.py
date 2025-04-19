"""
Interactive mode and prompt processing for the CLI.
"""

import asyncio
from typing import Optional
import click
from rich.console import Console
from rich.markdown import Markdown
from ..core.executor import CommandExecutor, ExecResult

console = Console()

async def process_prompt(executor: CommandExecutor, prompt: str) -> None:
    """Process a single prompt and display results.
    
    Args:
        executor: Command executor to use
        prompt: Prompt to process
    """
    try:
        async for response in executor.process_message(prompt):
            if isinstance(response, str):
                # Regular text response
                console.print(Markdown(response))
            else:
                # Command execution result
                await _display_exec_result(response)
                
    except Exception as e:
        console.print(f"[red]Error processing prompt: {e}[/red]")
        if executor.context.env.get('DEBUG') == '1':
            import traceback
            console.print(traceback.format_exc())

async def interactive_mode(executor: CommandExecutor) -> None:
    """Run in interactive mode.
    
    Args:
        executor: Command executor to use
    """
    console.print("[bold]Open Codex CLI - Interactive Mode[/bold]")
    console.print("Type 'exit' or press Ctrl+C to quit\n")
    
    history = []
    
    while True:
        try:
            # Get input with history support
            prompt = click.prompt(
                ">",
                type=str,
                default="",
                show_default=False
            )
            
            if not prompt:
                continue
                
            if prompt.lower() in ('exit', 'quit'):
                break
                
            # Add to history
            history.append(prompt)
            
            # Process the prompt
            await process_prompt(executor, prompt)
            console.print()  # Add spacing between interactions
            
        except click.Abort:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if executor.context.env.get('DEBUG') == '1':
                import traceback
                console.print(traceback.format_exc())

async def _display_exec_result(result: ExecResult) -> None:
    """Display a command execution result.
    
    Args:
        result: Execution result to display
    """
    if result.error:
        console.print(f"[red]Error: {result.error}[/red]")
        
    if result.stdout:
        # Check if we should show full output
        if (len(result.stdout) > 1000 and 
            not result.context.env.get('FULL_STDOUT') == '1'):
            # Show truncated output
            console.print(
                result.stdout[:500] + 
                "\n... [dim](output truncated, use --full-stdout to see all)[/dim] ...\n" +
                result.stdout[-500:]
            )
        else:
            console.print(result.stdout, end="")
            
    if result.stderr:
        console.print(f"[yellow]{result.stderr}[/yellow]", end="")
