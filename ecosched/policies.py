"""Integration baseline. LR/MMT and memory-aware policies belong to D3.

select_host(request, hosts, now) returns a host ID or None to defer the FIFO head.
Optional on_tick(now, hosts, running) returns Migration objects. Snapshots expose
no runtime, expected completion, original placement, or future trace measurements.
"""


class FirstFit:
    name = "first_fit"

    def select_host(self, request, hosts, now):
        # Reuse powered hosts before waking another, preserving file-order ties.
        for state in ("active", "waking", "sleep"):
            for host in hosts:
                if host.state == state and host.fits(request):
                    return host.host_id
        return None
