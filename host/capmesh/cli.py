import asyncio
import click
import json
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .transport.ble import BLETransportAdapter
from .transport.http import HTTPTransportAdapter
from .provider.local_provider import LaptopProvider
from .protocol.models import InvocationRequest
from .protocol.auth import generate_nonce, create_auth_payload, verify_receipt
from .agent.policy import AgentPolicyEngine
from .payment.verifier import SolanaDevnetVerifier, MockPaymentVerifier

console = Console()

def get_engine(solana: bool = False):
    verifier = SolanaDevnetVerifier() if solana else MockPaymentVerifier()
    transports = [BLETransportAdapter(), LaptopProvider()]
    return AgentPolicyEngine(transports=transports, payment_verifier=verifier)

@click.group()
def main():
    """CapMesh — Machine Capability Marketplace CLI."""
    pass

@main.command()
@click.option("--timeout", default=4.0, help="Scan duration in seconds")
def scan(timeout: float):
    """Scan for all nearby CapMesh capability providers (BLE + Local)."""
    console.print(f"[bold cyan]Scanning for CapMesh providers ({timeout}s)...[/bold cyan]")
    engine = get_engine()

    results = asyncio.run(engine.discover_all(timeout=timeout))
    if not results:
        console.print("[yellow]No CapMesh providers found.[/yellow]")
        return

    for m, transport in results:
        console.print(f"\n[bold green]{m.device_id}[/bold green] [dim]({m.address} via {transport.transport_name})[/dim]")
        for cap in m.capabilities:
            console.print(f"  [bold]{cap.id}[/bold]: {cap.description}")
            console.print(f"  price: {cap.pricing.amount} {cap.pricing.currency}")

@main.command()
@click.argument("device_id")
def manifest(device_id: str):
    """Retrieve full manifest JSON from a provider."""
    engine = get_engine()
    results = asyncio.run(engine.discover_all(timeout=4.0))
    for m, _ in results:
        if m.device_id == device_id or m.address == device_id:
            console.print(Panel(m.to_json(), title=f"Manifest: {m.device_id}", expand=False))
            return
    console.print(f"[red]Device '{device_id}' not found.[/red]")

@main.command()
@click.argument("device_id")
@click.argument("capability")
@click.option("--duration", default=3, help="Duration in seconds (for led.blink)")
@click.option("--count", default=5, help="Number of blink cycles")
@click.option("--data", default="CapMesh payload test", help="Data argument (for compute/echo)")
@click.option("--auth", default="hmac-sha256", type=click.Choice(["mock", "hmac-sha256"]), help="Authorization type")
@click.option("--nonce", default=None, type=int, help="Explicit nonce (for replay testing)")
@click.option("--expiration", default=None, type=int, help="Explicit expiration epoch (for expiration testing)")
def invoke(device_id: str, capability: str, duration: int, count: int, data: str, auth: str, nonce: int, expiration: int):
    """Invoke a capability on a remote provider."""
    engine = get_engine()
    results = asyncio.run(engine.discover_all(timeout=4.0))
    chosen_pair = next(((m, t) for m, t in results if m.device_id == device_id or m.address == device_id), None)

    if not chosen_pair:
        console.print(f"[red]Device '{device_id}' not found.[/red]")
        return

    manifest, transport = chosen_pair
    req_nonce = nonce if nonce is not None else generate_nonce()
    now_epoch = int(time.time())
    req_expiration = expiration if expiration is not None else (now_epoch + 300)
    request_id = f"req-{int(time.time() * 1000) % 100000000:08x}"

    auth_payload = create_auth_payload(
        request_id=request_id,
        capability=capability,
        nonce=req_nonce,
        expiration=req_expiration,
        auth_type=auth
    )

    params = {"duration": duration, "count": count}
    if capability in ("compute.sha256", "storage.echo"):
        params = {"data": data, "payload": data}

    req = InvocationRequest(
        request_id=request_id,
        device_id=manifest.device_id,
        capability=capability,
        parameters=params,
        nonce=req_nonce,
        timestamp=now_epoch,
        expiration=req_expiration,
        authorization=auth_payload
    )

    console.print(f"\n[bold cyan]Invoking {capability} on {manifest.device_id} via {transport.transport_name}...[/bold cyan]")
    console.print(f"Request ID: [dim]{request_id}[/dim] (Nonce: {req_nonce}, Auth: {auth})")

    receipt = asyncio.run(transport.invoke(manifest.device_id, req))

    if receipt.status == "success":
        console.print(f"[bold green]✓ Execution Successful![/bold green]")
        table = Table(show_header=False, box=None)
        table.add_row("Provider:", f"[green]{receipt.provider}[/green]")
        table.add_row("Capability:", receipt.capability)
        table.add_row("Execution Time:", f"{receipt.started_at}s -> {receipt.completed_at}s")
        table.add_row("Result:", json.dumps(receipt.result))
        table.add_row("Signature:", f"[dim]{receipt.receipt_signature}[/dim]")

        sig_valid = verify_receipt(receipt)
        table.add_row("Receipt Verified:", "[green]VALID (HMAC-SHA256)[/green]" if sig_valid else "[yellow]UNVERIFIED[/yellow]")
        console.print(table)
    else:
        console.print(f"[bold red]✗ Execution Failed![/bold red]")
        console.print(f"Error Code: [red]{receipt.error.get('code') if receipt.error else 'UNKNOWN'}[/red]")
        console.print(f"Message: {receipt.error.get('message') if receipt.error else 'No error message'}")

@main.command()
@click.argument("intent")
@click.option("--max-price", default=0.01, type=float, help="Maximum price willing to pay")
@click.option("--solana-tx", default=None, help="Solana Devnet transaction signature for payment settlement")
def policy_run(intent: str, max_price: float, solana_tx: str):
    """
    Autonomous agent capability routing.
    Example: capmesh policy-run visual_signal --max-price 0.01
    """
    console.print(f"[bold cyan]Agent Policy Engine evaluating goal: '{intent}' (Budget: <= ${max_price})...[/bold cyan]")
    engine = get_engine(solana=bool(solana_tx))

    result = asyncio.run(engine.select_and_invoke(
        capability_or_tag=intent,
        max_price=max_price,
        solana_tx_sig=solana_tx
    ))

    if result.get("status") == "success":
        console.print(f"\n[bold green]✓ Policy Solved & Executed![/bold green]")
        table = Table(show_header=False, box=None)
        table.add_row("Chosen Provider:", f"[bold cyan]{result['chosen_provider']}[/bold cyan] ({result['transport']})")
        table.add_row("Selected Capability:", result["capability"])
        table.add_row("Agreed Price:", f"{result['price']} {result['currency']}")
        receipt = result["receipt"]
        table.add_row("Execution Result:", json.dumps(receipt.result))
        table.add_row("Receipt Signature:", f"[dim]{receipt.receipt_signature}[/dim]")
        table.add_row("Cryptographic Proof:", "[bold green]VERIFIED AUTHENTIC[/bold green]" if result["receipt_verified"] else "[red]UNVERIFIED[/red]")
        console.print(table)
    else:
        console.print(f"[bold red]Policy Execution Failed: {result.get('message')}[/bold red]")

if __name__ == "__main__":
    main()
